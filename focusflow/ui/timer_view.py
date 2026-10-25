"""
Dedicated Full-Screen Focus Timer View for FocusFlow.
Provides an immersive, distraction-free environment with large circular progress ring,
segmented mode switcher, active task selector, and timer controls.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository
from focusflow.ui.components.timer_display import TimerDisplayWidget
from focusflow.config import format_duration_short


class TimerView(QWidget):
    """Dedicated distraction-free Pomodoro & Break timer screen."""

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
        self._wire_engine()
        self.refresh_timer_state()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered Master Focus Card
        self.card = QFrame()
        self.card.setProperty("class", "Card")
        self.card.setMaximumWidth(680)
        self.card.setMinimumWidth(440)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(18)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Header Title
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        header_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel("Focus Timer")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(title_lbl)

        sub_lbl = QLabel("Distraction-free deep work & recharge session")
        sub_lbl.setStyleSheet("font-size: 12px; color: #8a95af;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(sub_lbl)
        card_layout.addLayout(header_box)

        # Mode Segmented Control Row
        self.mode_row = QHBoxLayout()
        self.mode_row.setSpacing(0)
        self.mode_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_pomo = QPushButton("Pomodoro")
        self.btn_short = QPushButton("Short Break")
        self.btn_long = QPushButton("Long Break")

        for b in (self.btn_pomo, self.btn_short, self.btn_long):
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_pomo.clicked.connect(lambda: self._on_mode_switched("focus"))
        self.btn_short.clicked.connect(lambda: self._on_mode_switched("short_break"))
        self.btn_long.clicked.connect(lambda: self._on_mode_switched("long_break"))

        self.mode_row.addWidget(self.btn_pomo)
        self.mode_row.addWidget(self.btn_short)
        self.mode_row.addWidget(self.btn_long)
        card_layout.addLayout(self.mode_row)

        # Large Circular Timer Ring
        self.timer_ring = TimerDisplayWidget(self.card)
        self.timer_ring.setFixedSize(260, 260)
        card_layout.addWidget(self.timer_ring, alignment=Qt.AlignmentFlag.AlignCenter)

        # Active Task Selector Box
        task_box = QHBoxLayout()
        task_box.setSpacing(8)
        task_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_task_icon = QLabel("🎯")
        lbl_task_icon.setStyleSheet("font-size: 14px;")
        task_box.addWidget(lbl_task_icon)

        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(260)
        self.task_combo.setMaximumWidth(380)
        self.task_combo.currentIndexChanged.connect(self._on_task_selected)
        task_box.addWidget(self.task_combo)
        card_layout.addLayout(task_box)

        # Primary Control Buttons: Play/Pause, Stop, Restart, Skip
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(12)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_restart = QPushButton("↺")
        self.btn_restart.setToolTip("Restart Timer")
        self.btn_restart.setFixedSize(40, 40)
        self.btn_restart.setStyleSheet("""
            QPushButton {
                background-color: #141b2c;
                color: #cbd5e1;
                border: 1px solid #1e263d;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #232c45;
                color: #ffffff;
            }
        """)
        self.btn_restart.clicked.connect(self.engine.restart)
        ctrl_layout.addWidget(self.btn_restart)

        # Prominent Start/Pause Button
        self.btn_play_pause = QPushButton("▶  Start Focus")
        self.btn_play_pause.setMinimumWidth(160)
        self.btn_play_pause.setFixedHeight(44)
        self.btn_play_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_pause.clicked.connect(self._on_play_pause_clicked)
        ctrl_layout.addWidget(self.btn_play_pause)

        # Stop Button
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setToolTip("Stop Session")
        self.btn_stop.setFixedSize(40, 40)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #141b2c;
                color: #cbd5e1;
                border: 1px solid #1e263d;
                border-radius: 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ef444422;
                color: #ef4444;
                border-color: #ef444455;
            }
        """)
        self.btn_stop.clicked.connect(self.engine.stop)
        ctrl_layout.addWidget(self.btn_stop)

        # Skip Button
        self.btn_skip = QPushButton("⏭")
        self.btn_skip.setToolTip("Skip to Next Phase")
        self.btn_skip.setFixedSize(40, 40)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background-color: #141b2c;
                color: #cbd5e1;
                border: 1px solid #1e263d;
                border-radius: 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #232c45;
                color: #ffffff;
            }
        """)
        self.btn_skip.clicked.connect(self.engine.skip)
        ctrl_layout.addWidget(self.btn_skip)

        card_layout.addLayout(ctrl_layout)

        # Bottom Day Metrics Pill
        self.stats_pill = QFrame()
        self.stats_pill.setStyleSheet("""
            QFrame {
                background-color: #0b0f19;
                border: 1px solid #192237;
                border-radius: 12px;
                padding: 6px 14px;
            }
        """)
        pill_layout = QHBoxLayout(self.stats_pill)
        pill_layout.setContentsMargins(10, 4, 10, 4)
        pill_layout.setSpacing(14)

        self.lbl_day_focus = QLabel("Focus: 0m")
        self.lbl_day_focus.setStyleSheet("font-size: 12px; font-weight: 600; color: #818cf8;")
        pill_layout.addWidget(self.lbl_day_focus)

        self.lbl_day_pomos = QLabel("Pomodoros: 0")
        self.lbl_day_pomos.setStyleSheet("font-size: 12px; font-weight: 600; color: #10b981;")
        pill_layout.addWidget(self.lbl_day_pomos)

        self.lbl_cycle = QLabel("Cycle: 1/4")
        self.lbl_cycle.setStyleSheet("font-size: 12px; font-weight: 500; color: #94a3b8;")
        pill_layout.addWidget(self.lbl_cycle)

        card_layout.addWidget(self.stats_pill, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)

        self._update_mode_segmented_style()

    def _wire_engine(self):
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)
        self.engine.subscribe_completed(self._on_completed)

    def _update_mode_segmented_style(self):
        active_mode = "focus"
        if self.engine.state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            active_mode = "short_break"
        elif self.engine.state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            active_mode = "long_break"

        self.btn_pomo.setChecked(active_mode == "focus")
        self.btn_short.setChecked(active_mode == "short_break")
        self.btn_long.setChecked(active_mode == "long_break")

        base_style = """
            QPushButton {
                background-color: #121827;
                color: #8a95af;
                border: 1px solid #1e263d;
                padding: 7px 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1a2236;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
                border-color: #3b82f6;
            }
        """
        self.btn_pomo.setStyleSheet(base_style + "border-top-left-radius: 12px; border-bottom-left-radius: 12px; border-right: none;")
        self.btn_short.setStyleSheet(base_style + "border-left: none; border-right: none;")
        self.btn_long.setStyleSheet(base_style + "border-top-right-radius: 12px; border-bottom-right-radius: 12px; border-left: none;")

    def _on_mode_switched(self, mode: str):
        self.engine.switch_mode(mode)
        self._update_mode_segmented_style()
        self.refresh_timer_state()

    def _on_play_pause_clicked(self):
        if self.engine.state == TimerState.IDLE:
            if not self.engine.active_task_id and self.repo.get_preference("prompt_no_task", True):
                from focusflow.ui.components.no_task_dialog import NoTaskDialog
                dlg = NoTaskDialog(self.task_manager, self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    if dlg.dont_ask_again:
                        self.repo.set_preference("prompt_no_task", False)
                    if dlg.selected_task_id:
                        self.engine.set_active_task(dlg.selected_task_id)
                    self.engine.start(task_id=dlg.selected_task_id)
                    return
                else:
                    return

        self.engine.toggle_play_pause()

    def _on_task_selected(self, idx: int):
        task_id = self.task_combo.currentData()
        if task_id:
            self.engine.set_active_task(task_id)
        else:
            self.engine.set_active_task(None)

    def _on_tick(self, remaining: int, total: int, fraction: float):
        task_title = ""
        if self.engine.active_task_id:
            t = self.task_manager.get_task(self.engine.active_task_id)
            if t:
                task_title = t.title
        self.timer_ring.set_timer_data(remaining, total, fraction, self.engine.state, task_title)

    def _on_state_changed(self, new_state: TimerState):
        self._update_mode_segmented_style()
        if new_state == TimerState.IDLE:
            self.btn_play_pause.setText("▶  Start Focus")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                    color: #ffffff;
                    border: none;
                    border-radius: 22px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
                }
            """)
        elif new_state.is_running:
            self.btn_play_pause.setText("⏸  Pause")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                    color: #ffffff;
                    border: none;
                    border-radius: 22px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
                }
            """)
        elif new_state.is_paused:
            self.btn_play_pause.setText("▶  Resume")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #d97706);
                    color: #ffffff;
                    border: none;
                    border-radius: 22px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #b45309);
                }
            """)

        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, self.engine.progress_fraction)
        self.refresh_stats()

    def _on_completed(self, session_type: str, session_id: Optional[int]):
        self.refresh_timer_state()

    def refresh_task_dropdown(self):
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("No specific task (Free Flow)", None)

        tasks = self.task_manager.get_active_tasks()
        active_idx = 0
        for i, t in enumerate(tasks, start=1):
            pomo_badge = f"[{t.completed_pomodoros}/{t.estimated_pomodoros}] " if t.estimated_pomodoros > 0 else ""
            self.task_combo.addItem(f"{pomo_badge}{t.title}", t.id)
            if self.engine.active_task_id == t.id:
                active_idx = i

        self.task_combo.setCurrentIndex(active_idx)
        self.task_combo.blockSignals(False)

    def refresh_stats(self):
        from datetime import date
        today = date.today().isoformat()
        daily = self.repo.get_daily_stats(today)
        focus_s = daily.total_focus_seconds if daily else 0
        pomos = getattr(daily, "pomodoros_completed", getattr(daily, "completed_pomodoros", 0)) if daily else 0

        self.lbl_day_focus.setText(f"Focus: {format_duration_short(focus_s)}")
        self.lbl_day_pomos.setText(f"Pomodoros: {pomos}")

        interval = getattr(self.engine, "long_break_interval", 4)
        cycles = getattr(self.engine, "completed_cycles_today", 0)
        cycle_idx = (cycles % interval) + 1
        self.lbl_cycle.setText(f"Cycle: {cycle_idx}/{interval}")

    def refresh_timer_state(self):
        self.refresh_task_dropdown()
        self._update_mode_segmented_style()
        self._on_state_changed(self.engine.state)
        self.refresh_stats()
