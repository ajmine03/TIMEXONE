"""
Data Access Layer (Repository) for FocusFlow.
Handles models, queries, aggregations, and transactions.
"""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from focusflow.db.database import Database
from focusflow.config import DEFAULT_PREFERENCES


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"          # 'low', 'medium', 'high'
    status: str = "pending"           # 'pending', 'in_progress', 'completed'
    estimated_pomodoros: int = 1
    completed_pomodoros: int = 0
    tags: str = ""                    # comma-separated string
    total_focus_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def tag_list(self) -> List[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]


@dataclass
class PomodoroSession:
    id: str
    task_id: Optional[str]
    session_type: str                  # 'focus', 'short_break', 'long_break'
    start_time: str
    end_time: str
    duration_seconds: int
    status: str                        # 'completed', 'interrupted'
    date: str                          # YYYY-MM-DD

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyStats:
    date: str
    total_focus_seconds: int = 0
    pomodoros_completed: int = 0
    tasks_completed: int = 0
    longest_session_seconds: int = 0
    interruptions_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Repository:
    """Provides high-level data access for FocusFlow."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else Database()

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------
    def create_task(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium",
        estimated_pomodoros: int = 1,
        tags: str = "",
    ) -> Task:
        now = datetime.now().isoformat()
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title.strip(),
            description=description.strip(),
            created_at=now,
            updated_at=now,
            completed_at=None,
            due_date=due_date,
            priority=priority.lower(),
            status="pending",
            estimated_pomodoros=max(1, estimated_pomodoros),
            completed_pomodoros=0,
            tags=tags.strip(),
            total_focus_seconds=0,
        )

        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO tasks (
                    id, title, description, created_at, updated_at,
                    completed_at, due_date, priority, status,
                    estimated_pomodoros, completed_pomodoros, tags, total_focus_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task.id, task.title, task.description, task.created_at,
                    task.updated_at, task.completed_at, task.due_date,
                    task.priority, task.status, task.estimated_pomodoros,
                    task.completed_pomodoros, task.tags, task.total_focus_seconds,
                ),
            )
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        cursor = self.db.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Task(**dict(row))

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None

        now = datetime.now().isoformat()
        kwargs["updated_at"] = now

        # If marking complete, set completed_at
        if "status" in kwargs:
            if kwargs["status"] == "completed" and not task.completed_at:
                kwargs["completed_at"] = now
            elif kwargs["status"] != "completed":
                kwargs["completed_at"] = None

        fields = []
        values = []
        for k, v in kwargs.items():
            if hasattr(task, k):
                fields.append(f"{k} = ?")
                values.append(v)
                setattr(task, k, v)

        if fields:
            values.append(task_id)
            query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?;"
            with self.db.transaction():
                self.db.execute(query, tuple(values))

        return task

    def delete_task(self, task_id: str) -> bool:
        with self.db.transaction():
            cursor = self.db.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            return cursor.rowcount > 0

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        due_filter: Optional[str] = None,  # 'today', 'upcoming', 'overdue'
        sort_by: str = "created_desc",      # 'priority', 'due_date', 'created_asc', 'created_desc', 'remaining_pomodoros'
    ) -> List[Task]:
        clauses = []
        params = []

        if status:
            clauses.append("status = ?")
            params.append(status)

        if priority:
            clauses.append("priority = ?")
            params.append(priority)

        if tag:
            clauses.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if search:
            clauses.append("(title LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        today_str = date.today().isoformat()
        if due_filter == "today":
            clauses.append("due_date = ?")
            params.append(today_str)
        elif due_filter == "upcoming":
            clauses.append("due_date > ?")
            params.append(today_str)
        elif due_filter == "overdue":
            clauses.append("due_date < ? AND status != 'completed'")
            params.append(today_str)

        where_stmt = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        # Order by mapping
        order_map = {
            "created_desc": "created_at DESC",
            "created_asc": "created_at ASC",
            "due_date": "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC",
            "priority": "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END ASC",
            "remaining_pomodoros": "(estimated_pomodoros - completed_pomodoros) DESC",
        }
        order_clause = order_map.get(sort_by, "created_at DESC")

        query = f"SELECT * FROM tasks {where_stmt} ORDER BY {order_clause};"
        cursor = self.db.execute(query, tuple(params))
        return [Task(**dict(row)) for row in cursor.fetchall()]

    def record_task_pomodoro(self, task_id: str, duration_seconds: int):
        """Increment completed pomodoros and add to total focus seconds."""
        task = self.get_task(task_id)
        if not task:
            return
        new_count = task.completed_pomodoros + 1
        new_seconds = task.total_focus_seconds + duration_seconds
        now = datetime.now().isoformat()
        with self.db.transaction():
            self.db.execute(
                """
                UPDATE tasks
                SET completed_pomodoros = ?, total_focus_seconds = ?, updated_at = ?
                WHERE id = ?;
                """,
                (new_count, new_seconds, now, task_id),
            )

    # -------------------------------------------------------------------------
    # Pomodoro Session Operations
    # -------------------------------------------------------------------------
    def record_session(
        self,
        task_id: Optional[str],
        session_type: str,
        start_time: str,
        end_time: str,
        duration_seconds: int,
        status: str = "completed",
    ) -> PomodoroSession:
        session_id = str(uuid.uuid4())
        session_date = start_time[:10]  # YYYY-MM-DD

        session = PomodoroSession(
            id=session_id,
            task_id=task_id,
            session_type=session_type,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            status=status,
            date=session_date,
        )

        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO pomodoro_sessions (
                    id, task_id, session_type, start_time, end_time,
                    duration_seconds, status, date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session.id, session.task_id, session.session_type,
                    session.start_time, session.end_time, session.duration_seconds,
                    session.status, session.date,
                ),
            )

        # If it was a focus session, update daily aggregate stats
        if session_type == "focus":
            pomodoro_inc = 1 if status == "completed" else 0
            interruption_inc = 1 if status == "interrupted" else 0
            self._update_daily_stats(
                date_str=session_date,
                focus_seconds=duration_seconds,
                pomodoros=pomodoro_inc,
                interruptions=interruption_inc,
            )

            # If associated with a task and completed, increment task's pomodoro count
            if task_id and status == "completed":
                self.record_task_pomodoro(task_id, duration_seconds)

        return session

    def list_sessions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        task_id: Optional[str] = None,
        session_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[PomodoroSession]:
        clauses = []
        params = []
        if start_date:
            clauses.append("date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("date <= ?")
            params.append(end_date)
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        if session_type:
            clauses.append("session_type = ?")
            params.append(session_type)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM pomodoro_sessions {where_clause} ORDER BY start_time DESC LIMIT ?;"
        params.append(limit)

        cursor = self.db.execute(query, tuple(params))
        return [PomodoroSession(**dict(row)) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Daily Statistics Operations
    # -------------------------------------------------------------------------
    def _update_daily_stats(
        self,
        date_str: str,
        focus_seconds: int,
        pomodoros: int = 0,
        tasks_completed: int = 0,
        interruptions: int = 0,
    ):
        with self.db.transaction():
            # Upsert into daily_statistics
            self.db.execute(
                """
                INSERT INTO daily_statistics (
                    date, total_focus_seconds, pomodoros_completed,
                    tasks_completed, longest_session_seconds, interruptions_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_focus_seconds = total_focus_seconds + excluded.total_focus_seconds,
                    pomodoros_completed = pomodoros_completed + excluded.pomodoros_completed,
                    tasks_completed = tasks_completed + excluded.tasks_completed,
                    longest_session_seconds = MAX(longest_session_seconds, excluded.longest_session_seconds),
                    interruptions_count = interruptions_count + excluded.interruptions_count;
                """,
                (date_str, focus_seconds, pomodoros, tasks_completed, focus_seconds, interruptions),
            )

    def get_daily_stats(self, date_str: str) -> DailyStats:
        cursor = self.db.execute("SELECT * FROM daily_statistics WHERE date = ?;", (date_str,))
        row = cursor.fetchone()
        if not row:
            return DailyStats(date=date_str)
        return DailyStats(**dict(row))

    def get_stats_range(self, start_date: str, end_date: str) -> List[DailyStats]:
        cursor = self.db.execute(
            "SELECT * FROM daily_statistics WHERE date >= ? AND date <= ? ORDER BY date ASC;",
            (start_date, end_date),
        )
        stats_map = {row["date"]: DailyStats(**dict(row)) for row in cursor.fetchall()}

        # Fill in any missing dates with 0-value DailyStats
        result = []
        cur_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
        while cur_date <= end_d:
            d_str = cur_date.isoformat()
            result.append(stats_map.get(d_str, DailyStats(date=d_str)))
            cur_date += timedelta(days=1)
        return result

    def get_productivity_streak(self) -> int:
        """Calculate consecutive days of reaching at least one completed pomodoro."""
        cursor = self.db.execute(
            """
            SELECT date, pomodoros_completed
            FROM daily_statistics
            WHERE pomodoros_completed > 0
            ORDER BY date DESC;
            """
        )
        rows = cursor.fetchall()
        if not rows:
            return 0

        streak = 0
        expected = date.today()
        # If user hasn't done a pomodoro today yet, allow streak to continue from yesterday
        first_date = datetime.strptime(rows[0]["date"], "%Y-%m-%d").date()
        if first_date == expected:
            expected = expected
        elif first_date == expected - timedelta(days=1):
            expected = expected - timedelta(days=1)
        else:
            return 0

        for row in rows:
            row_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            if row_date == expected:
                streak += 1
                expected -= timedelta(days=1)
            else:
                break
        return streak

    def get_longest_streak(self) -> int:
        """Calculate the longest consecutive days of completed pomodoros."""
        cursor = self.db.execute(
            """
            SELECT date
            FROM daily_statistics
            WHERE pomodoros_completed > 0
            ORDER BY date ASC;
            """
        )
        rows = cursor.fetchall()
        if not rows:
            return 0

        dates = [datetime.strptime(r["date"], "%Y-%m-%d").date() for r in rows]
        max_streak = 1
        current = 1
        for i in range(1, len(dates)):
            if dates[i] == dates[i - 1] + timedelta(days=1):
                current += 1
                max_streak = max(max_streak, current)
            elif dates[i] > dates[i - 1] + timedelta(days=1):
                current = 1
        return max_streak

    def get_time_distribution(self, days: int = 7) -> Dict[str, int]:
        """
        Group focus duration into morning (06:00-12:00),
        afternoon (12:00-18:00), and evening/night (18:00-06:00).
        """
        start_date = (date.today() - timedelta(days=days)).isoformat()
        cursor = self.db.execute(
            """
            SELECT start_time, duration_seconds
            FROM pomodoro_sessions
            WHERE session_type = 'focus' AND date >= ?;
            """,
            (start_date,),
        )
        distribution = {"Morning": 0, "Afternoon": 0, "Evening": 0}
        for row in cursor.fetchall():
            try:
                dt = datetime.fromisoformat(row["start_time"])
                hour = dt.hour
                dur = row["duration_seconds"]
                if 6 <= hour < 12:
                    distribution["Morning"] += dur
                elif 12 <= hour < 18:
                    distribution["Afternoon"] += dur
                else:
                    distribution["Evening"] += dur
            except Exception:
                pass
        return distribution

    # -------------------------------------------------------------------------
    # Preferences Operations
    # -------------------------------------------------------------------------
    def get_preference(self, key: str, default: Any = None) -> Any:
        cursor = self.db.execute("SELECT value FROM preferences WHERE key = ?;", (key,))
        row = cursor.fetchone()
        if row is None:
            return DEFAULT_PREFERENCES.get(key, default)
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def set_preference(self, key: str, value: Any):
        val_str = json.dumps(value)
        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO preferences (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, val_str),
            )

    def get_all_preferences(self) -> Dict[str, Any]:
        result = dict(DEFAULT_PREFERENCES)
        cursor = self.db.execute("SELECT key, value FROM preferences;")
        for row in cursor.fetchall():
            try:
                result[row["key"]] = json.loads(row["value"])
            except Exception:
                result[row["key"]] = row["value"]
        return result

    # -------------------------------------------------------------------------
    # Application Usage (Privacy-Preserving)
    # -------------------------------------------------------------------------
    def record_app_usage(
        self,
        app_name: str,
        duration_seconds: int,
        window_title: str = "",
        date_str: Optional[str] = None,
    ):
        d_str = date_str or date.today().isoformat()
        with self.db.transaction():
            self.db.execute(
                """
                INSERT INTO application_usage (date, app_name, window_title, duration_seconds)
                VALUES (?, ?, ?, ?);
                """,
                (d_str, app_name, window_title, duration_seconds),
            )

    def get_app_usage_summary(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        d_str = date_str or date.today().isoformat()
        cursor = self.db.execute(
            """
            SELECT app_name, SUM(duration_seconds) as total_seconds
            FROM application_usage
            WHERE date = ?
            GROUP BY app_name
            ORDER BY total_seconds DESC;
            """,
            (d_str,),
        )
        return [dict(row) for row in cursor.fetchall()]
