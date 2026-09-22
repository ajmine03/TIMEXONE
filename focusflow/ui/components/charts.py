"""
Lightweight, native QPainter vector charts for FocusFlow.
Renders weekly bar graphs and time-of-day distribution progress bars.
"""

from typing import List, Tuple, Dict
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRectF


class WeeklyBarChart(QWidget):
    """Clean, antialiased 7-day focus time bar chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # List of (day_name, focus_minutes)
        self.data: List[Tuple[str, int]] = [
            ("Mon", 0), ("Tue", 0), ("Wed", 0), ("Thu", 0),
            ("Fri", 0), ("Sat", 0), ("Sun", 0)
        ]
        self.setMinimumHeight(200)

    def set_data(self, data: List[Tuple[str, int]]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        padding_bottom = 32
        padding_top = 24
        padding_sides = 20

        chart_height = height - padding_top - padding_bottom
        chart_width = width - (padding_sides * 2)

        max_val = max([val for _, val in self.data] + [60])  # Minimum scale 60 mins

        n_bars = len(self.data)
        slot_width = chart_width / max(1, n_bars)
        bar_width = min(42.0, slot_width * 0.55)

        # Draw light baseline grid
        grid_pen = QPen(QColor("#313244"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        painter.drawLine(int(padding_sides), int(height - padding_bottom), int(width - padding_sides), int(height - padding_bottom))

        for idx, (label, val) in enumerate(self.data):
            slot_center = padding_sides + (idx + 0.5) * slot_width
            bar_x = slot_center - (bar_width / 2.0)

            # Fraction of max height
            fraction = min(1.0, val / max_val)
            bar_h = max(4.0 if val > 0 else 0.0, fraction * chart_height)
            bar_y = height - padding_bottom - bar_h

            bar_rect = QRectF(bar_x, bar_y, bar_width, bar_h)

            # Bar gradient
            if val > 0:
                grad = QLinearGradient(bar_rect.topLeft(), bar_rect.bottomLeft())
                grad.setColorAt(0.0, QColor("#3b82f6"))
                grad.setColorAt(1.0, QColor("#1d4ed8"))
                painter.setBrush(grad)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bar_rect, 6, 6)

                # Draw value on top of bar if space permits
                val_text = f"{val}m" if val < 60 else f"{val/60:.1f}h"
                painter.setPen(QColor("#cdd6f4"))
                painter.setFont(QFont("Inter", 9, QFont.Weight.Medium))
                val_rect = QRectF(slot_center - 30, bar_y - 18, 60, 16)
                painter.drawText(val_rect, Qt.AlignmentFlag.AlignCenter, val_text)
            else:
                # Muted small placeholder pill
                empty_rect = QRectF(bar_x, height - padding_bottom - 4, bar_width, 4)
                painter.setBrush(QColor("#313244"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(empty_rect, 2, 2)

            # Day Label
            painter.setPen(QColor("#a6adc8"))
            painter.setFont(QFont("Inter", 11, QFont.Weight.SemiBold))
            lbl_rect = QRectF(slot_center - 25, height - padding_bottom + 8, 50, 20)
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, label)

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
            # Draw placeholder bar
            painter.setBrush(QColor("#313244"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(12, bar_y, width - 24, bar_height), 7, 7)
            painter.setPen(QColor("#6c7086"))
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

        # Legend row
        legend_y = bar_y + bar_height + 12
        leg_x = 14
        for key in ("Morning", "Afternoon", "Evening"):
            val = self.distribution.get(key, 0)
            mins = val // 60
            painter.setBrush(colors[key])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(leg_x, legend_y + 3, 8, 8)

            painter.setPen(QColor("#cdd6f4"))
            painter.setFont(QFont("Inter", 10))
            text = f"{key} ({mins}m)"
            painter.drawText(leg_x + 14, legend_y + 11, text)
            leg_x += 120

        painter.end()
