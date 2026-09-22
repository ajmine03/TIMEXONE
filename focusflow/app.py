"""
FocusFlow Application Orchestrator.
Initializes database, domain engines, UI views, tray, shortcuts, and event loops.
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt

from focusflow.config import (
    APP_NAME, APP_ID, APP_VERSION, APP_DESCRIPTION,
    DEFAULT_DB_PATH, LOG_FILE_PATH
)
import logging.handlers

# Setup persistent file logging alongside stderr
handlers = [logging.StreamHandler(sys.stderr)]
try:
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=1024 * 1024 * 2, backupCount=3, encoding="utf-8"
    )
    handlers.append(file_handler)
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)


class FocusFlowApp:
    """Master application coordinator."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH, test_mode: bool = False):
        self.test_mode = test_mode
        self.db = Database(db_path)
        self.repo = Repository(self.db)

        # Core Engines
        prefs = self.repo.get_all_preferences()
        self.engine = PomodoroEngine(
            repository=self.repo,
            focus_duration=int(prefs.get("focus_duration", 1500)),
            short_break_duration=int(prefs.get("short_break", 300)),
            long_break_duration=int(prefs.get("long_break", 900)),
            long_break_interval=int(prefs.get("long_break_interval", 4)),
            auto_start_breaks=bool(prefs.get("auto_start_breaks", True)),
            auto_start_focus=bool(prefs.get("auto_start_focus", False)),
        )
        self.task_manager = TaskManager(self.repo)
        self.sound = SoundPlayer()
        self.notify = NotificationService(self.sound)
        self.reminders = ReminderService(self.repo, self.notify, self.engine)
        self.idle_detector = IdleDetector(self.repo, self.engine)
        self.data_manager = DataManager(self.repo)

        # UI Components
        self.main_window = MainWindow(self.engine, self.task_manager, self.repo)
        self.floating_timer = FloatingTimerWidget(self.engine, self.task_manager, self.repo)
        self.tray = SystemTrayManager(self.engine, self.task_manager)

        # Views for stack
        self.stats_view = StatsView(self.repo)
        self.settings_view = SettingsView(self.repo, self.engine, self.notify, self.sound)

        self.main_window.set_stats_view(self.stats_view)
        self.main_window.set_settings_view(self.settings_view)

        # Apply saved theme
        saved_theme = prefs.get("theme", "dark")
        self.main_window.apply_theme(saved_theme)

        self._wire_signals()
        self._setup_heartbeat_timer()

    def _wire_signals(self):
        # 1. Floating Timer Toggles
        self.main_window.toggle_floating_requested.connect(self._toggle_floating_timer)
        self.tray.toggle_floating_timer_requested.connect(self._toggle_floating_timer)
        self.floating_timer.visibility_changed.connect(self.tray.set_floating_visible_label)
        self.floating_timer.open_dashboard_requested.connect(self.main_window.show_dashboard)

        # 2. Tray Navigation
        self.tray.show_main_window_requested.connect(self.main_window.show_dashboard)
        self.tray.open_settings_requested.connect(self.main_window.show_settings)
        self.tray.quit_requested.connect(self.quit)

        # 3. Settings updates
        self.settings_view.theme_changed.connect(self.main_window.apply_theme)
        self.settings_view.durations_changed.connect(self.main_window.dashboard_view.refresh_dashboard)

        # 4. Engine events -> Notifications & Auto-show
        self.engine.subscribe_completed(self._on_session_completed)
        self.engine.subscribe_state_changed(self._on_engine_state_changed)

        # 5. Inactivity return handling
        self.idle_detector.returned_from_idle.connect(self._on_user_returned_from_idle)

    def _on_user_returned_from_idle(self, idle_seconds: int):
        if self.test_mode or not self.engine.state.is_focus:
            return

        from focusflow.ui.components.idle_dialog import IdleReturnDialog
        parent_win = self.main_window if self.main_window.isVisible() else self.floating_timer
        dlg = IdleReturnDialog(idle_seconds=idle_seconds, parent=parent_win)
        dlg.exec()

        action = dlg.selected_action
        if action == IdleReturnDialog.KEEP_TIME:
            if self.engine.state.is_paused:
                self.engine.resume()
        elif action == IdleReturnDialog.DISCARD_AND_PAUSE:
            self.engine.adjust_remaining_time(idle_seconds)
            if self.engine.state.is_running:
                self.engine.pause()
        elif action == IdleReturnDialog.DISCARD_AND_RESUME:
            self.engine.adjust_remaining_time(idle_seconds)
            if self.engine.state.is_paused:
                self.engine.resume()
        elif action == IdleReturnDialog.DISCARD_SESSION:
            self.engine.stop(save_interrupted=False)

    def _setup_heartbeat_timer(self):
        """1-second tick loop driving timer engine, idle checks, and reminders."""
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_heartbeat)
        self.timer.start()

    def _on_heartbeat(self):
        self.engine.tick()
        self.reminders.check_reminders()
        self.idle_detector.check_idle()

    def _toggle_floating_timer(self):
        if self.floating_timer.isVisible():
            self.floating_timer.hide()
        else:
            self.floating_timer.show()
            self.floating_timer.raise_()

    def _on_engine_state_changed(self, new_state: TimerState):
        # Auto-show floating timer if configured
        if new_state == TimerState.RUNNING_FOCUS:
            auto_show = self.repo.get_preference("floating_auto_show", True)
            if auto_show and not self.floating_timer.isVisible():
                self.floating_timer.show()
                self.floating_timer.raise_()

    def _on_session_completed(self, state: TimerState, task_id):
        play_sound = self.repo.get_preference("sound_enabled", True)
        notif_enabled = self.repo.get_preference("notifications_enabled", True)

        if state == TimerState.RUNNING_FOCUS:
            task_title = None
            if task_id:
                t = self.task_manager.get(task_id)
                if t:
                    task_title = t.title

            mins = self.engine.focus_duration // 60
            if notif_enabled:
                self.notify.notify_pomodoro_completed(task_title, mins)
            elif play_sound:
                self.sound.play_chime()

            # Refresh views
            self.main_window.dashboard_view.refresh_dashboard()
            self.main_window.history_view.refresh_history()
            self.stats_view.refresh_stats()

        elif state in (TimerState.RUNNING_SHORT_BREAK, TimerState.RUNNING_LONG_BREAK):
            if notif_enabled:
                self.notify.notify_break_completed()
            elif play_sound:
                self.sound.play_chime()

    def run(self, start_minimized: bool = False, floating_only: bool = False):
        """Launch the application windows."""
        # Check first run wizard
        first_run_done = self.repo.get_preference("first_run_completed", False)
        if not first_run_done and not self.test_mode:
            wizard = FirstRunWizard(self.repo)
            wizard.exec()
            # Reload preferences in case changed in wizard
            self.settings_view.load_settings()

        self.tray.show()

        if floating_only:
            self.floating_timer.show()
        elif not start_minimized:
            self.main_window.show()

    def quit(self):
        self.timer.stop()
        self.floating_timer.close()
        self.main_window.close()
        self.tray.hide()
        QApplication.quit()


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} - {APP_DESCRIPTION}")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument("--minimized", action="store_true", help="Start minimized to the system tray")
    parser.add_argument("--floating-only", action="store_true", help="Start only the floating timer widget")
    parser.add_argument("--test-mode", action="store_true", help="Run in test verification mode (skip wizard)")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite database file path")
    args = parser.parse_args()

    # Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setDesktopFileName(APP_ID)

    db_path = Path(args.db_path) if args.db_path else DEFAULT_DB_PATH
    focusflow_app = FocusFlowApp(db_path=db_path, test_mode=args.test_mode)

    if args.test_mode:
        # Test mode execution: verify startup, tick once, and exit 0
        focusflow_app.run(start_minimized=True)
        focusflow_app._on_heartbeat()
        logger.info("FocusFlow sanity test passed successfully.")
        return 0

    focusflow_app.run(start_minimized=args.minimized, floating_only=args.floating_only)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
