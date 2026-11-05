"""Free time dialog: calendar on the left, free intervals on the right."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..services.free_time import FreeTimeService
from ..services.palette import PaletteService
from ..services.parity import ParityService
from .calendar import RoundedCalendar


def _format_minutes(total: int) -> str:
    total = max(0, int(total))
    h, m = divmod(total, 60)
    if h and m:
        return f"{h}h {m:02d}m"
    if h:
        return f"{h}h"
    return f"{m}m"


_HEAT_RED = "#E74C3C"
_HEAT_SALAD = "#B8E986"
_HEAT_LIGHT_GREEN = "#7ED321"
_HEAT_GREEN = "#27AE60"
_HEAT_LEGEND = (
    (_HEAT_RED, "<2h"),
    (_HEAT_SALAD, "2-4h"),
    (_HEAT_LIGHT_GREEN, "4-6h"),
    (_HEAT_GREEN, ">6h"),
)


def _heat_color(free_minutes: int) -> str:
    if free_minutes < 120:
        return _HEAT_RED
    if free_minutes < 240:
        return _HEAT_SALAD
    if free_minutes < 360:
        return _HEAT_LIGHT_GREEN
    return _HEAT_GREEN


class FreeTimeDialog(QDialog):
    def __init__(
        self,
        free_time_service: FreeTimeService,
        parity_service: ParityService,
        palette_service: PaletteService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._free = free_time_service
        self._parity = parity_service
        self._palette = palette_service
        self.setWindowTitle("Free time")
        self.resize(960, 620)
        self._build_ui()
        self._refresh_for_selected()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        calendar_page = QWidget()
        cp_layout = QVBoxLayout(calendar_page)
        cp_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        cp_layout.addWidget(splitter, 1)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 6)
        self._btn_today = QPushButton("Today")
        top_bar.addWidget(self._btn_today)
        top_bar.addStretch(1)
        ll.addLayout(top_bar)

        self._calendar = RoundedCalendar()
        self._calendar.setStyleSheet(
            """
            QCalendarWidget QToolButton::menu-indicator {
                image: none;
                width: 0;
                height: 0;
                border: none;
                margin: 0;
            }
            QCalendarWidget QToolButton {
                color: white;
                background-color: rgba(255, 255, 255, 40);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 4px;
                padding: 2px 10px;
                margin: 2px 6px;
                font-weight: 600;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(255, 255, 255, 90);
                border-color: rgba(255, 255, 255, 160);
            }
            QCalendarWidget QToolButton:pressed {
                background-color: rgba(255, 255, 255, 140);
            }
            """
        )
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(RoundedCalendar.NoVerticalHeader)
        self._calendar.selectionChanged.connect(self._refresh_for_selected)
        self._calendar.currentPageChanged.connect(lambda _y, _m: self._refresh_heatmap())
        ll.addWidget(self._calendar, 1)

        legend = QWidget()
        lh = QHBoxLayout(legend)
        lh.setContentsMargins(0, 6, 0, 0)
        lh.setSpacing(6)
        for color, label_text in _HEAT_LEGEND:
            sw = QLabel()
            sw.setFixedSize(14, 14)
            sw.setStyleSheet(f"background: {color}; border-radius: 3px;")
            lh.addWidget(sw)
            lab = QLabel(label_text)
            lab.setStyleSheet("color: #aaa; font-size: 11px; margin-right: 10px;")
            lh.addWidget(lab)
        lh.addStretch(1)
        ll.addWidget(legend)

        splitter.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self._day_label = QLabel("")
        self._day_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        rl.addWidget(self._day_label)

        self._list = QListWidget()
        rl.addWidget(self._list, 1)

        self._total_label = QLabel("")
        self._total_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        rl.addWidget(self._total_label)

        self._extra_label = QLabel("")
        self._extra_label.setStyleSheet("color: #888; font-size: 12px;")
        self._extra_label.setVisible(False)
        rl.addWidget(self._extra_label)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 360])

        self._stack.addWidget(calendar_page)

        text_page = QWidget()
        tp_layout = QVBoxLayout(text_page)
        tp_layout.setContentsMargins(0, 0, 0, 0)
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        mono = QFont("Consolas")
        mono.setPointSize(12)
        self._text_edit.setFont(mono)
        tp_layout.addWidget(self._text_edit, 1)
        self._stack.addWidget(text_page)

        bottom = QHBoxLayout()
        self._btn_show_text = QPushButton("Show as text")
        self._btn_back_to_calendar = QPushButton("Back to calendar")
        self._btn_back_to_calendar.setVisible(False)
        self._btn_close = QPushButton("Close")
        bottom.addWidget(self._btn_show_text)
        bottom.addWidget(self._btn_back_to_calendar)
        bottom.addStretch(1)
        bottom.addWidget(self._btn_close)
        layout.addLayout(bottom)

        self._btn_show_text.clicked.connect(self._on_show_text)
        self._btn_back_to_calendar.clicked.connect(self._on_show_calendar)
        self._btn_close.clicked.connect(self.accept)
        self._btn_today.clicked.connect(self._on_today)

        self._refresh_heatmap()

    def _on_show_text(self) -> None:
        self._refresh_text()
        self._stack.setCurrentIndex(1)
        self._btn_show_text.setVisible(False)
        self._btn_back_to_calendar.setVisible(True)

    def _on_show_calendar(self) -> None:
        self._stack.setCurrentIndex(0)
        self._btn_show_text.setVisible(True)
        self._btn_back_to_calendar.setVisible(False)

    def _refresh_text(self) -> None:
        today = date.today()
        lines = ["= Free time =", ""]
        for offset in range(14):
            day = today + timedelta(days=offset)
            if offset == 0:
                header = "Today:"
            elif offset == 1:
                header = "Tomorrow:"
            else:
                header = day.strftime("%a, %d %B:")
            lines.append(header)
            parity = self._parity.week_parity_for(day)
            intervals = self._free.free_intervals_for_day(day, parity, include_sleep=True)
            if not intervals:
                lines.append("No free time")
            else:
                for _s, _e, s_str, e_str in intervals:
                    lines.append(f"\u2022 {s_str} \u2014 {e_str}")
            lines.append("")
        self._text_edit.setPlainText("\n".join(lines))

    def _on_today(self) -> None:
        self._calendar.setSelectedDate(QDate.currentDate())

    def _make_icon(self, hex_color: str) -> QIcon:
        pix = QPixmap(14, 14)
        pix.fill(QColor(hex_color))
        return QIcon(pix)

    def _refresh_heatmap(self) -> None:
        year = self._calendar.yearShown()
        month = self._calendar.monthShown()
        first = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last = next_month - timedelta(days=1)
        start = first - timedelta(days=7)
        end = last + timedelta(days=7)
        mapping = {}
        d = start
        while d <= end:
            parity = self._parity.week_parity_for(d)
            mins = self._free.free_minutes_for_day(d, parity, include_sleep=True)
            mapping[d] = [_heat_color(mins)]
            d += timedelta(days=1)
        self._calendar.set_day_colors(mapping)

    def _refresh_for_selected(self) -> None:
        qd = self._calendar.selectedDate()
        day = date(qd.year(), qd.month(), qd.day())
        parity = self._parity.week_parity_for(day)
        self._day_label.setText(f"{parity.capitalize()} Week, {day.strftime('%A, %d %B %Y')}")
        self._list.clear()

        free_color = self._palette.get("free_time")
        intervals = self._free.free_intervals_for_day(day, parity, include_sleep=True)
        if not intervals:
            placeholder = QListWidgetItem("No free time")
            placeholder.setFlags(Qt.NoItemFlags)
            self._list.addItem(placeholder)
        else:
            icon = self._make_icon(free_color)
            for _s, _e, s_str, e_str in intervals:
                item = QListWidgetItem(f"{s_str} — {e_str}")
                item.setIcon(icon)
                self._list.addItem(item)

        total = sum(e - s for s, e, _a, _b in intervals)
        self._total_label.setText(f"Total: {_format_minutes(total)}")

        extra = self._free.additional_minutes_if_no_sleep(day, parity)
        if extra > 0:
            self._extra_label.setText(f"If you skip sleep: +{_format_minutes(extra)}")
            self._extra_label.setVisible(True)
        else:
            self._extra_label.setVisible(False)