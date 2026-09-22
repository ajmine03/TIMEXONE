"""
Productivity and Break Reminder Service for FocusFlow.
Monitors daily focus targets and sends gentle, non-intrusive reminders.
"""

import time
from datetime import datetime, date
from typing import Optional

from focusflow.db.repository import Repository
from focusflow.ui.notifications import NotificationService
from focusflow.core.timer import PomodoroEngine


class ReminderService:
    """Manages smart periodic productivity reminders."""

    def __init__(
        self,
        repository: Repository,
        notification_service: NotificationService,
        engine: PomodoroEngine,
    ):
        self.repo = repository
        self.notify = notification_service
        self.engine = engine

        self._last_reminder_check = 0.0
        self._goal_notified_today = False
        self._current_day_str = date.today().isoformat()

    def check_reminders(self):
        """Called periodically (e.g. once per minute) by the main timer loop."""
        now = time.time()
        # Rate limit checks to at most once per 60 seconds
        if now - self._last_reminder_check < 60.0:
            return
        self._last_reminder_check = now

        today_str = date.today().isoformat()
        if today_str != self._current_day_str:
            # Reset daily flags on day rollover
            self._current_day_str = today_str
            self._goal_notified_today = False

        if not self.repo.get_preference("notifications_enabled", True):
            return

        # 1. Daily Goal Check
        if not self._goal_notified_today:
            stats = self.repo.get_daily_stats(today_str)
            goal_seconds = int(self.repo.get_preference("daily_goal_seconds", 7200))
            if stats.total_focus_seconds >= goal_seconds and goal_seconds > 0:
                self._goal_notified_today = True
                goal_hours = goal_seconds / 3600.0
                self.notify.notify_daily_goal_reached(goal_hours)
