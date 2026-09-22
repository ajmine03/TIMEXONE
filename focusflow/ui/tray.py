"""
System Tray Integration for FocusFlow.
Displays live timer status, active task, and quick controls via QSystemTrayIcon.
"""

from typing import Optional, Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject

from focusflow.config import APP_NAME, ICON_PATH
from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager


class SystemTrayManager(QObject):
    """Manages the Linux system tray icon and dynamic context menu."""

    # Signals to communicate with MainWindow and FloatingTimer
    show_main_window_requested = pyqtSignal()
    toggle_floating_timer_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(
        self,
        engine: PomodoroEngine,
        task_manager: TaskManager,
        parent=None,
    ):
        super().__init__(parent)
        self.engine = engine
        self.task_manager = task_manager

        self.tray_icon = QSystemTrayIcon(parent)
        if ICON_PATH.exists():
            self.tray_icon.setIcon(QIcon(str(ICON_PATH)))
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("alarm"))

        self.tray_icon.setToolTip(f"{APP_NAME} - Idle")

        self._create_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Hook into engine events
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)

    def _create_menu(self):
        self.menu = QMenu()

        # Status Headers (Disabled actions serving as informative display)
        self.title_action = QAction(f"<b>{APP_NAME}</b>", self.menu)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)

        self.task_action = QAction("Task: None", self.menu)
        self.task_action.setEnabled(False)
        self.menu.addAction(self.task_action)

        self.timer_action = QAction("Timer: 25:00", self.menu)
        self.timer_action.setEnabled(False)
        self.menu.addAction(self.timer_action)

        self.menu.addSeparator()

        # Timer Controls
        self.play_pause_action = QAction("Start Pomodoro", self.menu)
        self.play_pause_action.triggered.connect(self._on_play_pause_triggered)
        self.menu.addAction(self.play_pause_action)

        self.stop_action = QAction("Stop Timer", self.menu)
        self.stop_action.triggered.connect(self.engine.stop)
        self.stop_action.setEnabled(False)
        self.menu.addAction(self.stop_action)

        self.floating_toggle_action = QAction("Show Floating Timer", self.menu)
        self.floating_toggle_action.triggered.connect(self.toggle_floating_timer_requested.emit)
        self.menu.addAction(self.floating_toggle_action)

        self.menu.addSeparator()

        # Navigation
        self.dashboard_action = QAction("Open Dashboard", self.menu)
        self.dashboard_action.triggered.connect(self.show_main_window_requested.emit)
        self.menu.addAction(self.dashboard_action)

        self.settings_action = QAction("Settings", self.menu)
        self.settings_action.triggered.connect(self.open_settings_requested.emit)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # Quit
        self.quit_action = QAction("Quit", self.menu)
        self.quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def show(self):
        self.tray_icon.show()

    def hide(self):
        self.tray_icon.hide()

    def set_floating_visible_label(self, is_visible: bool):
        """Update floating toggle menu text based on current visibility."""
        text = "Hide Floating Timer" if is_visible else "Show Floating Timer"
        self.floating_toggle_action.setText(text)

    def _on_play_pause_triggered(self):
        self.engine.toggle_play_pause()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_main_window_requested.emit()

    def _format_time(self, seconds: int) -> str:
        mins, secs = divmod(max(0, seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def _on_tick(self, remaining: int, total: int, fraction: float):
        time_str = self._format_time(remaining)
        status = "Focus" if self.engine.state.is_focus else ("Break" if self.engine.state.is_break else "Idle")
        if self.engine.state.is_paused:
            status += " (Paused)"

        self.timer_action.setText(f"Timer: {time_str} ({status})")
        self.tray_icon.setToolTip(f"{APP_NAME} - {time_str} ({status})")

    def _on_state_changed(self, new_state: TimerState):
        # Update Task Label
        task_title = "None"
        if self.engine.active_task_id:
            task = self.task_manager.get(self.engine.active_task_id)
            if task:
                task_title = task.title
                if len(task_title) > 24:
                    task_title = task_title[:21] + "..."
        self.task_action.setText(f"Task: {task_title}")

        # Update Play/Pause Button
        if new_state == TimerState.IDLE:
            self.play_pause_action.setText("Start Pomodoro")
            self.stop_action.setEnabled(False)
        elif new_state.is_running:
            self.play_pause_action.setText("Pause Timer")
            self.stop_action.setEnabled(True)
        elif new_state.is_paused:
            self.play_pause_action.setText("Resume Timer")
            self.stop_action.setEnabled(True)
