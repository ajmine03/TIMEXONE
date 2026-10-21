"""
Custom Circular Timer Display Component for FocusFlow.
Renders smooth antialiased multicolor progress arcs, tomato icon, and high-DPI typography.
Matches Image 4's exact timer aesthetic.
"""

import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QLinearGradient, QConicalGradient,
    QPainterPath, QPixmap
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtSvg import QSvgRenderer

from focusflow.core.timer import TimerState
from focusflow.config import TOMATO_PATH


class TimerDisplayWidget(QWidget):
    """Circular multicolor progress timer matching Image 4."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.remaining_seconds = 25 * 60
        self.total_duration = 25 * 60
        self.progress_fraction = 0.0
        self.state = TimerState.IDLE
        self.task_title = ""
        self.mode_label = "Focus Session"
        self.setMinimumSize(250, 250)

        self._svg_renderer = None
        if TOMATO_PATH.exists():
            try:
                self._svg_renderer = QSvgRenderer(str(TOMATO_PATH))
            except Exception:
                self._svg_renderer = None

    def set_timer_data(
        self,
        remaining_seconds: int,
        total_duration: int,
        progress_fraction: float,
        state: TimerState,
        task_title: str = "",
    ):
        self.remaining_seconds = remaining_seconds
        self.total_duration = max(1, total_duration)
        self.progress_fraction = max(0.0, min(1.0, progress_fraction))
        self.state = state
        self.task_title = task_title

        # Determine mode subtitle
        if self.state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            self.mode_label = "Short Break"
        elif self.state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            self.mode_label = "Long Break"
        else:
            self.mode_label = "Focus Session"

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        radius = min(w, h) * 0.42
        thickness = 10.0

        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        # 1. Dark Background Track
        track_pen = QPen(QColor(28, 35, 56, 180), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # 2. Glowing Multi-color Progress Arc
        # Semicircle or full circle sweep:
        # In Image 4, the arc covers about 240-270 degrees or full circumference, starting around 135 deg to 405 deg,
        # or standard 12 o'clock sweep clockwise.
        # Let's support smooth clockwise progress.
        progress = self.progress_fraction if (self.state != TimerState.IDLE or self.progress_fraction > 0) else 0.0

        if progress > 0.001:
            # Multi-color gradient: Electric Blue (#3b82f6) -> Purple (#a855f7) -> Pink (#ec4899) -> Orange (#f97316)
            # Create a conic gradient centered at (cx, cy)
            conic = QConicalGradient(cx, cy, 90.0)  # Start at 90 deg (12 o'clock)
            # Conic gradient runs counter-clockwise in Qt by default, so we interpolate
            conic.setColorAt(0.0, QColor("#3b82f6"))  # Blue
            conic.setColorAt(0.25, QColor("#8b5cf6")) # Violet
            conic.setColorAt(0.55, QColor("#ec4899")) # Pink
            conic.setColorAt(0.85, QColor("#f97316")) # Coral/Orange
            conic.setColorAt(1.0, QColor("#3b82f6"))

            arc_pen = QPen(conic, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)

            span_angle = -int(progress * 360 * 16)
            painter.drawArc(rect, 90 * 16, span_angle)

            # Glowing indicator bead at leading head of the arc
            # Angle in radians: 90 deg minus progress * 360 deg
            theta_deg = 90.0 - (progress * 360.0)
            theta_rad = math.radians(theta_deg)
            bead_x = cx + radius * math.cos(theta_rad)
            bead_y = cy - radius * math.sin(theta_rad)

            # Glow halo
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(236, 72, 153, 90))
            painter.drawEllipse(QPointF(bead_x, bead_y), 9, 9)

            # Core white bead
            painter.setBrush(QColor(255, 255, 255, 250))
            painter.drawEllipse(QPointF(bead_x, bead_y), 5, 5)

        # 3. Tomato Icon (in center top)
        icon_size = 40.0
        icon_rect = QRectF(cx - icon_size / 2.0, cy - radius * 0.58, icon_size, icon_size)
        if self._svg_renderer:
            self._svg_renderer.render(painter, icon_rect)
        else:
            # Fallback vector tomato
            painter.setBrush(QColor("#ef4444"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(icon_rect)

        # 4. Large Digital Countdown (e.g. "25:00")
        mins, secs = divmod(max(0, self.remaining_seconds), 60)
        time_text = f"{mins:02d}:{secs:02d}"

        painter.setPen(QColor("#ffffff"))
        font_size = int(radius * 0.40)
        time_font = QFont("Inter", font_size, QFont.Weight.Bold)
        time_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        painter.setFont(time_font)

        time_rect = QRectF(cx - radius * 0.9, cy - radius * 0.08, radius * 1.8, radius * 0.48)
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, time_text)

        # 5. Mode Subtitle (e.g. "Focus Session")
        sub_text = self.mode_label
        if self.state.is_paused:
            sub_text += " (Paused)"

        painter.setPen(QColor("#8a95af"))
        sub_font = QFont("Inter", max(9, int(radius * 0.12)), QFont.Weight.Medium)
        painter.setFont(sub_font)

        sub_rect = QRectF(cx - radius * 0.8, cy + radius * 0.38, radius * 1.6, 24)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, sub_text)

        painter.end()
