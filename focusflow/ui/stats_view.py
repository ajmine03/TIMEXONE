"""
Productivity Statistics and Analytics View for FocusFlow.
Comprehensive reporting dashboard providing date presets, summary cards,
daily trend charts, task breakdown, outcome distribution, and CSV export.
Powered by the authoritative AnalyticsService.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QComboBox, QDateEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from focusflow.config import ENGLISH_MONTHS_SHORT, ENGLISH_MONTHS_FULL
from focusflow.db.repository import Repository
from focusflow.core.analytics_service import AnalyticsService, PeriodSummary, DailyTrendItem, TaskBreakdownItem
from focusflow.ui.components.charts import WeeklyBarChart, TimeDistributionBar
from focusflow.utils.export_import import DataManager


class StatsSummaryCard(QFrame):
    """Modern summary metric card with primary value and contextual subtitle/badge."""

    def __init__(self, title: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8a95af; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)

        self.lbl_value = QLabel("—")
        self.lbl_value.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {accent_color};")
        layout.addWidget(self.lbl_value)

        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #a6adc8; font-weight: 500;")
        layout.addWidget(self.lbl_sub)

    def set_content(self, value: str, subtitle: str = ""):
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)


class StatsView(QWidget):
    """Authoritative Analytics & Reports Dashboard."""

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.analytics = AnalyticsService(repository)
        self.data_manager = DataManager(repository)

        self.current_preset = "last_7_days"
        self.start_date = date.today() - timedelta(days=6)
        self.end_date = date.today()

        self._init_ui()
        self.refresh_stats()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 22, 28, 22)
        main_layout.setSpacing(18)

        # ---------------------------------------------------------------------
        # 1. Header Toolbar
        # ---------------------------------------------------------------------
        header_card = QFrame()
        header_card.setProperty("class", "Card")
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(18, 14, 18, 14)
        h_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        v_title = QVBoxLayout()
        v_title.setSpacing(2)
        title_lbl = QLabel("Analytics & Reports")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        v_title.addWidget(title_lbl)

        sub_lbl = QLabel("Authoritative productivity intelligence, focus duration trends, and session audit.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #8a95af;")
        v_title.addWidget(sub_lbl)
        top_row.addLayout(v_title)

        top_row.addStretch()

        # CSV Export Button
        self.btn_export = QPushButton("📥 Export CSV")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #1e263d;
                color: #e2e8f0;
                border: 1px solid #2e3b5e;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3554;
                color: #ffffff;
            }
        """)
        self.btn_export.clicked.connect(self._export_csv_dialog)
        top_row.addWidget(self.btn_export)

        # Jump to history button
        self.btn_view_history = QPushButton("📜 View History")
        self.btn_view_history.setStyleSheet("""
            QPushButton {
                background-color: #1e263d;
                color: #e2e8f0;
                border: 1px solid #2e3b5e;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a3554;
                color: #ffffff;
            }
        """)
        self.btn_view_history.clicked.connect(self._navigate_to_history)
        top_row.addWidget(self.btn_view_history)

        h_layout.addLayout(top_row)

        # Filter controls row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        lbl_range = QLabel("Period:")
        lbl_range.setStyleSheet("font-size: 12px; font-weight: 600; color: #cbd5e1;")
        filter_row.addWidget(lbl_range)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Last 7 Days",
            "Today",
            "Yesterday",
            "This Week",
            "Last Week",
            "This Month",
            "Last Month",
            "Last 30 Days",
            "All Time",
            "Custom Range",
        ])
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        filter_row.addWidget(self.combo_presets)

        # Prev / Next navigation buttons
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setToolTip("Previous Period")
        self.btn_prev.clicked.connect(self._step_prev_period)
        filter_row.addWidget(self.btn_prev)

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setToolTip("Next Period")
        self.btn_next.clicked.connect(self._step_next_period)
        filter_row.addWidget(self.btn_next)

        # Date Pickers for Custom
        self.date_start_edit = QDateEdit()
        self.date_start_edit.setCalendarPopup(True)
        self.date_start_edit.setDate(QDate(self.start_date.year, self.start_date.month, self.start_date.day))
        self.date_start_edit.dateChanged.connect(self._on_custom_date_changed)
        self.date_start_edit.setVisible(False)
        filter_row.addWidget(self.date_start_edit)

        self.lbl_to = QLabel("to")
        self.lbl_to.setStyleSheet("color: #8a95af; font-size: 12px;")
        self.lbl_to.setVisible(False)
        filter_row.addWidget(self.lbl_to)

        self.date_end_edit = QDateEdit()
        self.date_end_edit.setCalendarPopup(True)
        self.date_end_edit.setDate(QDate(self.end_date.year, self.end_date.month, self.end_date.day))
        self.date_end_edit.dateChanged.connect(self._on_custom_date_changed)
        self.date_end_edit.setVisible(False)
        filter_row.addWidget(self.date_end_edit)

        filter_row.addStretch()

        self.lbl_date_range_display = QLabel("")
        self.lbl_date_range_display.setStyleSheet("font-size: 13px; font-weight: bold; color: #818cf8;")
        filter_row.addWidget(self.lbl_date_range_display)

        h_layout.addLayout(filter_row)
        main_layout.addWidget(header_card)

        # ---------------------------------------------------------------------
        # Scrollable Analytics Content
        # ---------------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 4, 0, 8)
        self.content_layout.setSpacing(16)

        # 2. Top Summary Metrics Cards (5 Cards)
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        self.card_focus_time = StatsSummaryCard("Total Focus Time", "#6366f1")
        self.card_completed_pomos = StatsSummaryCard("Completed Pomodoros", "#10b981")
        self.card_daily_avg = StatsSummaryCard("Daily Average Focus", "#38bdf8")
        self.card_goal_progress = StatsSummaryCard("Goal Progress", "#f59e0b")
        self.card_breaks = StatsSummaryCard("Breaks & Rest", "#a855f7")

        summary_row.addWidget(self.card_focus_time)
        summary_row.addWidget(self.card_completed_pomos)
        summary_row.addWidget(self.card_daily_avg)
        summary_row.addWidget(self.card_goal_progress)
        summary_row.addWidget(self.card_breaks)
        self.content_layout.addLayout(summary_row)

        # 3. Daily Focus Bar Chart Card
        chart_card = QFrame()
        chart_card.setProperty("class", "Card")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(18, 16, 18, 16)
        chart_layout.setSpacing(12)

        chart_head = QHBoxLayout()
        lbl_c_title = QLabel("Daily Focus Time Trend")
        lbl_c_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        chart_head.addWidget(lbl_c_title)
        chart_head.addStretch()

        self.lbl_chart_subtitle = QLabel("")
        self.lbl_chart_subtitle.setStyleSheet("font-size: 12px; color: #8a95af;")
        chart_head.addWidget(self.lbl_chart_subtitle)
        chart_layout.addLayout(chart_head)

        self.bar_chart = WeeklyBarChart()
        self.bar_chart.setMinimumHeight(160)
        chart_layout.addWidget(self.bar_chart)
        self.content_layout.addWidget(chart_card)

        # 4. Two-Column Row: Task Breakdown + Outcomes & Time Distribution
        two_col = QHBoxLayout()
        two_col.setSpacing(14)

        # Left: Task Focus Breakdown Table Card
        task_card = QFrame()
        task_card.setProperty("class", "Card")
        t_layout = QVBoxLayout(task_card)
        t_layout.setContentsMargins(18, 16, 18, 16)
        t_layout.setSpacing(10)

        t_head = QLabel("Task Focus Breakdown")
        t_head.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        t_layout.addWidget(t_head)

        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["Task", "Poms", "Focus Time", "Share"])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.task_table.setMinimumHeight(220)
        self.task_table.setStyleSheet("""
            QTableWidget {
                background-color: #0e1320;
                border: 1px solid #1a2236;
                border-radius: 8px;
                gridline-color: #1a2236;
            }
            QHeaderView::section {
                background-color: #141b2d;
                color: #8a95af;
                font-weight: 600;
                font-size: 11px;
                border: none;
                padding: 6px;
            }
            QTableWidget::item {
                color: #cdd6f4;
                padding: 6px;
            }
        """)
        t_layout.addWidget(self.task_table)
        two_col.addWidget(task_card, stretch=3)

        # Right: Outcomes & Time-of-Day Distribution Card
        right_card = QFrame()
        right_card.setProperty("class", "Card")
        r_layout = QVBoxLayout(right_card)
        r_layout.setContentsMargins(18, 16, 18, 16)
        r_layout.setSpacing(12)

        lbl_dist_title = QLabel("Session Outcomes & Timing")
        lbl_dist_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        r_layout.addWidget(lbl_dist_title)

        # Outcome summary mini pills
        outcomes_row = QHBoxLayout()
        outcomes_row.setSpacing(8)

        self.card_out_comp = self._create_mini_outcome("Completed", "0", "#10b981")
        self.card_out_stop = self._create_mini_outcome("Stopped", "0", "#f59e0b")
        self.card_out_intr = self._create_mini_outcome("Interrupted", "0", "#ef4444")

        outcomes_row.addWidget(self.card_out_comp)
        outcomes_row.addWidget(self.card_out_stop)
        outcomes_row.addWidget(self.card_out_intr)
        r_layout.addLayout(outcomes_row)

        lbl_tod = QLabel("Time of Day Distribution")
        lbl_tod.setStyleSheet("font-size: 13px; font-weight: 600; color: #cdd6f4; margin-top: 6px;")
        r_layout.addWidget(lbl_tod)

        self.dist_bar = TimeDistributionBar()
        r_layout.addWidget(self.dist_bar)

        # Productivity Highlights
        self.lbl_highlights = QLabel("")
        self.lbl_highlights.setStyleSheet("font-size: 12px; color: #a6adc8; line-height: 1.4;")
        self.lbl_highlights.setWordWrap(True)
        r_layout.addWidget(self.lbl_highlights)

        two_col.addWidget(right_card, stretch=2)
        self.content_layout.addLayout(two_col)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

    def _create_mini_outcome(self, title: str, val: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background-color: #0e1320;
                border: 1px solid #1a2236;
                border-radius: 8px;
                padding: 8px 10px;
            }}
        """)
        l = QVBoxLayout(f)
        l.setContentsMargins(4, 4, 4, 4)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; color: #8a95af; font-weight: 600;")
        l.addWidget(lbl_t)

        lbl_v = QLabel(val)
        lbl_v.setObjectName("val")
        lbl_v.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        l.addWidget(lbl_v)
        return f

    # -------------------------------------------------------------------------
    # Period Navigation & Updates
    # -------------------------------------------------------------------------
    def _on_preset_changed(self, idx: int):
        text = self.combo_presets.currentText()
        preset_key = text.lower().replace(" ", "_")

        is_custom = (preset_key == "custom_range")
        self.date_start_edit.setVisible(is_custom)
        self.lbl_to.setVisible(is_custom)
        self.date_end_edit.setVisible(is_custom)
        self.btn_prev.setEnabled(not is_custom)
        self.btn_next.setEnabled(not is_custom)

        if not is_custom:
            s_d, e_d, _ = self.analytics.resolve_date_range(preset_key)
            self.start_date = s_d
            self.end_date = e_d
            self.refresh_stats()

    def _on_custom_date_changed(self):
        qd_start = self.date_start_edit.date()
        qd_end = self.date_end_edit.date()
        self.start_date = date(qd_start.year, qd_start.month, qd_start.day)
        self.end_date = date(qd_end.year, qd_end.month, qd_end.day)
        if self.start_date > self.end_date:
            self.start_date, self.end_date = self.end_date, self.start_date
        self.refresh_stats()

    def _step_prev_period(self):
        delta_days = max(1, (self.end_date - self.start_date).days + 1)
        self.start_date -= timedelta(days=delta_days)
        self.end_date -= timedelta(days=delta_days)
        self.refresh_stats()

    def _step_next_period(self):
        delta_days = max(1, (self.end_date - self.start_date).days + 1)
        self.start_date += timedelta(days=delta_days)
        self.end_date += timedelta(days=delta_days)
        self.refresh_stats()

    def _navigate_to_history(self):
        w = self.window()
        if hasattr(w, "show_history"):
            w.show_history()

    # -------------------------------------------------------------------------
    # Authoritative Refresh
    # -------------------------------------------------------------------------
    def refresh_stats(self):
        # Read daily goal from settings
        prefs = self.repo.get_all_preferences()
        goal_secs = prefs.get("daily_goal_seconds", 14400)

        # 1. Period Summary
        summary: PeriodSummary = self.analytics.get_period_summary(
            self.start_date, self.end_date, daily_goal_seconds=goal_secs
        )

        # Update Date Range Label
        days_count = summary.days_in_period
        if self.start_date == self.end_date:
            m_full = ENGLISH_MONTHS_FULL[self.start_date.month]
            range_str = f"{m_full} {self.start_date.day:02d}, {self.start_date.year} (1 day)"
        else:
            m1 = ENGLISH_MONTHS_SHORT[self.start_date.month]
            m2 = ENGLISH_MONTHS_SHORT[self.end_date.month]
            range_str = f"{m1} {self.start_date.day:02d} – {m2} {self.end_date.day:02d}, {self.end_date.year} ({days_count} days)"
        self.lbl_date_range_display.setText(range_str)

        # Card 1: Total Focus Time & Comparison
        hrs = summary.total_focus_seconds // 3600
        mins = (summary.total_focus_seconds % 3600) // 60
        focus_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"

        if summary.comparison_pct is not None:
            sign = "+" if summary.comparison_pct >= 0 else ""
            badge_str = f"{sign}{summary.comparison_pct:.1f}% vs previous period"
        else:
            badge_str = "No previous-period data"
        self.card_focus_time.set_content(focus_str, badge_str)

        # Card 2: Completed Pomodoros & Outcomes
        pomo_str = f"{summary.completed_pomodoros}"
        sub_pomo = f"{summary.stopped_sessions} stopped, {summary.interrupted_sessions} interrupted"
        self.card_completed_pomos.set_content(pomo_str, sub_pomo)

        # Card 3: Daily Average (Calendar-day & Active-day distinctly labeled)
        c_mins = int(summary.calendar_day_average_seconds // 60)
        c_h = c_mins // 60
        c_m = c_mins % 60
        c_str = f"{c_h}h {c_m}m" if c_h > 0 else f"{c_m}m"

        a_mins = int(summary.active_day_average_seconds // 60)
        a_h = a_mins // 60
        a_m = a_mins % 60
        a_str = f"{a_h}h {a_m}m" if a_h > 0 else f"{a_m}m"

        self.card_daily_avg.set_content(
            f"{c_str} / day",
            f"Active: {a_str}/day ({summary.active_days_count} active days)"
        )

        # Card 4: Goal Progress
        goal_h = goal_secs // 3600
        total_goal_h = summary.total_goal_seconds // 3600
        self.card_goal_progress.set_content(
            f"{summary.goal_completion_pct:.0f}% of target",
            f"Target: {goal_h}h/day ({total_goal_h}h period goal)"
        )

        # Card 5: Breaks & Rest
        b_h = summary.total_break_seconds // 3600
        b_m = (summary.total_break_seconds % 3600) // 60
        b_time_str = f"{b_h}h {b_m}m" if b_h > 0 else f"{b_m}m"
        self.card_breaks.set_content(
            f"{summary.completed_breaks} breaks",
            f"{b_time_str} total rest time"
        )

        # 2. Daily Trend Bar Chart
        trend: List[DailyTrendItem] = self.analytics.get_daily_trend(
            self.start_date, self.end_date, daily_goal_seconds=goal_secs
        )

        # Convert to chart format (label, float_hours)
        chart_data = []
        for item in trend:
            # If period <= 14 days, show "Mon 20", else show "20"
            if len(trend) <= 14:
                lbl = f"{item.day_name} {item.date_obj.day}"
            else:
                lbl = str(item.date_obj.day)
            h_val = round(item.focus_seconds / 3600.0, 2)
            chart_data.append((lbl, h_val))

        self.bar_chart.set_data(chart_data)
        self.lbl_chart_subtitle.setText(f"Daily focus hours across {len(trend)} days")

        # 3. Task Breakdown Table
        tasks: List[TaskBreakdownItem] = self.analytics.get_task_breakdown(self.start_date, self.end_date)
        self.task_table.setRowCount(len(tasks))

        for row_idx, t in enumerate(tasks):
            t_hrs = t.focus_seconds // 3600
            t_mins = (t.focus_seconds % 3600) // 60
            dur_str = f"{t_hrs}h {t_mins}m" if t_hrs > 0 else f"{t_mins}m"

            poms_str = f"{t.completed_pomodoros}"
            if t.estimated_pomodoros > 0:
                poms_str += f" / {t.estimated_pomodoros}"

            it_title = QTableWidgetItem(f"🎯 {t.task_title}")
            it_poms = QTableWidgetItem(poms_str)
            it_dur = QTableWidgetItem(dur_str)
            it_share = QTableWidgetItem(f"{t.pct_of_total:.1f}%")

            it_poms.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_share.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.task_table.setItem(row_idx, 0, it_title)
            self.task_table.setItem(row_idx, 1, it_poms)
            self.task_table.setItem(row_idx, 2, it_dur)
            self.task_table.setItem(row_idx, 3, it_share)

        if not tasks:
            self.task_table.setRowCount(1)
            empty_it = QTableWidgetItem("No tasks tracked in this period")
            empty_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.task_table.setItem(0, 0, empty_it)

        # 4. Outcome Mini Cards
        outcomes = self.analytics.get_outcome_distribution(self.start_date, self.end_date)
        self.card_out_comp.findChild(QLabel, "val").setText(str(outcomes["completed"]))
        self.card_out_stop.findChild(QLabel, "val").setText(str(outcomes["stopped"]))
        self.card_out_intr.findChild(QLabel, "val").setText(str(outcomes["interrupted"]))

        # Time of Day Distribution
        dist = self.repo.get_time_distribution(days=max(1, days_count))
        self.dist_bar.set_data(dist)

        # Highlights & Insights
        cur_streak = self.repo.get_productivity_streak()
        best_streak = self.repo.get_longest_streak()
        if summary.completed_pomodoros > 0:
            top_task = tasks[0].task_title if tasks else "None"
            high_text = (
                f"• Top Focus Area: <b>{top_task}</b><br>"
                f"• Active Streak: <b>{cur_streak} days</b> (Best: {best_streak} days)<br>"
                f"• Completion Rate: <b>{summary.goal_completion_pct:.0f}%</b> of your daily focus target"
            )
        else:
            high_text = f"• Active Streak: <b>{cur_streak} days</b><br>• Complete a focus session to generate productivity insights."
        self.lbl_highlights.setText(high_text)

    # -------------------------------------------------------------------------
    # CSV Export Dialog
    # -------------------------------------------------------------------------
    def _export_csv_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Export Analytics Report")
        msg.setText("Select which report format to export:")
        btn_daily = msg.addButton("Daily Totals CSV", QMessageBox.ButtonRole.ActionRole)
        btn_tasks = msg.addButton("Task Focus CSV", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_cancel:
            return

        is_daily = (clicked == btn_daily)
        default_name = f"focusflow_daily_{self.start_date}_{self.end_date}.csv" if is_daily else f"focusflow_tasks_{self.start_date}_{self.end_date}.csv"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Analytics Report CSV",
            str(Path.home() / default_name),
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            if is_daily:
                count = self.data_manager.export_daily_totals_csv(Path(path), self.start_date, self.end_date)
            else:
                count = self.data_manager.export_task_focus_csv(Path(path), self.start_date, self.end_date)
            QMessageBox.information(self, "Export Successful", f"Successfully exported {count} records to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not write CSV file:\n{e}")
