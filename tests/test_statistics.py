"""Unit tests for FocusFlow statistics and analytics calculations."""

import unittest
import tempfile
from pathlib import Path
from datetime import date, datetime, timedelta

from focusflow.db.database import Database
from focusflow.db.repository import Repository


class TestStatistics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_stats.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_stats_range_and_fill_missing_dates(self):
        today = date.today()
        d1 = (today - timedelta(days=2)).isoformat()
        d2 = today.isoformat()

        # Add stats for d1
        self.repo._update_daily_stats(d1, focus_seconds=1800, pomodoros=1, interruptions=0)
        # Add stats for d2
        self.repo._update_daily_stats(d2, focus_seconds=3600, pomodoros=2, interruptions=1)

        # Range query covers 3 days: d1, d1+1, d2
        stats = self.repo.get_stats_range(d1, d2)
        self.assertEqual(len(stats), 3)
        self.assertEqual(stats[0].total_focus_seconds, 1800)
        self.assertEqual(stats[1].total_focus_seconds, 0) # Filled missing date with 0
        self.assertEqual(stats[2].total_focus_seconds, 3600)
        self.assertEqual(stats[2].interruptions_count, 1)

    def test_time_distribution_bucketing(self):
        today_str = date.today().isoformat()

        # Morning session: 09:00
        start_morning = f"{today_str}T09:00:00"
        end_morning = f"{today_str}T09:25:00"
        self.repo.record_session(
            task_id=None,
            session_type="focus",
            start_time=start_morning,
            end_time=end_morning,
            duration_seconds=1500,
            status="completed",
        )

        # Afternoon session: 14:00
        start_afternoon = f"{today_str}T14:00:00"
        end_afternoon = f"{today_str}T14:25:00"
        self.repo.record_session(
            task_id=None,
            session_type="focus",
            start_time=start_afternoon,
            end_time=end_afternoon,
            duration_seconds=1500,
            status="completed",
        )

        # Evening session: 20:00
        start_evening = f"{today_str}T20:00:00"
        end_evening = f"{today_str}T20:25:00"
        self.repo.record_session(
            task_id=None,
            session_type="focus",
            start_time=start_evening,
            end_time=end_evening,
            duration_seconds=1500,
            status="completed",
        )

        dist = self.repo.get_time_distribution(days=7)
        self.assertEqual(dist["Morning"], 1500)
        self.assertEqual(dist["Afternoon"], 1500)
        self.assertEqual(dist["Evening"], 1500)


if __name__ == "__main__":
    unittest.main()
