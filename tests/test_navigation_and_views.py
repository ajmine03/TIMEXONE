"""
Automated unit tests for FocusFlow navigation routing, dedicated TimerView,
dedicated CalendarView, WeeklyBarChart label rendering, and SpinBox arrows.
"""

import sys
import unittest
from datetime import date, timedelta
from PyQt6.QtWidgets import QApplication, QSpinBox, QLabel
from PyQt6.QtCore import Qt

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.database import Database
from focusflow.db.repository import Repository
from focusflow.ui.main_window import MainWindow
from focusflow.ui.timer_view import TimerView
from focusflow.ui.calendar_view import CalendarView
from focusflow.ui.components.charts import WeeklyBarChart
from focusflow.ui.stats_view import StatsView
from focusflow.ui.styles import DARK_THEME, LIGHT_THEME
from focusflow.config import ASSETS_DIR


import tempfile
from pathlib import Path


class TestNavigationAndViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_nav.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)
        self.engine = PomodoroEngine(focus_duration=1500, short_break_duration=300, long_break_duration=900)
        self.task_manager = TaskManager(self.repo)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_01_main_window_has_7_nav_items_and_stack_screens(self):
        """MainWindow should have 7 navigation items mapped to 7 distinct stacked views."""
        mw = MainWindow(self.engine, self.task_manager, self.repo)
        stats = StatsView(self.repo)
        mw.set_stats_view(stats)

        # Expected nav items
        expected_keys = ["dashboard", "tasks", "timer", "analytics", "calendar", "history", "settings"]
        self.assertEqual(list(mw.nav_buttons.keys()), expected_keys)
        self.assertEqual(mw.stack.count(), 7)

        # Verify switching to each nav item updates stack index properly
        mw.show_dashboard()
        self.assertEqual(mw.stack.currentIndex(), 0)

        mw.show_tasks()
        self.assertEqual(mw.stack.currentIndex(), 1)

        mw.show_timer()
        self.assertEqual(mw.stack.currentIndex(), 2)

        mw.show_analytics()
        self.assertEqual(mw.stack.currentIndex(), 3)

        mw.show_calendar()
        self.assertEqual(mw.stack.currentIndex(), 4)

        mw.show_history()
        self.assertEqual(mw.stack.currentIndex(), 5)

        mw.show_settings()
        self.assertEqual(mw.stack.currentIndex(), 6)

    def test_02_tasks_view_refresh_does_not_crash(self):
        """Clicking tasks view must not raise AttributeError or crash the app."""
        mw = MainWindow(self.engine, self.task_manager, self.repo)
        # Call refresh_tasks directly and through navigation
        mw.tasks_view.refresh_tasks()
        mw.tasks_view.refresh_task_list()
        mw._on_nav_clicked(1, "tasks")
        self.assertEqual(mw.stack.currentIndex(), 1)

    def test_03_timer_view_lifecycle_and_modes(self):
        """TimerView should reflect engine mode switches and state updates."""
        tv = TimerView(self.engine, self.task_manager, self.repo)
        self.assertEqual(tv.btn_pomo.isChecked(), True)

        # Switch to short break
        tv._on_mode_switched("short_break")
        self.assertTrue(self.engine.state.is_break)
        self.assertEqual(tv.btn_short.isChecked(), True)

        # Switch to long break
        tv._on_mode_switched("long_break")
        self.assertEqual(tv.btn_long.isChecked(), True)

        # Switch back to pomo
        tv._on_mode_switched("focus")
        self.assertEqual(tv.btn_pomo.isChecked(), True)

    def test_04_calendar_view_date_selection_and_sessions(self):
        """CalendarView should query month sessions and display day inspection."""
        # Create a task and session
        t = self.task_manager.create_task("Algorithm Study")
        today_str = date.today().isoformat()
        self.repo.record_session(
            task_id=t.id,
            duration_seconds=1500,
            session_type="focus",
            status="completed",
            start_time=f"{today_str}T10:00:00",
            end_time=f"{today_str}T10:25:00",
        )

        cv = CalendarView(self.repo)
        cv.refresh_calendar()

        # Today should be marked in session_days
        self.assertIn(date.today().day, cv.grid.session_days)

        # Day inspector should have the session
        cv._on_date_selected(date.today())
        self.assertIn("25m", cv.card_day_focus.findChild(QLabel, "val").text())
        self.assertEqual(cv.card_day_pomos.findChild(QLabel, "val").text(), "1")

    def test_05_weekly_bar_chart_handles_wide_labels(self):
        """WeeklyBarChart should render multi-character dates like 'Wed 21', 'Sun 25' without crashing."""
        chart = WeeklyBarChart()
        chart.resize(400, 200)
        data = [
            ("Tue 20", 1.5),
            ("Wed 21", 2.0),
            ("Thu 22", 0.5),
            ("Fri 23", 3.0),
            ("Sat 24", 0.0),
            ("Sun 25", 1.8),
            ("Mon 26", 2.2),
        ]
        chart.set_data(data)
        chart.show()
        self.app.processEvents()
        pix = chart.grab()
        self.assertFalse(pix.isNull())
        self.assertEqual(pix.width(), 400)

    def test_06_spinbox_arrows_stylesheet_and_assets(self):
        """SpinBox stylesheet must have up-arrow and down-arrow images that resolve to existing SVG assets."""
        self.assertTrue((ASSETS_DIR / "arrow_up.svg").exists())
        self.assertTrue((ASSETS_DIR / "arrow_down.svg").exists())

        self.assertIn("QSpinBox::up-arrow", DARK_THEME)
        self.assertIn("QSpinBox::down-arrow", DARK_THEME)
        self.assertIn("arrow_up.svg", DARK_THEME)
        self.assertIn("arrow_down.svg", DARK_THEME)

        # Verify spinbox renders cleanly with DARK_THEME
        sb = QSpinBox()
        sb.setStyleSheet(DARK_THEME)
        sb.setValue(25)
        sb.resize(180, 40)
        sb.show()
        self.app.processEvents()
        pix = sb.grab()
        self.assertFalse(pix.isNull())


if __name__ == "__main__":
    unittest.main()
