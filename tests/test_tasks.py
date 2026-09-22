"""Unit tests for FocusFlow TaskManager."""

import unittest
import tempfile
from pathlib import Path
from datetime import date, timedelta

from focusflow.db.database import Database
from focusflow.db.repository import Repository
from focusflow.core.task_manager import TaskManager


class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_tasks.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)
        self.manager = TaskManager(self.repo)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_create_task_and_validation(self):
        task = self.manager.create(
            title="Design System Tray",
            description="StatusNotifierItem with custom menu",
            priority="high",
            estimated_pomodoros=3,
            tags="gui,linux",
        )
        self.assertEqual(task.title, "Design System Tray")
        self.assertEqual(task.priority, "high")

        # Validation: empty title
        with self.assertRaises(ValueError):
            self.manager.create(title="   ")

        # Validation: invalid date format
        with self.assertRaises(ValueError):
            self.manager.create(title="Test", due_date="09-22-2026")

    def test_toggle_complete(self):
        task = self.manager.create(title="Setup Autostart")
        self.assertEqual(task.status, "pending")

        completed = self.manager.toggle_complete(task.id)
        self.assertEqual(completed.status, "completed")
        self.assertIsNotNone(completed.completed_at)

        # Toggle back
        reopened = self.manager.toggle_complete(task.id)
        self.assertEqual(reopened.status, "pending")
        self.assertIsNone(reopened.completed_at)

    def test_filtering_and_sorting(self):
        today_str = date.today().isoformat()
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

        t1 = self.manager.create("High Pri Task", priority="high", due_date=today_str)
        t2 = self.manager.create("Med Pri Tomorrow", priority="medium", due_date=tomorrow_str)
        t3 = self.manager.create("Low Pri Completed", priority="low")
        self.manager.toggle_complete(t3.id)

        # Filter by today
        today_tasks = self.manager.list(filter_mode="today")
        self.assertTrue(any(t.id == t1.id for t in today_tasks))

        # Filter by upcoming
        upcoming = self.manager.list(filter_mode="upcoming")
        self.assertTrue(any(t.id == t2.id for t in upcoming))

        # Filter by high_priority
        high_pri = self.manager.list(filter_mode="high_priority")
        self.assertTrue(any(t.id == t1.id for t in high_pri))

        # Filter by completed
        completed = self.manager.list(filter_mode="completed")
        self.assertTrue(any(t.id == t3.id for t in completed))

    def test_tag_extraction(self):
        self.manager.create("Task A", tags="frontend, python")
        self.manager.create("Task B", tags="backend, python, linux")
        tags = self.manager.get_all_tags()
        self.assertEqual(tags, ["backend", "frontend", "linux", "python"])


if __name__ == "__main__":
    unittest.main()
