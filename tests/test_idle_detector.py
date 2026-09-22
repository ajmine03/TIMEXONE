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

    def test_idle_return_signal(self):
        self.repo.set_preference("idle_action", "pause")
        self.repo.set_preference("idle_threshold_seconds", 300)

        returned_payload = []
        self.detector.returned_from_idle.connect(lambda sec: returned_payload.append(sec))

        self.engine.start()

        # 1. User becomes idle (exceeds 300s)
        self.detector.get_idle_seconds = MagicMock(return_value=350)
        self.detector.check_idle()
        self.assertEqual(len(returned_payload), 0)

        # 2. Inactive time increases
        self.detector.get_idle_seconds = MagicMock(return_value=420)
        self.detector.check_idle()
        self.assertEqual(len(returned_payload), 0)

        # 3. User returns (idle time drops to 0)
        self.detector.get_idle_seconds = MagicMock(return_value=0)
        self.detector.check_idle()

        # Signal should have fired with the max accumulated idle duration
        self.assertEqual(len(returned_payload), 1)
        self.assertEqual(returned_payload[0], 420)


if __name__ == "__main__":
    unittest.main()
