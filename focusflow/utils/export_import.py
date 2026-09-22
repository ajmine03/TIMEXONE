"""
Data Export, Import, and Backup Utilities for FocusFlow.
Supports CSV, JSON, and SQLite database snapshots.
"""

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from focusflow.db.repository import Repository, Task, PomodoroSession


class DataManager:
    """Manages CSV/JSON exports, imports, and backup operations."""

    def __init__(self, repository: Repository):
        self.repo = repository

    # -------------------------------------------------------------------------
    # CSV Export / Import
    # -------------------------------------------------------------------------
    def export_sessions_csv(self, output_file: Path) -> int:
        """Export all recorded pomodoro sessions to CSV."""
        sessions = self.repo.list_sessions(limit=100000)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "start_time", "end_time", "duration_seconds", "session_type", "status", "task_id", "task_title"])
            for s in sessions:
                task_title = ""
                if s.task_id:
                    t = self.repo.get_task(s.task_id)
                    if t:
                        task_title = t.title
                writer.writerow([
                    s.id, s.date, s.start_time, s.end_time,
                    s.duration_seconds, s.session_type, s.status,
                    s.task_id or "", task_title
                ])
        return len(sessions)

    def export_tasks_csv(self, output_file: Path) -> int:
        """Export all tasks to CSV."""
        tasks = self.repo.list_tasks()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "title", "description", "status", "priority",
                "estimated_pomodoros", "completed_pomodoros", "due_date",
                "tags", "total_focus_seconds", "created_at", "completed_at"
            ])
            for t in tasks:
                writer.writerow([
                    t.id, t.title, t.description, t.status, t.priority,
                    t.estimated_pomodoros, t.completed_pomodoros, t.due_date or "",
                    t.tags, t.total_focus_seconds, t.created_at, t.completed_at or ""
                ])
        return len(tasks)

    # -------------------------------------------------------------------------
    # JSON Export / Import
    # -------------------------------------------------------------------------
    def export_all_json(self, output_file: Path) -> Dict[str, int]:
        """Export entire database (tasks, sessions, preferences) to JSON."""
        tasks = [t.to_dict() for t in self.repo.list_tasks()]
        sessions = [s.to_dict() for s in self.repo.list_sessions(limit=100000)]
        prefs = self.repo.get_all_preferences()

        payload = {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
            "tasks": tasks,
            "sessions": sessions,
            "preferences": prefs,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return {"tasks": len(tasks), "sessions": len(sessions)}

    def import_all_json(self, input_file: Path) -> Dict[str, int]:
        """Import tasks and sessions from a FocusFlow JSON export."""
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported_tasks = 0
        imported_sessions = 0

        # Import Tasks
        for t_dict in data.get("tasks", []):
            existing = self.repo.get_task(t_dict["id"])
            if not existing:
                with self.repo.db.transaction():
                    self.repo.db.execute(
                        """
                        INSERT INTO tasks (
                            id, title, description, created_at, updated_at,
                            completed_at, due_date, priority, status,
                            estimated_pomodoros, completed_pomodoros, tags, total_focus_seconds
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            t_dict["id"], t_dict["title"], t_dict.get("description", ""),
                            t_dict["created_at"], t_dict["updated_at"], t_dict.get("completed_at"),
                            t_dict.get("due_date"), t_dict.get("priority", "medium"),
                            t_dict.get("status", "pending"), t_dict.get("estimated_pomodoros", 1),
                            t_dict.get("completed_pomodoros", 0), t_dict.get("tags", ""),
                            t_dict.get("total_focus_seconds", 0)
                        )
                    )
                imported_tasks += 1

        # Import Sessions
        for s_dict in data.get("sessions", []):
            with self.repo.db.transaction():
                # Check if session already exists
                cur = self.repo.db.execute("SELECT id FROM pomodoro_sessions WHERE id = ?;", (s_dict["id"],))
                if not cur.fetchone():
                    self.repo.db.execute(
                        """
                        INSERT INTO pomodoro_sessions (
                            id, task_id, session_type, start_time, end_time,
                            duration_seconds, status, date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            s_dict["id"], s_dict.get("task_id"), s_dict["session_type"],
                            s_dict["start_time"], s_dict["end_time"], s_dict["duration_seconds"],
                            s_dict["status"], s_dict["date"]
                        )
                    )
                    imported_sessions += 1

        return {"tasks": imported_tasks, "sessions": imported_sessions}

    # -------------------------------------------------------------------------
    # Database Backup
    # -------------------------------------------------------------------------
    def backup_database(self, destination_dir: Path) -> Path:
        """Create a timestamped SQLite database copy."""
        destination_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = destination_dir / f"focusflow_backup_{timestamp}.db"
        shutil.copy2(str(self.repo.db.db_path), str(target_file))
        return target_file
