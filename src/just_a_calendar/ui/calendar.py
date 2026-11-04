"""Custom rounded calendar view for Just a Calendar."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette
from PySide6.QtWidgets import QCalendarWidget


class RoundedCalendar(QCalendarWidget):
    """QCalendarWidget with rounded day cells and per-day multi-color highlight.

    Colors for a day are drawn as vertical stripes from left to right in the
    order the events occur within that day. A single event gives a solid
    rounded rectangle; multiple events are split into equal vertical bands.
    """

    _RADIUS = 6

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._day_colors: dict[date, list[str]] = {}

    def set_day_colors(self, mapping: dict[date, list[str]]) -> None:
        self._day_colors = dict(mapping)
        self.updateCells()

    def paintCell(self, painter: QPainter, rect, qdate: QDate) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        d = date(qdate.year(), qdate.month(), qdate.day())
        colors = self._day_colors.get(d, [])
        is_selected = qdate == self.selectedDate()
        is_today = qdate == QDate.currentDate()

        fill = QRectF(rect.adjusted(3, 3, -3, -3))

        if is_selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.palette().color(QPalette.ColorRole.Highlight))
            painter.drawRoundedRect(fill, self._RADIUS, self._RADIUS)
        elif colors:
            if len(colors) == 1:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(colors[0]))
                painter.drawRoundedRect(fill, self._RADIUS, self._RADIUS)
            else:
                clip_path = QPainterPath()
                clip_path.addRoundedRect(fill, self._RADIUS, self._RADIUS)
                painter.save()
                painter.setClipPath(clip_path)
                painter.setPen(Qt.PenStyle.NoPen)
                n = len(colors)
                for i, c in enumerate(colors):
                    y1 = fill.top() + fill.height() * i / n
                    y2 = fill.top() + fill.height() * (i + 1) / n
                    painter.setBrush(QColor(c))
                    painter.drawRect(QRectF(fill.left(), y1, fill.width(), y2 - y1))
                painter.restore()

        if is_today and not is_selected:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QColor(255, 255, 255, 150))
            painter.drawRoundedRect(fill, self._RADIUS, self._RADIUS)

        if is_selected or colors:
            text_color = QColor("#FFFFFF")
        else:
            base = self.palette().color(QPalette.ColorRole.Text)
            text_color = QColor(base)
            if qdate.month() != self.monthShown() or qdate.year() != self.yearShown():
                text_color.setAlpha(110)

        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(qdate.day()))
        painter.restore()