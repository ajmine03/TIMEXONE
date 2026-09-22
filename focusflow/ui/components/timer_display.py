"""
Custom Circular Timer Display Component for FocusFlow.
Renders smooth antialiased progress arcs, status badges, and typography.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRectF

from focusflow.core.timer import TimerState


class TimerDisplayWidget(QWidget):
    """Circular progress timer with responsive typography and state coloring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.remaining_seconds = 25 * 60
        self.total_duration = 25 * 60
        self.progress_fraction = 0.0
        self.state = TimerState.IDLE
        self.task_title = "No Active Task"
        self.setMinimumSize(280, 280)

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
        if task_title:
            self.task_title = task_title
        elif state == TimerState.IDLE:
            self.task_title = "Ready to Focus"
        self.update()

    def _get_colors(self):
        """Return (track_color, arc_start, arc_end, text_accent) based on state."""
        if self.state.is_paused:
            return (QColor("#313244"), QColor("#f59e0b"), QColor("#d97706"), QColor("#fbbf24"))
        elif self.state.is_break:
            if self.state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
                return (QColor("#313244"), QColor("#8b5cf6"), QColor("#6d28d9"), QColor("#a78bfa"))
            else:
                return (QColor("#313244"), QColor("#10b981"), QColor("#059669"), QColor("#34d399"))
        elif self.state == TimerState.RUNNING_FOCUS:
            return (QColor("#313244"), QColor("#06b6d4"), QColor("#3b82f6"), QColor("#60a5fa"))
        else: # IDLE
            return (QColor("#313244"), QColor("#64748b"), QColor("#475569"), QColor("#94a3b8"))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height) - 24
        x = (width - size) / 2
        y = (height - size) / 2
        rect = QRectF(x, y, size, size)

        track_color, arc_start, arc_end, text_accent = self._get_colors()

        # 1. Background Track
        track_pen = QPen(track_color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # 2. Foreground Progress Arc
        if self.state != TimerState.IDLE or self.progress_fraction > 0:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, arc_start)
            gradient.setColorAt(1.0, arc_end)

            arc_pen = QPen(gradient, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)

            # Arc angle in 1/16th of a degree. Start at 90 deg (12 o'clock), sweep clockwise (negative)
            span_angle = -int(self.progress_fraction * 360 * 16)
            painter.drawArc(rect, 90 * 16, span_angle)

        # 3. Status Badge Text (e.g. FOCUS, SHORT BREAK, PAUSED)
        badge_text = "FOCUS"
        if self.state.is_paused:
            badge_text = "PAUSED"
        elif self.state in (TimerState.RUNNING_SHORT_BREAK, TimerState.PAUSED_SHORT_BREAK):
            badge_text = "SHORT BREAK"
        elif self.state in (TimerState.RUNNING_LONG_BREAK, TimerState.PAUSED_LONG_BREAK):
            badge_text = "LONG BREAK"
        elif self.state == TimerState.IDLE:
            badge_text = "FOCUS FLOW"

        painter.setPen(text_accent)
        badge_font = QFont("Inter", 10, QFont.Weight.Bold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(badge_font)
        badge_rect = QRectF(x, y + size * 0.22, size, 24)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # 4. Large Digital Countdown (e.g. 24:37)
        mins, secs = divmod(self.remaining_seconds, 60)
        time_text = f"{mins:02d}:{secs:02d}"

        painter.setPen(QColor("#ffffff"))
        time_font = QFont("Inter", int(size * 0.18), QFont.Weight.Bold)
        painter.setFont(time_font)
        time_rect = QRectF(x, y + size * 0.35, size, size * 0.3)
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, time_text)

        # 5. Active Task Title
        task_label = self.task_title if len(self.task_title) <= 28 else (self.task_title[:25] + "...")
        painter.setPen(QColor("#a6adc8"))
        task_font = QFont("Inter", 11, QFont.Weight.Normal)
        painter.setFont(task_font)
        task_rect = QRectF(x + 16, y + size * 0.68, size - 32, 30)
        painter.drawText(task_rect, Qt.AlignmentFlag.AlignCenter, task_label)

        painter.end()
