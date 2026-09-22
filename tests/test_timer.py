import unittest
import tempfile
import time
import math
from pathlib import Path

from focusflow.db.database import Database
from focusflow.db.repository import Repository
from focusflow.core.timer import PomodoroEngine, TimerState


class TestTimerEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_timer.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)
        # Use short test durations: focus 2s, short 1s, long 3s, interval 2
        self.engine = PomodoroEngine(
            repository=self.repo,
            focus_duration=2,
            short_break_duration=1,
            long_break_duration=3,
            long_break_interval=2,
            auto_start_breaks=True,
            auto_start_focus=False,
        )

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_initial_state(self):
        self.assertEqual(self.engine.state, TimerState.IDLE)
        self.assertEqual(self.engine.remaining_seconds, 2)
        self.assertEqual(self.engine.total_duration, 2)

    def test_start_pause_resume_stop(self):
        tick_updates = []
        self.engine.subscribe_tick(lambda rem, tot, frac: tick_updates.append((rem, tot, frac)))

        self.engine.start()
        self.assertEqual(self.engine.state, TimerState.RUNNING_FOCUS)
        self.assertTrue(len(tick_updates) > 0)

        # Pause
        self.engine.pause()
        self.assertEqual(self.engine.state, TimerState.PAUSED_FOCUS)

        # Resume
        self.engine.resume()
        self.assertEqual(self.engine.state, TimerState.RUNNING_FOCUS)

        # Stop
        self.engine.stop(save_interrupted=False)
        self.assertEqual(self.engine.state, TimerState.IDLE)
        self.assertEqual(self.engine.remaining_seconds, 2)

    def test_timer_completion_and_break_transition(self):
        completed_events = []
        self.engine.subscribe_completed(lambda st, task: completed_events.append((st, task)))

        # Create task and assign to timer
        task = self.repo.create_task("Write Tests", estimated_pomodoros=3)
        self.engine.start(task_id=task.id)

        # Mock time elapsed by overriding target_monotonic
        self.engine._target_monotonic = time.monotonic() - 1.0
        self.engine.tick()

        # Should have completed focus and auto-started short break
        self.assertEqual(len(completed_events), 1)
        self.assertEqual(completed_events[0][0], TimerState.RUNNING_FOCUS)
        self.assertEqual(completed_events[0][1], task.id)
        self.assertEqual(self.engine.state, TimerState.RUNNING_SHORT_BREAK)
        self.assertEqual(self.engine.remaining_seconds, 1)

        # Verify task was updated in database
        updated_task = self.repo.get_task(task.id)
        self.assertEqual(updated_task.completed_pomodoros, 1)

        # Finish break
        self.engine._target_monotonic = time.monotonic() - 1.0
        self.engine.tick()
        self.assertEqual(len(completed_events), 2)
        self.assertEqual(completed_events[1][0], TimerState.RUNNING_SHORT_BREAK)
        # auto_start_focus is False, so should be PAUSED_FOCUS ready for next round
        self.assertEqual(self.engine.state, TimerState.PAUSED_FOCUS)
        self.assertEqual(self.engine.remaining_seconds, 2)

    def test_long_break_after_interval(self):
        # Set cycles today to 1, next completion will make it 2 (which equals interval 2)
        self.engine.completed_cycles_today = 1
        self.engine.start()
        self.engine._target_monotonic = time.monotonic() - 1.0
        self.engine.tick()

        # Should transition to long break
        self.assertEqual(self.engine.completed_cycles_today, 2)
        self.assertEqual(self.engine.state, TimerState.RUNNING_LONG_BREAK)
        self.assertEqual(self.engine.total_duration, 3)

    def test_timer_drift_resilience(self):
        """Verify that monotonic clock arithmetic prevents cumulative tick drift."""
        import math
        self.engine.start()
        start_mono = self.engine._target_monotonic - 2.0
        # 1.2 seconds elapsed: 0.8s remain -> ceil is 1s
        now_mono = start_mono + 1.2
        rem = int(math.ceil(self.engine._target_monotonic - now_mono))
        self.assertEqual(rem, 1)

        # 1.95 seconds elapsed: 0.05s remain -> ceil is 1s
        now_mono = start_mono + 1.95
        rem = int(math.ceil(self.engine._target_monotonic - now_mono))
        self.assertEqual(rem, 1)

        # 2.0 seconds elapsed: 0.0s remain -> 0s
        now_mono = start_mono + 2.0
        rem = int(math.ceil(self.engine._target_monotonic - now_mono))
    def test_normal_countdown_and_ui_freeze(self):
        """Simulate normal tick progression and recovery after multi-second UI freeze."""
        # 1500 second (25 minute) focus session
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        start_mono = eng._target_monotonic - 1500.0

        # Normal ticks: 1s passes -> 1499s remain
        eng._target_monotonic = start_mono + 1500.0
        eng._last_tick_monotonic = start_mono
        # Tick at t = 1.0s
        eng._target_monotonic = start_mono + 1500.0
        now_fake = start_mono + 1.0
        rem = int(math.ceil(eng._target_monotonic - now_fake))
        self.assertEqual(rem, 1499)

        # UI Freeze: 5 seconds pass with no ticks
        now_fake_freeze = start_mono + 6.0
        rem_after_freeze = int(math.ceil(eng._target_monotonic - now_fake_freeze))
        # Timer immediately reflects the exact elapsed 6 seconds: 1494 seconds
        self.assertEqual(rem_after_freeze, 1494)

    def test_pause_period_does_not_count_as_focus(self):
        """Paused period must be completely isolated and not reduce remaining focus time."""
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        # Simulate 300 seconds elapsed (5 mins) -> 1200 remain
        eng._target_monotonic = time.monotonic() + 1200
        eng.pause()
        self.assertEqual(eng.state, TimerState.PAUSED_FOCUS)
        self.assertEqual(eng.remaining_seconds, 1200)

        # Simulate user pausing for 1 hour (3600 seconds)
        # When resuming, target_monotonic is reset to now + remaining_seconds
        eng.resume()
        self.assertEqual(eng.state, TimerState.RUNNING_FOCUS)
        self.assertEqual(eng.remaining_seconds, 1200)
        # Target monotonic is 1200 seconds in the future from current time
        remaining_now = int(math.ceil(eng._target_monotonic - time.monotonic()))
        self.assertEqual(remaining_now, 1200)

    def test_system_suspend_detection(self):
        """Verify that when wall clock advances significantly more than monotonic clock, suspend is detected."""
        from datetime import datetime, timedelta
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()

        # Simulate system suspend: wall clock advances by 1800s (30 mins), while monotonic advanced only 1s
        eng._last_tick_wall = datetime.now() - timedelta(seconds=1800)
        eng._last_tick_monotonic = time.monotonic() - 1.0

        eng.tick()
        # Timer should detect suspend and pause to preserve state
        self.assertTrue(eng._suspend_detected)
        self.assertTrue(eng.state.is_paused)

    def test_application_restart_recovery(self):
        """Test that active/paused state persists in database and is recovered upon new engine launch."""
        task = self.repo.create_task("Persisted Task")
        eng1 = PomodoroEngine(self.repo, focus_duration=1500)
        eng1.start(task_id=task.id)
        # Simulate 700 seconds elapsed (800 seconds remain)
        eng1._target_monotonic = time.monotonic() + 800
        eng1.pause()  # Persists state as paused with 800s left

        # Simulate application close and restart: instantiate new engine with same repository
        eng2 = PomodoroEngine(self.repo, focus_duration=1500)
        self.assertEqual(eng2.state, TimerState.PAUSED_FOCUS)
        self.assertEqual(eng2.active_task_id, task.id)
        self.assertEqual(eng2.remaining_seconds, 800)


if __name__ == "__main__":
    unittest.main()

