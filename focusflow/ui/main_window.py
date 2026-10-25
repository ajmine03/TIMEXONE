"""
Main Application Window for FocusFlow.
Hosts the left sidebar navigation, top navigation bar, views stack,
keyboard shortcuts, and tray event handlers.
Faithfully reproduces the layout and design of Image 4.
"""

from datetime import date, datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QLineEdit, QApplication
)
from PyQt6.QtGui import (
    QIcon, QKeySequence, QShortcut, QPixmap, QPainter, QColor,
    QPainterPath, QPen, QFont
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF

from focusflow.config import (
    APP_NAME, APP_VERSION, ICON_PATH, TOMATO_PATH,
    SIDEBAR_BG_PATH, AVATAR_PATH, format_date_short
)
from focusflow.core.timer import PomodoroEngine
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository
from focusflow.ui.dashboard_view import DashboardView
from focusflow.ui.tasks_view import TasksView
from focusflow.ui.history_view import HistoryView
from focusflow.ui.styles import DARK_THEME, LIGHT_THEME


class SidebarQuoteCard(QFrame):
    """Mid-sidebar card with local mountain background artwork."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self.setMaximumHeight(130)
        self._bg_pix = None
        if SIDEBAR_BG_PATH.exists():
            self._bg_pix = QPixmap(str(SIDEBAR_BG_PATH))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 12.0
        rect = QRectF(0, 0, w, h)

        clip = QPainterPath()
        clip.addRoundedRect(rect, radius, radius)
        painter.save()
        painter.setClipPath(clip)

        if self._bg_pix and not self._bg_pix.isNull():
            scaled = self._bg_pix.scaled(
                int(w), int(h),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            sx = max(0, (scaled.width() - w) // 2)
            sy = max(0, (scaled.height() - h) // 2)
            painter.drawPixmap(0, 0, scaled, sx, sy, int(w), int(h))

            # Darkening gradient for clear text readability
            painter.fillRect(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()), QColor(10, 14, 25, 110))
        else:
            painter.fillRect(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()), QColor(18, 24, 40))

        painter.restore()

        # Outline border
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)

        # Text overlay
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        text_rect = QRectF(14, 16, w - 28, h - 32)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, "Small steps\nmake big progress.")
        painter.end()


class AvatarWidget(QLabel):
    """Circular profile avatar displaying sunset artwork."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self._pix = None
        if AVATAR_PATH.exists():
            self._pix = QPixmap(str(AVATAR_PATH))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        rect = QRectF(0, 0, size, size)

        clip = QPainterPath()
        clip.addEllipse(rect)
        painter.save()
        painter.setClipPath(clip)

        if self._pix and not self._pix.isNull():
            scaled = self._pix.scaled(
                int(size), int(size),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled)
        else:
            painter.setBrush(QColor("#4f46e5"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)

        painter.restore()

        # Outline border
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)
        painter.end()


class NotificationBellWidget(QPushButton):
    """Bell button with notification dot indicator."""

    def __init__(self, parent=None):
        super().__init__("🔔", parent)
        self.setFixedSize(32, 32)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 15px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #141b2e;
                color: #ffffff;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Red notification dot at top right
        painter.setBrush(QColor("#ef4444"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(21, 6, 6, 6)
        painter.end()


class MainWindow(QMainWindow):
    """Primary desktop interface matching Image 4."""

    toggle_floating_requested = pyqtSignal()
    quit_application_requested = pyqtSignal()

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

        self.setWindowTitle(f"{APP_NAME} — Productivity Tracker")
        self.resize(1200, 780)
        self.setMinimumSize(960, 620)

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._init_ui()
        self._setup_shortcuts()
        self.apply_theme("dark")
        self._refresh_task_badge()
        self.task_manager.subscribe_change(self._refresh_task_badge)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------------------------------------------------------------------
        # 1. Left Sidebar
        # ---------------------------------------------------------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 14)
        sidebar_layout.setSpacing(4)

        # Brand Header (Tomato logo + FocusFlow + Focus • Plan • Achieve)
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(8, 6, 8, 12)
        brand_layout.setSpacing(10)

        lbl_logo = QLabel()
        lbl_logo.setFixedSize(30, 30)
        if TOMATO_PATH.exists():
            pix = QPixmap(str(TOMATO_PATH)).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
        else:
            lbl_logo.setText("🍅")
        brand_layout.addWidget(lbl_logo)

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(1)

        brand_title = QLabel(APP_NAME)
        brand_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        brand_text_col.addWidget(brand_title)

        brand_sub = QLabel("Focus • Plan • Achieve")
        brand_sub.setStyleSheet("font-size: 10px; color: #64748b; font-weight: 500;")
        brand_text_col.addWidget(brand_sub)

        brand_layout.addLayout(brand_text_col)
        sidebar_layout.addLayout(brand_layout)

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🏠  Dashboard", 0),
            ("tasks", "☑  Tasks", 1),
            ("timer", "⏰  Timer", 0),
            ("analytics", "📊  Analytics", 3),
            ("calendar", "📅  Calendar", 0),
            ("settings", "⚙  Settings", 4),
        ]

        for key, label, index in nav_items:
            btn_container = QWidget()
            b_layout = QHBoxLayout(btn_container)
            b_layout.setContentsMargins(0, 0, 0, 0)
            b_layout.setSpacing(0)

            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index, k=key: self._on_nav_clicked(idx, k))
            b_layout.addWidget(btn, stretch=1)

            # Badge for Tasks
            if key == "tasks":
                self.lbl_task_badge = QLabel("0")
                self.lbl_task_badge.setStyleSheet("""
                    QLabel {
                        background-color: #1a2236;
                        color: #a0aec0;
                        border-radius: 9px;
                        padding: 1px 7px;
                        font-size: 11px;
                        font-weight: bold;
                        margin-right: 12px;
                    }
                """)
                b_layout.addWidget(self.lbl_task_badge)

            sidebar_layout.addWidget(btn_container)
            self.nav_buttons[key] = btn

        self.nav_buttons["dashboard"].setChecked(True)
        sidebar_layout.addSpacing(10)

        # Motivational Mountain Card
        self.quote_card = SidebarQuoteCard(self.sidebar)
        sidebar_layout.addWidget(self.quote_card)

        sidebar_layout.addStretch()

        # Bottom "Today" Info Card
        today_card = QFrame()
        today_card.setStyleSheet("""
            QFrame {
                background-color: #0f1422;
                border: 1px solid #1a2236;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        today_layout = QVBoxLayout(today_card)
        today_layout.setContentsMargins(10, 8, 10, 8)
        today_layout.setSpacing(4)

        t_head = QHBoxLayout()
        t_title = QLabel("Today")
        t_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff;")
        t_head.addWidget(t_title)
        t_head.addStretch()

        t_icon = QLabel("☀️")
        t_icon.setStyleSheet("font-size: 13px;")
        t_head.addWidget(t_icon)
        today_layout.addLayout(t_head)

        t_date = QLabel(format_date_short(date.today()))
        t_date.setStyleSheet("font-size: 11px; color: #8a95af;")
        today_layout.addWidget(t_date)

        t_quote = QLabel('"A focused mind\nbuilds a brighter\ntomorrow."')
        t_quote.setStyleSheet("font-size: 10px; color: #64748b; font-style: italic; padding-top: 4px;")
        today_layout.addWidget(t_quote)

        sidebar_layout.addWidget(today_card)
        sidebar_layout.addSpacing(6)

        root_layout.addWidget(self.sidebar)

        # ---------------------------------------------------------------------
        # 2. Right Content Pane with Top Navigation Bar & Stack
        # ---------------------------------------------------------------------
        self.content_pane = QFrame()
        self.content_pane.setObjectName("ContentPane")
        content_layout = QVBoxLayout(self.content_pane)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Navigation Bar
        self.top_bar = QFrame(self.content_pane)
        self.top_bar.setStyleSheet("""
            QFrame {
                background-color: #0b0f19;
                border-bottom: 1px solid #141b2c;
                min-height: 48px;
                max-height: 48px;
            }
        """)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(18, 6, 18, 6)
        top_layout.setSpacing(12)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("🔍  Search tasks, notes...")
        self.search_input.setMinimumWidth(260)
        self.search_input.setMaximumWidth(360)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        top_layout.addWidget(self.search_input)

        top_layout.addStretch()

        # Notification Bell
        self.bell_btn = NotificationBellWidget()
        top_layout.addWidget(self.bell_btn)

        # User Profile Avatar
        self.avatar = AvatarWidget()
        top_layout.addWidget(self.avatar)

        # Window Controls: Minimize, Maximize, Close
        win_ctrl_style = """
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #141b2e;
                color: #ffffff;
            }
        """

        btn_min = QPushButton("—")
        btn_min.setFixedSize(28, 28)
        btn_min.setStyleSheet(win_ctrl_style)
        btn_min.clicked.connect(self.showMinimized)
        top_layout.addWidget(btn_min)

        btn_max = QPushButton("▢")
        btn_max.setFixedSize(28, 28)
        btn_max.setStyleSheet(win_ctrl_style)
        btn_max.clicked.connect(self._toggle_maximize)
        top_layout.addWidget(btn_max)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8a95af;
                border: none;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.close)
        top_layout.addWidget(btn_close)

        content_layout.addWidget(self.top_bar)

        # Views Stack
        self.stack = QStackedWidget()

        self.dashboard_view = DashboardView(self.engine, self.task_manager, self.repo)
        self.tasks_view = TasksView(self.task_manager, self.engine)
        self.history_view = HistoryView(self.repo)

        self.tasks_view.focus_task_requested.connect(self._on_task_focus_requested)
        self.dashboard_view.open_settings_requested.connect(self.show_settings)
        self.dashboard_view.open_history_requested.connect(self.show_history)
        self.dashboard_view.open_tasks_requested.connect(self.show_tasks)

        self.stack.addWidget(self.dashboard_view) # Index 0
        self.stack.addWidget(self.tasks_view)      # Index 1
        self.stack.addWidget(self.history_view)    # Index 2

        self.stats_placeholder = QWidget()
        self.settings_placeholder = QWidget()
        self.stack.addWidget(self.stats_placeholder)    # Index 3
        self.stack.addWidget(self.settings_placeholder) # Index 4

        content_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(self.content_pane, stretch=1)

    def _setup_shortcuts(self):
        """Standard application keyboard shortcuts."""
        self.sc_toggle = QShortcut(QKeySequence("Ctrl+Alt+Space"), self)
        self.sc_toggle.activated.connect(self.engine.toggle_play_pause)

        self.sc_stop = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        self.sc_stop.activated.connect(self.engine.stop)

        self.sc_float = QShortcut(QKeySequence("Ctrl+Alt+F"), self)
        self.sc_float.activated.connect(self.toggle_floating_requested.emit)

        self.sc_new_task = QShortcut(QKeySequence("Ctrl+Alt+N"), self)
        self.sc_new_task.activated.connect(self.tasks_view._open_new_task_dialog)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_search_text_changed(self, text: str):
        self.dashboard_view.set_search_query(text)
        self.tasks_view.search_edit.setText(text)

    def _on_nav_clicked(self, index: int, active_key: str):
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == active_key)
        self.stack.setCurrentIndex(index)
        if index == 0 and hasattr(self, "dashboard_view"):
            self.dashboard_view.refresh_dashboard()
        elif index == 1 and hasattr(self, "tasks_view"):
            self.tasks_view.refresh_tasks()
        elif index == 2 and hasattr(self, "history_view"):
            self.history_view.refresh_history()
        elif index == 3 and hasattr(self, "stats_view"):
            self.stats_view.refresh_stats()
        elif index == 4 and hasattr(self, "settings_view"):
            self.settings_view.load_settings()

    def _on_task_focus_requested(self, task_id: str):
        self._on_nav_clicked(0, "dashboard")

    def _refresh_task_badge(self):
        all_tasks = self.task_manager.list(filter_mode="all")
        pending_count = sum(1 for t in all_tasks if t.status != "completed")
        if hasattr(self, "lbl_task_badge"):
            self.lbl_task_badge.setText(str(pending_count))

    def show_dashboard(self):
        self._on_nav_clicked(0, "dashboard")
        self.show()
        self.raise_()
        self.activateWindow()

    def show_tasks(self):
        self._on_nav_clicked(1, "tasks")
        self.show()
        self.raise_()
        self.activateWindow()

    def show_history(self):
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        self.stack.setCurrentIndex(2)
        if hasattr(self, "history_view"):
            self.history_view.refresh_history()
        self.show()
        self.raise_()
        self.activateWindow()

    def show_analytics(self):
        self._on_nav_clicked(3, "analytics")
        self.show()
        self.raise_()
        self.activateWindow()

    def show_settings(self):
        self._on_nav_clicked(4, "settings")
        self.show()
        self.raise_()
        self.activateWindow()

    def set_stats_view(self, view_widget: QWidget):
        self.stats_view = view_widget
        self.stack.removeWidget(self.stats_placeholder)
        self.stack.insertWidget(3, view_widget)

    def set_settings_view(self, view_widget: QWidget):
        self.settings_view = view_widget
        self.stack.removeWidget(self.settings_placeholder)
        self.stack.insertWidget(4, view_widget)

    def apply_theme(self, theme_name: str = "dark"):
        if theme_name == "light":
            self.setStyleSheet(LIGHT_THEME)
        else:
            self.setStyleSheet(DARK_THEME)

    def closeEvent(self, event):
        if self.engine.state.is_running:
            event.ignore()
            self.hide()
        else:
            event.accept()
