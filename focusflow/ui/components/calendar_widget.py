"""
Custom Interactive Month Calendar Widget for FocusFlow.
Matches Image 4's exact calendar card with month navigation,
highlighted current date, and subtle session indicator dots based on real database records.
"""

import calendar
from datetime import date, datetime
from typing import Set, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal

from focusflow.db.repository import Repository
from focusflow.config import format_month_year


class CalendarGrid(QWidget):
    """Custom painted 7-column calendar grid with today highlight and session dots."""

    date_selected = pyqtSignal(date)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.year = date.today().year
        self.month = date.today().month
        self.selected_date = date.today()
        self.session_days: Set[int] = set()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumHeight(170)

    def set_month(self, year: int, month: int, session_days: Set[int]):
        self.year = year
        self.month = month
        self.session_days = session_days
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.width()
            h = self.height()
            col_w = w / 7.0

            # Monday is first day of week
            month_days = calendar.monthcalendar(self.year, self.month)
            n_rows = len(month_days)
            row_h = (h - 22) / max(1, n_rows)

            pos = event.position()
            if pos.y() < 22:
                return

            col = int(pos.x() // col_w)
            row = int((pos.y() - 22) // row_h)

            if 0 <= row < n_rows and 0 <= col < 7:
                day_num = month_days[row][col]
                if day_num != 0:
                    self.selected_date = date(self.year, self.month, day_num)
                    self.date_selected.emit(self.selected_date)
                    self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        col_w = w / 7.0

        # 1. Day headers: Mon Tue Wed Thu Fri Sat Sun
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        painter.setFont(QFont("Inter", 9, QFont.Weight.Medium))
        painter.setPen(QColor("#64748b"))

        for col, name in enumerate(day_names):
            x = col * col_w
            painter.drawText(QRectF(x, 2, col_w, 18), Qt.AlignmentFlag.AlignCenter, name)

        # 2. Days grid
        month_days = calendar.monthcalendar(self.year, self.month)
        n_rows = len(month_days)
        row_h = (h - 24) / max(1, n_rows)

        today = date.today()

        for r_idx, week in enumerate(month_days):
            y = 24 + r_idx * row_h
            for c_idx, day in enumerate(week):
                x = c_idx * col_w
                cell_rect = QRectF(x, y, col_w, row_h)

                if day == 0:
                    continue

                is_today = (self.year == today.year and self.month == today.month and day == today.day)
                is_selected = (self.selected_date and self.selected_date.year == self.year and
                               self.selected_date.month == self.month and self.selected_date.day == day)

                # Today / Selected Highlight Circle
                cx = x + col_w / 2.0
                cy = y + row_h / 2.0 - 2
                circle_radius = min(col_w, row_h) * 0.40

                if is_today or is_selected:
                    # Blue-purple circle
                    painter.setBrush(QColor("#4f46e5"))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(cx, cy), circle_radius, circle_radius)
                    painter.setPen(QColor("#ffffff"))
                    painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
                else:
                    painter.setPen(QColor("#cbd5e1"))
                    painter.setFont(QFont("Inter", 10, QFont.Weight.Normal))

                painter.drawText(cell_rect, Qt.AlignmentFlag.AlignCenter, str(day))

                # Session indicator dot
                if day in self.session_days:
                    dot_y = cy + circle_radius + 1
                    painter.setBrush(QColor("#38bdf8"))  # Light cyan dot
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(cx, dot_y), 2.0, 2.0)

        painter.end()


class MonthCalendarWidget(QFrame):
    """Complete calendar card with month navigation buttons and grid."""

    date_selected = pyqtSignal(date)

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.year = date.today().year
        self.month = date.today().month

        self.setObjectName("Card")
        self.setProperty("class", "Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui()
        self.refresh_calendar()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setBrush(QColor("#111726"))
        painter.setPen(QPen(QColor("#1e293f"), 1.0))
        painter.drawRoundedRect(rect, 16.0, 16.0)
        painter.end()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        # Header: "Calendar" title
        header = QHBoxLayout()
        title_lbl = QLabel("Calendar")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Month Navigation Row: <  December 2024  >
        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)

        btn_prev = QPushButton("‹")
        btn_prev.setFixedSize(24, 24)
        btn_prev.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e263d;
                color: #ffffff;
            }
        """)
        btn_prev.clicked.connect(self._prev_month)
        nav_row.addWidget(btn_prev)

        self.month_year_lbl = QLabel()
        self.month_year_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_year_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #e2e8f0;")
        nav_row.addWidget(self.month_year_lbl, stretch=1)

        btn_next = QPushButton("›")
        btn_next.setFixedSize(24, 24)
        btn_next.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e263d;
                color: #ffffff;
            }
        """)
        btn_next.clicked.connect(self._next_month)
        nav_row.addWidget(btn_next)

        layout.addLayout(nav_row)

        # Grid
        self.grid = CalendarGrid(self)
        self.grid.date_selected.connect(self.date_selected.emit)
        layout.addWidget(self.grid)

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

    def refresh_calendar(self):
        # Month name formatted in English
        self.month_year_lbl.setText(format_month_year(self.year, self.month))

        # Query sessions in this month from repository
        session_days = self.repo.get_dates_with_sessions(self.year, self.month)
        self.grid.set_month(self.year, self.month, session_days)
