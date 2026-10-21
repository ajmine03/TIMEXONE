"""
Productivity Dashboard View for FocusFlow.
Faithfully reproduces the layout, visual hierarchy, colors, and components of Image 4:
- Mountain-at-sunset hero banner with dynamic greeting, quote, and 4 real-data stat cards.
- Multicolor circular timer panel with Pomodoro/Break tabs and glowing pill controls.
- Today's tasks panel with Add Task, filter pills (All, High, Medium, Low), and task list.
- Bottom analytics panels: weekly focus time bar chart and task completion donut chart.
- Right sidebar: interactive monthly calendar and recent sessions list.
"""

from datetime import date, datetime, timedelta
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QScrollArea, QMenu, QDialog, QMessageBox
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QPixmap, QPainterPath, QAction
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF

from focusflow.core.timer import PomodoroEngine, TimerState
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository, Task, PomodoroSession
from focusflow.config import (
    HERO_BG_PATH, TOMATO_PATH, format_date_weekday, format_time_12h
)
from focusflow.ui.components.timer_display import TimerDisplayWidget
from focusflow.ui.components.charts import WeeklyBarChart, TaskCompletionDonutChart
from focusflow.ui.components.calendar_widget import MonthCalendarWidget
from focusflow.ui.tasks_view import TaskEditDialog


class DashboardCard(QFrame):
    """
    Elevated card container matching Image 4.
    Guaranteed dark navy background and subtle border that always renders cleanly.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setBrush(QColor("#111726"))
        painter.setPen(QPen(QColor("#1e293f"), 1.0))
        painter.drawRoundedRect(rect, 16.0, 16.0)
        painter.end()


class HeroBannerCard(QFrame):
    """Custom painted Hero Banner with local mountain-at-sunset background and rounded corners."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroCard")
        self.setMinimumHeight(175)
        self.setMaximumHeight(210)
        self._bg_pixmap = None
        if HERO_BG_PATH.exists():
            self._bg_pixmap = QPixmap(str(HERO_BG_PATH))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 16.0
        rect = QRectF(0, 0, w, h)

        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, radius, radius)
        painter.save()
        painter.setClipPath(clip_path)

        if self._bg_pixmap and not self._bg_pixmap.isNull():
            # Scale background to cover
            scaled = self._bg_pixmap.scaled(
                int(w), int(h),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # Center crop
            sx = max(0, (scaled.width() - w) // 2)
            sy = max(0, (scaled.height() - h) // 2)
            painter.drawPixmap(0, 0, scaled, sx, sy, int(w), int(h))

            # Darkening gradient overlay for high contrast readability
            dark_overlay = QPainterPath()
            dark_overlay.addRect(rect)
            painter.fillPath(dark_overlay, QColor(10, 14, 25, 95))
        else:
            # Fallback rich gradient
            from PyQt6.QtGui import QLinearGradient
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#1e1534"))
            grad.setColorAt(0.5, QColor("#3f1e40"))
            grad.setColorAt(1.0, QColor("#e8654c"))
            painter.fillRect(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()), grad)

        painter.restore()

        # Outline border
        painter.setPen(QPen(QColor(255, 255, 255, 25), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)
        painter.end()


class WaveHandWidget(QWidget):
    """Clean vector waving hand matching Image 4 without missing emoji glyphs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#f59e0b"))
        painter.setPen(QPen(QColor("#d97706"), 0.8))
        # Palm
        painter.drawRoundedRect(QRectF(4, 9, 13, 11), 4, 4)
        # Thumb
        painter.drawRoundedRect(QRectF(1, 11, 6, 4), 2, 2)
        # Fingers
        painter.drawRoundedRect(QRectF(4, 3, 3, 8), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(7.5, 2, 3, 9), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(11, 2.5, 3, 8.5), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(14.5, 4, 2.8, 7), 1.4, 1.4)
        painter.end()


class FocusDayBadge(QFrame):
    """Pill badge for Focus Day matching Image 4."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 20, 36, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 11px;
            }
        """)
        l = QHBoxLayout(self)
        l.setContentsMargins(8, 2, 8, 2)
        l.setSpacing(6)

        dot = QLabel(self)
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("background-color: #ef4444; border-radius: 4px; border: 1.5px solid #fca5a5;")
        l.addWidget(dot)

        txt = QLabel("Focus Day", self)
        txt.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        l.addWidget(txt)


class StatIconBox(QWidget):
    """Small rounded icon box for StatCard supporting vector drawing."""

    def __init__(self, icon_type: str, icon_color: str, bg_color: str, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.icon_color = QColor(icon_color)
        self.bg_color = QColor(bg_color)
        self.setFixedSize(36, 36)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background rounded rect
        painter.setBrush(self.bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, 0, 36, 36), 8, 8)

        # Icon drawing
        if self.icon_type == "tomato":
            if TOMATO_PATH.exists():
                pix = QPixmap(str(TOMATO_PATH)).scaled(
                    20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                painter.drawPixmap(8, 8, pix)
            else:
                painter.setBrush(QColor("#ef4444"))
                painter.drawEllipse(8, 8, 20, 20)
        elif self.icon_type == "check":
            painter.setPen(QPen(self.icon_color, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(10, 18, 15, 23)
            painter.drawLine(15, 23, 26, 12)
        elif self.icon_type == "bars":
            painter.setBrush(self.icon_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(10, 20, 4, 8), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(16, 14, 4, 14), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(22, 10, 4, 18), 1.5, 1.5)
        elif self.icon_type == "star":
            painter.setFont(QFont("Inter", 14, QFont.Weight.Bold))
            painter.setPen(self.icon_color)
            painter.drawText(QRectF(0, 0, 36, 36), Qt.AlignmentFlag.AlignCenter, "★")
        painter.end()


class StatCard(QFrame):
    """Compact metric card inside hero section matching Image 4."""

    clicked = pyqtSignal()

    def __init__(
        self,
        icon_type: str,
        icon_color: str,
        icon_bg: str,
        title: str,
        subtitle: str,
        bg_color: str,
        border_color: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self._init_ui(icon_type, icon_color, icon_bg, title, subtitle)

    def _init_ui(self, icon_type: str, icon_color: str, icon_bg: str, title: str, subtitle: str):
        self.setMinimumHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Left: Icon square
        self.icon_box = StatIconBox(icon_type, icon_color, icon_bg, self)
        layout.addWidget(self.icon_box)

        # Right: Value + Title + Subtitle
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.val_lbl = QLabel("0", self)
        self.val_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        text_layout.addWidget(self.val_lbl)

        self.title_lbl = QLabel(title, self)
        self.title_lbl.setStyleSheet("font-size: 11px; color: #e2e8f0; font-weight: 600;")
        text_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(subtitle, self)
        self.sub_lbl.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: normal;")
        text_layout.addWidget(self.sub_lbl)

        layout.addLayout(text_layout, stretch=1)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()

    def set_value(self, val_str: str):
        self.val_lbl.setText(val_str)


class TodayTaskRow(QFrame):
    """Single task row with checkbox, title, priority badge, due time, and menu."""

    toggle_completed = pyqtSignal(str) # task_id
    focus_task = pyqtSignal(str)
    edit_task = pyqtSignal(str)
    delete_task = pyqtSignal(str)

    def __init__(self, task: Task, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.task = task
        self.is_active = is_active
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #161c2d;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(34)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # 1. Custom Checkbox button
        self.btn_check = QPushButton(self)
        self.btn_check.setFixedSize(20, 20)
        self._update_checkbox_style()
        self.btn_check.clicked.connect(lambda: self.toggle_completed.emit(self.task.id))
        layout.addWidget(self.btn_check)

        # 2. Title
        self.lbl_title = QLabel(self.task.title, self)
        if self.task.status == "completed":
            self.lbl_title.setStyleSheet("color: #64748b; text-decoration: line-through; font-size: 13px;")
        elif self.is_active:
            self.lbl_title.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 13px;")
        else:
            self.lbl_title.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.lbl_title, stretch=1)

        # 3. Priority badge
        p_color_map = {
            "high": ("#ef4444", "#3e181e"),
            "medium": ("#f59e0b", "#332414"),
            "low": ("#10b981", "#143328"),
        }
        text_c, bg_c = p_color_map.get(self.task.priority.lower(), ("#94a3b8", "#1e263d"))
        lbl_pri = QLabel(self.task.priority.capitalize(), self)
        lbl_pri.setStyleSheet(f"""
            QLabel {{
                color: {text_c};
                background-color: {bg_c};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(lbl_pri)

        # 4. Due time (e.g. "12:00 PM" or "10-21")
        time_text = ""
        if self.task.due_date:
            if "T" in self.task.due_date or " " in self.task.due_date:
                try:
                    dt = datetime.fromisoformat(self.task.due_date)
                    time_text = format_time_12h(dt)
                except Exception:
                    time_text = self.task.due_date[11:16]
            else:
                time_text = self.task.due_date[5:]  # MM-DD
        lbl_time = QLabel(time_text, self)
        lbl_time.setStyleSheet("color: #8a95af; font-size: 11px; min-width: 60px;")
        lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl_time)

        # 5. Three-dots action menu
        btn_menu = QPushButton("⋮", self)
        btn_menu.setFixedSize(20, 24)
        btn_menu.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        btn_menu.clicked.connect(self._open_menu)
        layout.addWidget(btn_menu)

    def _update_checkbox_style(self):
        if self.task.status == "completed":
            self.btn_check.setText("✓")
            self.btn_check.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: #ffffff;
                    border: none;
                    border-radius: 5px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
        else:
            self.btn_check.setText("")
            self.btn_check.setStyleSheet("""
                QPushButton {
                    background-color: #121727;
                    border: 1.5px solid #2d3856;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    border-color: #4f5f8a;
                }
            """)

    def _open_menu(self):
        menu = QMenu(self)
        if self.task.status != "completed":
            act_focus = QAction("Focus This Task", self)
            act_focus.triggered.connect(lambda: self.focus_task.emit(self.task.id))
            menu.addAction(act_focus)

        act_edit = QAction("Edit Task", self)
        act_edit.triggered.connect(lambda: self.edit_task.emit(self.task.id))
        menu.addAction(act_edit)

        act_del = QAction("Delete Task", self)
        act_del.triggered.connect(lambda: self.delete_task.emit(self.task.id))
        menu.addAction(act_del)

        menu.exec(self.mapToGlobal(QPointF(self.width() - 80, self.height()).toPoint()))


class DashboardView(QWidget):
    """Main productivity dashboard matching Image 4."""

    start_task_requested = pyqtSignal(str)
    open_settings_requested = pyqtSignal()
    open_history_requested = pyqtSignal()
    open_tasks_requested = pyqtSignal()

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
        self.active_task_filter = "all"
        self.search_query = ""

        self._init_ui()
        self._connect_signals()
        self.refresh_dashboard()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 18)
        root_layout.setSpacing(14)

        # Scroll Area for high-DPI and responsive screen sizes
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        self.container_layout = QHBoxLayout(container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # Left Main Column (~70% width)
        # ---------------------------------------------------------------------
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        # 1. Hero Section Banner
        self.hero_card = HeroBannerCard(left_col)
        hero_inner = QVBoxLayout(self.hero_card)
        hero_inner.setContentsMargins(18, 12, 18, 12)
        hero_inner.setSpacing(6)

        # Hero Top Row: Greeting & Subtitle (Left) + Date & Focus Day Badge (Right)
        hero_top = QHBoxLayout()
        greeting_col = QVBoxLayout()
        greeting_col.setSpacing(2)

        # Dynamic greeting based on current hour
        hr = datetime.now().hour
        greeting_word = "Good Evening!" if hr >= 17 else ("Good Morning!" if hr < 12 else "Good Afternoon!")
        
        greet_row = QHBoxLayout()
        greet_row.setSpacing(8)
        self.lbl_greeting = QLabel(greeting_word, self.hero_card)
        self.lbl_greeting.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        greet_row.addWidget(self.lbl_greeting)
        
        self.wave_hand = WaveHandWidget(self.hero_card)
        greet_row.addWidget(self.wave_hand)
        greet_row.addStretch()
        greeting_col.addLayout(greet_row)

        lbl_sub = QLabel("Stay focused, keep going!", self.hero_card)
        lbl_sub.setStyleSheet("font-size: 13px; color: #cbd5e1;")
        greeting_col.addWidget(lbl_sub)
        hero_top.addLayout(greeting_col)
        hero_top.addStretch()

        # Right date & badge
        date_col = QVBoxLayout()
        date_col.setSpacing(4)
        date_col.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.lbl_hero_date = QLabel(format_date_weekday(datetime.now()), self.hero_card)
        self.lbl_hero_date.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff;")
        self.lbl_hero_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        date_col.addWidget(self.lbl_hero_date)

        lbl_focus_badge = FocusDayBadge(self.hero_card)
        date_col.addWidget(lbl_focus_badge, alignment=Qt.AlignmentFlag.AlignRight)

        hero_top.addLayout(date_col)
        hero_inner.addLayout(hero_top)

        # Hero Quote Box (mid)
        quote_frame = QFrame(self.hero_card)
        quote_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(14, 18, 32, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
            }
        """)
        q_layout = QVBoxLayout(quote_frame)
        q_layout.setContentsMargins(8, 3, 8, 3)
        lbl_quote = QLabel('"Discipline today creates freedom tomorrow."', quote_frame)
        lbl_quote.setStyleSheet("font-size: 11px; color: #e2e8f0; font-style: italic;")
        q_layout.addWidget(lbl_quote)
        hero_inner.addWidget(quote_frame, alignment=Qt.AlignmentFlag.AlignLeft)

        # Hero Bottom Row: 4 Stat Cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        # 1. Pomodoros (Red)
        self.card_pomos = StatCard(
            "tomato", "#ef4444", "rgba(239, 68, 68, 0.2)",
            "Pomodoros", "completed today >",
            "rgba(34, 18, 25, 0.85)", "#4a1e27", self.hero_card
        )
        self.card_pomos.clicked.connect(self.open_history_requested.emit)
        stats_row.addWidget(self.card_pomos)

        # 2. Tasks (Green)
        self.card_tasks = StatCard(
            "check", "#10b981", "rgba(16, 185, 129, 0.2)",
            "Tasks", "completed",
            "rgba(16, 36, 28, 0.85)", "#1b4d3a", self.hero_card
        )
        stats_row.addWidget(self.card_tasks)

        # 3. Focus Time (Purple)
        self.card_focus = StatCard(
            "bars", "#a855f7", "rgba(168, 85, 247, 0.2)",
            "Focus Time", "today",
            "rgba(29, 20, 48, 0.85)", "#3d2260", self.hero_card
        )
        stats_row.addWidget(self.card_focus)

        # 4. Productivity (Gold)
        self.card_prod = StatCard(
            "star", "#f59e0b", "rgba(245, 158, 11, 0.2)",
            "Productivity", "this week",
            "rgba(41, 32, 17, 0.85)", "#57421e", self.hero_card
        )
        stats_row.addWidget(self.card_prod)

        hero_inner.addLayout(stats_row)
        left_layout.addWidget(self.hero_card)

        # 2. Middle Row: Focus Timer Card (Left) & Today's Tasks Card (Right)
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        # --- A. Focus Timer Card ---
        self.timer_card = DashboardCard(left_col)
        self.timer_card.setMinimumHeight(280)
        self.timer_card.setMaximumHeight(350)
        timer_layout = QVBoxLayout(self.timer_card)
        timer_layout.setContentsMargins(18, 14, 18, 14)
        timer_layout.setSpacing(10)
        timer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Top Mode Switcher Pills: [Pomodoro] [Short Break] [Long Break] + Gear
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)

        self.btn_mode_pomo = QPushButton("Pomodoro", self.timer_card)
        self.btn_mode_pomo.setProperty("class", "Pill")
        self.btn_mode_pomo.setCheckable(True)
        self.btn_mode_pomo.setChecked(True)
        self.btn_mode_pomo.clicked.connect(lambda: self._on_mode_switched("focus"))
        mode_row.addWidget(self.btn_mode_pomo)

        self.btn_mode_short = QPushButton("Short Break", self.timer_card)
        self.btn_mode_short.setProperty("class", "Pill")
        self.btn_mode_short.setCheckable(True)
        self.btn_mode_short.clicked.connect(lambda: self._on_mode_switched("short_break"))
        mode_row.addWidget(self.btn_mode_short)

        self.btn_mode_long = QPushButton("Long Break", self.timer_card)
        self.btn_mode_long.setProperty("class", "Pill")
        self.btn_mode_long.setCheckable(True)
        self.btn_mode_long.clicked.connect(lambda: self._on_mode_switched("long_break"))
        mode_row.addWidget(self.btn_mode_long)

        btn_gear = QPushButton("⚙", self.timer_card)
        btn_gear.setFixedSize(26, 26)
        btn_gear.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        btn_gear.clicked.connect(self.open_settings_requested.emit)
        mode_row.addWidget(btn_gear)

        timer_layout.addLayout(mode_row)

        # Multicolor Circular Timer Display
        self.timer_display = TimerDisplayWidget(self.timer_card)
        timer_layout.addWidget(self.timer_display, alignment=Qt.AlignmentFlag.AlignCenter)

        # Start / Pause Glowing Pill Button
        self.btn_play_pause = QPushButton("▶  Start", self.timer_card)
        self.btn_play_pause.setMinimumSize(170, 42)
        self.btn_play_pause.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
                border: none;
                border-radius: 21px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
            }
        """)
        self.btn_play_pause.clicked.connect(self._on_play_pause_clicked)
        timer_layout.addWidget(self.btn_play_pause, alignment=Qt.AlignmentFlag.AlignCenter)

        # Secondary row: Sound toggle, Restart, Stop, More menu
        sec_row = QHBoxLayout()
        sec_row.setSpacing(10)
        sec_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sec_btn_style = """
            QPushButton {
                background-color: #1a2236;
                color: #ffffff;
                border: 1px solid #283553;
                border-radius: 16px;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #24304c;
                color: #ffffff;
                border-color: #3e507b;
            }
        """

        self.btn_sound = QPushButton("♫", self.timer_card)
        self.btn_sound.setFixedSize(36, 32)
        self.btn_sound.setStyleSheet(sec_btn_style)
        self.btn_sound.setToolTip("Toggle Sound Chime")
        self.btn_sound.clicked.connect(self._toggle_sound)
        self._update_sound_icon()
        sec_row.addWidget(self.btn_sound)

        self.btn_restart = QPushButton("↺", self.timer_card)
        self.btn_restart.setFixedSize(36, 32)
        self.btn_restart.setStyleSheet(sec_btn_style)
        self.btn_restart.setToolTip("Restart Session")
        self.btn_restart.clicked.connect(self.engine.restart)
        sec_row.addWidget(self.btn_restart)

        self.btn_stop = QPushButton("■", self.timer_card)
        self.btn_stop.setFixedSize(36, 32)
        self.btn_stop.setStyleSheet(sec_btn_style)
        self.btn_stop.setToolTip("Stop Session")
        self.btn_stop.clicked.connect(self.engine.stop)
        sec_row.addWidget(self.btn_stop)

        btn_more = QPushButton("···", self.timer_card)
        btn_more.setFixedSize(36, 32)
        btn_more.setStyleSheet(sec_btn_style)
        btn_more.setToolTip("Options")
        btn_more.clicked.connect(self._open_timer_options_menu)
        sec_row.addWidget(btn_more)

        timer_layout.addLayout(sec_row)
        mid_row.addWidget(self.timer_card, stretch=4)

        # --- B. Today's Tasks Card ---
        self.tasks_card = DashboardCard(left_col)
        self.tasks_card.setMinimumHeight(280)
        self.tasks_card.setMaximumHeight(350)
        tasks_layout = QVBoxLayout(self.tasks_card)
        tasks_layout.setContentsMargins(18, 14, 18, 14)
        tasks_layout.setSpacing(10)

        # Header: "Today's Tasks" + "+ Add Task" button
        tasks_header = QHBoxLayout()
        tasks_title = QLabel("Today's Tasks", self.tasks_card)
        tasks_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        tasks_header.addWidget(tasks_title)
        tasks_header.addStretch()

        btn_add_task = QPushButton("+ Add Task", self.tasks_card)
        btn_add_task.setMinimumHeight(30)
        btn_add_task.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #3b82f6);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #2563eb);
            }
        """)
        btn_add_task.clicked.connect(self._open_add_task_dialog)
        tasks_header.addWidget(btn_add_task)
        tasks_layout.addLayout(tasks_header)

        # Filter Pills Row: All, High, Medium, Low
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.btn_f_all = QPushButton("All", self.tasks_card)
        self.btn_f_all.setProperty("class", "Pill")
        self.btn_f_all.setCheckable(True)
        self.btn_f_all.setChecked(True)
        self.btn_f_all.clicked.connect(lambda: self._set_task_filter("all"))
        filter_row.addWidget(self.btn_f_all)

        self.btn_f_high = QPushButton("High", self.tasks_card)
        self.btn_f_high.setProperty("class", "Pill")
        self.btn_f_high.setCheckable(True)
        self.btn_f_high.clicked.connect(lambda: self._set_task_filter("high"))
        filter_row.addWidget(self.btn_f_high)

        self.btn_f_med = QPushButton("Medium", self.tasks_card)
        self.btn_f_med.setProperty("class", "Pill")
        self.btn_f_med.setCheckable(True)
        self.btn_f_med.clicked.connect(lambda: self._set_task_filter("medium"))
        filter_row.addWidget(self.btn_f_med)

        self.btn_f_low = QPushButton("Low", self.tasks_card)
        self.btn_f_low.setProperty("class", "Pill")
        self.btn_f_low.setCheckable(True)
        self.btn_f_low.clicked.connect(lambda: self._set_task_filter("low"))
        filter_row.addWidget(self.btn_f_low)
        filter_row.addStretch()

        tasks_layout.addLayout(filter_row)

        # Task Items Container (Scrollable)
        self.task_list_container = QWidget(self.tasks_card)
        self.task_list_layout = QVBoxLayout(self.task_list_container)
        self.task_list_layout.setContentsMargins(0, 4, 0, 4)
        self.task_list_layout.setSpacing(4)
        self.task_list_layout.addStretch()

        tasks_layout.addWidget(self.task_list_container, stretch=1)
        mid_row.addWidget(self.tasks_card, stretch=6)

        left_layout.addLayout(mid_row)

        # 3. Bottom Row: Focus Time Chart & Task Completion Donut Chart
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # --- A. Focus Time Card ---
        self.chart_card = DashboardCard(left_col)
        self.chart_card.setMinimumHeight(180)
        self.chart_card.setMaximumHeight(225)
        chart_layout = QVBoxLayout(self.chart_card)
        chart_layout.setContentsMargins(18, 14, 18, 14)
        chart_layout.setSpacing(8)

        chart_header = QHBoxLayout()
        lbl_chart_title = QLabel("Focus Time", self.chart_card)
        lbl_chart_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        chart_header.addWidget(lbl_chart_title)
        chart_header.addStretch()

        self.chart_period_combo = QComboBox(self.chart_card)
        self.chart_period_combo.addItem("This Week", "week")
        self.chart_period_combo.addItem("Last 7 Days", "7days")
        self.chart_period_combo.addItem("Last 30 Days", "30days")
        self.chart_period_combo.setMinimumWidth(110)
        self.chart_period_combo.currentIndexChanged.connect(self._on_chart_period_changed)
        chart_header.addWidget(self.chart_period_combo)
        chart_layout.addLayout(chart_header)

        self.bar_chart = WeeklyBarChart(self.chart_card)
        chart_layout.addWidget(self.bar_chart)
        bottom_row.addWidget(self.chart_card, stretch=5)

        # --- B. Task Completion Card ---
        self.donut_card = DashboardCard(left_col)
        self.donut_card.setMinimumHeight(180)
        self.donut_card.setMaximumHeight(225)
        donut_layout = QVBoxLayout(self.donut_card)
        donut_layout.setContentsMargins(18, 14, 18, 14)
        donut_layout.setSpacing(8)

        donut_title = QLabel("Task Completion", self.donut_card)
        donut_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        donut_layout.addWidget(donut_title)

        self.donut_chart = TaskCompletionDonutChart(self.donut_card)
        donut_layout.addWidget(self.donut_chart)
        bottom_row.addWidget(self.donut_card, stretch=5)

        left_layout.addLayout(bottom_row)
        self.container_layout.addWidget(left_col, stretch=7)

        # ---------------------------------------------------------------------
        # Right Sidebar Column (~30% width)
        # ---------------------------------------------------------------------
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        # 1. Monthly Calendar
        self.calendar_card = MonthCalendarWidget(self.repo, right_col)
        self.calendar_card.setMinimumHeight(240)
        self.calendar_card.setMaximumHeight(290)
        self.calendar_card.date_selected.connect(self._on_date_selected)
        right_layout.addWidget(self.calendar_card)

        # 2. Recent Sessions Card
        self.recent_card = DashboardCard(right_col)
        self.recent_card.setMinimumHeight(220)
        recent_layout = QVBoxLayout(self.recent_card)
        recent_layout.setContentsMargins(16, 14, 16, 14)
        recent_layout.setSpacing(10)

        recent_header = QHBoxLayout()
        lbl_recent_title = QLabel("Recent Sessions", self.recent_card)
        lbl_recent_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        recent_header.addWidget(lbl_recent_title)
        recent_header.addStretch()

        btn_view_all = QPushButton("View All", self.recent_card)
        btn_view_all.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #60a5fa;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        btn_view_all.clicked.connect(self.open_history_requested.emit)
        recent_header.addWidget(btn_view_all)
        recent_layout.addLayout(recent_header)

        # Recent sessions list container
        self.recent_list_container = QWidget(self.recent_card)
        self.recent_list_layout = QVBoxLayout(self.recent_list_container)
        self.recent_list_layout.setContentsMargins(0, 4, 0, 4)
        self.recent_list_layout.setSpacing(8)
        recent_layout.addWidget(self.recent_list_container, stretch=1)

        right_layout.addWidget(self.recent_card, stretch=1)
        self.container_layout.addWidget(right_col, stretch=3)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _connect_signals(self):
        self.engine.subscribe_tick(self._on_tick)
        self.engine.subscribe_state_changed(self._on_state_changed)
        self.task_manager.subscribe_change(self.refresh_tasks)

    # -------------------------------------------------------------------------
    # Mode Switcher (Pomodoro, Short Break, Long Break)
    # -------------------------------------------------------------------------
    def _on_mode_switched(self, mode: str):
        self.btn_mode_pomo.setChecked(mode == "focus")
        self.btn_mode_short.setChecked(mode == "short_break")
        self.btn_mode_long.setChecked(mode == "long_break")
        self.engine.switch_mode(mode)
        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, 0.0)

    # -------------------------------------------------------------------------
    # Play / Pause / Start
    # -------------------------------------------------------------------------
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

    def _on_state_changed(self, new_state: TimerState):
        if new_state == TimerState.IDLE:
            self.btn_play_pause.setText("▶  Start")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                    color: #ffffff;
                    border: none;
                    border-radius: 21px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        elif new_state.is_running:
            self.btn_play_pause.setText("⏸  Pause")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
                    color: #ffffff;
                    border: none;
                    border-radius: 21px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        elif new_state.is_paused:
            self.btn_play_pause.setText("▶  Resume")
            self.btn_play_pause.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                    color: #ffffff;
                    border: none;
                    border-radius: 21px;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)

        # Sync mode buttons
        mode = self.engine.current_mode
        self.btn_mode_pomo.setChecked(mode == "focus")
        self.btn_mode_short.setChecked(mode == "short_break")
        self.btn_mode_long.setChecked(mode == "long_break")

        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, 0.0)

    def _on_tick(self, remaining: int, total: int, fraction: float):
        task_title = ""
        if self.engine.active_task_id:
            task = self.task_manager.get(self.engine.active_task_id)
            if task:
                task_title = task.title
        self.timer_display.set_timer_data(remaining, total, fraction, self.engine.state, task_title)

    def _toggle_sound(self):
        curr = self.repo.get_preference("sound_enabled", True)
        self.repo.set_preference("sound_enabled", not curr)
        self._update_sound_icon()

    def _update_sound_icon(self):
        enabled = self.repo.get_preference("sound_enabled", True)
        self.btn_sound.setText("♫" if enabled else "♪̸")

    def _open_timer_options_menu(self):
        menu = QMenu(self)
        act_restart = QAction("Restart Session", self)
        act_restart.triggered.connect(self.engine.restart)
        menu.addAction(act_restart)

        act_skip = QAction("Skip Session", self)
        act_skip.triggered.connect(self.engine.skip)
        menu.addAction(act_skip)

        act_stop = QAction("Stop Session", self)
        act_stop.triggered.connect(self.engine.stop)
        menu.addAction(act_stop)

        menu.addSeparator()
        act_clear_task = QAction("Clear Active Task", self)
        act_clear_task.triggered.connect(lambda: self.engine.set_active_task(None))
        menu.addAction(act_clear_task)

        menu.exec(self.timer_card.mapToGlobal(QPointF(self.timer_card.width() // 2, self.timer_card.height() - 20).toPoint()))

    # -------------------------------------------------------------------------
    # Today's Tasks
    # -------------------------------------------------------------------------
    def _set_task_filter(self, filter_key: str):
        self.active_task_filter = filter_key
        self.btn_f_all.setChecked(filter_key == "all")
        self.btn_f_high.setChecked(filter_key == "high")
        self.btn_f_med.setChecked(filter_key == "medium")
        self.btn_f_low.setChecked(filter_key == "low")
        self.refresh_tasks()

    def set_search_query(self, query: str):
        self.search_query = query.strip()
        self.refresh_tasks()

    def _open_add_task_dialog(self):
        dlg = TaskEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.task_manager.create(**data)

    def refresh_tasks(self):
        # Clear previous rows except stretch
        while self.task_list_layout.count() > 1:
            item = self.task_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today_iso = date.today().isoformat()
        all_today_tasks = [t for t in self.task_manager.list(filter_mode="all", sort_by="due_date") 
                           if t.due_date and t.due_date.startswith(today_iso)]
        if not all_today_tasks:
            all_today_tasks = self.task_manager.list(filter_mode="all")

        tasks = all_today_tasks
        if self.search_query:
            tasks = [t for t in tasks if self.search_query.lower() in t.title.lower()]

        # Filter by priority if selected
        if self.active_task_filter != "all":
            tasks = [t for t in tasks if t.priority.lower() == self.active_task_filter]

        # Update button count badges
        n_all = len(all_today_tasks)
        n_high = sum(1 for t in all_today_tasks if t.priority.lower() == "high")
        n_med = sum(1 for t in all_today_tasks if t.priority.lower() == "medium")
        n_low = sum(1 for t in all_today_tasks if t.priority.lower() == "low")

        self.btn_f_all.setText(f"All {n_all}")
        self.btn_f_high.setText(f"High {n_high}")
        self.btn_f_med.setText(f"Medium {n_med}")
        self.btn_f_low.setText(f"Low {n_low}")

        if not tasks:
            empty = QLabel("No tasks found.")
            empty.setStyleSheet("color: #64748b; font-size: 13px; padding: 24px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.task_list_layout.insertWidget(0, empty)
            return

        for idx, t in enumerate(tasks[:5]):  # Display top 5 in dashboard matching Image 4
            is_active = (t.id == self.engine.active_task_id)
            row = TodayTaskRow(t, is_active=is_active)
            row.toggle_completed.connect(self._toggle_task_completed)
            row.focus_task.connect(self._focus_task)
            row.edit_task.connect(self._edit_task)
            row.delete_task.connect(self._delete_task)
            self.task_list_layout.insertWidget(idx, row)

    def _toggle_task_completed(self, task_id: str):
        self.task_manager.toggle_complete(task_id)

    def _focus_task(self, task_id: str):
        self.engine.set_active_task(task_id)
        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, 0.0)

    def _edit_task(self, task_id: str):
        task = self.task_manager.get(task_id)
        if not task:
            return
        dlg = TaskEditDialog(self, task=task)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.task_manager.update(task_id, **dlg.get_data())

    def _delete_task(self, task_id: str):
        self.task_manager.delete(task_id)

    # -------------------------------------------------------------------------
    # Bottom Analytics & Right Column
    # -------------------------------------------------------------------------
    def _on_chart_period_changed(self, index: int):
        self.refresh_analytics()

    def _on_date_selected(self, sel_date: date):
        pass

    def refresh_recent_sessions(self):
        while self.recent_list_layout.count() > 0:
            item = self.recent_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = self.repo.list_sessions(limit=5)
        if not sessions:
            lbl_empty = QLabel("No sessions recorded today.")
            lbl_empty.setStyleSheet("color: #64748b; font-size: 12px; padding: 14px 0;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.recent_list_layout.addWidget(lbl_empty)
            self.recent_list_layout.addStretch()
            return

        for s in sessions:
            row = QFrame()
            row.setFixedHeight(34)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(4, 2, 4, 2)
            r_layout.setSpacing(8)

            # Dot indicator
            dot_color = "#ef4444" if s.session_type == "focus" else ("#10b981" if s.session_type == "short_break" else "#a855f7")
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px;")
            r_layout.addWidget(dot)

            # Session label & duration
            text_col = QVBoxLayout()
            text_col.setSpacing(1)

            type_name = "Focus Session" if s.session_type == "focus" else ("Short Break" if s.session_type == "short_break" else "Long Break")
            lbl_name = QLabel(type_name)
            lbl_name.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 500;")
            text_col.addWidget(lbl_name)

            dur_mins = max(1, s.duration_seconds // 60)
            lbl_dur = QLabel(f"{dur_mins} min")
            lbl_dur.setStyleSheet("color: #8a95af; font-size: 10px;")
            text_col.addWidget(lbl_dur)

            r_layout.addLayout(text_col, stretch=1)

            # Time formatted in English
            time_str = ""
            try:
                dt = datetime.fromisoformat(s.start_time)
                time_str = format_time_12h(dt)
            except Exception:
                time_str = s.start_time[11:16] if len(s.start_time) >= 16 else ""

            lbl_time = QLabel(time_str)
            lbl_time.setStyleSheet("color: #8a95af; font-size: 11px;")
            r_layout.addWidget(lbl_time)

            self.recent_list_layout.addWidget(row)
        self.recent_list_layout.addStretch()

    def refresh_analytics(self):
        # Weekly focus bar chart
        week_data = self.repo.get_week_focus_data()
        self.bar_chart.set_data(week_data)

        # Task completion donut chart
        breakdown = self.repo.get_task_completion_breakdown()
        self.donut_chart.set_counts(
            completed=breakdown["completed"],
            pending=breakdown["pending"],
            overdue=breakdown["overdue"]
        )

    def refresh_dashboard(self):
        """Update metrics for today."""
        today_str = date.today().isoformat()
        stats = self.repo.get_daily_stats(today_str)

        # 1. Hero Greeting & Date
        hr = datetime.now().hour
        greeting_word = "Good Evening!" if hr >= 17 else ("Good Morning!" if hr < 12 else "Good Afternoon!")
        self.lbl_greeting.setText(greeting_word)
        self.lbl_hero_date.setText(format_date_weekday(datetime.now()))

        # 2. Hero Stat Cards
        # Pomodoros completed today
        self.card_pomos.set_value(str(stats.pomodoros_completed))

        # Tasks completed
        breakdown = self.repo.get_task_completion_breakdown()
        self.card_tasks.set_value(str(breakdown["completed"]))

        # Focus Time today
        hours = stats.total_focus_seconds // 3600
        mins = (stats.total_focus_seconds % 3600) // 60
        focus_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        self.card_focus.set_value(focus_str)

        # Productivity this week
        prod_pct = self.repo.get_weekly_productivity_pct()
        self.card_prod.set_value(f"{prod_pct}%")

        # 3. Tasks & Charts
        self.refresh_tasks()
        self.refresh_analytics()
        self.refresh_recent_sessions()
        self.calendar_card.refresh_calendar()

        # Update timer display with current engine values
        self._on_tick(self.engine.remaining_seconds, self.engine.total_duration, 0.0)
