"""Unit tests for FocusFlow export and import."""

import unittest
import tempfile
from pathlib import Path
from datetime import datetime

from focusflow.db.database import Database
from focusflow.db.repository import Repository
from focusflow.utils.export_import import DataManager


class TestExportImport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_data.db"
        self.db = Database(self.db_path)
        self.repo = Repository(self.db)
        self.manager = DataManager(self.repo)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_export_and_import_roundtrip(self):
        # Create test task and session
        t = self.repo.create_task("Export Task", description="Export test", priority="high", tags="tag1,tag2")
        now = datetime.now().isoformat()
        self.repo.record_session(
            task_id=t.id,
            session_type="focus",
            start_time=now,
            end_time=now,
            duration_seconds=1500,
            status="completed",
        )

        # 1. Export CSV
        csv_path = Path(self.temp_dir.name) / "sessions.csv"
        count = self.manager.export_sessions_csv(csv_path)
        self.assertEqual(count, 1)
        self.assertTrue(csv_path.exists())

        # 2. Export JSON
        json_path = Path(self.temp_dir.name) / "backup.json"
        counts = self.manager.export_all_json(json_path)
        self.assertEqual(counts["tasks"], 1)
        self.assertEqual(counts["sessions"], 1)
        self.assertTrue(json_path.exists())

        # 3. Create a fresh second database and import
        db2_path = Path(self.temp_dir.name) / "test_data_2.db"
        db2 = Database(db2_path)
        repo2 = Repository(db2)
        manager2 = DataManager(repo2)

        import_counts = manager2.import_all_json(json_path)
        self.assertEqual(import_counts["tasks"], 1)
        self.assertEqual(import_counts["sessions"], 1)

        imported_task = repo2.get_task(t.id)
        self.assertIsNotNone(imported_task)
        self.assertEqual(imported_task.title, "Export Task")
        self.assertEqual(imported_task.priority, "high")
        db2.close()

    def test_database_backup(self):
        backup_dir = Path(self.temp_dir.name) / "backups"
        backup_file = self.manager.backup_database(backup_dir)
        self.assertTrue(backup_file.exists())
        self.assertTrue(backup_file.stat().st_size > 0)

    def test_rolling_database_backups(self):
        backup_dir = Path(self.temp_dir.name) / "rolling_backups"
        # Create 7 backups
        for _ in range(7):
            self.manager.create_rolling_backup(backup_dir=backup_dir, max_backups=5)

        backups = list(backup_dir.glob("focusflow_backup_*.db"))
        self.assertEqual(len(backups), 5)


if __name__ == "__main__":
    unittest.main()
