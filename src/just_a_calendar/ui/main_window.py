"""Main window: monthly calendar + day events list."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QDate, QDateTime, QTime, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services.events import EventsService
from ..services.palette import PaletteService
from .calendar import RoundedCalendar
from .event_dialog import EventDialog


class MainWindow(QMainWindow):
    def __init__(self, events_service: EventsService, palette_service: PaletteService) -> None:
        super().__init__()
        self.setWindowTitle("Just a Calendar")
        self.resize(1000, 680)
        self._events = events_service
        self._palette = palette_service
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
        self._btn_settings = QPushButton("Settings...")
        self._btn_settings.setEnabled(False)
        toolbar.addWidget(self._btn_today)
        toolbar.addWidget(self._btn_new)
        toolbar.addWidget(self._btn_settings)
        toolbar.addStretch(1)
        outer.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        self._calendar = RoundedCalendar()
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(RoundedCalendar.NoVerticalHeader)
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
        self._btn_new.clicked.connect(self._on_new_event)
        self._calendar.selectionChanged.connect(self._refresh_day_list)
        self._events_list.itemDoubleClicked.connect(self._on_item_activated)
        self._events_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._events_list.customContextMenuRequested.connect(self._on_context_menu)

    def _on_today(self) -> None:
        self._calendar.setSelectedDate(QDate.currentDate())

    def _refresh_events_highlight(self) -> None:
        palette_color = self._palette.get("events")
        events_by_day: dict[date, list] = {}
        for e in self._events.list_all():
            try:
                day = datetime.fromisoformat(e.starts_at).date()
            except ValueError:
                continue
            events_by_day.setdefault(day, []).append(e)

        day_colors: dict[date, list[str]] = {}
        for day, evs in events_by_day.items():
            evs.sort(key=lambda x: x.starts_at)
            day_colors[day] = [e.color or palette_color for e in evs]
        self._calendar.set_day_colors(day_colors)

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
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, e.id)
            self._events_list.addItem(item)

    def _selected_date(self) -> date:
        qd = self._calendar.selectedDate()
        return date(qd.year(), qd.month(), qd.day())

    def _event_id_from_item(self, item) -> int | None:
        if item is None:
            return None
        val = item.data(Qt.ItemDataRole.UserRole)
        return int(val) if val is not None else None

    def _on_new_event(self) -> None:
        day = self._selected_date()
        start_qdt = QDateTime(QDate(day.year, day.month, day.day), QTime(9, 0))
        end_qdt = QDateTime(QDate(day.year, day.month, day.day), QTime(10, 0))
        dlg = EventDialog(
            self, self._events, self._palette,
            event=None,
            default_start=start_qdt,
            default_end=end_qdt,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_events_highlight()
            self._refresh_day_list()

    def _on_item_activated(self, item) -> None:
        eid = self._event_id_from_item(item)
        if eid is not None:
            self._edit_event_by_id(eid)

    def _on_context_menu(self, pos) -> None:
        item = self._events_list.itemAt(pos)
        eid = self._event_id_from_item(item)
        if eid is None:
            return
        menu = QMenu(self)
        act_edit = menu.addAction("Edit")
        act_delete = menu.addAction("Delete")
        chosen = menu.exec(self._events_list.mapToGlobal(pos))
        if chosen is act_edit:
            self._edit_event_by_id(eid)
        elif chosen is act_delete:
            self._delete_event_by_id(eid)

    def _edit_event_by_id(self, event_id: int) -> None:
        event = None
        for e in self._events.list_all():
            if e.id == event_id:
                event = e
                break
        if event is None:
            return
        dlg = EventDialog(self, self._events, self._palette, event=event)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_events_highlight()
            self._refresh_day_list()

    def _delete_event_by_id(self, event_id: int) -> None:
        ok = QMessageBox.question(
            self, "Delete event", "Delete this event?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            self._events.delete(event_id)
            self._refresh_events_highlight()
            self._refresh_day_list()