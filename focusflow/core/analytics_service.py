"""
FocusFlow Authoritative Analytics Service.
Single source of truth for all metrics calculations across Dashboard,
Analytics/Reports, History, and Data Exports.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import calendar
from typing import Dict, List, Optional, Tuple

from focusflow.config import ENGLISH_DAYS_SHORT
from focusflow.db.repository import Repository, PomodoroSession, Task


@dataclass
class PeriodSummary:
    total_focus_seconds: int
    completed_pomodoros: int
    stopped_sessions: int
    interrupted_sessions: int
    completed_breaks: int
    total_break_seconds: int
    days_in_period: int
    active_days_count: int
    calendar_day_average_seconds: float
    active_day_average_seconds: float
    daily_goal_seconds: int
    total_goal_seconds: int
    goal_completion_pct: float
    prev_focus_seconds: int
    comparison_pct: Optional[float]


@dataclass
class DailyTrendItem:
    date_str: str
    date_obj: date
    day_name: str
    focus_seconds: int
    completed_pomodoros: int
    break_seconds: int
    goal_seconds: int


@dataclass
class TaskBreakdownItem:
    task_id: Optional[str]
    task_title: str
    focus_seconds: int
    completed_pomodoros: int
    estimated_pomodoros: int
    is_completed: bool
    pct_of_total: float


class AnalyticsService:
    """Provides centralized, authoritative calculations for all productivity metrics."""

    def __init__(self, repository: Repository):
        self.repo = repository

    # -------------------------------------------------------------------------
    # Date Range Resolution
    # -------------------------------------------------------------------------
    @staticmethod
    def resolve_date_range(
        preset: str,
        custom_start: Optional[date] = None,
        custom_end: Optional[date] = None,
        anchor_date: Optional[date] = None,
    ) -> Tuple[date, date, str]:
        """
        Resolve a preset or custom range to (start_date, end_date, label).
        Start and end dates are inclusive.
        """
        today = anchor_date or date.today()
        preset = preset.lower().replace(" ", "_")

        if preset == "today":
            return today, today, "Today"

        if preset == "yesterday":
            y = today - timedelta(days=1)
            return y, y, "Yesterday"

        if preset == "this_week":
            # Monday to Sunday of current week
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, end, "This Week"

        if preset == "last_week":
            # Monday to Sunday of previous week
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
            return start, end, "Last Week"

        if preset == "this_month":
            start = today.replace(day=1)
            _, last_day = calendar.monthrange(today.year, today.month)
            end = today.replace(day=last_day)
            return start, end, "This Month"

        if preset == "last_month":
            first_this_month = today.replace(day=1)
            last_day_prev = first_this_month - timedelta(days=1)
            start = last_day_prev.replace(day=1)
            return start, last_day_prev, "Last Month"

        if preset in ("last_7_days", "7_days", "past_7_days"):
            start = today - timedelta(days=6)
            return start, today, "Last 7 Days"

        if preset in ("last_30_days", "30_days", "past_30_days"):
            start = today - timedelta(days=29)
            return start, today, "Last 30 Days"

        if preset == "custom":
            s = custom_start or today
            e = custom_end or today
            if s > e:
                s, e = e, s
            return s, e, f"{s.strftime('%b %d')} - {e.strftime('%b %d, %Y')}"

        if preset == "all_time":
            # Earliest session or stat date to today
            earliest = today - timedelta(days=30)
            try:
                history = self.repo.get_session_history(limit=10000)
                if history:
                    earliest_sess = min(datetime.fromisoformat(s.start_time).date() for s in history)
                    if earliest_sess < earliest:
                        earliest = earliest_sess
            except Exception:
                pass
            return earliest, today, "All Time"

        # Default fallback
        start = today - timedelta(days=6)
        return start, today, "Last 7 Days"

    # -------------------------------------------------------------------------
    # Core Queries
    # -------------------------------------------------------------------------
    def get_sessions_in_range(self, start_date: date, end_date: date) -> List[PomodoroSession]:
        """Fetch all sessions that started within [start_date, end_date] inclusive."""
        # Query with ample limit
        all_sessions = self.repo.get_session_history(limit=50000)
        filtered = []
        for s in all_sessions:
            try:
                st = datetime.fromisoformat(s.start_time).date()
                if start_date <= st <= end_date:
                    filtered.append(s)
            except Exception:
                continue
        # Return sorted chronologically
        filtered.sort(key=lambda s: s.start_time)
        return filtered

    def get_period_summary(
        self,
        start_date: date,
        end_date: date,
        daily_goal_seconds: int = 14400,
    ) -> PeriodSummary:
        """
        Calculate summary metrics over [start_date, end_date] inclusive.
        Guarantees zero-division safety and coherent totals.
        """
        sessions = self.get_sessions_in_range(start_date, end_date)

        total_focus = 0
        completed_pomodoros = 0
        stopped_sessions = 0
        interrupted_sessions = 0
        completed_breaks = 0
        total_break = 0
        active_dates = set()

        for s in sessions:
            st_date = datetime.fromisoformat(s.start_time).date()
            if s.session_type == "focus":
                total_focus += s.duration_seconds
                if s.duration_seconds > 0:
                    active_dates.add(st_date)

                status = (s.status or "").lower()
                if status == "completed":
                    completed_pomodoros += 1
                elif status == "stopped":
                    stopped_sessions += 1
                elif status == "interrupted":
                    interrupted_sessions += 1
                else:
                    # Legacy fallback
                    completed_pomodoros += 1
            else:
                # Breaks
                completed_breaks += 1
                total_break += s.duration_seconds

        days_in_period = max(1, (end_date - start_date).days + 1)
        active_days_count = len(active_dates)

        calendar_avg = total_focus / days_in_period
        active_avg = total_focus / max(1, active_days_count) if active_days_count > 0 else 0.0

        total_goal = daily_goal_seconds * days_in_period
        goal_pct = min(100.0, (total_focus / total_goal * 100.0)) if total_goal > 0 else 0.0

        # Previous period comparison
        period_len = days_in_period
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_len - 1)
        prev_sessions = self.get_sessions_in_range(prev_start, prev_end)
        prev_focus = sum(s.duration_seconds for s in prev_sessions if s.session_type == "focus")

        comparison_pct: Optional[float] = None
        if prev_focus > 0:
            comparison_pct = ((total_focus - prev_focus) / prev_focus) * 100.0

        return PeriodSummary(
            total_focus_seconds=total_focus,
            completed_pomodoros=completed_pomodoros,
            stopped_sessions=stopped_sessions,
            interrupted_sessions=interrupted_sessions,
            completed_breaks=completed_breaks,
            total_break_seconds=total_break,
            days_in_period=days_in_period,
            active_days_count=active_days_count,
            calendar_day_average_seconds=calendar_avg,
            active_day_average_seconds=active_avg,
            daily_goal_seconds=daily_goal_seconds,
            total_goal_seconds=total_goal,
            goal_completion_pct=goal_pct,
            prev_focus_seconds=prev_focus,
            comparison_pct=comparison_pct,
        )

    # -------------------------------------------------------------------------
    # Daily Trend
    # -------------------------------------------------------------------------
    def get_daily_trend(
        self,
        start_date: date,
        end_date: date,
        daily_goal_seconds: int = 14400,
    ) -> List[DailyTrendItem]:
        """
        Generate daily trend items for every calendar day in range.
        Guaranteed to have an item for every single day (even if 0 focus).
        """
        # Read from daily_statistics table for accurate pre-aggregated or midnight-split stats
        stats_map = {}
        try:
            db_stats = self.repo.get_daily_stats_range(start_date.isoformat(), end_date.isoformat())
            for st in db_stats:
                stats_map[st.date] = st
        except Exception:
            pass

        # Also aggregate directly from sessions in case stats table was missing entries
        sessions = self.get_sessions_in_range(start_date, end_date)
        sess_focus_by_day: Dict[str, int] = {}
        sess_poms_by_day: Dict[str, int] = {}
        sess_break_by_day: Dict[str, int] = {}

        for s in sessions:
            day_str = datetime.fromisoformat(s.start_time).date().isoformat()
            if s.session_type == "focus":
                sess_focus_by_day[day_str] = sess_focus_by_day.get(day_str, 0) + s.duration_seconds
                if (s.status or "").lower() == "completed":
                    sess_poms_by_day[day_str] = sess_poms_by_day.get(day_str, 0) + 1
            else:
                sess_break_by_day[day_str] = sess_break_by_day.get(day_str, 0) + s.duration_seconds

        trend = []
        curr = start_date
        while curr <= end_date:
            curr_str = curr.isoformat()
            st = stats_map.get(curr_str)

            # Prefer daily_statistics if present (as it accounts for midnight splits),
            # but ensure we never undercount if sessions exist.
            db_focus = st.total_focus_seconds if st else 0
            db_poms = st.pomodoros_completed if st else 0
            db_break = getattr(st, "total_break_seconds", 0) if st else 0

            focus_secs = max(db_focus, sess_focus_by_day.get(curr_str, 0))
            poms = max(db_poms, sess_poms_by_day.get(curr_str, 0))
            break_secs = max(db_break, sess_break_by_day.get(curr_str, 0))

            trend.append(
                DailyTrendItem(
                    date_str=curr_str,
                    date_obj=curr,
                    day_name=ENGLISH_DAYS_SHORT[curr.weekday()],
                    focus_seconds=focus_secs,
                    completed_pomodoros=poms,
                    break_seconds=break_secs,
                    goal_seconds=daily_goal_seconds,
                )
            )
            curr += timedelta(days=1)

        return trend

    # -------------------------------------------------------------------------
    # Task Breakdown
    # -------------------------------------------------------------------------
    def get_task_breakdown(
        self,
        start_date: date,
        end_date: date,
    ) -> List[TaskBreakdownItem]:
        """
        Aggregate focus time by task in [start_date, end_date].
        Handles deleted tasks and untracked (General Focus) cleanly.
        """
        sessions = self.get_sessions_in_range(start_date, end_date)
        focus_sessions = [s for s in sessions if s.session_type == "focus"]

        tasks_by_id: Dict[str, Task] = {t.id: t for t in self.repo.get_all_tasks()}

        task_time: Dict[Optional[str], int] = {}
        task_poms: Dict[Optional[str], int] = {}

        for s in focus_sessions:
            tid = s.task_id
            task_time[tid] = task_time.get(tid, 0) + s.duration_seconds
            if (s.status or "").lower() == "completed":
                task_poms[tid] = task_poms.get(tid, 0) + 1

        total_focus = sum(task_time.values())
        items = []

        for tid, secs in task_time.items():
            if tid is None:
                title = "General Focus"
                est = 0
                completed = False
            elif tid in tasks_by_id:
                t = tasks_by_id[tid]
                title = t.title
                est = t.estimated_pomodoros
                completed = t.is_completed
            else:
                title = "[Deleted Task]"
                est = 0
                completed = False

            poms = task_poms.get(tid, 0)
            pct = (secs / total_focus * 100.0) if total_focus > 0 else 0.0

            items.append(
                TaskBreakdownItem(
                    task_id=tid,
                    task_title=title,
                    focus_seconds=secs,
                    completed_pomodoros=poms,
                    estimated_pomodoros=est,
                    is_completed=completed,
                    pct_of_total=pct,
                )
            )

        items.sort(key=lambda x: x.focus_seconds, reverse=True)
        return items

    # -------------------------------------------------------------------------
    # Outcome Distribution
    # -------------------------------------------------------------------------
    def get_outcome_distribution(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[str, int]:
        """Return counts of completed, stopped, interrupted focus sessions and breaks."""
        sessions = self.get_sessions_in_range(start_date, end_date)
        res = {
            "completed": 0,
            "stopped": 0,
            "interrupted": 0,
            "breaks": 0,
        }
        for s in sessions:
            if s.session_type == "focus":
                st = (s.status or "").lower()
                if st in res:
                    res[st] += 1
                else:
                    res["completed"] += 1
            else:
                res["breaks"] += 1
        return res
