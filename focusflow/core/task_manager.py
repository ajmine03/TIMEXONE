"""
Task Manager Service for FocusFlow.
Handles task business logic, validation, filtering, sorting, and UI observer signals.
"""

import re
from datetime import datetime, date
from typing import Optional, List, Callable, Dict, Any

from focusflow.db.repository import Repository, Task

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"pending", "in_progress", "completed"}


class TaskManager:
    """High-level task business logic and observer notifications."""

    def __init__(self, repository: Repository):
        self.repo = repository
        self._listeners: List[Callable[[], None]] = []

    def subscribe_change(self, listener: Callable[[], None]):
        """Subscribe to task changes (created, updated, deleted)."""
        self._listeners.append(listener)

    def _notify(self):
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                pass

    def create(
        self,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "medium",
        estimated_pomodoros: int = 1,
        tags: str = "",
    ) -> Task:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")

        clean_priority = priority.lower().strip()
        if clean_priority not in VALID_PRIORITIES:
            clean_priority = "medium"

        clean_due = due_date.strip() if due_date and due_date.strip() else None
        if clean_due:
            # Validate ISO date format YYYY-MM-DD
            try:
                datetime.strptime(clean_due, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Due date must be in YYYY-MM-DD format.")

        task = self.repo.create_task(
            title=clean_title,
            description=description.strip(),
            due_date=clean_due,
            priority=clean_priority,
            estimated_pomodoros=max(1, int(estimated_pomodoros)),
            tags=tags.strip(),
        )
        self._notify()
        return task

    def update(self, task_id: str, **kwargs) -> Optional[Task]:
        if "title" in kwargs:
            clean_title = kwargs["title"].strip()
            if not clean_title:
                raise ValueError("Task title cannot be empty.")
            kwargs["title"] = clean_title

        if "priority" in kwargs:
            clean_p = kwargs["priority"].lower().strip()
            if clean_p not in VALID_PRIORITIES:
                clean_p = "medium"
            kwargs["priority"] = clean_p

        if "status" in kwargs:
            clean_s = kwargs["status"].lower().strip()
            if clean_s not in VALID_STATUSES:
                clean_s = "pending"
            kwargs["status"] = clean_s

        if "due_date" in kwargs and kwargs["due_date"]:
            try:
                datetime.strptime(kwargs["due_date"].strip(), "%Y-%m-%d")
                kwargs["due_date"] = kwargs["due_date"].strip()
            except ValueError:
                raise ValueError("Due date must be in YYYY-MM-DD format.")

        updated = self.repo.update_task(task_id, **kwargs)
        if updated:
            self._notify()
        return updated

    def toggle_complete(self, task_id: str) -> Optional[Task]:
        task = self.repo.get_task(task_id)
        if not task:
            return None

        new_status = "pending" if task.status == "completed" else "completed"
        return self.update(task_id, status=new_status)

    def delete(self, task_id: str) -> bool:
        success = self.repo.delete_task(task_id)
        if success:
            self._notify()
        return success

    def get(self, task_id: str) -> Optional[Task]:
        return self.repo.get_task(task_id)

    def list(
        self,
        filter_mode: str = "all",     # 'all', 'today', 'upcoming', 'completed', 'high_priority'
        search: Optional[str] = None,
        sort_by: str = "created_desc", # 'created_desc', 'created_asc', 'priority', 'due_date', 'remaining_pomodoros'
        tag: Optional[str] = None,
    ) -> List[Task]:
        """
        Query tasks based on UI tab filters and search options.
        """
        status = None
        priority = None
        due_filter = None

        if filter_mode == "today":
            due_filter = "today"
        elif filter_mode == "upcoming":
            due_filter = "upcoming"
        elif filter_mode == "completed":
            status = "completed"
        elif filter_mode == "high_priority":
            priority = "high"

        # By default, if not explicitly viewing 'completed', exclude completed tasks
        # unless filter_mode is 'all' or 'completed'
        tasks = self.repo.list_tasks(
            status=status,
            priority=priority,
            tag=tag,
            search=search,
            due_filter=due_filter,
            sort_by=sort_by,
        )

        # For 'all' or 'today' or 'high_priority', user typically sees active first
        if filter_mode in ("all", "today", "high_priority"):
            # Sort so uncompleted come before completed if not completed filter
            tasks.sort(key=lambda t: 1 if t.status == "completed" else 0)

        return tasks

    def get_all_tags(self) -> List[str]:
        """Collect all unique tags across tasks."""
        all_tasks = self.repo.list_tasks()
        tags_set = set()
        for t in all_tasks:
            for tag in t.tag_list:
                tags_set.add(tag)
        return sorted(list(tags_set))
