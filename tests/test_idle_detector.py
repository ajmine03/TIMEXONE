"""Unit tests for FocusFlow IdleDetector."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from focusflow.db.database import Database
from focusflow.db.repository import Repository
from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.tracker import IdleDetector


class TestIdleDetector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test_idle.db")
        self.repo = Repository(self.db)
        self.engine = PomodoroEngine(self.repo)
        self.detector = IdleDetector(self.repo, self.engine)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_idle_detector_initialization(self):
        self.assertIsNotNone(self.detector)

    def test_idle_action_pause(self):
        # Set preference to pause when idle
        self.repo.set_preference("idle_action", "pause")
        self.repo.set_preference("idle_threshold_seconds", 300)

        # Mock get_idle_seconds to return 400 (exceeded)
        self.detector.get_idle_seconds = MagicMock(return_value=400)

        # Start focus timer
        self.engine.start()
        self.assertEqual(self.engine.state, TimerState.RUNNING_FOCUS)

        # Trigger check
        self.detector.check_idle()

        # Engine should have been paused automatically
        self.assertEqual(self.engine.state, TimerState.PAUSED_FOCUS)


if __name__ == "__main__":
    unittest.main()
