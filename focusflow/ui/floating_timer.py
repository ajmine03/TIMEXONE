"""
Always-on-top Floating Timer Widget for FocusFlow.
Features drag-to-move, compact mode toggle, opacity adjustment, and live controls.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QMenu
)
from PyQt6.QtGui import QMouseEvent, QAction, QFont, QColor
from PyQt6.QtCore import Qt, QPoint, pyqtSignal

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository


class FloatingTimerWidget(QWidget):
    """Minimal, borderless, always-on-top draggable timer widget."""

    visibility_changed = pyqtSignal(bool)
    open_dashboard_requested = pyqtSignal()

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

        # Window Flags: Always on Top, Frameless, Tool window (no taskbar clutter)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._drag_pos = QPoint()
        self.is_compact = False
        self.opacity = 0.95

        self._init_ui()
        self._load_saved_geometry()
        self._connect_signals()
        self._update_display(self.engine.remaining_seconds)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)

        # Outer rounded frame with dark styling
        self.frame = QFrame()
        self.frame.setObjectName("FloatingFrame")
        self.frame.setStyleSheet("""
            QFrame#FloatingFrame {
                background-color: rgba(24, 24, 37, 240);
                border: 1px solid #45475a;
                border-radius: 14px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
            QPushButton#CloseBtn {
                border: none;
                background: transparent;
                color: #6c7086;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#CloseBtn:hover {
                color: #ef4444;
            }
        """)

        self.card_layout = QVBoxLayout(self.frame)
        self.card_layout.setContentsMargins(12, 10, 12, 10)
        self.card_layout.setSpacing(6)

        # 1. Top Header Row (Status dot + State label + Compact Toggle + Close)
        self.header_row = QHBoxLayout()
        self.header_row.setSpacing(6)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #06b6d4; font-size: 12px;")
        self.header_row.addWidget(self.status_dot)

        self.state_label = QLabel("FOCUS")
        self.state_label.setStyleSheet("color: #a6adc8; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.header_row.addWidget(self.state_label)

        self.header_row.addStretch()

        self.btn_compact_toggle = QPushButton("⛶")
        self.btn_compact_toggle.setToolTip("Toggle Compact Mode")
        self.btn_compact_toggle.setFixedSize(22, 22)
        self.btn_compact_toggle.clicked.connect(self.toggle_compact_mode)
        self.header_row.addWidget(self.btn_compact_toggle)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("CloseBtn")
        self.btn_close.setToolTip("Hide Floating Timer")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.clicked.connect(self.hide)
        self.header_row.addWidget(self.btn_close)

        self.card_layout.addLayout(self.header_row)

        # 2. Digital Countdown Timer
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: bold; font-family: 'Inter', sans-serif;")
        self.card_layout.addWidget(self.time_label)

        # 3. Active Task Title
        self.task_label = QLabel("Ready to Focus")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setStyleSheet("color: #9399b2; font-size: 11px;")
        self.card_layout.addWidget(self.task_label)

        # 4. Control Buttons Row (Play/Pause, Stop, Dashboard)
        self.controls_row = QHBoxLayout()
        self.controls_row.setSpacing(6)
        self.controls_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_play_pause = QPushButton("▶")
        self.btn_play_pause.setFixedSize(32, 28)
        self.btn_play_pause.setToolTip("Start / Pause Timer")
        self.btn_play_pause.clicked.connect(self.engine.toggle_play_pause)
        self.controls_row.addWidget(self.btn_play_pause)

        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(32, 28)
        self.btn_stop.setToolTip("Stop Timer")
        self.btn_stop.clicked.connect(self.engine.stop)
        self.controls_row.addWidget(self.btn_stop)

        self.btn_more = QPushButton("⋮")
        self.btn_more.setFixedSize(28, 28)
        self.btn_more.setToolTip("Options")
        self.btn_more.clicked.connect(self._show_options_menu)
        self.controls_row.addWidget(self.btn_more)

        self.card_layout.addLayout(self.controls_row)

        root_layout.addWidget(self.frame)
        self.resize(220, 140)

    def _connect_signals(self):
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)

    def _load_saved_geometry(self):
        saved_x = self.repo.get_preference("floating_x", 120)
        saved_y = self.repo.get_preference("floating_y", 120)
        self.opacity = float(self.repo.get_preference("floating_opacity", 0.95))
        self.setWindowOpacity(self.opacity)
        self.move(int(saved_x), int(saved_y))

    def _save_geometry(self):
        self.repo.set_preference("floating_x", self.x())
        self.repo.set_preference("floating_y", self.y())

    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        if self.is_compact:
            self.task_label.hide()
            self.controls_row.setEnabled(False)
            # Hide individual widgets in controls row
            self.btn_play_pause.hide()
            self.btn_stop.hide()
            self.btn_more.hide()
            self.state_label.hide()
            self.time_label.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
            self.resize(150, 68)
        else:
            self.task_label.show()
            self.btn_play_pause.show()
            self.btn_stop.show()
            self.btn_more.show()
            self.state_label.show()
            self.time_label.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: bold;")
            self.resize(220, 140)

    def _on_tick(self, remaining: int, total: int, fraction: float):
        self._update_display(remaining)

    def _update_display(self, remaining: int):
        mins, secs = divmod(max(0, remaining), 60)
        self.time_label.setText(f"{mins:02d}:{secs:02d}")

        task_title = "Ready to Focus"
        if self.engine.active_task_id:
            task = self.task_manager.get(self.engine.active_task_id)
            if task:
                task_title = task.title
        if len(task_title) > 22:
            task_title = task_title[:19] + "..."
        self.task_label.setText(task_title)

    def _on_state_changed(self, new_state: TimerState):
        if new_state.is_paused:
            self.status_dot.setStyleSheet("color: #f59e0b; font-size: 12px;")
            self.state_label.setText("PAUSED")
            self.btn_play_pause.setText("▶")
        elif new_state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            self.status_dot.setStyleSheet("color: #10b981; font-size: 12px;")
            self.state_label.setText("BREAK")
            self.btn_play_pause.setText("⏸")
        elif new_state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            self.status_dot.setStyleSheet("color: #8b5cf6; font-size: 12px;")
            self.state_label.setText("LONG BREAK")
            self.btn_play_pause.setText("⏸")
        elif new_state == TimerState.RUNNING_FOCUS:
            self.status_dot.setStyleSheet("color: #06b6d4; font-size: 12px;")
            self.state_label.setText("FOCUS")
            self.btn_play_pause.setText("⏸")
        else: # IDLE
            self.status_dot.setStyleSheet("color: #64748b; font-size: 12px;")
            self.state_label.setText("IDLE")
            self.btn_play_pause.setText("▶")

        self._update_display(self.engine.remaining_seconds)

    def _show_options_menu(self):
        menu = QMenu(self)

        act_dash = QAction("Open Dashboard", self)
        act_dash.triggered.connect(self.open_dashboard_requested.emit)
        menu.addAction(act_dash)

        act_skip = QAction("Skip to Next", self)
        act_skip.triggered.connect(self.engine.skip)
        menu.addAction(act_skip)

        act_compact = QAction("Compact View" if not self.is_compact else "Expanded View", self)
        act_compact.triggered.connect(self.toggle_compact_mode)
        menu.addAction(act_compact)

        menu.addSeparator()

        # Opacity presets
        op_menu = menu.addMenu("Opacity")
        for val, label in [(1.0, "100%"), (0.85, "85%"), (0.70, "70%"), (0.50, "50%")]:
            op_act = QAction(label, self)
            op_act.triggered.connect(lambda ch, v=val: self.set_opacity(v))
            op_menu.addAction(op_act)

        menu.exec(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height())))

    def set_opacity(self, value: float):
        self.opacity = value
        self.setWindowOpacity(value)
        self.repo.set_preference("floating_opacity", value)

    # -------------------------------------------------------------------------
    # Drag-to-Move Window Event Handlers
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._save_geometry()
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibility_changed.emit(False)
