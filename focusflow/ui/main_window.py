"""
Main Application Window for FocusFlow.
Hosts the sidebar navigation, views stack, keyboard shortcuts, and tray event handlers.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QApplication
)
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, pyqtSignal

from focusflow.config import APP_NAME, APP_VERSION, ICON_PATH
from focusflow.core.timer import PomodoroEngine
from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Repository
from focusflow.ui.dashboard_view import DashboardView
from focusflow.ui.tasks_view import TasksView
from focusflow.ui.styles import DARK_THEME, LIGHT_THEME


class MainWindow(QMainWindow):
    """Primary desktop interface with native Linux desktop aesthetics."""

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
        self.resize(980, 680)
        self.setMinimumSize(820, 560)

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._init_ui()
        self._setup_shortcuts()
        self.apply_theme("dark")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 16)
        sidebar_layout.setSpacing(4)

        # App Brand Header
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(16, 18, 16, 12)
        brand_label = QLabel(f"⚡ {APP_NAME}")
        brand_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        brand_layout.addWidget(brand_label)
        sidebar_layout.addLayout(brand_layout)

        # Nav Buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🏠  Dashboard", 0),
            ("tasks", "📋  Tasks", 1),
            ("history", "📜  History", 2),
            ("stats", "📊  Statistics", 3),
            ("settings", "⚙️  Settings", 4),
        ]

        for key, label, index in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index, k=key: self._on_nav_clicked(idx, k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        self.nav_buttons["dashboard"].setChecked(True)
        sidebar_layout.addStretch()

        # Floating Timer Quick Launcher in Sidebar
        self.btn_floating_toggle = QPushButton("🗗 Floating Timer")
        self.btn_floating_toggle.setObjectName("NavButton")
        self.btn_floating_toggle.clicked.connect(self.toggle_floating_requested.emit)
        sidebar_layout.addWidget(self.btn_floating_toggle)

        # Version string
        version_lbl = QLabel(f"v{APP_VERSION} (Linux)")
        version_lbl.setStyleSheet("color: #6c7086; font-size: 11px; padding-left: 20px; padding-top: 8px;")
        sidebar_layout.addWidget(version_lbl)

        root_layout.addWidget(self.sidebar)

        # 2. Right Content Stack
        self.content_pane = QFrame()
        self.content_pane.setObjectName("ContentPane")
        content_layout = QVBoxLayout(self.content_pane)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        
        # Instantiate views
        self.dashboard_view = DashboardView(self.engine, self.task_manager, self.repo)
        self.tasks_view = TasksView(self.task_manager, self.engine)
        from focusflow.ui.history_view import HistoryView
        self.history_view = HistoryView(self.repo)

        # When user clicks "Focus" on a task in tasks_view, switch to dashboard
        self.tasks_view.focus_task_requested.connect(self._on_task_focus_requested)

        self.stack.addWidget(self.dashboard_view) # Index 0
        self.stack.addWidget(self.tasks_view)      # Index 1
        self.stack.addWidget(self.history_view)    # Index 2

        # Placeholder widgets for stats and settings
        self.stats_placeholder = QWidget()
        self.settings_placeholder = QWidget()
        self.stack.addWidget(self.stats_placeholder)    # Index 3
        self.stack.addWidget(self.settings_placeholder) # Index 4

        content_layout.addWidget(self.stack)
        root_layout.addWidget(self.content_pane, stretch=1)

    def _setup_shortcuts(self):
        """Standard application keyboard shortcuts."""
        # Ctrl+Alt+Space: Play / Pause
        self.sc_toggle = QShortcut(QKeySequence("Ctrl+Alt+Space"), self)
        self.sc_toggle.activated.connect(self.engine.toggle_play_pause)

        # Ctrl+Alt+S: Stop Timer
        self.sc_stop = QShortcut(QKeySequence("Ctrl+Alt+S"), self)
        self.sc_stop.activated.connect(self.engine.stop)

        # Ctrl+Alt+F: Toggle Floating Timer
        self.sc_float = QShortcut(QKeySequence("Ctrl+Alt+F"), self)
        self.sc_float.activated.connect(self.toggle_floating_requested.emit)

        # Ctrl+Alt+N: New Task Dialog
        self.sc_new_task = QShortcut(QKeySequence("Ctrl+Alt+N"), self)
        self.sc_new_task.activated.connect(self.tasks_view._open_new_task_dialog)

    def _on_nav_clicked(self, index: int, active_key: str):
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == active_key)
        self.stack.setCurrentIndex(index)

    def _on_task_focus_requested(self, task_id: str):
        self._on_nav_clicked(0, "dashboard")

    def show_dashboard(self):
        self._on_nav_clicked(0, "dashboard")
        self.show()
        self.raise_()
        self.activateWindow()

    def show_settings(self):
        self._on_nav_clicked(4, "settings")
        self.show()
        self.raise_()
        self.activateWindow()

    def set_stats_view(self, view_widget: QWidget):
        """Replace the placeholder stats view."""
        self.stack.removeWidget(self.stats_placeholder)
        self.stack.insertWidget(3, view_widget)

    def set_settings_view(self, view_widget: QWidget):
        """Replace the placeholder settings view."""
        self.stack.removeWidget(self.settings_placeholder)
        self.stack.insertWidget(4, view_widget)

    def apply_theme(self, theme_name: str = "dark"):
        if theme_name == "light":
            self.setStyleSheet(LIGHT_THEME)
        else:
            self.setStyleSheet(DARK_THEME)

    def closeEvent(self, event):
        """
        When the window is closed, keep running in tray if timer is active
        or if user enabled tray background mode.
        """
        # If timer is running, minimize to tray rather than killing
        if self.engine.state.is_running:
            event.ignore()
            self.hide()
        else:
            event.accept()
