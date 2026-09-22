"""
Todo and Task Management View for FocusFlow.
Features task creation/editing dialogs, filtering, sorting, and direct Pomodoro linking.
"""

from datetime import date
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QScrollArea, QDialog,
    QFormLayout, QTextEdit, QSpinBox, QDateEdit, QMessageBox,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont

from focusflow.core.task_manager import TaskManager
from focusflow.core.timer import PomodoroEngine
from focusflow.db.repository import Task


class TaskEditDialog(QDialog):
    """Modal dialog for creating or updating a task."""

    def __init__(self, parent=None, task: Optional[Task] = None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Edit Task" if task else "Create New Task")
        self.setMinimumWidth(440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Study Linux Kernel Modules")
        if self.task:
            self.title_edit.setText(self.task.title)
        form.addRow("Title *:", self.title_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Notes, sub-items, or context...")
        self.desc_edit.setMaximumHeight(80)
        if self.task:
            self.desc_edit.setPlainText(self.task.description)
        form.addRow("Notes:", self.desc_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"])
        if self.task:
            idx = {"low": 0, "medium": 1, "high": 2}.get(self.task.priority.lower(), 1)
            self.priority_combo.setCurrentIndex(idx)
        else:
            self.priority_combo.setCurrentIndex(1)  # Default Medium
        form.addRow("Priority:", self.priority_combo)

        self.pomo_spin = QSpinBox()
        self.pomo_spin.setRange(1, 50)
        self.pomo_spin.setValue(self.task.estimated_pomodoros if self.task else 2)
        form.addRow("Estimated Pomodoros:", self.pomo_spin)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        if self.task and self.task.due_date:
            d = QDate.fromString(self.task.due_date, "yyyy-MM-dd")
            self.due_date_edit.setDate(d)
        else:
            self.due_date_edit.setDate(QDate.currentDate())
        
        self.has_due_date = QCheckBox("Set due date")
        self.has_due_date.setChecked(bool(self.task and self.task.due_date))
        self.has_due_date.toggled.connect(self.due_date_edit.setEnabled)
        self.due_date_edit.setEnabled(self.has_due_date.isChecked())

        due_row = QHBoxLayout()
        due_row.addWidget(self.has_due_date)
        due_row.addWidget(self.due_date_edit)
        form.addRow("Due Date:", due_row)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g. study, dev, reading")
        if self.task:
            self.tags_edit.setText(self.task.tags)
        form.addRow("Tags:", self.tags_edit)

        layout.addLayout(form)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Task")
        btn_save.setProperty("class", "Primary")
        btn_save.clicked.connect(self._validate_and_save)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _validate_and_save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Task title cannot be empty.")
            return
        self.accept()

    def get_data(self) -> dict:
        due_str = None
        if self.has_due_date.isChecked():
            due_str = self.due_date_edit.date().toString("yyyy-MM-dd")

        return {
            "title": self.title_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "priority": self.priority_combo.currentText().lower(),
            "estimated_pomodoros": self.pomo_spin.value(),
            "due_date": due_str,
            "tags": self.tags_edit.text().strip(),
        }


class TaskCard(QFrame):
    """Visual card for a single task."""

    focus_requested = pyqtSignal(str)  # task_id
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal(str)

    def __init__(self, task: Task, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.task = task
        self.is_active = is_active
        self.setProperty("class", "Card")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.task.status == "completed")
        self.checkbox.clicked.connect(lambda: self.toggle_requested.emit(self.task.id))
        layout.addWidget(self.checkbox)

        # Center details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)

        # Title + Badges row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        title_lbl = QLabel(self.task.title)
        if self.task.status == "completed":
            title_lbl.setStyleSheet("text-decoration: line-through; color: #6c7086; font-size: 14px;")
        else:
            title_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")
        top_row.addWidget(title_lbl)

        # Priority badge
        p_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#3b82f6"}
        p_color = p_colors.get(self.task.priority, "#6c7086")
        p_badge = QLabel(self.task.priority.upper())
        p_badge.setStyleSheet(
            f"background-color: {p_color}22; color: {p_color}; border: 1px solid {p_color}44; "
            "border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: bold;"
        )
        top_row.addWidget(p_badge)

        # Pomodoros Badge
        pomo_badge = QLabel(f"🍅 {self.task.completed_pomodoros}/{self.task.estimated_pomodoros}")
        pomo_badge.setStyleSheet(
            "background-color: #10b98122; color: #10b981; border: 1px solid #10b98144; "
            "border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: bold;"
        )
        top_row.addWidget(pomo_badge)

        # Due date badge if present
        if self.task.due_date:
            is_overdue = self.task.due_date < date.today().isoformat() and self.task.status != "completed"
            d_color = "#ef4444" if is_overdue else "#94a3b8"
            due_badge = QLabel(f"📅 {self.task.due_date}")
            due_badge.setStyleSheet(
                f"color: {d_color}; font-size: 11px; font-weight: 500;"
            )
            top_row.addWidget(due_badge)

        top_row.addStretch()
        details_layout.addLayout(top_row)

        # Description / Tags
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        if self.task.description:
            desc_snip = self.task.description if len(self.task.description) <= 60 else (self.task.description[:57] + "...")
            desc_lbl = QLabel(desc_snip)
            desc_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
            bottom_row.addWidget(desc_lbl)

        for tag in self.task.tag_list:
            t_badge = QLabel(f"#{tag}")
            t_badge.setStyleSheet("color: #89b4fa; font-size: 11px;")
            bottom_row.addWidget(t_badge)

        bottom_row.addStretch()
        details_layout.addLayout(bottom_row)

        layout.addLayout(details_layout, stretch=1)

        # Action Buttons
        if self.task.status != "completed":
            btn_focus = QPushButton("Focus" if not self.is_active else "Active")
            if self.is_active:
                btn_focus.setProperty("class", "Success")
            else:
                btn_focus.setProperty("class", "Primary")
            btn_focus.clicked.connect(lambda: self.focus_requested.emit(self.task.id))
            layout.addWidget(btn_focus)

        btn_edit = QPushButton("Edit")
        btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.task.id))
        layout.addWidget(btn_edit)

        btn_del = QPushButton("Delete")
        btn_del.setProperty("class", "Danger")
        btn_del.clicked.connect(lambda: self.delete_requested.emit(self.task.id))
        layout.addWidget(btn_del)


class TasksView(QWidget):
    """Full task manager screen with filter pills, search, and cards list."""

    focus_task_requested = pyqtSignal(str)  # task_id

    def __init__(
        self,
        task_manager: TaskManager,
        engine: PomodoroEngine,
        parent=None,
    ):
        super().__init__(parent)
        self.task_manager = task_manager
        self.engine = engine
        self.current_filter = "all"

        self._init_ui()
        self.task_manager.subscribe_change(self.refresh_task_list)
        self.engine.subscribe_state_changed(lambda s: self.refresh_task_list())
        self.refresh_task_list()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # Top Header
        top_layout = QHBoxLayout()
        title_label = QLabel("Tasks & Todos")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        top_layout.addWidget(title_label)
        top_layout.addStretch()

        btn_new_task = QPushButton("+ New Task")
        btn_new_task.setProperty("class", "Primary")
        btn_new_task.setMinimumHeight(38)
        btn_new_task.clicked.connect(self._open_new_task_dialog)
        top_layout.addWidget(btn_new_task)
        main_layout.addLayout(top_layout)

        # Filter Pills & Search/Sort Row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Filter Buttons
        self.filter_buttons = {}
        for key, label in [
            ("all", "All"),
            ("today", "Today"),
            ("upcoming", "Upcoming"),
            ("high_priority", "High Priority"),
            ("completed", "Completed"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._set_filter(k))
            toolbar.addWidget(btn)
            self.filter_buttons[key] = btn

        self.filter_buttons["all"].setChecked(True)
        toolbar.addStretch()

        # Search Bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search tasks...")
        self.search_edit.setMinimumWidth(180)
        self.search_edit.textChanged.connect(self.refresh_task_list)
        toolbar.addWidget(self.search_edit)

        # Sort Dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Newest First", "created_desc")
        self.sort_combo.addItem("Oldest First", "created_asc")
        self.sort_combo.addItem("Priority", "priority")
        self.sort_combo.addItem("Due Date", "due_date")
        self.sort_combo.addItem("Remaining 🍅", "remaining_pomodoros")
        self.sort_combo.currentIndexChanged.connect(self.refresh_task_list)
        toolbar.addWidget(self.sort_combo)

        main_layout.addLayout(toolbar)

        # Scrollable Task Cards List
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 0, 4)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll)

    def _set_filter(self, filter_key: str):
        self.current_filter = filter_key
        for k, btn in self.filter_buttons.items():
            btn.setChecked(k == filter_key)
        self.refresh_task_list()

    def _open_new_task_dialog(self):
        dlg = TaskEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.task_manager.create(**data)

    def _open_edit_task_dialog(self, task_id: str):
        task = self.task_manager.get(task_id)
        if not task:
            return
        dlg = TaskEditDialog(self, task=task)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            self.task_manager.update(task_id, **data)

    def _delete_task_prompt(self, task_id: str):
        task = self.task_manager.get(task_id)
        if not task:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Task",
            f"Are you sure you want to delete '{task.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.task_manager.delete(task_id)

    def _toggle_task(self, task_id: str):
        self.task_manager.toggle_complete(task_id)

    def _focus_task(self, task_id: str):
        self.engine.set_active_task(task_id)
        self.focus_task_requested.emit(task_id)

    def refresh_task_list(self):
        # Clear existing cards except stretch
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        search_query = self.search_edit.text().strip()
        sort_by = self.sort_combo.currentData() or "created_desc"

        tasks = self.task_manager.list(
            filter_mode=self.current_filter,
            search=search_query if search_query else None,
            sort_by=sort_by,
        )

        if not tasks:
            empty_lbl = QLabel("No tasks found.")
            empty_lbl.setStyleSheet("color: #6c7086; font-size: 14px; padding: 40px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.insertWidget(0, empty_lbl)
            return

        for idx, task in enumerate(tasks):
            is_active = (task.id == self.engine.active_task_id)
            card = TaskCard(task=task, is_active=is_active)
            card.focus_requested.connect(self._focus_task)
            card.edit_requested.connect(self._open_edit_task_dialog)
            card.delete_requested.connect(self._delete_task_prompt)
            card.toggle_requested.connect(self._toggle_task)
            self.cards_layout.insertWidget(idx, card)
