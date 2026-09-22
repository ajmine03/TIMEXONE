"""
Always-on-top Floating Timer Widget for FocusFlow.
Minimal, distraction-free desktop utility with reliable Wayland/X11 dragging,
multi-monitor safety, compact mode, and context menu.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMenu
)
from PyQt6.QtGui import QMouseEvent, QAction, QGuiApplication
from PyQt6.QtCore import Qt, QPoint, QSize, QRect, QEvent, QTimer, pyqtSignal

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository


class FloatingTimerWidget(QWidget):
    """
    Clean, minimal, always-on-top draggable floating timer widget.
    Works reliably on both Wayland (KDE Plasma, GNOME) and X11.
    """

    visibility_changed = pyqtSignal(bool)
    open_dashboard_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

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

        self.always_on_top = bool(self.repo.get_preference("floating_always_on_top", True))
        self.is_compact = bool(self.repo.get_preference("floating_compact", False))
        self.opacity = float(self.repo.get_preference("floating_opacity", 0.95))
        self.auto_hide_controls = bool(self.repo.get_preference("floating_auto_hide_controls", False))

        # Window Flags: Standard top-level Window + Frameless + Always on Top
        # Avoid Qt.WindowType.Tool on Wayland (KDE Plasma) because KWin does not keep Tool above other windows
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._dragging = False
        self._drag_start = QPoint()

        # Debounce timer to save coordinates after dragging finishes
        self._save_debounce_timer = QTimer(self)
        self._save_debounce_timer.setSingleShot(True)
        self._save_debounce_timer.setInterval(400)
        self._save_debounce_timer.timeout.connect(self.save_position)

        self._init_ui()
        self._load_saved_geometry()
        self._connect_signals()
        self._install_drag_filters()
        self._update_display(self.engine.remaining_seconds)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)

        # Main styled card frame
        self.frame = QFrame(self)
        self.frame.setObjectName("FloatingCard")
        self.frame.setStyleSheet("""
            QFrame#FloatingCard {
                background-color: rgba(22, 22, 32, 240);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 4px;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
        """)

        card_layout = QVBoxLayout(self.frame)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        # ---------------------------------------------------------------------
        # 1. Normal Mode Container
        # ---------------------------------------------------------------------
        self.normal_box = QWidget(self.frame)
        self.normal_layout = QVBoxLayout(self.normal_box)
        self.normal_layout.setContentsMargins(0, 0, 0, 0)
        self.normal_layout.setSpacing(3)
        self.normal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # State label (FOCUS, SHORT BREAK, PAUSED, etc.)
        self.state_label = QLabel("FOCUS", self.normal_box)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("color: #06b6d4; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        self.normal_layout.addWidget(self.state_label)

        # Countdown Timer (Big, clear, bold)
        self.time_label = QLabel("25:00", self.normal_box)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold; font-family: 'Inter', 'Noto Sans', sans-serif;")
        self.normal_layout.addWidget(self.time_label)

        # Task title (Subtle)
        self.task_label = QLabel("General Focus", self.normal_box)
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.normal_layout.addWidget(self.task_label)

        # Minimal controls row (Play/Pause, Stop, Menu)
        self.controls_row_widget = QWidget(self.normal_box)
        controls_row = QHBoxLayout(self.controls_row_widget)
        controls_row.setContentsMargins(0, 2, 0, 0)
        controls_row.setSpacing(6)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_play_pause = QPushButton("▶", self.controls_row_widget)
        self.btn_play_pause.setFixedSize(28, 24)
        self.btn_play_pause.setToolTip("Start / Pause Timer")
        self.btn_play_pause.clicked.connect(self.engine.toggle_play_pause)
        controls_row.addWidget(self.btn_play_pause)

        self.btn_stop = QPushButton("■", self.controls_row_widget)
        self.btn_stop.setFixedSize(28, 24)
        self.btn_stop.setToolTip("Stop Timer")
        self.btn_stop.clicked.connect(self.engine.stop)
        controls_row.addWidget(self.btn_stop)

        self.btn_more = QPushButton("⋮", self.controls_row_widget)
        self.btn_more.setFixedSize(24, 24)
        self.btn_more.setToolTip("Options (Right-click anywhere also opens menu)")
        self.btn_more.clicked.connect(self._show_options_from_btn)
        controls_row.addWidget(self.btn_more)

        self.normal_layout.addWidget(self.controls_row_widget)
        card_layout.addWidget(self.normal_box)

        # ---------------------------------------------------------------------
        # 2. Compact Mode Container: [ 24:37  ▶  ⋮ ]
        # ---------------------------------------------------------------------
        self.compact_box = QWidget(self.frame)
        compact_layout = QHBoxLayout(self.compact_box)
        compact_layout.setContentsMargins(2, 0, 2, 0)
        compact_layout.setSpacing(6)
        compact_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.compact_time_label = QLabel("25:00", self.compact_box)
        self.compact_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compact_time_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        compact_layout.addWidget(self.compact_time_label)

        self.compact_btn_play_pause = QPushButton("▶", self.compact_box)
        self.compact_btn_play_pause.setFixedSize(26, 22)
        self.compact_btn_play_pause.clicked.connect(self.engine.toggle_play_pause)
        compact_layout.addWidget(self.compact_btn_play_pause)

        self.compact_btn_more = QPushButton("⋮", self.compact_box)
        self.compact_btn_more.setFixedSize(22, 22)
        self.compact_btn_more.clicked.connect(self._show_options_from_compact_btn)
        compact_layout.addWidget(self.compact_btn_more)

        card_layout.addWidget(self.compact_box)
        root_layout.addWidget(self.frame)

        # Apply initial mode layout
        if self.is_compact:
            self.normal_box.hide()
            self.compact_box.show()
            self.resize(136, 40)
        else:
            self.compact_box.hide()
            self.normal_box.show()
            if self.auto_hide_controls:
                self.controls_row_widget.hide()
                self.resize(175, 84)
            else:
                self.resize(175, 110)

    def _install_drag_filters(self):
        """
        Installs an event filter on all non-button child widgets.
        Ensures dragging works from anywhere: text labels, frame background, margins.
        """
        self.installEventFilter(self)
        for child in self.findChildren(QWidget):
            if not isinstance(child, QPushButton):
                child.installEventFilter(self)

    def _connect_signals(self):
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)

    # -------------------------------------------------------------------------
    # Drag Event Filter: Native Wayland (KWin) & X11 Drag Handling
    # -------------------------------------------------------------------------
    def eventFilter(self, watched, event: QEvent) -> bool:
        # Never intercept events for buttons so clicks/hover work normally
        if isinstance(watched, QPushButton):
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                # 1. On Wayland (KDE Plasma) and X11: start native system move
                handle = self.windowHandle()
                if handle:
                    try:
                        if handle.startSystemMove():
                            return True
                    except Exception:
                        pass

                # 2. Client-side move fallback (X11 / offscreen)
                self._dragging = True
                self._drag_start = event.globalPosition().toPoint() - self.pos()
                return True

            elif event.button() == Qt.MouseButton.RightButton:
                self.open_context_menu(event.globalPosition().toPoint())
                return True

        elif event.type() == QEvent.Type.MouseMove:
            if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag_start)
                return True

        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self._dragging:
                self._dragging = False
                self.save_position()
                return True

        return super().eventFilter(watched, event)

    def moveEvent(self, event):
        super().moveEvent(event)
        # When moved by Wayland compositor, debounce saving the new coordinates
        self._save_debounce_timer.start()

    # -------------------------------------------------------------------------
    # Multi-Monitor Safety & Persistence
    # -------------------------------------------------------------------------
    @staticmethod
    def ensure_on_screen(pos: QPoint, size: QSize) -> QPoint:
        """
        Verify that pos is within the visible bounds of at least one connected screen.
        If off-screen or an external monitor was disconnected, fallback to primary screen.
        """
        screens = QGuiApplication.screens()
        if not screens:
            return pos

        widget_rect = QRect(pos, size)
        for screen in screens:
            avail = screen.availableGeometry()
            intersection = avail.intersected(widget_rect)
            if intersection.width() >= 20 and intersection.height() >= 20:
                return pos

        # Off-screen fallback
        primary = QGuiApplication.primaryScreen() or screens[0]
        avail = primary.availableGeometry()
        safe_x = avail.x() + avail.width() - size.width() - 32
        safe_y = avail.y() + 48
        return QPoint(safe_x, safe_y)

    def _load_saved_geometry(self):
        saved_x = int(self.repo.get_preference("floating_x", 120))
        saved_y = int(self.repo.get_preference("floating_y", 120))
        self.set_opacity(self.opacity)

        safe_pos = self.ensure_on_screen(QPoint(saved_x, saved_y), self.size())
        self.move(safe_pos)

    def save_position(self):
        """Save current widget coordinates to preferences."""
        self.repo.set_preference("floating_x", self.x())
        self.repo.set_preference("floating_y", self.y())

    # -------------------------------------------------------------------------
    # Auto-Hide Controls on Hover
    # -------------------------------------------------------------------------
    def enterEvent(self, event):
        super().enterEvent(event)
        if self.auto_hide_controls and not self.is_compact:
            self.controls_row_widget.show()
            self.resize(175, 110)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self.auto_hide_controls and not self.is_compact:
            self.controls_row_widget.hide()
            self.resize(175, 84)

    # -------------------------------------------------------------------------
    # Mode, Opacity & Always-On-Top Toggles
    # -------------------------------------------------------------------------
    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        self.repo.set_preference("floating_compact", self.is_compact)
        if self.is_compact:
            self.normal_box.hide()
            self.compact_box.show()
            self.resize(136, 40)
        else:
            self.compact_box.hide()
            self.normal_box.show()
            if self.auto_hide_controls:
                self.controls_row_widget.hide()
                self.resize(175, 84)
            else:
                self.controls_row_widget.show()
                self.resize(175, 110)
        self._reinstall_filters_later()

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.repo.set_preference("floating_always_on_top", self.always_on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        self.show()
        if self.always_on_top:
            self.raise_()

    def toggle_auto_hide_controls(self):
        self.auto_hide_controls = not self.auto_hide_controls
        self.repo.set_preference("floating_auto_hide_controls", self.auto_hide_controls)
        if not self.is_compact:
            if self.auto_hide_controls:
                self.controls_row_widget.hide()
                self.resize(175, 84)
            else:
                self.controls_row_widget.show()
                self.resize(175, 110)

    def set_opacity(self, value: float):
        self.opacity = value
        self.setWindowOpacity(value)
        self.repo.set_preference("floating_opacity", value)

    def _reinstall_filters_later(self):
        QTimer.singleShot(50, self._install_drag_filters)

    # -------------------------------------------------------------------------
    # Timer Event Observers
    # -------------------------------------------------------------------------
    def _on_tick(self, remaining: int, total: int, fraction: float):
        self._update_display(remaining)

    def _update_display(self, remaining: int):
        mins, secs = divmod(max(0, remaining), 60)
        time_text = f"{mins:02d}:{secs:02d}"
        self.time_label.setText(time_text)
        self.compact_time_label.setText(time_text)

        task_title = "General Focus"
        if self.engine.active_task_id:
            task = self.task_manager.get(self.engine.active_task_id)
            if task:
                task_title = task.title
        if len(task_title) > 20:
            task_title = task_title[:17] + "..."
        self.task_label.setText(task_title)

    def _on_state_changed(self, new_state: TimerState):
        if new_state.is_paused:
            self.state_label.setText("PAUSED")
            self.state_label.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
            self.btn_play_pause.setText("▶")
            self.compact_btn_play_pause.setText("▶")
        elif new_state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            self.state_label.setText("SHORT BREAK")
            self.state_label.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
            self.btn_play_pause.setText("⏸")
            self.compact_btn_play_pause.setText("⏸")
        elif new_state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            self.state_label.setText("LONG BREAK")
            self.state_label.setStyleSheet("color: #8b5cf6; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
            self.btn_play_pause.setText("⏸")
            self.compact_btn_play_pause.setText("⏸")
        elif new_state == TimerState.RUNNING_FOCUS:
            self.state_label.setText("FOCUS")
            self.state_label.setStyleSheet("color: #06b6d4; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
            self.btn_play_pause.setText("⏸")
            self.compact_btn_play_pause.setText("⏸")
        else:  # IDLE
            self.state_label.setText("IDLE")
            self.state_label.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
            self.btn_play_pause.setText("▶")
            self.compact_btn_play_pause.setText("▶")

        self._update_display(self.engine.remaining_seconds)
        if self.always_on_top:
            self.raise_()

    # -------------------------------------------------------------------------
    # Context Menu
    # -------------------------------------------------------------------------
    def _show_options_from_btn(self):
        self.open_context_menu(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height())))

    def _show_options_from_compact_btn(self):
        self.open_context_menu(self.compact_btn_more.mapToGlobal(QPoint(0, self.compact_btn_more.height())))

    def open_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)

        # Title
        title_act = QAction("FocusFlow", self)
        title_act.setEnabled(False)
        menu.addAction(title_act)
        menu.addSeparator()

        # Timer Controls
        if self.engine.state.is_running:
            act_play = QAction("Pause Timer", self)
            act_play.triggered.connect(self.engine.pause)
            menu.addAction(act_play)
        elif self.engine.state.is_paused:
            act_play = QAction("Resume Timer", self)
            act_play.triggered.connect(self.engine.resume)
            menu.addAction(act_play)
        else:
            act_play = QAction("Start Pomodoro", self)
            act_play.triggered.connect(self.engine.start)
            menu.addAction(act_play)

        act_stop = QAction("Stop Timer", self)
        act_stop.triggered.connect(self.engine.stop)
        act_stop.setEnabled(self.engine.state != TimerState.IDLE)
        menu.addAction(act_stop)

        act_skip = QAction("Skip Session", self)
        act_skip.triggered.connect(self.engine.skip)
        menu.addAction(act_skip)

        menu.addSeparator()

        # Change Task Submenu
        task_menu = menu.addMenu("Change Task")
        act_no_task = QAction("None (General Focus)", self)
        act_no_task.triggered.connect(lambda: self.engine.set_active_task(None))
        task_menu.addAction(act_no_task)
        task_menu.addSeparator()

        tasks = self.task_manager.list(filter_mode="all")
        for t in tasks:
            if t.status != "completed":
                t_act = QAction(f"{t.title} ({t.completed_pomodoros}/{t.estimated_pomodoros} 🍅)", self)
                t_act.triggered.connect(lambda ch, tid=t.id: self.engine.set_active_task(tid))
                task_menu.addAction(t_act)

        menu.addSeparator()

        # Always on Top Toggle
        act_above = QAction("Keep Always on Top", self)
        act_above.setCheckable(True)
        act_above.setChecked(self.always_on_top)
        act_above.triggered.connect(self.toggle_always_on_top)
        menu.addAction(act_above)

        # Modes & Appearance
        act_compact = QAction("Compact Mode", self)
        act_compact.setCheckable(True)
        act_compact.setChecked(self.is_compact)
        act_compact.triggered.connect(self.toggle_compact_mode)
        menu.addAction(act_compact)

        act_autohide = QAction("Hide Controls Automatically", self)
        act_autohide.setCheckable(True)
        act_autohide.setChecked(self.auto_hide_controls)
        act_autohide.triggered.connect(self.toggle_auto_hide_controls)
        menu.addAction(act_autohide)

        op_menu = menu.addMenu("Opacity")
        for val, label in [(1.0, "100%"), (0.85, "85%"), (0.70, "70%"), (0.50, "50%")]:
            op_act = QAction(label, self)
            op_act.setCheckable(True)
            op_act.setChecked(abs(self.opacity - val) < 0.05)
            op_act.triggered.connect(lambda ch, v=val: self.set_opacity(v))
            op_menu.addAction(op_act)

        menu.addSeparator()

        # Navigation & System
        act_dash = QAction("Show Dashboard", self)
        act_dash.triggered.connect(self.open_dashboard_requested.emit)
        menu.addAction(act_dash)

        act_settings = QAction("Settings", self)
        act_settings.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)

        menu.exec(global_pos)

    def showEvent(self, event):
        super().showEvent(event)
        if self.always_on_top:
            self.raise_()
        self.visibility_changed.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibility_changed.emit(False)
