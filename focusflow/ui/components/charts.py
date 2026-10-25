"""
Lightweight, native QPainter vector charts for FocusFlow.
Renders weekly bar graphs, task completion donut chart, and time-of-day distribution.
Matches Image 4's exact analytics cards.
"""

from typing import List, Tuple, Dict
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRectF, QPointF


class WeeklyBarChart(QWidget):
    """Clean, antialiased 7-day focus time bar chart matching Image 4."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # List of (day_name, focus_hours)
        self.data: List[Tuple[str, float]] = [
            ("Mon", 1.2), ("Tue", 2.5), ("Wed", 0.9), ("Thu", 1.6),
            ("Fri", 3.2), ("Sat", 1.8), ("Sun", 0.8)
        ]
        self.max_scale_hours = 4.0
        self.y_steps = [0, 1, 2, 3, 4]
        self.setMinimumHeight(150)

    def set_data(self, data: List[Tuple[str, float]]):
        self.data = data
        max_val = max([val for _, val in self.data] + [0.0])
        if max_val <= 0.0:
            self.max_scale_hours = 4.0
            self.y_steps = [0, 1, 2, 3, 4]
        elif max_val <= 1.0:
            self.max_scale_hours = 1.0
            self.y_steps = [0, 0.5, 1.0]
        elif max_val <= 2.0:
            self.max_scale_hours = 2.0
            self.y_steps = [0, 1, 2]
        elif max_val <= 4.0:
            self.max_scale_hours = 4.0
            self.y_steps = [0, 1, 2, 3, 4]
        else:
            import math
            ceil_val = int(math.ceil(max_val))
            self.max_scale_hours = float(ceil_val)
            step = max(1, ceil_val // 4)
            self.y_steps = list(range(0, ceil_val + 1, step))
            if ceil_val not in self.y_steps:
                self.y_steps.append(ceil_val)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        padding_left = 30
        padding_right = 22
        padding_top = 16
        padding_bottom = 28

        chart_w = w - padding_left - padding_right
        chart_h = h - padding_top - padding_bottom

        # 1. Y-Axis Grid Lines & Labels
        grid_pen = QPen(QColor(36, 46, 74, 90), 1, Qt.PenStyle.DashLine)
        label_font = QFont("Inter", 9, QFont.Weight.Medium)
        painter.setFont(label_font)

        for step in self.y_steps:
            if step > self.max_scale_hours:
                continue
            y_pos = padding_top + chart_h - (step / self.max_scale_hours) * chart_h

            # Label
            lbl_str = f"{int(step)}h" if step == int(step) else f"{step}h"
            painter.setPen(QColor("#64748b"))
            painter.drawText(QRectF(0, y_pos - 8, padding_left - 8, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, lbl_str)

            # Line
            painter.setPen(grid_pen)
            painter.drawLine(int(padding_left), int(y_pos), int(w - padding_right), int(y_pos))

        # Check for empty dataset
        total_hours = sum(val for _, val in self.data)
        if total_hours <= 0.001 and len(self.data) > 0:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Inter", 11, QFont.Weight.Normal))
            painter.drawText(QRectF(padding_left, padding_top, chart_w, chart_h - 10), Qt.AlignmentFlag.AlignCenter, "No focus sessions recorded for this period")

        # 2. Render Bars
        n_bars = len(self.data)
        slot_w = chart_w / max(1, n_bars)
        bar_w = min(28.0, max(12.0, slot_w * 0.42))

        for idx, (label, val) in enumerate(self.data):
            slot_center = padding_left + (idx + 0.5) * slot_w
            bar_x = slot_center - (bar_w / 2.0)

            # Slot background / track (subtle rounded slot background matching Image 4)
            track_rect = QRectF(bar_x, padding_top, bar_w, chart_h)
            painter.setBrush(QColor(24, 32, 50, 75))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(track_rect, 6, 6)

            if val > 0.001:
                frac = min(1.0, max(0.0, val / self.max_scale_hours))
                bar_height = max(6.0, frac * chart_h)
                bar_y = padding_top + chart_h - bar_height
                bar_rect = QRectF(bar_x, bar_y, bar_w, bar_height)

                # Purple/Violet gradient (#a855f7 to #6366f1)
                grad = QLinearGradient(bar_rect.topLeft(), bar_rect.bottomLeft())
                grad.setColorAt(0.0, QColor("#a855f7"))
                grad.setColorAt(1.0, QColor("#6366f1"))

                painter.setBrush(grad)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bar_rect, 6, 6)

            # High-contrast Day Label (unclipped with full slot centering)
            painter.setPen(QColor("#cbd5e1"))
            lbl_font_size = 9 if n_bars > 7 else 10
            painter.setFont(QFont("Inter", lbl_font_size, QFont.Weight.Medium))
            label_w = max(slot_w, 48.0)
            lbl_rect = QRectF(slot_center - (label_w / 2.0), h - padding_bottom + 4, label_w, 20)
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.end()


class TaskCompletionDonutChart(QWidget):
    """Donut chart showing Completed, Pending, and Overdue tasks with legend."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.completed = 0
        self.pending = 0
        self.overdue = 0
        self.setMinimumHeight(150)

    def set_counts(self, completed: int, pending: int, overdue: int):
        self.completed = max(0, completed)
        self.pending = max(0, pending)
        self.overdue = max(0, overdue)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        total = self.completed + self.pending + self.overdue
        pct = int(round((self.completed / total * 100.0))) if total > 0 else 0

        # Donut dimensions (placed on left side)
        donut_size = min(h - 20, 120)
        cx = 24 + donut_size / 2.0
        cy = h / 2.0
        radius = donut_size / 2.0
        thickness = 13.0
        rect = QRectF(cx - radius, cy - radius, donut_size, donut_size)

        # 1. Base track
        track_pen = QPen(QColor(22, 28, 44), thickness, Qt.PenStyle.SolidLine)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # 2. Segments
        if total > 0:
            start_angle = 90 * 16
            segments = [
                (self.completed, QColor("#10b981")), # Green Completed
                (self.pending, QColor("#3b82f6")),   # Blue Pending
                (self.overdue, QColor("#ef4444")),   # Red Overdue
            ]

            for count, color in segments:
                if count <= 0:
                    continue
                span = -int((count / total) * 360 * 16)
                seg_pen = QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(seg_pen)
                painter.drawArc(rect, start_angle, span)
                start_angle += span

        # 3. Center percentage text
        if total > 0:
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Inter", 16, QFont.Weight.Bold))
            painter.drawText(QRectF(cx - 35, cy - 15, 70, 22), Qt.AlignmentFlag.AlignCenter, f"{pct}%")

            painter.setPen(QColor("#8a95af"))
            painter.setFont(QFont("Inter", 9, QFont.Weight.Medium))
            painter.drawText(QRectF(cx - 35, cy + 6, 70, 16), Qt.AlignmentFlag.AlignCenter, "Completed")
        else:
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Inter", 15, QFont.Weight.Bold))
            painter.drawText(QRectF(cx - 35, cy - 14, 70, 20), Qt.AlignmentFlag.AlignCenter, "0%")

            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Inter", 9, QFont.Weight.Medium))
            painter.drawText(QRectF(cx - 35, cy + 6, 70, 16), Qt.AlignmentFlag.AlignCenter, "No Tasks")

        # 4. Legend on right side
        leg_x = cx + radius + 24
        leg_w = w - leg_x - 16
        leg_items = [
            ("Completed", self.completed, QColor("#10b981")),
            ("Pending", self.pending, QColor("#3b82f6")),
            ("Overdue", self.overdue, QColor("#ef4444")),
        ]

        leg_y_start = cy - 32
        for i, (label, count, color) in enumerate(leg_items):
            y = leg_y_start + i * 24

            # Dot
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(leg_x, y + 6), 4, 4)

            # Label
            painter.setPen(QColor("#a0aec0"))
            painter.setFont(QFont("Inter", 11, QFont.Weight.Normal))
            painter.drawText(QRectF(leg_x + 14, y, 80, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

            # Count
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            painter.drawText(QRectF(leg_x + 14, y, leg_w - 14, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(count))

        painter.end()


class TimeDistributionBar(QWidget):
    """Horizontal stacked bar showing Morning, Afternoon, and Evening focus breakdown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.distribution: Dict[str, int] = {"Morning": 0, "Afternoon": 0, "Evening": 0}
        self.setMinimumHeight(64)

    def set_data(self, distribution: Dict[str, int]):
        self.distribution = distribution
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        bar_height = 14
        bar_y = 12

        total = sum(self.distribution.values())

        if total <= 0:
            painter.setBrush(QColor("#1e263d"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(12, bar_y, width - 24, bar_height), 7, 7)
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Inter", 10))
            painter.drawText(QRectF(12, bar_y + 20, width - 24, 20), Qt.AlignmentFlag.AlignCenter, "No sessions recorded yet")
            painter.end()
            return

        colors = {
            "Morning": QColor("#06b6d4"),
            "Afternoon": QColor("#3b82f6"),
            "Evening": QColor("#8b5cf6"),
        }

        usable_width = width - 24
        current_x = 12.0

        for key in ("Morning", "Afternoon", "Evening"):
            val = self.distribution.get(key, 0)
            if val > 0:
                frac = val / total
                seg_width = frac * usable_width
                rect = QRectF(current_x, bar_y, seg_width, bar_height)
                painter.setBrush(colors[key])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 4, 4)
                current_x += seg_width

        legend_y = bar_y + bar_height + 12
        leg_x = 14
        for key in ("Morning", "Afternoon", "Evening"):
            val = self.distribution.get(key, 0)
            mins = val // 60
            painter.setBrush(colors[key])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(leg_x, legend_y + 3, 8, 8)

            painter.setPen(QColor("#cbd5e1"))
            painter.setFont(QFont("Inter", 10))
            text = f"{key} ({mins}m)"
            painter.drawText(leg_x + 14, legend_y + 11, text)
            leg_x += 120

        painter.end()
