"""Main window: monthly calendar + day events list."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services.events import EventsService
from ..services.palette import PaletteService


class MainWindow(QMainWindow):
    def __init__(self, events_service: EventsService, palette_service: PaletteService) -> None:
        super().__init__()
        self.setWindowTitle("Just a Calendar")
        self.resize(1000, 680)
        self._events = events_service
        self._palette = palette_service
        self._highlighted: set[QDate] = set()
        self._build_ui()
        self._refresh_events_highlight()
        self._refresh_day_list()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        self._btn_today = QPushButton("Today")
        self._btn_new = QPushButton("New event...")
        self._btn_new.setEnabled(False)
        self._btn_settings = QPushButton("Settings...")
        self._btn_settings.setEnabled(False)
        toolbar.addWidget(self._btn_today)
        toolbar.addWidget(self._btn_new)
        toolbar.addWidget(self._btn_settings)
        toolbar.addStretch(1)
        outer.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self._calendar.setSelectedDate(QDate.currentDate())
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
        splitter.addWidget(self._calendar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._day_label = QLabel("")
        self._day_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        right_layout.addWidget(self._day_label)
        self._events_list = QListWidget()
        right_layout.addWidget(self._events_list, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 400])

        self._btn_today.clicked.connect(self._on_today)
        self._calendar.selectionChanged.connect(self._refresh_day_list)

    def _on_today(self) -> None:
        self._calendar.setSelectedDate(QDate.currentDate())

    def _refresh_events_highlight(self) -> None:
        default_fmt = QTextCharFormat()
        for qd in self._highlighted:
            self._calendar.setDateTextFormat(qd, default_fmt)
        self._highlighted.clear()

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(self._palette.get("events")))
        fmt.setForeground(QColor("#FFFFFF"))

        seen_days: set[date] = set()
        for e in self._events.list_all():
            try:
                day = datetime.fromisoformat(e.starts_at).date()
            except ValueError:
                continue
            if day in seen_days:
                continue
            seen_days.add(day)
            qd = QDate(day.year, day.month, day.day)
            self._calendar.setDateTextFormat(qd, fmt)
            self._highlighted.add(qd)

    def _refresh_day_list(self) -> None:
        qd = self._calendar.selectedDate()
        day = date(qd.year(), qd.month(), qd.day())
        self._day_label.setText(day.strftime("%A, %d %B %Y"))
        self._events_list.clear()
        items = self._events.list_for_day(day)
        items.sort(key=lambda e: e.starts_at)
        if not items:
            placeholder = QListWidgetItem("No events")
            placeholder.setFlags(Qt.NoItemFlags)
            self._events_list.addItem(placeholder)
            return
        for e in items:
            try:
                start = datetime.fromisoformat(e.starts_at)
                end = datetime.fromisoformat(e.ends_at)
                text = f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}  {e.title}"
            except ValueError:
                text = f"{e.starts_at} - {e.starts_at}  {e.title}"
            if e.description:
                text += f"\n{e.description}"
            self._events_list.addItem(QListWidgetItem(text))