"""
Comprehensive Master Accounting & Analytics Test Suite.
Validates all 26 authoritative requirements:
Timer engine accuracy, partial sessions, pause/resume, break accounting,
crash recovery, midnight crossing, database migration V2,
AnalyticsService metrics, task consistency, and CSV exports.
"""

import unittest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
import time

from focusflow.db.database import Database
from focusflow.db.schema import INITIAL_SCHEMA_V1, MIGRATIONS
from focusflow.db.repository import Repository, PomodoroSession, Task
from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.analytics_service import AnalyticsService
from focusflow.utils.export_import import DataManager


class TestMasterAccounting(unittest.TestCase):
    """Test suite covering authoritative session accounting and analytics."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_master.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)
        self.analytics = AnalyticsService(self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    # 1. 25-minute focus session completed naturally
    def test_01_natural_focus_completion(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        # Simulate ticking down to 0
        eng.remaining_seconds = 0
        eng.tick()

        self.assertTrue(eng.state.is_break)
        eng.stop()
        self.assertEqual(eng.state, TimerState.IDLE)
        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.pomodoros_completed, 1)
        self.assertEqual(today_stats.total_focus_seconds, 1500)

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "completed")
        self.assertEqual(history[0].duration_seconds, 1500)
        self.assertEqual(history[0].planned_duration_seconds, 1500)

    # 2. 25-minute focus session stopped after 15 minutes (900s)
    def test_02_focus_session_stopped_partial(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 600  # 900s elapsed
        eng.stop(save_interrupted=True)

        self.assertEqual(eng.state, TimerState.IDLE)
        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        # Does NOT increment completed Pomodoro count!
        self.assertEqual(today_stats.pomodoros_completed, 0)
        # DOES credit 900 seconds of focus time!
        self.assertEqual(today_stats.total_focus_seconds, 900)

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "stopped")
        self.assertEqual(history[0].duration_seconds, 900)
        self.assertEqual(history[0].planned_duration_seconds, 1500)

    # 3. Stopping after < 60 seconds preserves exact seconds
    def test_03_stopping_short_partial(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 1455  # exactly 45s elapsed
        eng.stop(save_interrupted=True)

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.total_focus_seconds, 45)
        self.assertEqual(today_stats.pomodoros_completed, 0)

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].duration_seconds, 45)

    # 4. Stopping after 0 seconds records nothing
    def test_04_stopping_zero_elapsed_records_nothing(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.stop(save_interrupted=True)

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.total_focus_seconds, 0)
        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 0)

    # 5. Pausing at minute 10, resuming, completing: excludes paused time
    def test_05_pause_resume_completion(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 900  # 10m elapsed
        eng.pause()
        self.assertTrue(eng.state.is_paused)

        # Time passes during pause
        time.sleep(0.01)

        eng.resume()
        self.assertTrue(eng.state.is_running)
        self.assertEqual(eng.remaining_seconds, 900)

        # Finish session
        eng.remaining_seconds = 0
        eng.tick()

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.pomodoros_completed, 1)
        self.assertEqual(today_stats.total_focus_seconds, 1500)

    # 6. Pausing at minute 10, then stopping
    def test_06_pause_then_stop(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 900  # 10m elapsed
        eng.pause()
        eng.stop(save_interrupted=True)

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.pomodoros_completed, 0)
        self.assertEqual(today_stats.total_focus_seconds, 600)

    # 7. Restarting after 12 minutes (720s) saves partial as stopped and resets
    def test_07_restart_saves_partial_as_stopped(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 780  # 720s elapsed
        eng.restart()

        # Engine is reset to running with full duration
        self.assertEqual(eng.total_duration, 1500)
        self.assertEqual(eng.remaining_seconds, 1500)

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "stopped")
        self.assertEqual(history[0].duration_seconds, 720)

    # 8. Skipping focus after 8 minutes (480s)
    def test_08_skip_focus_saves_partial_as_stopped(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 1020  # 480s elapsed
        eng.skip()

        # Transitioned to break
        self.assertTrue(eng.state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK, TimerState.IDLE))
        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "stopped")
        self.assertEqual(history[0].duration_seconds, 480)

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.pomodoros_completed, 0)
        self.assertEqual(today_stats.total_focus_seconds, 480)

    # 9. Short break completed credits daily break seconds, not focus
    def test_09_short_break_completed(self):
        eng = PomodoroEngine(self.repo, short_break_duration=300)
        eng.switch_mode("short_break", auto_start=True)
        eng.remaining_seconds = 0
        eng.tick()

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.pomodoros_completed, 0)
        self.assertEqual(today_stats.total_focus_seconds, 0)
        self.assertEqual(today_stats.total_break_seconds, 300)

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].session_type, "short_break")
        self.assertEqual(history[0].duration_seconds, 300)

    # 10. Short break stopped after 2 minutes (120s)
    def test_10_short_break_stopped_partial(self):
        eng = PomodoroEngine(self.repo, short_break_duration=300)
        eng.switch_mode("short_break", auto_start=True)
        eng.remaining_seconds = 180  # 120s elapsed
        eng.stop(save_interrupted=True)

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.total_focus_seconds, 0)
        self.assertEqual(today_stats.total_break_seconds, 120)

    # 11. Long break completed
    def test_11_long_break_completed(self):
        eng = PomodoroEngine(self.repo, long_break_duration=900)
        eng.switch_mode("long_break", auto_start=True)
        eng.remaining_seconds = 0
        eng.tick()

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.total_break_seconds, 900)
        self.assertEqual(today_stats.total_focus_seconds, 0)

    # 12. Skipping a break does not record unelapsed break time
    def test_12_skip_break_preserves_only_elapsed(self):
        eng = PomodoroEngine(self.repo, short_break_duration=300)
        eng.switch_mode("short_break", auto_start=True)
        eng.remaining_seconds = 240  # 60s elapsed
        eng.skip()

        today_stats = self.repo.get_daily_stats(date.today().isoformat())
        self.assertEqual(today_stats.total_break_seconds, 60)

    # 13. Midnight crossing allocates duration across consecutive calendar days
    def test_13_midnight_crossing_allocation(self):
        # Session from 23:50 to 00:10 (20 min = 1200s: 600s on Day 1, 600s on Day 2)
        start_time = "2026-10-20T23:50:00"
        end_time = "2026-10-21T00:10:00"

        self.repo.record_session(
            task_id=None,
            session_type="focus",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=1200,
            status="completed",
            planned_duration_seconds=1500,
        )

        day1_stats = self.repo.get_daily_stats("2026-10-20")
        day2_stats = self.repo.get_daily_stats("2026-10-21")

        self.assertEqual(day1_stats.total_focus_seconds, 600)
        self.assertEqual(day2_stats.total_focus_seconds, 600)

        # Single session record preserved
        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].duration_seconds, 1200)

    # 14. Crash / unexpected exit during focus recovery
    def test_14_crash_recovery_interrupted(self):
        # Save running state in persisted_timer_state preference
        past_start = (datetime.now() - timedelta(minutes=20)).isoformat()
        last_tick = (datetime.now() - timedelta(minutes=16)).isoformat()
        state_data = {
            "state": "running_focus",
            "remaining_seconds": 900,
            "total_duration": 1500,
            "session_start_wall": past_start,
            "last_tick_wall": last_tick,
            "active_task_id": None,
        }
        self.repo.set_preference("persisted_timer_state", state_data)

        eng = PomodoroEngine(self.repo, focus_duration=1500)
        self.assertEqual(eng.state, TimerState.IDLE)

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "interrupted")
        self.assertEqual(history[0].duration_seconds, 600)

    # 15. Idempotent natural completion
    def test_15_idempotent_natural_completion(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        eng.remaining_seconds = 0
        eng.tick()
        # Call tick again
        eng.tick()

        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)

    # 16. Task association credits total_focus_seconds on task
    def test_16_task_association_focus_time(self):
        task = self.repo.create_task("Test Task A", estimated_pomodoros=3)
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start(task_id=task.id)
        eng.remaining_seconds = 0
        eng.tick()

        updated_task = self.repo.get_task(task.id)
        self.assertEqual(updated_task.total_focus_seconds, 1500)
        self.assertEqual(updated_task.completed_pomodoros, 1)

    # 17. Task completion sets completed_at and preserves focus time
    def test_17_task_completion_status(self):
        task = self.repo.create_task("Test Task B")
        self.repo.record_task_focus_time(task.id, 1200)
        self.repo.complete_task(task.id)

        updated_task = self.repo.get_task(task.id)
        self.assertEqual(updated_task.status, "completed")
        self.assertTrue(updated_task.is_completed)
        self.assertEqual(updated_task.total_focus_seconds, 1200)
        self.assertIsNotNone(updated_task.completed_at)

    # 18. Deleted task retains session history without FK error
    def test_18_deleted_task_session_history(self):
        task = self.repo.create_task("Temporary Task")
        self.repo.record_session(
            task_id=task.id,
            session_type="focus",
            start_time="2026-10-22T10:00:00",
            end_time="2026-10-22T10:25:00",
            duration_seconds=1500,
            status="completed",
        )
        deleted = self.repo.delete_task(task.id)
        self.assertTrue(deleted)

        # Session history is preserved 100%
        history = self.repo.get_session_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].duration_seconds, 1500)

        # Analytics breakdown runs cleanly without error and includes the focus time
        breakdown = self.analytics.get_task_breakdown(date(2026, 10, 22), date(2026, 10, 22))
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0].focus_seconds, 1500)

    # 19. Analytics period summary equals sum of focus durations
    def test_19_analytics_period_summary_sum(self):
        d1 = date(2026, 10, 10)
        d2 = date(2026, 10, 12)
        self.repo.record_session(None, "focus", f"{d1}T10:00:00", f"{d1}T10:25:00", 1500, "completed")
        self.repo.record_session(None, "focus", f"{d2}T14:00:00", f"{d2}T14:15:00", 900, "stopped")

        summary = self.analytics.get_period_summary(d1, d2)
        self.assertEqual(summary.total_focus_seconds, 2400)
        self.assertEqual(summary.completed_pomodoros, 1)
        self.assertEqual(summary.stopped_sessions, 1)

    # 20. Calendar-day vs active-day average
    def test_20_calendar_vs_active_day_average(self):
        # 3 day period: Oct 10, 11, 12. Only Oct 10 and 12 have focus.
        d1 = date(2026, 10, 10)
        d2 = date(2026, 10, 12)
        self.repo.record_session(None, "focus", "2026-10-10T10:00:00", "2026-10-10T10:30:00", 1800, "completed")
        self.repo.record_session(None, "focus", "2026-10-12T10:00:00", "2026-10-12T10:30:00", 1800, "completed")

        summary = self.analytics.get_period_summary(d1, d2)
        self.assertEqual(summary.days_in_period, 3)
        self.assertEqual(summary.active_days_count, 2)
        self.assertEqual(summary.total_focus_seconds, 3600)
        # Calendar-day avg: 3600 / 3 = 1200
        self.assertEqual(summary.calendar_day_average_seconds, 1200.0)
        # Active-day avg: 3600 / 2 = 1800
        self.assertEqual(summary.active_day_average_seconds, 1800.0)

    # 21. Empty date range zero division safe
    def test_21_empty_range_safe(self):
        d1 = date(2026, 1, 1)
        d2 = date(2026, 1, 5)
        summary = self.analytics.get_period_summary(d1, d2)
        self.assertEqual(summary.total_focus_seconds, 0)
        self.assertEqual(summary.calendar_day_average_seconds, 0.0)
        self.assertEqual(summary.active_day_average_seconds, 0.0)
        self.assertIsNone(summary.comparison_pct)

    # 22. Daily trend contains 0-activity slots
    def test_22_daily_trend_slots(self):
        d1 = date(2026, 5, 1)
        d2 = date(2026, 5, 5)
        trend = self.analytics.get_daily_trend(d1, d2)
        self.assertEqual(len(trend), 5)
        for item in trend:
            self.assertEqual(item.focus_seconds, 0)

    # 23. Task breakdown percentages
    def test_23_task_breakdown_percentage(self):
        t1 = self.repo.create_task("Alpha")
        t2 = self.repo.create_task("Beta")
        d = date(2026, 7, 1)

        self.repo.record_session(t1.id, "focus", f"{d}T10:00:00", f"{d}T10:30:00", 1800, "completed")
        self.repo.record_session(t2.id, "focus", f"{d}T11:00:00", f"{d}T11:30:00", 600, "stopped")

        breakdown = self.analytics.get_task_breakdown(d, d)
        self.assertEqual(len(breakdown), 2)
        self.assertEqual(breakdown[0].task_title, "Alpha")
        self.assertAlmostEqual(breakdown[0].pct_of_total, 75.0, places=1)
        self.assertEqual(breakdown[1].task_title, "Beta")
        self.assertAlmostEqual(breakdown[1].pct_of_total, 25.0, places=1)

    # 24. Migration V2 idempotency
    def test_24_migration_v2_idempotency(self):
        # Create a fresh DB with schema V1 directly
        legacy_db_file = Path(self.temp_dir.name) / "legacy.db"
        conn = sqlite3.connect(legacy_db_file)
        conn.executescript(INITIAL_SCHEMA_V1)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT NOT NULL
            );
        """)
        conn.execute("INSERT INTO schema_migrations VALUES (1, datetime('now'), 'V1');")
        conn.commit()
        conn.close()

        # Opening Database on legacy DB will automatically run migration 2
        test_db = Database(legacy_db_file)

        # Verify columns exist
        cursor = test_db.connection.cursor()
        cursor.execute("PRAGMA table_info(pomodoro_sessions)")
        p_cols = [r[1] for r in cursor.fetchall()]
        self.assertIn("planned_duration_seconds", p_cols)

        cursor.execute("PRAGMA table_info(daily_statistics)")
        d_cols = [r[1] for r in cursor.fetchall()]
        self.assertIn("total_break_seconds", d_cols)

        # Run again to ensure idempotency
        test_db._run_migrations()
        test_db.close()

    # 25. CSV exports
    def test_25_csv_exports(self):
        d = date(2026, 8, 1)
        self.repo.record_session(None, "focus", f"{d}T10:00:00", f"{d}T10:25:00", 1500, "completed")
        mgr = DataManager(self.repo)

        daily_csv = Path(self.temp_dir.name) / "daily.csv"
        task_csv = Path(self.temp_dir.name) / "tasks.csv"

        count1 = mgr.export_daily_totals_csv(daily_csv, d, d)
        self.assertEqual(count1, 1)
        self.assertTrue(daily_csv.exists())
        content = daily_csv.read_text()
        self.assertIn("focus_seconds", content)
        self.assertIn("1500", content)

        count2 = mgr.export_task_focus_csv(task_csv, d, d)
        self.assertEqual(count2, 1)
        self.assertTrue(task_csv.exists())
        content2 = task_csv.read_text()
        self.assertIn("General Focus", content2)

    # 26. Monotonic timer property synchronization
    def test_26_monotonic_property_sync(self):
        eng = PomodoroEngine(self.repo, focus_duration=1500)
        eng.start()
        self.assertTrue(eng.state.is_running)

        # Setting remaining_seconds updates target_monotonic
        eng.remaining_seconds = 1000
        now_mono = time.monotonic()
        diff = eng._target_monotonic - now_mono
        self.assertAlmostEqual(diff, 1000, delta=1.0)


if __name__ == "__main__":
    unittest.main()
