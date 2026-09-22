"""
Session History View for FocusFlow.
Chronological timeline of focus and break sessions with date filters and search.
"""

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt

from focusflow.db.repository import Repository, PomodoroSession


class SessionHistoryCard(QFrame):
    """Visual representation of a single recorded focus or break session."""

    def __init__(self, session: PomodoroSession, task_title: str, parent=None):
        super().__init__(parent)
        self.session = session
        self.task_title = task_title
        self.setProperty("class", "Card")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # 1. Left: Time Interval
        start_t = self.session.start_time[11:16] if len(self.session.start_time) >= 16 else self.session.start_time
        end_t = self.session.end_time[11:16] if len(self.session.end_time) >= 16 else self.session.end_time
        time_lbl = QLabel(f"{start_t} — {end_t}")
        time_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; min-width: 100px;")
        layout.addWidget(time_lbl)

        # 2. Middle: Task Title and Session Type
        center_layout = QVBoxLayout()
        center_layout.setSpacing(3)

        type_icon = "🎯" if self.session.session_type == "focus" else "☕"
        title_text = self.task_title if self.task_title else "General Focus"
        task_lbl = QLabel(f"{type_icon}  {title_text}")
        task_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #cdd6f4;")
        center_layout.addWidget(task_lbl)

        type_lbl = QLabel(self.session.session_type.replace("_", " ").title())
        type_lbl.setStyleSheet("font-size: 11px; color: #6c7086;")
        center_layout.addWidget(type_lbl)
        layout.addLayout(center_layout, stretch=1)

        # 3. Duration
        mins = max(1, self.session.duration_seconds // 60)
        dur_lbl = QLabel(f"{mins} min")
        dur_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #9399b2; min-width: 60px;")
        dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dur_lbl)

        # 4. Status Badge
        status_lbl = QLabel(self.session.status.upper())
        if self.session.status == "completed":
            status_lbl.setStyleSheet(
                "background-color: #10b98122; color: #10b981; border: 1px solid #10b98144; "
                "border-radius: 4px; padding: 3px 8px; font-size: 10px; font-weight: bold;"
            )
        else:
            status_lbl.setStyleSheet(
                "background-color: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; "
                "border-radius: 4px; padding: 3px 8px; font-size: 10px; font-weight: bold;"
            )
        layout.addWidget(status_lbl)


class HistoryView(QWidget):
    """Session history view with date filtering, search, and day group headers."""

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.current_filter = "today"  # 'today', 'yesterday', '7days', '30days', 'all'

        self._init_ui()
        self.refresh_history()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # Top Header
        top_layout = QHBoxLayout()
        title_label = QLabel("Session History")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        top_layout.addWidget(title_label)
        top_layout.addStretch()

        self.summary_label = QLabel("0 sessions recorded")
        self.summary_label.setStyleSheet("color: #a6adc8; font-weight: 600; font-size: 13px;")
        top_layout.addWidget(self.summary_label)
        main_layout.addLayout(top_layout)

        # Filter Pills & Search
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.filter_buttons = {}
        for key, label in [
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("7days", "Last 7 Days"),
            ("30days", "Last 30 Days"),
            ("all", "All Time"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda ch, k=key: self._set_filter(k))
            toolbar.addWidget(btn)
            self.filter_buttons[key] = btn

        self.filter_buttons["today"].setChecked(True)
        toolbar.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by task...")
        self.search_input.setMinimumWidth(180)
        self.search_input.textChanged.connect(self.refresh_history)
        toolbar.addWidget(self.search_input)

        main_layout.addLayout(toolbar)

        # Scrollable Sessions Container
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")

        self.container = QWidget()
        self.sessions_layout = QVBoxLayout(self.container)
        self.sessions_layout.setContentsMargins(0, 4, 0, 4)
        self.sessions_layout.setSpacing(10)
        self.sessions_layout.addStretch()

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

    def _set_filter(self, filter_key: str):
        self.current_filter = filter_key
        for k, btn in self.filter_buttons.items():
            btn.setChecked(k == filter_key)
        self.refresh_history()

    def refresh_history(self):
        # Clear existing widgets except stretch
        while self.sessions_layout.count() > 1:
            item = self.sessions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        today = date.today()
        start_date = None
        end_date = None

        if self.current_filter == "today":
            start_date = today.isoformat()
            end_date = today.isoformat()
        elif self.current_filter == "yesterday":
            yest = today - timedelta(days=1)
            start_date = yest.isoformat()
            end_date = yest.isoformat()
        elif self.current_filter == "7days":
            start_date = (today - timedelta(days=7)).isoformat()
            end_date = today.isoformat()
        elif self.current_filter == "30days":
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()

        sessions = self.repo.list_sessions(start_date=start_date, end_date=end_date, limit=500)
        search_q = self.search_input.text().strip().lower()

        # Cache task titles
        tasks_map: Dict[str, str] = {t.id: t.title for t in self.repo.list_tasks()}

        # Filter by search
        filtered_sessions = []
        for s in sessions:
            title = tasks_map.get(s.task_id, "General Focus" if not s.task_id else "")
            if search_q and (search_q not in title.lower() and search_q not in s.session_type.lower()):
                continue
            filtered_sessions.append((s, title))

        if not filtered_sessions:
            empty_lbl = QLabel("No recorded sessions for this period.")
            empty_lbl.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_layout.insertWidget(0, empty_lbl)
            self.summary_label.setText("0 sessions")
            return

        # Update summary
        total_secs = sum(s.duration_seconds for s, _ in filtered_sessions if s.session_type == "focus")
        completed_cnt = sum(1 for s, _ in filtered_sessions if s.status == "completed")
        hrs = total_secs // 3600
        mins = (total_secs % 3600) // 60
        time_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
        self.summary_label.setText(f"{len(filtered_sessions)} sessions ({completed_cnt} completed) — {time_str} focused")

        # Group by date
        current_date_group = None
        idx = 0
        for s, title in filtered_sessions:
            if s.date != current_date_group:
                current_date_group = s.date
                d_obj = datetime.strptime(s.date, "%Y-%m-%d").date()
                if d_obj == today:
                    header_str = f"Today — {d_obj.strftime('%B %d, %Y')}"
                elif d_obj == today - timedelta(days=1):
                    header_str = f"Yesterday — {d_obj.strftime('%B %d, %Y')}"
                else:
                    header_str = d_obj.strftime("%A, %B %d, %Y")

                date_header = QLabel(header_str)
                date_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #89b4fa; padding-top: 10px;")
                self.sessions_layout.insertWidget(idx, date_header)
                idx += 1

            card = SessionHistoryCard(session=s, task_title=title)
            self.sessions_layout.insertWidget(idx, card)
            idx += 1
