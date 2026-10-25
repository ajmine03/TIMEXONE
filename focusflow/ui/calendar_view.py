"""
Dedicated Full-Screen Interactive Calendar View for FocusFlow.
Displays interactive month calendar with session presence dots,
month-level productivity metrics, and a detailed Day Inspector panel.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import Set, Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QFont

from focusflow.config import format_month_year, format_date_full, format_duration_short
from focusflow.db.repository import Repository, PomodoroSession
from focusflow.ui.components.calendar_widget import CalendarGrid


class CalendarSessionItem(QFrame):
    """Compact session entry in the Day Inspector."""

    def __init__(self, session: PomodoroSession, task_title: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.task_title = task_title
        self.setStyleSheet("""
            QFrame {
                background-color: #0d121f;
                border: 1px solid #1a2338;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Time range
        start_t = self.session.start_time[11:16] if len(self.session.start_time) >= 16 else self.session.start_time
        end_t = self.session.end_time[11:16] if len(self.session.end_time) >= 16 else self.session.end_time
        lbl_time = QLabel(f"{start_t}–{end_t}")
        lbl_time.setStyleSheet("font-size: 11px; font-weight: bold; color: #8a95af; min-width: 75px;")
        layout.addWidget(lbl_time)

        # Type icon and title
        type_icon = "🎯" if self.session.session_type == "focus" else "☕"
        title_text = self.task_title if self.task_title else ("General Focus" if self.session.session_type == "focus" else "Break")
        lbl_title = QLabel(f"{type_icon} {title_text}")
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #e2e8f0;")
        layout.addWidget(lbl_title, stretch=1)

        # Duration
        secs = self.session.duration_seconds
        dur_str = f"{secs // 60}m" if secs >= 60 else f"{secs}s"
        lbl_dur = QLabel(dur_str)
        lbl_dur.setStyleSheet("font-size: 11px; font-weight: bold; color: #9399b2; min-width: 40px;")
        lbl_dur.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl_dur)

        # Status badge
        status = (self.session.status or "completed").lower()
        lbl_st = QLabel(status.capitalize())
        if status == "completed":
            lbl_st.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        elif status == "stopped":
            lbl_st.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold;")
        else:
            lbl_st.setStyleSheet("color: #ef4444; font-size: 10px; font-weight: bold;")
        layout.addWidget(lbl_st)


class CalendarView(QWidget):
    """Full-screen interactive monthly calendar with day session inspection."""

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository

        today = date.today()
        self.year = today.year
        self.month = today.month
        self.selected_date = today

        self._init_ui()
        self.refresh_calendar()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Top Header Bar
        header_card = QFrame()
        header_card.setProperty("class", "Card")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(18, 12, 18, 12)
        h_layout.setSpacing(14)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title_lbl = QLabel("Activity Calendar")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        v_head.addWidget(title_lbl)

        sub_lbl = QLabel("Monthly focus schedule, daily session logs, and streak inspection.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #8a95af;")
        v_head.addWidget(sub_lbl)
        h_layout.addLayout(v_head)

        h_layout.addStretch()

        # Month Navigation Controls
        nav_box = QHBoxLayout()
        nav_box.setSpacing(6)

        self.btn_prev = QPushButton("‹")
        self.btn_prev.setFixedSize(30, 30)
        self.btn_prev.setToolTip("Previous Month")
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: #141b2c;
                color: #cbd5e1;
                border: 1px solid #1e263d;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #232c45;
                color: #ffffff;
            }
        """)
        self.btn_prev.clicked.connect(self._prev_month)
        nav_box.addWidget(self.btn_prev)

        self.lbl_month_year = QLabel()
        self.lbl_month_year.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_month_year.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; min-width: 140px;")
        nav_box.addWidget(self.lbl_month_year)

        self.btn_next = QPushButton("›")
        self.btn_next.setFixedSize(30, 30)
        self.btn_next.setToolTip("Next Month")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #141b2c;
                color: #cbd5e1;
                border: 1px solid #1e263d;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #232c45;
                color: #ffffff;
            }
        """)
        self.btn_next.clicked.connect(self._next_month)
        nav_box.addWidget(self.btn_next)

        self.btn_today = QPushButton("Today")
        self.btn_today.setFixedHeight(30)
        self.btn_today.setStyleSheet("""
            QPushButton {
                background-color: #1e263d;
                color: #cbd5e1;
                border: 1px solid #2e3b5e;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3554;
                color: #ffffff;
            }
        """)
        self.btn_today.clicked.connect(self._go_today)
        nav_box.addWidget(self.btn_today)

        h_layout.addLayout(nav_box)
        main_layout.addWidget(header_card)

        # 2. Month Summary Pill Bar
        self.month_stats_pill = QFrame()
        self.month_stats_pill.setStyleSheet("""
            QFrame {
                background-color: #0b0f19;
                border: 1px solid #192237;
                border-radius: 10px;
                padding: 6px 16px;
            }
        """)
        m_pill_layout = QHBoxLayout(self.month_stats_pill)
        m_pill_layout.setContentsMargins(12, 4, 12, 4)
        m_pill_layout.setSpacing(24)

        self.lbl_m_focus = QLabel("Month Focus: 0h 0m")
        self.lbl_m_focus.setStyleSheet("font-size: 12px; font-weight: 600; color: #818cf8;")
        m_pill_layout.addWidget(self.lbl_m_focus)

        self.lbl_m_sessions = QLabel("Sessions: 0")
        self.lbl_m_sessions.setStyleSheet("font-size: 12px; font-weight: 600; color: #10b981;")
        m_pill_layout.addWidget(self.lbl_m_sessions)

        self.lbl_m_active_days = QLabel("Active Days: 0")
        self.lbl_m_active_days.setStyleSheet("font-size: 12px; font-weight: 600; color: #38bdf8;")
        m_pill_layout.addWidget(self.lbl_m_active_days)

        m_pill_layout.addStretch()
        main_layout.addWidget(self.month_stats_pill)

        # 3. Two-Column Layout: Calendar Grid (Left) + Day Inspector (Right)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # Left Column: Month Calendar Card
        cal_card = QFrame()
        cal_card.setProperty("class", "Card")
        cal_layout = QVBoxLayout(cal_card)
        cal_layout.setContentsMargins(18, 16, 18, 16)
        cal_layout.setSpacing(12)

        cal_title = QLabel("Monthly View")
        cal_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        cal_layout.addWidget(cal_title)

        self.grid = CalendarGrid(cal_card)
        self.grid.setMinimumHeight(280)
        self.grid.date_selected.connect(self._on_date_selected)
        cal_layout.addWidget(self.grid, stretch=1)

        body_layout.addWidget(cal_card, stretch=5)

        # Right Column: Day Inspector Card
        self.inspector_card = QFrame()
        self.inspector_card.setProperty("class", "Card")
        insp_layout = QVBoxLayout(self.inspector_card)
        insp_layout.setContentsMargins(18, 16, 18, 16)
        insp_layout.setSpacing(12)

        self.lbl_insp_date = QLabel("Day Inspection")
        self.lbl_insp_date.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        insp_layout.addWidget(self.lbl_insp_date)

        # Daily Metric Badges Row
        day_badges = QHBoxLayout()
        day_badges.setSpacing(8)

        self.card_day_focus = self._create_inspector_badge("Focus Time", "0m", "#6366f1")
        self.card_day_pomos = self._create_inspector_badge("Pomodoros", "0", "#10b981")
        self.card_day_breaks = self._create_inspector_badge("Breaks", "0m", "#a855f7")

        day_badges.addWidget(self.card_day_focus)
        day_badges.addWidget(self.card_day_pomos)
        day_badges.addWidget(self.card_day_breaks)
        insp_layout.addLayout(day_badges)

        lbl_log_head = QLabel("Recorded Sessions")
        lbl_log_head.setStyleSheet("font-size: 12px; font-weight: 700; color: #8a95af; letter-spacing: 0.5px; margin-top: 4px;")
        insp_layout.addWidget(lbl_log_head)

        # Scrollable session list
        self.scroll_sessions = QScrollArea()
        self.scroll_sessions.setWidgetResizable(True)
        self.scroll_sessions.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_sessions.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_sessions.setStyleSheet("background: transparent;")

        self.sessions_container = QWidget()
        self.sessions_list_layout = QVBoxLayout(self.sessions_container)
        self.sessions_list_layout.setContentsMargins(0, 4, 0, 4)
        self.sessions_list_layout.setSpacing(8)
        self.sessions_list_layout.addStretch()

        self.scroll_sessions.setWidget(self.sessions_container)
        insp_layout.addWidget(self.scroll_sessions, stretch=1)

        body_layout.addWidget(self.inspector_card, stretch=5)
        main_layout.addLayout(body_layout, stretch=1)

    def _create_inspector_badge(self, title: str, value: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet("""
            QFrame {
                background-color: #0e1320;
                border: 1px solid #1a2236;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        l = QVBoxLayout(f)
        l.setContentsMargins(4, 4, 4, 4)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; color: #8a95af; font-weight: 600;")
        l.addWidget(lbl_t)

        lbl_v = QLabel(value)
        lbl_v.setObjectName("val")
        lbl_v.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color};")
        l.addWidget(lbl_v)
        return f

    def _prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self.refresh_calendar()

    def _next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self.refresh_calendar()

    def _go_today(self):
        today = date.today()
        self.year = today.year
        self.month = today.month
        self.selected_date = today
        self.refresh_calendar()

    def _on_date_selected(self, selected: date):
        self.selected_date = selected
        self._refresh_day_inspector()

    def _refresh_day_inspector(self):
        date_str = self.selected_date.isoformat()
        self.lbl_insp_date.setText(format_date_full(date_str))

        # Query daily stats
        daily = self.repo.get_daily_stats(date_str)
        focus_s = daily.total_focus_seconds if daily else 0
        pomos = getattr(daily, "pomodoros_completed", getattr(daily, "completed_pomodoros", 0)) if daily else 0
        break_s = getattr(daily, "total_break_seconds", 0) if daily else 0

        self.card_day_focus.findChild(QLabel, "val").setText(format_duration_short(focus_s))
        self.card_day_pomos.findChild(QLabel, "val").setText(str(pomos))
        self.card_day_breaks.findChild(QLabel, "val").setText(format_duration_short(break_s))

        # Query sessions for this date
        sessions = self.repo.list_sessions(start_date=date_str, end_date=date_str, limit=100)

        # Clear existing items except stretch
        while self.sessions_list_layout.count() > 1:
            item = self.sessions_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not sessions:
            lbl_empty = QLabel("No focus sessions recorded on this day.")
            lbl_empty.setStyleSheet("color: #6c7086; font-size: 12px; padding: 24px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_list_layout.insertWidget(0, lbl_empty)
            return

        tasks_map: Dict[str, str] = {t.id: t.title for t in self.repo.list_tasks()}
        for i, s in enumerate(sessions):
            task_title = tasks_map.get(s.task_id, "") if s.task_id else ""
            item_card = CalendarSessionItem(s, task_title, self.sessions_container)
            self.sessions_list_layout.insertWidget(i, item_card)

    def refresh_calendar(self):
        self.lbl_month_year.setText(format_month_year(self.year, self.month))

        session_days = self.repo.get_dates_with_sessions(self.year, self.month)
        self.grid.set_month(self.year, self.month, session_days)

        # Month totals
        num_days = calendar.monthrange(self.year, self.month)[1]
        m_start = f"{self.year:04d}-{self.month:02d}-01"
        m_end = f"{self.year:04d}-{self.month:02d}-{num_days:02d}"
        month_sessions = self.repo.list_sessions(start_date=m_start, end_date=m_end, limit=1000)

        total_focus = sum(s.duration_seconds for s in month_sessions if s.session_type == "focus")
        total_count = sum(1 for s in month_sessions if s.session_type == "focus")
        active_days_count = len(session_days)

        self.lbl_m_focus.setText(f"Month Focus: {format_duration_short(total_focus)}")
        self.lbl_m_sessions.setText(f"Sessions: {total_count}")
        self.lbl_m_active_days.setText(f"Active Days: {active_days_count}")

        self._refresh_day_inspector()
