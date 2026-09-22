"""
Settings and Configuration View for FocusFlow.
Manages timer preferences, appearance, notifications, floating timer, and autostart.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QCheckBox, QComboBox, QSlider, QScrollArea,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from focusflow.config import APP_NAME
from focusflow.db.repository import Repository
from focusflow.core.timer import PomodoroEngine
from focusflow.ui.notifications import NotificationService
from focusflow.utils.sound import SoundPlayer
from focusflow.utils.autostart import enable_autostart, disable_autostart, is_autostart_enabled


class SettingsView(QWidget):
    """Configuration interface for all FocusFlow options."""

    theme_changed = pyqtSignal(str)           # 'dark', 'light'
    durations_changed = pyqtSignal()

    def __init__(
        self,
        repository: Repository,
        engine: PomodoroEngine,
        notification_service: NotificationService,
        sound_player: SoundPlayer,
        parent=None,
    ):
        super().__init__(parent)
        self.repo = repository
        self.engine = engine
        self.notify = notification_service
        self.sound = sound_player

        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # Title Row
        top_row = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        top_row.addWidget(title)
        top_row.addStretch()

        self.btn_save = QPushButton("Save Changes")
        self.btn_save.setProperty("class", "Primary")
        self.btn_save.clicked.connect(self.save_settings)
        top_row.addWidget(self.btn_save)
        main_layout.addLayout(top_row)

        # Scrollable Settings Form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        self.form_layout = QVBoxLayout(container)
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(18)

        # 1. Timer Settings Card
        self.form_layout.addWidget(self._create_timer_section())

        # 2. Notifications & Audio Card
        self.form_layout.addWidget(self._create_notification_section())

        # 3. Appearance Card
        self.form_layout.addWidget(self._create_appearance_section())

        # 4. Productivity & Autostart Card
        self.form_layout.addWidget(self._create_productivity_section())

        # 5. Floating Timer Card
        self.form_layout.addWidget(self._create_floating_section())

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_section_frame(self, title_text: str):
        frame = QFrame()
        frame.setProperty("class", "Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        lbl = QLabel(title_text)
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl)
        return frame, layout

    def _create_timer_section(self) -> QFrame:
        card, layout = self._create_section_frame("⏱️ Timer Configuration")
        form = QFormLayout()
        form.setSpacing(12)

        self.spin_focus = QSpinBox()
        self.spin_focus.setRange(1, 120)
        self.spin_focus.setSuffix(" minutes")
        form.addRow("Focus Duration:", self.spin_focus)

        self.spin_short_break = QSpinBox()
        self.spin_short_break.setRange(1, 45)
        self.spin_short_break.setSuffix(" minutes")
        form.addRow("Short Break Duration:", self.spin_short_break)

        self.spin_long_break = QSpinBox()
        self.spin_long_break.setRange(1, 60)
        self.spin_long_break.setSuffix(" minutes")
        form.addRow("Long Break Duration:", self.spin_long_break)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 12)
        self.spin_interval.setSuffix(" pomodoros")
        form.addRow("Long Break Interval:", self.spin_interval)

        self.check_auto_breaks = QCheckBox("Automatically start breaks when focus completes")
        form.addRow("", self.check_auto_breaks)

        self.check_auto_focus = QCheckBox("Automatically start focus when breaks complete")
        form.addRow("", self.check_auto_focus)

        layout.addLayout(form)
        return card

    def _create_notification_section(self) -> QFrame:
        card, layout = self._create_section_frame("🔔 Notifications & Audio")
        form = QFormLayout()
        form.setSpacing(12)

        self.check_notify = QCheckBox("Enable native Linux desktop notifications")
        form.addRow("", self.check_notify)

        self.check_sound = QCheckBox("Play sound effect on timer completion (PipeWire/ALSA)")
        form.addRow("", self.check_sound)

        # Test buttons
        test_row = QHBoxLayout()
        btn_test_notif = QPushButton("Test Notification")
        btn_test_notif.clicked.connect(self._test_notification)
        test_row.addWidget(btn_test_notif)

        btn_test_sound = QPushButton("Test Sound Chime")
        btn_test_sound.clicked.connect(self._test_sound)
        test_row.addWidget(btn_test_sound)
        test_row.addStretch()

        form.addRow("Diagnostics:", test_row)
        layout.addLayout(form)
        return card

    def _create_appearance_section(self) -> QFrame:
        card, layout = self._create_section_frame("🎨 Appearance & Themes")
        form = QFormLayout()
        form.setSpacing(12)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dark Theme (Default)", "Light Theme"])
        form.addRow("Color Theme:", self.combo_theme)

        layout.addLayout(form)
        return card

    def _create_productivity_section(self) -> QFrame:
        card, layout = self._create_section_frame("🎯 Goals & System Integration")
        form = QFormLayout()
        form.setSpacing(12)

        self.spin_goal = QSpinBox()
        self.spin_goal.setRange(1, 16)
        self.spin_goal.setSuffix(" hours")
        form.addRow("Daily Focus Target:", self.spin_goal)

        self.check_autostart = QCheckBox("Start FocusFlow automatically on Linux login")
        form.addRow("", self.check_autostart)

        layout.addLayout(form)
        return card

    def _create_floating_section(self) -> QFrame:
        card, layout = self._create_section_frame("🗗 Floating Timer Widget")
        form = QFormLayout()
        form.setSpacing(12)

        self.check_auto_show = QCheckBox("Show floating timer automatically when focus session starts")
        form.addRow("", self.check_auto_show)

        self.check_always_top = QCheckBox("Keep floating timer always on top of other windows")
        form.addRow("", self.check_always_top)

        layout.addLayout(form)
        return card

    def load_settings(self):
        prefs = self.repo.get_all_preferences()

        self.spin_focus.setValue(prefs.get("focus_duration", 1500) // 60)
        self.spin_short_break.setValue(prefs.get("short_break", 300) // 60)
        self.spin_long_break.setValue(prefs.get("long_break", 900) // 60)
        self.spin_interval.setValue(prefs.get("long_break_interval", 4))

        self.check_auto_breaks.setChecked(prefs.get("auto_start_breaks", True))
        self.check_auto_focus.setChecked(prefs.get("auto_start_focus", False))

        self.check_notify.setChecked(prefs.get("notifications_enabled", True))
        self.check_sound.setChecked(prefs.get("sound_enabled", True))

        theme = prefs.get("theme", "dark")
        self.combo_theme.setCurrentIndex(1 if theme == "light" else 0)

        self.spin_goal.setValue(prefs.get("daily_goal_seconds", 7200) // 3600)
        self.check_autostart.setChecked(is_autostart_enabled())

        self.check_auto_show.setChecked(prefs.get("floating_auto_show", True))
        self.check_always_top.setChecked(prefs.get("floating_always_on_top", True))

    def save_settings(self):
        focus_sec = self.spin_focus.value() * 60
        short_sec = self.spin_short_break.value() * 60
        long_sec = self.spin_long_break.value() * 60
        interval = self.spin_interval.value()

        self.repo.set_preference("focus_duration", focus_sec)
        self.repo.set_preference("short_break", short_sec)
        self.repo.set_preference("long_break", long_sec)
        self.repo.set_preference("long_break_interval", interval)
        self.repo.set_preference("auto_start_breaks", self.check_auto_breaks.isChecked())
        self.repo.set_preference("auto_start_focus", self.check_auto_focus.isChecked())

        self.repo.set_preference("notifications_enabled", self.check_notify.isChecked())
        self.repo.set_preference("sound_enabled", self.check_sound.isChecked())

        theme_name = "light" if self.combo_theme.currentIndex() == 1 else "dark"
        self.repo.set_preference("theme", theme_name)
        self.theme_changed.emit(theme_name)

        goal_sec = self.spin_goal.value() * 3600
        self.repo.set_preference("daily_goal_seconds", goal_sec)

        autostart_active = self.check_autostart.isChecked()
        self.repo.set_preference("autostart_enabled", autostart_active)
        if autostart_active:
            enable_autostart()
        else:
            disable_autostart()

        self.repo.set_preference("floating_auto_show", self.check_auto_show.isChecked())
        self.repo.set_preference("floating_always_on_top", self.check_always_top.isChecked())

        # Propagate to engine
        self.engine.update_durations(
            focus_duration=focus_sec,
            short_break=short_sec,
            long_break=long_sec,
            interval=interval,
        )
        self.engine.auto_start_breaks = self.check_auto_breaks.isChecked()
        self.engine.auto_start_focus = self.check_auto_focus.isChecked()
        self.durations_changed.emit()

        QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully!")

    def _test_notification(self):
        self.notify.send_notification(
            title=f"{APP_NAME} Test",
            message="Desktop notifications are configured and working properly!",
            play_sound=self.check_sound.isChecked(),
        )

    def _test_sound(self):
        self.sound.play_chime()
