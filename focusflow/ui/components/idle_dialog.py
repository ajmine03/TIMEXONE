"""
Idle Inactivity Return Dialog for FocusFlow.
Asks the user what to do with time elapsed while away.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class IdleReturnDialog(QDialog):
    """
    Dialog displayed when user returns after system inactivity during an active focus session.
    """

    # Action codes
    KEEP_TIME = "keep"
    DISCARD_AND_PAUSE = "discard_pause"
    DISCARD_AND_RESUME = "discard_resume"
    DISCARD_SESSION = "discard_session"

    def __init__(self, idle_seconds: int, parent=None):
        super().__init__(parent)
        self.idle_seconds = idle_seconds
        self.selected_action = self.KEEP_TIME

        self.setWindowTitle("FocusFlow — Inactivity Detected")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        icon_lbl = QLabel("⏳")
        icon_lbl.setFont(QFont("sans-serif", 24))
        header_row.addWidget(icon_lbl)

        mins = self.idle_seconds // 60
        secs = self.idle_seconds % 60
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        title_lbl = QLabel(f"You were away for {time_str}")
        title_lbl.setFont(QFont("sans-serif", 15, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #cdd6f4;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()
        layout.addLayout(header_row)

        desc_lbl = QLabel(
            "FocusFlow detected system inactivity during your focus session. "
            "How would you like to handle this time?"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #a6adc8; font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #313244;")
        layout.addWidget(line)

        # Action Buttons
        btn_keep = QPushButton("✓  Keep Inactive Time as Focus")
        btn_keep.setToolTip("Count the elapsed time toward your focus goal and continue.")
        btn_keep.setStyleSheet(
            "QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; "
            "padding: 10px; border-radius: 6px; text-align: left; } "
            "QPushButton:hover { background-color: #b4befe; }"
        )
        btn_keep.clicked.connect(lambda: self._choose(self.KEEP_TIME))
        layout.addWidget(btn_keep)

        btn_discard_resume = QPushButton("↺  Discard Inactivity & Resume Focus")
        btn_discard_resume.setToolTip("Subtract the idle time from this session and keep focusing.")
        btn_discard_resume.setStyleSheet(
            "QPushButton { background-color: #313244; color: #cdd6f4; font-weight: 500; "
            "padding: 10px; border-radius: 6px; text-align: left; border: 1px solid #45475a; } "
            "QPushButton:hover { background-color: #45475a; }"
        )
        btn_discard_resume.clicked.connect(lambda: self._choose(self.DISCARD_AND_RESUME))
        layout.addWidget(btn_discard_resume)

        btn_discard_pause = QPushButton("⏸  Discard Inactivity & Pause Timer")
        btn_discard_pause.setToolTip("Subtract the idle time from this session and leave timer paused.")
        btn_discard_pause.setStyleSheet(
            "QPushButton { background-color: #313244; color: #cdd6f4; font-weight: 500; "
            "padding: 10px; border-radius: 6px; text-align: left; border: 1px solid #45475a; } "
            "QPushButton:hover { background-color: #45475a; }"
        )
        btn_discard_pause.clicked.connect(lambda: self._choose(self.DISCARD_AND_PAUSE))
        layout.addWidget(btn_discard_pause)

        btn_cancel_session = QPushButton("✕  Discard Entire Pomodoro Session")
        btn_cancel_session.setToolTip("Cancel and reset the current Pomodoro.")
        btn_cancel_session.setStyleSheet(
            "QPushButton { background-color: transparent; color: #f38ba8; font-size: 12px; "
            "padding: 8px; border: none; text-align: left; } "
            "QPushButton:hover { text-decoration: underline; }"
        )
        btn_cancel_session.clicked.connect(lambda: self._choose(self.DISCARD_SESSION))
        layout.addWidget(btn_cancel_session)

    def _choose(self, action: str):
        self.selected_action = action
        self.accept()
