"""Unit tests for FocusFlow database layer."""

import unittest
import tempfile
from pathlib import Path
from datetime import date, datetime, timedelta

from focusflow.db.database import Database
from focusflow.db.repository import Repository, Task


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_database_initialization_and_migrations(self):
        self.assertTrue(self.db_path.exists())
        cursor = self.db.execute("SELECT version FROM schema_migrations;")
        versions = [row[0] for row in cursor.fetchall()]
        self.assertIn(1, versions)

    def test_task_crud_lifecycle(self):
        # Create
        task = self.repo.create_task(
            title="Implement Core Engine",
            description="Build drift-free Pomodoro timer",
            priority="high",
            estimated_pomodoros=4,
            tags="code,python",
            due_date="2026-09-25",
        )
        self.assertIsNotNone(task.id)
        self.assertEqual(task.title, "Implement Core Engine")
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.estimated_pomodoros, 4)
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.tag_list, ["code", "python"])

        # Read
        fetched = self.repo.get_task(task.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, task.title)

        # Update
        updated = self.repo.update_task(
            task.id,
            status="completed",
            description="Completed ahead of time",
        )
        self.assertEqual(updated.status, "completed")
        self.assertIsNotNone(updated.completed_at)
        self.assertEqual(updated.description, "Completed ahead of time")

        # List & Filter
        completed_tasks = self.repo.list_tasks(status="completed")
        self.assertEqual(len(completed_tasks), 1)
        pending_tasks = self.repo.list_tasks(status="pending")
        self.assertEqual(len(pending_tasks), 0)

        # Delete
        deleted = self.repo.delete_task(task.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_task(task.id))

    def test_session_and_daily_stats_rollup(self):
        today_str = date.today().isoformat()
        now = datetime.now().isoformat()
        end = (datetime.now() + timedelta(minutes=25)).isoformat()

        # Record completed focus session
        session = self.repo.record_session(
            task_id=None,
            session_type="focus",
            start_time=now,
            end_time=end,
            duration_seconds=1500,
            status="completed",
        )
        self.assertIsNotNone(session.id)
        self.assertEqual(session.status, "completed")

        # Verify daily stats aggregation
        stats = self.repo.get_daily_stats(today_str)
        self.assertEqual(stats.total_focus_seconds, 1500)
        self.assertEqual(stats.pomodoros_completed, 1)
        self.assertEqual(stats.longest_session_seconds, 1500)

        # Record second session (interrupted)
        self.repo.record_session(
            task_id=None,
            session_type="focus",
            start_time=now,
            end_time=end,
            duration_seconds=300,
            status="interrupted",
        )
        stats2 = self.repo.get_daily_stats(today_str)
        self.assertEqual(stats2.total_focus_seconds, 1800)
        self.assertEqual(stats2.pomodoros_completed, 1)
        self.assertEqual(stats2.interruptions_count, 1)

    def test_preferences_key_value(self):
        self.repo.set_preference("focus_duration", 1800)
        self.assertEqual(self.repo.get_preference("focus_duration"), 1800)
        self.repo.set_preference("auto_start_breaks", False)
        self.assertFalse(self.repo.get_preference("auto_start_breaks"))


if __name__ == "__main__":
    unittest.main()
