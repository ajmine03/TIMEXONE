"""
Always-on-top Floating Timer Widget for FocusFlow.
Redesigned to match Image 4's exact bottom-right floating widget.
Features dark glass aesthetic, glowing border, fluid wave background,
header-based dragging, pin/minimize/close window controls, and circular gradient action buttons.
"""

from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMenu, QApplication
)
from PyQt6.QtGui import (
    QMouseEvent, QAction, QGuiApplication, QPainter, QColor, QPen,
    QLinearGradient, QPainterPath, QFont, QIcon, QPixmap
)
from PyQt6.QtCore import Qt, QPoint, QSize, QRect, QRectF, QTimer, pyqtSignal
from PyQt6.QtSvg import QSvgRenderer

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository
from focusflow.config import TOMATO_PATH


def configure_kwin_keep_above(enable: bool = True):
    """
    Configures a KDE Plasma KWin window rule to force Keep Above for the floating timer.
    Works natively on KDE Plasma Wayland and X11 to keep widget above all windows.
    """
    import os
    import configparser
    import subprocess

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    if "KDE" not in desktop and not (Path.home() / ".config" / "kwinrc").exists():
        return

    rule_id = "focusflow-floating-above"
    config_path = Path.home() / ".config" / "kwinrulesrc"

    try:
        config = configparser.ConfigParser(interpolation=None)
        if config_path.exists():
            config.read(str(config_path), encoding="utf-8")

        if not config.has_section("General"):
            config.add_section("General")

        existing_rules = [r.strip() for r in config.get("General", "rules", fallback="").split(",") if r.strip()]

        if enable:
            if rule_id not in existing_rules:
                existing_rules.append(rule_id)

            if not config.has_section(rule_id):
                config.add_section(rule_id)

            config.set(rule_id, "Description", "FocusFlow Floating Timer Keep Above")
            config.set(rule_id, "above", "true")
            config.set(rule_id, "aboverule", "2")
            config.set(rule_id, "title", "FocusFlow Floating")
            config.set(rule_id, "titlematch", "2")
            config.set(rule_id, "wmclass", "focusflow")
            config.set(rule_id, "wmclasscomplete", "false")
            config.set(rule_id, "wmclassmatch", "2")

            config.set("General", "rules", ",".join(existing_rules))
            config.set("General", "count", str(len(existing_rules)))
        else:
            if rule_id in existing_rules:
                existing_rules.remove(rule_id)
                config.set("General", "rules", ",".join(existing_rules))
                config.set("General", "count", str(len(existing_rules)))
            if config.has_section(rule_id):
                config.remove_section(rule_id)

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

        for cmd in [
            ["qdbus6", "org.kde.KWin", "/KWin", "reconfigure"],
            ["qdbus", "org.kde.KWin", "/KWin", "reconfigure"],
            ["dbus-send", "--session", "--dest=org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure"],
        ]:
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                break
            except Exception:
                continue
    except Exception:
        pass


class FloatingTimerFrame(QFrame):
    """Styled frame with custom painted wavy glow and gradient border."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FloatingCard")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 16.0
        rect = QRectF(1, 1, w - 2, h - 2)

        # 1. Base dark navy background
        painter.setBrush(QColor(14, 18, 32, 245))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        # 2. Bottom Decorative Waves (blue/purple fluid glow matching Image 4)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, radius, radius)
        painter.save()
        painter.setClipPath(clip_path)

        # First wave (deep blue-purple)
        wave1 = QPainterPath()
        wave1.moveTo(0, h)
        wave1.lineTo(0, h - 35)
        wave1.cubicTo(w * 0.25, h - 55, w * 0.65, h - 15, w, h - 40)
        wave1.lineTo(w, h)
        wave1.closeSubpath()

        grad1 = QLinearGradient(0, h - 55, w, h)
        grad1.setColorAt(0.0, QColor(59, 130, 246, 120))  # Electric blue
        grad1.setColorAt(1.0, QColor(139, 92, 246, 80))   # Violet
        painter.fillPath(wave1, grad1)

        # Second wave (soft magenta-purple)
        wave2 = QPainterPath()
        wave2.moveTo(0, h)
        wave2.lineTo(0, h - 20)
        wave2.cubicTo(w * 0.35, h - 10, w * 0.70, h - 45, w, h - 25)
        wave2.lineTo(w, h)
        wave2.closeSubpath()

        grad2 = QLinearGradient(0, h - 45, w, h)
        grad2.setColorAt(0.0, QColor(168, 85, 247, 90))
        grad2.setColorAt(1.0, QColor(236, 72, 153, 60))
        painter.fillPath(wave2, grad2)

        painter.restore()

        # 3. Gradient Border (pink/purple gradient outline)
        border_grad = QLinearGradient(0, 0, w, h)
        border_grad.setColorAt(0.0, QColor(168, 85, 247, 180)) # Purple
        border_grad.setColorAt(0.5, QColor(99, 102, 241, 120)) # Indigo
        border_grad.setColorAt(1.0, QColor(236, 72, 153, 160)) # Pink

        border_pen = QPen(border_grad, 1.5)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        painter.end()


class PinButton(QPushButton):
    """Clean vector pushpin button that renders without missing emoji font glyphs."""

    def __init__(self, is_pinned: bool = True, parent=None):
        super().__init__(parent)
        self.is_pinned = is_pinned
        self.setFixedSize(20, 20)
        self.setToolTip("Always on Top")

    def set_pinned(self, pinned: bool):
        self.is_pinned = pinned
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor("#38bdf8") if self.is_pinned else QColor("#8a95af")
        if self.underMouse():
            color = QColor("#ffffff")

        painter.setPen(QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        # Needle pointing down-left
        painter.drawLine(8, 12, 4, 16)
        # Pin head bar
        painter.drawLine(7, 7, 13, 13)
        # Pin top cap
        painter.drawLine(11, 5, 15, 9)
        # Stem
        painter.drawLine(10, 10, 13, 7)
        painter.end()


class DraggableHeader(QWidget):
    """Header area specifically designed for dragging the floating window."""

    def __init__(self, target_window, parent=None):
        super().__init__(parent)
        self.target_window = target_window
        self._dragging = False
        self._drag_start = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.target_window.windowHandle()
            if handle:
                try:
                    if handle.startSystemMove():
                        return
                except Exception:
                    pass

            self._dragging = True
            self._drag_start = event.globalPosition().toPoint() - self.target_window.pos()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.target_window.open_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.target_window.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging:
            self._dragging = False
            self.target_window.save_position()
            event.accept()


class FloatingTimerWidget(QWidget):
    """
    Floating timer widget matching Image 4's bottom-right design.
    Features header dragging, pin/minimize/close, circular controls, and state sync.
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

        self.setWindowTitle("FocusFlow Floating Timer")
        self.setObjectName("focusflow_floating")

        self.always_on_top = bool(self.repo.get_preference("floating_always_on_top", True))
        self.is_compact = bool(self.repo.get_preference("floating_compact", False))
        self.opacity = float(self.repo.get_preference("floating_opacity", 0.98))
        self.auto_hide_controls = bool(self.repo.get_preference("floating_auto_hide_controls", False))

        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        if self.always_on_top:
            configure_kwin_keep_above(True)

        self._save_debounce_timer = QTimer(self)
        self._save_debounce_timer.setSingleShot(True)
        self._save_debounce_timer.setInterval(400)
        self._save_debounce_timer.timeout.connect(self.save_position)

        self._init_ui()
        self._load_saved_geometry()
        self._connect_signals()
        self._update_display(self.engine.remaining_seconds)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)

        self.frame = FloatingTimerFrame(self)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(12, 10, 12, 12)
        frame_layout.setSpacing(6)

        # ---------------------------------------------------------------------
        # Header (Tomato icon, "FocusFlow", Pin, Minimize, Close)
        # ---------------------------------------------------------------------
        self.header = DraggableHeader(self, self.frame)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        # Tomato icon
        self.lbl_logo = QLabel(self.header)
        self.lbl_logo.setFixedSize(16, 16)
        if TOMATO_PATH.exists():
            pix = QPixmap(str(TOMATO_PATH)).scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_logo.setPixmap(pix)
        else:
            self.lbl_logo.setText("🍅")
        header_layout.addWidget(self.lbl_logo)

        # Title
        title_lbl = QLabel("FocusFlow", self.header)
        title_lbl.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        # Window Controls: Pin, Minimize, Close
        btn_style = """
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
        """

        # Pin / Always on Top
        self.btn_pin = PinButton(self.always_on_top, self.header)
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        header_layout.addWidget(self.btn_pin)

        # Minimize to dashboard / tray
        self.btn_min = QPushButton("—", self.header)
        self.btn_min.setFixedSize(20, 20)
        self.btn_min.setToolTip("Minimize / Open Dashboard")
        self.btn_min.setStyleSheet(btn_style)
        self.btn_min.clicked.connect(self.open_dashboard_requested.emit)
        header_layout.addWidget(self.btn_min)

        # Close button (Hides floating widget without stopping timer)
        self.btn_close = QPushButton("✕", self.header)
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setToolTip("Close Floating Timer (Session continues)")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 11px;
                padding: 2px 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.hide)
        header_layout.addWidget(self.btn_close)

        frame_layout.addWidget(self.header)

        # ---------------------------------------------------------------------
        # Center: Countdown + Subtitle
        # ---------------------------------------------------------------------
        center_layout = QVBoxLayout()
        center_layout.setSpacing(2)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel("25:00", self.frame)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: bold; font-family: 'Inter', -apple-system, monospace;")
        time_font = self.time_label.font()
        time_font.setPointSize(26)
        time_font.setBold(True)
        try:
            time_font.setFeature(QFont.Tag.fromString("tnum"), 1)
        except Exception:
            pass
        self.time_label.setFont(time_font)
        center_layout.addWidget(self.time_label)

        self.task_label = QLabel("Focus Session", self.frame)
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setStyleSheet("color: #8a95af; font-size: 11px; font-weight: 500;")
        center_layout.addWidget(self.task_label)

        frame_layout.addLayout(center_layout)

        # ---------------------------------------------------------------------
        # Bottom Controls: Circular [Play/Pause], [Restart], [Stop]
        # ---------------------------------------------------------------------
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Circular Play/Pause (large gradient button)
        self.btn_play_pause = QPushButton("▶", self.frame)
        self.btn_play_pause.setFixedSize(38, 38)
        self.btn_play_pause.setToolTip("Start / Pause Session")
        self.btn_play_pause.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
                border: none;
                border-radius: 19px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #7c3aed);
            }
        """)
        self.btn_play_pause.clicked.connect(self.engine.toggle_play_pause)
        controls_layout.addWidget(self.btn_play_pause)

        # 2. Circular Restart Button (↺)
        self.btn_restart = QPushButton("↺", self.frame)
        self.btn_restart.setFixedSize(32, 32)
        self.btn_restart.setToolTip("Restart Session")
        self.btn_restart.setStyleSheet("""
            QPushButton {
                background-color: #1a2238;
                color: #cbd5e1;
                border: 1px solid #2d3a5e;
                border-radius: 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #263352;
                color: #ffffff;
            }
        """)
        self.btn_restart.clicked.connect(self.engine.restart)
        controls_layout.addWidget(self.btn_restart)

        # 3. Circular Stop Button (■)
        self.btn_stop = QPushButton("■", self.frame)
        self.btn_stop.setFixedSize(32, 32)
        self.btn_stop.setToolTip("Stop Session")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #1a2238;
                color: #cbd5e1;
                border: 1px solid #2d3a5e;
                border-radius: 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b1d28;
                border-color: #ef4444;
                color: #ef4444;
            }
        """)
        self.btn_stop.clicked.connect(self.engine.stop)
        controls_layout.addWidget(self.btn_stop)

        frame_layout.addLayout(controls_layout)
        root_layout.addWidget(self.frame)

        self.resize(220, 150)

    def _connect_signals(self):
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)

    def _on_tick(self, remaining: int, total: int, fraction: float):
        self._update_display(remaining)

    def _update_display(self, remaining: int):
        mins, secs = divmod(max(0, remaining), 60)
        time_text = f"{mins:02d}:{secs:02d}"
        self.time_label.setText(time_text)

        # Label: Task title if assigned, otherwise session type
        task_label_text = "Focus Session"
        if self.engine.active_task_id:
            task = self.task_manager.get(self.engine.active_task_id)
            if task:
                task_label_text = task.title
        elif self.engine.state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            task_label_text = "Short Break"
        elif self.engine.state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            task_label_text = "Long Break"

        if len(task_label_text) > 22:
            task_label_text = task_label_text[:19] + "..."
        self.task_label.setText(task_label_text)

    def _on_state_changed(self, new_state: TimerState):
        if new_state.is_paused:
            self.btn_play_pause.setText("▶")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10b981, stop:1 #059669);
                    color: #ffffff;
                    border: none;
                    border-radius: 19px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        elif new_state.is_running:
            self.btn_play_pause.setText("⏸")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                    color: #ffffff;
                    border: none;
                    border-radius: 19px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        else: # IDLE
            self.btn_play_pause.setText("▶")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #6366f1);
                    color: #ffffff;
                    border: none;
                    border-radius: 19px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)

        self._update_display(self.engine.remaining_seconds)
        if self.always_on_top:
            self.raise_()

    @staticmethod
    def ensure_on_screen(pos: QPoint, size: QSize) -> QPoint:
        """Verify widget position is visible; fallback safely if off-screen."""
        screens = QGuiApplication.screens()
        if not screens:
            return pos

        widget_rect = QRect(pos, size)
        for screen in screens:
            avail = screen.availableGeometry()
            intersection = avail.intersected(widget_rect)
            if intersection.width() >= 20 and intersection.height() >= 20:
                return pos

        primary = QGuiApplication.primaryScreen() or screens[0]
        avail = primary.availableGeometry()
        safe_x = avail.x() + avail.width() - size.width() - 32
        safe_y = avail.y() + avail.height() - size.height() - 48
        return QPoint(safe_x, safe_y)

    def _load_saved_geometry(self):
        saved_x = int(self.repo.get_preference("floating_x", 400))
        saved_y = int(self.repo.get_preference("floating_y", 400))
        self.setWindowOpacity(self.opacity)

        safe_pos = self.ensure_on_screen(QPoint(saved_x, saved_y), self.size())
        self.move(safe_pos)

    def save_position(self):
        self.repo.set_preference("floating_x", self.x())
        self.repo.set_preference("floating_y", self.y())

    def moveEvent(self, event):
        super().moveEvent(event)
        self._save_debounce_timer.start()

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.repo.set_preference("floating_always_on_top", self.always_on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.always_on_top)
        configure_kwin_keep_above(self.always_on_top)
        self.btn_pin.set_pinned(self.always_on_top)
        self.show()
        if self.always_on_top:
            self.raise_()

    def toggle_compact_mode(self):
        self.is_compact = not self.is_compact
        self.repo.set_preference("floating_compact", self.is_compact)
        if self.is_compact:
            self.resize(180, 110)
        else:
            self.resize(220, 150)

    def toggle_auto_hide_controls(self):
        self.auto_hide_controls = not self.auto_hide_controls
        self.repo.set_preference("floating_auto_hide_controls", self.auto_hide_controls)

    def open_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)

        title_act = QAction("FocusFlow Floating", self)
        title_act.setEnabled(False)
        menu.addAction(title_act)
        menu.addSeparator()

        if self.engine.state.is_running:
            act_play = QAction("Pause Timer", self)
            act_play.triggered.connect(self.engine.pause)
            menu.addAction(act_play)
        elif self.engine.state.is_paused:
            act_play = QAction("Resume Timer", self)
            act_play.triggered.connect(self.engine.resume)
            menu.addAction(act_play)
        else:
            act_play = QAction("Start Session", self)
            act_play.triggered.connect(self.engine.start)
            menu.addAction(act_play)

        act_stop = QAction("Stop Timer", self)
        act_stop.triggered.connect(self.engine.stop)
        menu.addAction(act_stop)

        act_skip = QAction("Skip Session", self)
        act_skip.triggered.connect(self.engine.skip)
        menu.addAction(act_skip)

        menu.addSeparator()

        # Always on top
        act_top = QAction("Always on Top", self)
        act_top.setCheckable(True)
        act_top.setChecked(self.always_on_top)
        act_top.triggered.connect(self.toggle_always_on_top)
        menu.addAction(act_top)

        act_dash = QAction("Open Dashboard", self)
        act_dash.triggered.connect(self.open_dashboard_requested.emit)
        menu.addAction(act_dash)

        menu.exec(global_pos)

    def showEvent(self, event):
        super().showEvent(event)
        if self.always_on_top:
            self.raise_()
        self.visibility_changed.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibility_changed.emit(False)
