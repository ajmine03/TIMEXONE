"""
Unit and regression tests for FocusFlow FloatingTimerWidget.
Verifies drag position persistence, multi-monitor bounds safety, and mode toggling.
"""

import unittest
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QSize, QRect

from focusflow.db.database import Database
from focusflow.db.repository import Repository
from focusflow.core.timer import PomodoroEngine
from focusflow.core.task_manager import TaskManager
from focusflow.ui.floating_timer import FloatingTimerWidget


class TestFloatingTimer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Offscreen Qt Application for headless execution
        cls.app = QApplication.instance() or QApplication(["focusflow", "-platform", "offscreen"])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_floating.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)
        self.engine = PomodoroEngine(self.repo)
        self.task_manager = TaskManager(self.repo)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_position_persistence(self):
        # Set arbitrary saved coordinates
        self.repo.set_preference("floating_x", 350)
        self.repo.set_preference("floating_y", 220)

        widget = FloatingTimerWidget(self.engine, self.task_manager, self.repo)
        self.assertEqual(widget.repo.get_preference("floating_x"), 350)
        self.assertEqual(widget.repo.get_preference("floating_y"), 220)

        # Move and save new position
        widget.move(480, 310)
        widget.save_position()

        self.assertEqual(self.repo.get_preference("floating_x"), 480)
        self.assertEqual(self.repo.get_preference("floating_y"), 310)
        widget.close()

    def test_multi_monitor_safety_offscreen_fallback(self):
        # Coordinates that are guaranteed to be off-screen
        offscreen_pos = QPoint(99999, 99999)
        size = QSize(175, 110)

        safe_pos = FloatingTimerWidget.ensure_on_screen(offscreen_pos, size)
        # Should NOT return (99999, 99999) if any screen exists
        screens = self.app.screens()
        if screens:
            primary_avail = screens[0].availableGeometry()
            self.assertTrue(primary_avail.contains(safe_pos))
            self.assertNotEqual(safe_pos.x(), 99999)
            self.assertNotEqual(safe_pos.y(), 99999)

    def test_multi_monitor_safety_onscreen_preserved(self):
        screens = self.app.screens()
        if screens:
            avail = screens[0].availableGeometry()
            valid_pos = QPoint(avail.x() + 100, avail.y() + 100)
            size = QSize(175, 110)

            result_pos = FloatingTimerWidget.ensure_on_screen(valid_pos, size)
            self.assertEqual(result_pos.x(), valid_pos.x())
            self.assertEqual(result_pos.y(), valid_pos.y())

    def test_compact_mode_toggle(self):
        widget = FloatingTimerWidget(self.engine, self.task_manager, self.repo)
        initial_mode = widget.is_compact

        widget.toggle_compact_mode()
        self.assertEqual(widget.is_compact, not initial_mode)
        self.assertEqual(self.repo.get_preference("floating_compact"), not initial_mode)
        widget.close()

    def test_auto_hide_controls_toggle(self):
        widget = FloatingTimerWidget(self.engine, self.task_manager, self.repo)
        initial_autohide = widget.auto_hide_controls

        widget.toggle_auto_hide_controls()
        self.assertEqual(widget.auto_hide_controls, not initial_autohide)
        self.assertEqual(self.repo.get_preference("floating_auto_hide_controls"), not initial_autohide)
        widget.close()


if __name__ == "__main__":
    unittest.main()
