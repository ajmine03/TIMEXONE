"""
Productivity Dashboard View for FocusFlow.
Displays circular timer, active task controls, quick metrics, and upcoming tasks.
"""

from datetime import date
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository
from focusflow.ui.components.timer_display import TimerDisplayWidget


class DashboardView(QWidget):
    """Main dashboard combining timer controls, metrics, and active task assignment."""

    start_task_requested = pyqtSignal(str)  # task_id

    def __init__(
        self,
        engine: PomodoroEngine,
        task_manager: TaskManager,
        repository: Repository,
        parent=None,
    ):
        super().__init__(parent)
        self.engine = engine
        self.task_manager = task_manager
        self.repo = repository

        self._init_ui()
        self._connect_signals()
        self.refresh_dashboard()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # Header Title
        header_layout = QHBoxLayout()
        title_label = QLabel("Productivity Dashboard")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.date_label = QLabel(date.today().strftime("%A, %B %d, %Y"))
        self.date_label.setStyleSheet("font-size: 13px; color: #a6adc8;")
        header_layout.addWidget(self.date_label)
        main_layout.addLayout(header_layout)

        # Scrollable container for smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(20)

        # 1. Metric Cards Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(14)

        self.stat_focus_card = self._create_metric_card("FOCUSED TODAY", "0m", "#3b82f6")
        self.stat_pomodoro_card = self._create_metric_card("POMODOROS", "0", "#10b981")
        self.stat_tasks_card = self._create_metric_card("TASKS REMAINING", "0", "#f59e0b")
        self.stat_streak_card = self._create_metric_card("DAILY STREAK", "0 days 🔥", "#ec4899")

        metrics_layout.addWidget(self.stat_focus_card)
        metrics_layout.addWidget(self.stat_pomodoro_card)
        metrics_layout.addWidget(self.stat_tasks_card)
        metrics_layout.addWidget(self.stat_streak_card)
        container_layout.addLayout(metrics_layout)

        # 2. Main Timer Card
        timer_card = QFrame()
        timer_card.setProperty("class", "Card")
        timer_card_layout = QVBoxLayout(timer_card)
        timer_card_layout.setContentsMargins(20, 20, 20, 20)
        timer_card_layout.setSpacing(16)
        timer_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Circular timer widget
        self.timer_display = TimerDisplayWidget()
        timer_card_layout.addWidget(self.timer_display, alignment=Qt.AlignmentFlag.AlignCenter)

        # Task Selector Dropdown
        task_select_layout = QHBoxLayout()
        task_select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        task_label = QLabel("Active Task:")
        task_label.setStyleSheet("font-weight: 600; color: #a6adc8;")
        task_select_layout.addWidget(task_label)

        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(260)
        self.task_combo.currentIndexChanged.connect(self._on_task_selected)
        task_select_layout.addWidget(self.task_combo)
        timer_card_layout.addLayout(task_select_layout)

        # Controls Row (Start/Pause, Stop, Skip, Restart)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_play_pause = QPushButton("Start Focus")
        self.btn_play_pause.setProperty("class", "Primary")
        self.btn_play_pause.setMinimumSize(130, 42)
        self.btn_play_pause.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_play_pause.clicked.connect(self.engine.toggle_play_pause)
        controls_layout.addWidget(self.btn_play_pause)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setMinimumSize(85, 42)
        self.btn_stop.clicked.connect(self.engine.stop)
        self.btn_stop.setEnabled(False)
        controls_layout.addWidget(self.btn_stop)

        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setMinimumSize(85, 42)
        self.btn_skip.clicked.connect(self.engine.skip)
        controls_layout.addWidget(self.btn_skip)

        self.btn_restart = QPushButton("Restart")
        self.btn_restart.setMinimumSize(85, 42)
        self.btn_restart.clicked.connect(self.engine.restart)
        controls_layout.addWidget(self.btn_restart)

        timer_card_layout.addLayout(controls_layout)
        container_layout.addWidget(timer_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_metric_card(self, title: str, initial_value: str, color: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #6c7086; letter-spacing: 1px;")
        layout.addWidget(title_lbl)

        val_lbl = QLabel(initial_value)
        val_lbl.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        val_lbl.setObjectName("metric_value")
        layout.addWidget(val_lbl)

        return card

    def _connect_signals(self):
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)
        self.engine.subscribe_completed(lambda s, t: self.refresh_dashboard())
        self.task_manager.subscribe_change(self.refresh_tasks_dropdown)

    def _on_tick(self, remaining: int, total: int, fraction: float):
        task_title = ""
        if self.engine.active_task_id:
            task = self.task_manager.get(self.engine.active_task_id)
            if task:
                task_title = task.title
        self.timer_display.set_timer_data(remaining, total, fraction, self.engine.state, task_title)

    def _on_state_changed(self, new_state: TimerState):
        if new_state == TimerState.IDLE:
            self.btn_play_pause.setText("Start Focus")
            self.btn_play_pause.setProperty("class", "Primary")
            self.btn_stop.setEnabled(False)
        elif new_state.is_running:
            self.btn_play_pause.setText("Pause")
            self.btn_play_pause.setProperty("class", "")
            self.btn_stop.setEnabled(True)
        elif new_state.is_paused:
            self.btn_play_pause.setText("Resume")
            self.btn_play_pause.setProperty("class", "Success")
            self.btn_stop.setEnabled(True)

        self.btn_play_pause.style().unpolish(self.btn_play_pause)
        self.btn_play_pause.style().polish(self.btn_play_pause)

        # Trigger tick display update with current data
        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, 0.0)

    def _on_task_selected(self, index: int):
        task_id = self.task_combo.currentData()
        self.engine.set_active_task(task_id)
        # Update display immediately
        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, 0.0)

    def refresh_tasks_dropdown(self):
        current_id = self.task_combo.currentData()
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("None (General Focus)", None)

        pending_tasks = self.task_manager.list(filter_mode="all")
        selected_index = 0
        idx = 1
        for t in pending_tasks:
            if t.status != "completed":
                label = f"{t.title} ({t.completed_pomodoros}/{t.estimated_pomodoros} 🍅)"
                self.task_combo.addItem(label, t.id)
                if t.id == current_id or t.id == self.engine.active_task_id:
                    selected_index = idx
                idx += 1

        self.task_combo.setCurrentIndex(selected_index)
        self.task_combo.blockSignals(False)

    def refresh_dashboard(self):
        """Update metrics for today."""
        today_str = date.today().isoformat()
        stats = self.repo.get_daily_stats(today_str)

        # Focus time formatted
        hours = stats.total_focus_seconds // 3600
        mins = (stats.total_focus_seconds % 3600) // 60
        focus_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        self.stat_focus_card.findChild(QLabel, "metric_value").setText(focus_str)

        # Pomodoros completed
        self.stat_pomodoro_card.findChild(QLabel, "metric_value").setText(str(stats.pomodoros_completed))

        # Tasks remaining
        pending = self.task_manager.list(filter_mode="all")
        rem_count = sum(1 for t in pending if t.status != "completed")
        self.stat_tasks_card.findChild(QLabel, "metric_value").setText(str(rem_count))

        # Streak
        streak = self.repo.get_productivity_streak()
        self.stat_streak_card.findChild(QLabel, "metric_value").setText(f"{streak} days 🔥")

        self.refresh_tasks_dropdown()
