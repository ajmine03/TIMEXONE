"""
No Task Selected confirmation and selection dialog for FocusFlow.
Allows starting general focus, selecting an existing task, or creating a new task quickly.
"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QGroupBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt

from focusflow.core.task_manager import TaskManager
from focusflow.db.repository import Task


class NoTaskDialog(QDialog):
    """Prompts user when starting a Pomodoro without an active task."""

    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.selected_task_id: Optional[str] = None
        self.dont_ask_again: bool = False

        self.setWindowTitle("No Task Selected")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title_lbl = QLabel("No Task Selected")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("How would you like to track this focus session?")
        desc_lbl.setStyleSheet("color: #a6adc8; font-size: 13px;")
        layout.addWidget(desc_lbl)

        # 1. Option: Select Existing Task
        pending_tasks = [t for t in self.task_manager.list(filter_mode="all") if t.status != "completed"]
        if pending_tasks:
            select_group = QGroupBox("Select an Existing Task")
            select_group.setStyleSheet("QGroupBox { color: #cdd6f4; font-weight: bold; }")
            sel_layout = QHBoxLayout(select_group)

            self.task_combo = QComboBox()
            for t in pending_tasks:
                self.task_combo.addItem(f"{t.title} ({t.completed_pomodoros}/{t.estimated_pomodoros} 🍅)", t.id)
            sel_layout.addWidget(self.task_combo)

            btn_start_sel = QPushButton("Focus Task")
            btn_start_sel.setProperty("class", "Primary")
            btn_start_sel.clicked.connect(self._select_existing_task)
            sel_layout.addWidget(btn_start_sel)

            layout.addWidget(select_group)

        # 2. Option: Quick Create Task
        create_group = QGroupBox("Or Create a New Task")
        create_group.setStyleSheet("QGroupBox { color: #cdd6f4; font-weight: bold; }")
        cr_layout = QHBoxLayout(create_group)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("New task title...")
        cr_layout.addWidget(self.title_input)

        btn_create = QPushButton("Create & Focus")
        btn_create.setProperty("class", "Success")
        btn_create.clicked.connect(self._create_new_task)
        cr_layout.addWidget(btn_create)

        layout.addWidget(create_group)

        # 3. Bottom controls
        bottom_row = QHBoxLayout()
        self.check_dont_ask = QCheckBox("Don't ask again")
        bottom_row.addWidget(self.check_dont_ask)
        bottom_row.addStretch()

        btn_continue_general = QPushButton("Continue Without Task")
        btn_continue_general.clicked.connect(self._continue_without_task)
        bottom_row.addWidget(btn_continue_general)

        layout.addLayout(bottom_row)

    def _select_existing_task(self):
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
