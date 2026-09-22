"""
First-Run Setup Wizard Dialog for FocusFlow.
Guides new users through setting Pomodoro durations, daily goals, and autostart.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QSpinBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from focusflow.config import APP_NAME
from focusflow.db.repository import Repository
from focusflow.utils.autostart import enable_autostart, disable_autostart


class FirstRunWizard(QDialog):
    """Clean 4-step first-launch onboarding wizard."""

    def __init__(self, repository: Repository, parent=None):
        super().__init__(parent)
        self.repo = repository
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.setFixedSize(480, 360)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        self.stack = QStackedWidget()

        # Step 1: Welcome
        self.stack.addWidget(self._create_welcome_step())
        # Step 2: Pomodoro Duration
        self.stack.addWidget(self._create_duration_step())
        # Step 3: Daily Goal
        self.stack.addWidget(self._create_goal_step())
        # Step 4: Autostart & Finish
        self.stack.addWidget(self._create_finish_step())

        main_layout.addWidget(self.stack)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
        btn_bar.addWidget(self.btn_back)

        btn_bar.addStretch()

        self.btn_next = QPushButton("Get Started")
        self.btn_next.setProperty("class", "Primary")
        self.btn_next.clicked.connect(self._go_next)
        btn_bar.addWidget(self.btn_next)

        main_layout.addLayout(btn_bar)

    def _create_welcome_step(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(12)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size: 48px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(icon_lbl)

        title = QLabel(f"Welcome to {APP_NAME}")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)

        desc = QLabel(
            "Your native Linux desktop companion for distraction-free focus, "
            "task management, and local productivity tracking.\n\n"
            "100% offline and privacy-first — no cloud account required."
        )
        desc.setStyleSheet("color: #a6adc8; font-size: 13px; line-height: 1.4;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(desc)
        return w

    def _create_duration_step(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(14)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Choose Pomodoro Duration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)

        desc = QLabel("Standard focus interval before taking a short 5-minute break:")
        desc.setStyleSheet("color: #a6adc8; font-size: 13px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(desc)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_focus = QSpinBox()
        self.spin_focus.setRange(5, 90)
        self.spin_focus.setValue(25)
        self.spin_focus.setSuffix(" minutes")
        self.spin_focus.setMinimumWidth(140)
        row.addWidget(self.spin_focus)
        l.addLayout(row)
        return w

    def _create_goal_step(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(14)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Set Daily Focus Target")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)

        desc = QLabel("How many hours of focused work do you want to aim for each day?")
        desc.setStyleSheet("color: #a6adc8; font-size: 13px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(desc)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_goal = QSpinBox()
        self.spin_goal.setRange(1, 14)
        self.spin_goal.setValue(2)
        self.spin_goal.setSuffix(" hours")
        self.spin_goal.setMinimumWidth(140)
        row.addWidget(self.spin_goal)
        l.addLayout(row)
        return w

    def _create_finish_step(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(14)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("All Set!")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)

        self.check_autostart = QCheckBox("Start FocusFlow automatically on Linux login")
        self.check_autostart.setChecked(False)
        self.check_autostart.setStyleSheet("font-size: 13px; color: #cdd6f4;")
        l.addWidget(self.check_autostart, alignment=Qt.AlignmentFlag.AlignCenter)

        note = QLabel("You can change any of these options at any time in Settings.")
        note.setStyleSheet("color: #6c7086; font-size: 12px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(note)
        return w

    def _go_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
        self._update_buttons()

    def _go_next(self):
        curr = self.stack.currentIndex()
        if curr == 0:
            self.stack.setCurrentIndex(1)
            self._update_buttons()
        elif curr == 1:
            self.stack.setCurrentIndex(2)
            self._update_buttons()
        elif curr == 2:
            self.stack.setCurrentIndex(3)
            self._update_buttons()
        elif curr == 3:
            # Save settings and complete wizard
            self._finish_wizard()

    def _update_buttons(self):
        curr = self.stack.currentIndex()
        self.btn_back.setEnabled(curr > 0)
        if curr == 3:
            self.btn_next.setText("Launch FocusFlow 🚀")
            self.btn_next.setProperty("class", "Success")
        else:
            self.btn_next.setText("Next")
            self.btn_next.setProperty("class", "Primary")
        self.btn_next.style().unpolish(self.btn_next)
        self.btn_next.style().polish(self.btn_next)

    def _finish_wizard(self):
        focus_mins = self.spin_focus.value()
        goal_hrs = self.spin_goal.value()
        autostart = self.check_autostart.isChecked()

        self.repo.set_preference("focus_duration", focus_mins * 60)
        self.repo.set_preference("daily_goal_seconds", goal_hrs * 3600)
        self.repo.set_preference("autostart_enabled", autostart)
        self.repo.set_preference("first_run_completed", True)

        if autostart:
            enable_autostart()
        else:
            disable_autostart()

        self.accept()
