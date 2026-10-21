"""
No Task Selected confirmation and selection dialog for FocusFlow.
Allows starting general focus, selecting an existing task, or creating a new task quickly.
Redesigned with high-end dark glass styling matching Image 4.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt

from focusflow.core.task_manager import TaskManager


class NoTaskDialog(QDialog):
    """Prompts user when starting a Pomodoro without an active task."""

    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.selected_task_id: Optional[str] = None
        self.dont_ask_again: bool = False

        self.setWindowTitle("No Task Selected — FocusFlow")
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog {
                background-color: #0d111d;
                color: #e2e8f0;
            }
            QFrame.OptionCard {
                background-color: #121727;
                border: 1px solid #1e263d;
                border-radius: 12px;
            }
            QLineEdit, QComboBox {
                background-color: #161c2e;
                color: #ffffff;
                border: 1px solid #283350;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #6366f1;
                background-color: #192035;
            }
            QComboBox QAbstractItemView {
                background-color: #161c2e;
                color: #ffffff;
                border: 1px solid #283350;
                selection-background-color: #4f46e5;
                padding: 4px;
            }
            QCheckBox {
                color: #cbd5e1;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #283350;
                background-color: #121727;
            }
            QCheckBox::indicator:checked {
                background-color: #10b981;
                border-color: #10b981;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 22)
        layout.setSpacing(18)

        # Header Title & Subtitle
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title_lbl = QLabel("No Task Selected")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_lbl)

        desc_lbl = QLabel("How would you like to track this focus session?")
        desc_lbl.setStyleSheet("color: #8a95af; font-size: 13px;")
        header_layout.addWidget(desc_lbl)
        layout.addLayout(header_layout)

        # 1. Option: Select Existing Task
        pending_tasks = [t for t in self.task_manager.list(filter_mode="all") if t.status != "completed"]
        if pending_tasks:
            select_card = QFrame()
            select_card.setProperty("class", "OptionCard")
            sel_card_layout = QVBoxLayout(select_card)
            sel_card_layout.setContentsMargins(14, 14, 14, 14)
            sel_card_layout.setSpacing(10)

            sel_title = QLabel("Select an Existing Task")
            sel_title.setStyleSheet("font-weight: 600; color: #ffffff; font-size: 13px;")
            sel_card_layout.addWidget(sel_title)

            sel_row = QHBoxLayout()
            sel_row.setSpacing(10)

            self.task_combo = QComboBox()
            self.task_combo.setMinimumHeight(38)
            for t in pending_tasks:
                self.task_combo.addItem(f"{t.title} ({t.completed_pomodoros}/{t.estimated_pomodoros})", t.id)
            sel_row.addWidget(self.task_combo, stretch=1)

            btn_start_sel = QPushButton("Focus Task")
            btn_start_sel.setMinimumHeight(38)
            btn_start_sel.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #6366f1);
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 0 16px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #4f46e5);
                }
            """)
            btn_start_sel.clicked.connect(self._select_existing_task)
            sel_row.addWidget(btn_start_sel)
            sel_card_layout.addLayout(sel_row)

            layout.addWidget(select_card)

        # 2. Option: Quick Create Task
        create_card = QFrame()
        create_card.setProperty("class", "OptionCard")
        cr_card_layout = QVBoxLayout(create_card)
        cr_card_layout.setContentsMargins(14, 14, 14, 14)
        cr_card_layout.setSpacing(10)

        cr_title = QLabel("Or Create a New Task")
        cr_title.setStyleSheet("font-weight: 600; color: #ffffff; font-size: 13px;")
        cr_card_layout.addWidget(cr_title)

        cr_row = QHBoxLayout()
        cr_row.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setMinimumHeight(38)
        self.title_input.setPlaceholderText("New task title...")
        self.title_input.returnPressed.connect(self._create_new_task)
        cr_row.addWidget(self.title_input, stretch=1)

        btn_create = QPushButton("Create && Focus")
        btn_create.setMinimumHeight(38)
        btn_create.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
            }
        """)
        btn_create.clicked.connect(self._create_new_task)
        cr_row.addWidget(btn_create)
        cr_card_layout.addLayout(cr_row)

        layout.addWidget(create_card)

        # 3. Bottom controls
        bottom_row = QHBoxLayout()
        self.check_dont_ask = QCheckBox("Don't ask again")
        bottom_row.addWidget(self.check_dont_ask)
        bottom_row.addStretch()

        btn_continue_general = QPushButton("Continue Without Task")
        btn_continue_general.setMinimumHeight(36)
        btn_continue_general.setStyleSheet("""
            QPushButton {
                background-color: #1a2136;
                color: #cbd5e1;
                border: 1px solid #273352;
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #232c48;
                color: #ffffff;
            }
        """)
        btn_continue_general.clicked.connect(self._continue_without_task)
        bottom_row.addWidget(btn_continue_general)

        layout.addLayout(bottom_row)

    def _select_existing_task(self):
        if hasattr(self, "task_combo"):
            self.selected_task_id = self.task_combo.currentData()
        self.dont_ask_again = self.check_dont_ask.isChecked()
        self.accept()

    def _create_new_task(self):
        title = self.title_input.text().strip()
        if not title:
            return
        t = self.task_manager.create(title=title)
        self.selected_task_id = t.id
        self.dont_ask_again = self.check_dont_ask.isChecked()
        self.accept()

    def _continue_without_task(self):
        self.selected_task_id = None
        self.dont_ask_again = self.check_dont_ask.isChecked()
        self.accept()
