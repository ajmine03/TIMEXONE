"""
Productivity Statistics and Analytics View for FocusFlow.
Renders daily, weekly, and monthly productivity rollups, charts, and distribution.
"""

from datetime import date, datetime, timedelta
from typing import List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt

from focusflow.db.repository import Repository
from focusflow.ui.components.charts import WeeklyBarChart, TimeDistributionBar


class StatsView(QWidget):
    """Visual analytics dashboard for productivity trends."""

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.mode = "weekly"  # 'weekly' or 'monthly'

        self._init_ui()
        self.refresh_stats()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # Header with Period Switcher
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Productivity Statistics")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        self.btn_weekly = QPushButton("Last 7 Days")
        self.btn_weekly.setCheckable(True)
        self.btn_weekly.setChecked(True)
        self.btn_weekly.clicked.connect(lambda: self._set_period("weekly"))
        header_layout.addWidget(self.btn_weekly)

        self.btn_monthly = QPushButton("Last 30 Days")
        self.btn_monthly.setCheckable(True)
        self.btn_monthly.clicked.connect(lambda: self._set_period("monthly"))
        header_layout.addWidget(self.btn_monthly)

        main_layout.addLayout(header_layout)

        # Scrollable area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)

        # 1. Top Summary Cards Row
        summary_row = QHBoxLayout()
        summary_row.setSpacing(14)

        self.card_total_time = self._create_card("TOTAL FOCUS TIME", "0h 0m", "#3b82f6")
        self.card_pomodoros = self._create_card("COMPLETED POMODOROS", "0", "#10b981")
        self.card_tasks = self._create_card("TASKS COMPLETED", "0", "#ec4899")
        self.card_avg = self._create_card("DAILY AVERAGE", "0m / day", "#f59e0b")

        summary_row.addWidget(self.card_total_time)
        summary_row.addWidget(self.card_pomodoros)
        summary_row.addWidget(self.card_tasks)
        summary_row.addWidget(self.card_avg)
        self.content_layout.addLayout(summary_row)

        # 2. Focus Time Bar Chart Card
        chart_card = QFrame()
        chart_card.setProperty("class", "Card")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(18, 16, 18, 16)
        chart_layout.setSpacing(12)

        chart_title = QLabel("Focus Time History")
        chart_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        chart_layout.addWidget(chart_title)

        self.bar_chart = WeeklyBarChart()
        chart_layout.addWidget(self.bar_chart)
        self.content_layout.addWidget(chart_card)

        # 3. Focus Distribution Card
        dist_card = QFrame()
        dist_card.setProperty("class", "Card")
        dist_layout = QVBoxLayout(dist_card)
        dist_layout.setContentsMargins(18, 16, 18, 16)
        dist_layout.setSpacing(12)

        dist_title = QLabel("Focus Time of Day Distribution")
        dist_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        dist_layout.addWidget(dist_title)

        self.dist_bar = TimeDistributionBar()
        dist_layout.addWidget(self.dist_bar)
        self.content_layout.addWidget(dist_card)

        # 4. Productivity Insights Card
        insights_card = QFrame()
        insights_card.setProperty("class", "Card")
        ins_layout = QGridLayout(insights_card)
        ins_layout.setContentsMargins(18, 16, 18, 16)
        ins_layout.setSpacing(16)

        self.lbl_best_day = QLabel("—")
        self.lbl_longest_session = QLabel("—")
        self.lbl_interruptions = QLabel("—")

        self._add_insight_row(ins_layout, 0, "🏆 Most Productive Day:", self.lbl_best_day)
        self._add_insight_row(ins_layout, 1, "⏱️ Longest Focus Session:", self.lbl_longest_session)
        self._add_insight_row(ins_layout, 2, "⚠️ Total Interruptions:", self.lbl_interruptions)

        self.content_layout.addWidget(insights_card)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _create_card(self, title: str, val: str, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #6c7086; letter-spacing: 1px;")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
        lbl_val.setObjectName("val")
        layout.addWidget(lbl_val)

        return card

    def _add_insight_row(self, grid: QGridLayout, row: int, label: str, value_lbl: QLabel):
        title = QLabel(label)
        title.setStyleSheet("color: #a6adc8; font-weight: 600; font-size: 13px;")
        value_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        grid.addWidget(title, row, 0)
        grid.addWidget(value_lbl, row, 1)

    def _set_period(self, period: str):
        self.mode = period
        self.btn_weekly.setChecked(period == "weekly")
        self.btn_monthly.setChecked(period == "monthly")
        self.refresh_stats()

    def refresh_stats(self):
        num_days = 7 if self.mode == "weekly" else 30
        today = date.today()
        start_d = today - timedelta(days=num_days - 1)

        stats_list = self.repo.get_stats_range(start_d.isoformat(), today.isoformat())

        total_seconds = sum(s.total_focus_seconds for s in stats_list)
        total_pomos = sum(s.pomodoros_completed for s in stats_list)
        total_tasks = sum(s.tasks_completed for s in stats_list)
        total_interruptions = sum(s.interruptions_count for s in stats_list)
        longest_session = max([s.longest_session_seconds for s in stats_list] + [0])

        # Formats
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        self.card_total_time.findChild(QLabel, "val").setText(time_str)
        self.card_pomodoros.findChild(QLabel, "val").setText(str(total_pomos))
        self.card_tasks.findChild(QLabel, "val").setText(str(total_tasks))

        avg_mins_day = (total_seconds // 60) // max(1, num_days)
        self.card_avg.findChild(QLabel, "val").setText(f"{avg_mins_day}m / day")

        # Bar chart data
        if self.mode == "weekly":
            chart_data = []
            for s in stats_list:
                d_obj = datetime.strptime(s.date, "%Y-%m-%d").date()
                day_name = d_obj.strftime("%a")
                mins_val = s.total_focus_seconds // 60
                chart_data.append((day_name, mins_val))
            self.bar_chart.set_data(chart_data)
        else:
            # For 30 days, bucket into 5 periods of 6 days each
            chart_data = []
            step = 6
            for i in range(0, len(stats_list), step):
                chunk = stats_list[i : i + step]
                label = f"W{i//step + 1}"
                mins_val = sum(s.total_focus_seconds for s in chunk) // 60
                chart_data.append((label, mins_val))
            self.bar_chart.set_data(chart_data)

        # Time of day distribution
        distribution = self.repo.get_time_distribution(days=num_days)
        self.dist_bar.set_data(distribution)

        # Insights
        best_day_stat = max(stats_list, key=lambda s: s.total_focus_seconds) if stats_list else None
        if best_day_stat and best_day_stat.total_focus_seconds > 0:
            b_date = datetime.strptime(best_day_stat.date, "%Y-%m-%d").strftime("%A, %b %d")
            b_mins = best_day_stat.total_focus_seconds // 60
            self.lbl_best_day.setText(f"{b_date} ({b_mins} mins)")
        else:
            self.lbl_best_day.setText("None yet")

        long_mins = longest_session // 60
        self.lbl_longest_session.setText(f"{long_mins} minutes" if long_mins > 0 else "—")
        self.lbl_interruptions.setText(f"{total_interruptions} sessions interrupted")
