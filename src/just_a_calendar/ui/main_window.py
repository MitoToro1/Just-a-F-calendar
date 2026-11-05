"""Main window: monthly calendar + day events list."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from PySide6.QtCore import QDate, QDateTime, QTime, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap, QShortcut
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
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..services.events import EventsService
from ..services.free_time import FreeTimeService
from ..services.palette import PaletteService
from ..services.parity import ParityService
from ..services.reminders import ReminderService
from ..services.schedules import SchedulesService
from ..services.sleep import SleepService
from ..services import time_format
from .calendar import RoundedCalendar
from .event_dialog import EventDialog
from .free_time_dialog import FreeTimeDialog
from .tray import TrayIcon
from .schedules_dialog import SchedulesDialog
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(
        self,
        events_service: EventsService,
        palette_service: PaletteService,
        schedules_service: SchedulesService,
        parity_service: ParityService,
        sleep_service: SleepService,
        free_time_service: FreeTimeService,
        reminder_service: ReminderService,
        tray_icon: Optional[TrayIcon] = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Just a Calendar")
        self.resize(1000, 680)
        self._events = events_service
        self._palette = palette_service
        self._schedules = schedules_service
        self._parity = parity_service
        self._sleep = sleep_service
        self._free_time = free_time_service
        self._reminders = reminder_service
        self._tray = tray_icon
        self._schedules_dialog = None
        self._settings_dialog = None
        self._free_time_dialog = None
        self._last_reminder_event_id: Optional[int] = None
        self._build_ui()
        self._refresh_events_highlight()
        self._refresh_day_list()
        self._setup_reminders()

    def _setup_reminders(self) -> None:
        if self._tray is not None:
            self._tray.messageClicked.connect(self._on_tray_message_clicked)
        self._reminder_timer = QTimer(self)
        self._reminder_timer.setInterval(30_000)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start()
        QTimer.singleShot(0, self._check_reminders)

    def _check_reminders(self) -> None:
        try:
            due = list(self._reminders.due_reminders())
        except Exception:
            return
        for event in due:
            try:
                self._reminders.mark_fired(event.id)
            except Exception:
                continue
            self._last_reminder_event_id = event.id
            if self._tray is not None:
                try:
                    hhmm = datetime.fromisoformat(event.starts_at).strftime("%H:%M")
                    body = f"{event.title} — {time_format.format_hhmm(hhmm)}"
                except ValueError:
                    body = event.title
                self._tray.showMessage(
                    "Just a Calendar",
                    body,
                    QSystemTrayIcon.MessageIcon.Information,
                    10_000,
                )

    def _on_tray_message_clicked(self) -> None:
        if self._last_reminder_event_id is None:
            self.show_from_tray()
            return
        event_id = self._last_reminder_event_id
        self._last_reminder_event_id = None
        for e in self._events.list_all():
            if e.id == event_id:
                try:
                    day = datetime.fromisoformat(e.starts_at).date()
                except ValueError:
                    break
                self._calendar.setSelectedDate(QDate(day.year, day.month, day.day))
                self._calendar.setCurrentPage(day.year, day.month)
                break
        self.show_from_tray()

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
        self._btn_schedules = QPushButton("Schedules...")
        self._btn_free_time = QPushButton("Free time...")
        self._btn_settings = QPushButton("Settings...")
        toolbar.addWidget(self._btn_today)
        toolbar.addWidget(self._btn_new)
        toolbar.addWidget(self._btn_schedules)
        toolbar.addWidget(self._btn_free_time)
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
        self._btn_schedules.clicked.connect(self._on_schedules)
        self._btn_free_time.clicked.connect(self._on_free_time)
        self._btn_settings.clicked.connect(self._on_settings)
        self._calendar.selectionChanged.connect(self._refresh_day_list)
        self._calendar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._calendar.customContextMenuRequested.connect(self._on_calendar_context_menu)

        # Ctrl+1 = Today, Ctrl+2 = New event, Ctrl+3 = Schedules, Ctrl+4 = Settings
        self._sc_today = QShortcut(QKeySequence("Ctrl+1"), self)
        self._sc_today.activated.connect(self._on_today)
        self._sc_new = QShortcut(QKeySequence("Ctrl+2"), self)
        self._sc_new.activated.connect(self._on_new_event)
        self._sc_schedules = QShortcut(QKeySequence("Ctrl+3"), self)
        self._sc_schedules.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._sc_schedules.activated.connect(self._on_schedules)
        self._sc_free_time = QShortcut(QKeySequence("Ctrl+4"), self)
        self._sc_free_time.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._sc_free_time.activated.connect(self._on_free_time)
        self._sc_settings = QShortcut(QKeySequence("Ctrl+5"), self)
        self._sc_settings.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._sc_settings.activated.connect(self._on_settings)
        self._events_list.itemDoubleClicked.connect(self._on_item_activated)
        self._events_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._events_list.customContextMenuRequested.connect(self._on_context_menu)

    def _on_today(self) -> None:
        self._calendar.setSelectedDate(QDate.currentDate())

    def _close_open_dialogs(self) -> None:
        for attr in ("_schedules_dialog", "_settings_dialog", "_free_time_dialog"):
            dlg = getattr(self, attr, None)
            if dlg is None:
                continue
            setattr(self, attr, None)
            try:
                dlg.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                dlg.close()
            except RuntimeError:
                pass

    def _on_settings(self) -> None:
        already_open = self._settings_dialog is not None
        self._close_open_dialogs()
        if already_open:
            return
        dlg = SettingsDialog(self._palette, self._parity, self._sleep, self)
        self._settings_dialog = dlg
        dlg.finished.connect(lambda result, d=dlg: self._on_settings_dialog_finished(d, result))
        dlg.show()

    def _on_settings_dialog_finished(self, dlg, result: int) -> None:
        if dlg is not self._settings_dialog:
            return
        self._settings_dialog = None
        if result == QDialog.DialogCode.Accepted:
            self._refresh_events_highlight()
            self._refresh_day_list()
            if self._tray is not None:
                self._tray.refresh_color()

    def _on_schedules(self) -> None:
        already_open = self._schedules_dialog is not None
        self._close_open_dialogs()
        if already_open:
            return
        dlg = SchedulesDialog(self._schedules, self._palette, self)
        self._schedules_dialog = dlg
        dlg.finished.connect(lambda _result, d=dlg: self._on_schedules_dialog_finished(d))
        dlg.show()

    def _on_schedules_dialog_finished(self, dlg) -> None:
        if dlg is not self._schedules_dialog:
            return
        self._schedules_dialog = None
        self._refresh_day_list()

    def _on_free_time(self) -> None:
        already_open = self._free_time_dialog is not None
        self._close_open_dialogs()
        if already_open:
            return
        dlg = FreeTimeDialog(self._free_time, self._parity, self._palette, self)
        self._free_time_dialog = dlg
        dlg.finished.connect(lambda _result, d=dlg: self._on_free_time_dialog_finished(d))
        dlg.show()

    def _on_free_time_dialog_finished(self, dlg) -> None:
        if dlg is not self._free_time_dialog:
            return
        self._free_time_dialog = None

    def closeEvent(self, event) -> None:
        if self._tray is not None and self._tray.isVisible():
            event.ignore()
            self.hide()
            self._tray.show_once_hint()
            return
        super().closeEvent(event)

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_calendar_context_menu(self, pos) -> None:
        qd = self._calendar.selectedDate()
        day = date(qd.year(), qd.month(), qd.day())
        menu = QMenu(self)
        act_even = menu.addAction("Mark this week as Even")
        act_odd = menu.addAction("Mark this week as Odd")
        chosen = menu.exec(self._calendar.mapToGlobal(pos))
        if chosen is act_even:
            self._parity.set_anchor(day, "even")
            self._refresh_day_list()
        elif chosen is act_odd:
            self._parity.set_anchor(day, "odd")
            self._refresh_day_list()

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
        parity = self._parity.week_parity_for(day)
        self._day_label.setText(f"{parity.capitalize()} Week, {day.strftime('%A, %d %B %Y')}")
        self._events_list.clear()

        event_items = self._events.list_for_day(day)
        event_items.sort(key=lambda e: e.starts_at)
        slot_items = self._schedules.slots_for_day(day, parity)
        slot_items.sort(key=lambda s: s.start_time)

        events_color = self._palette.get("events")
        sleep_color = self._palette.get("sleep")

        sleep_start, sleep_end = self._sleep.resolve_for_day(day)
        sleep_item = QListWidgetItem(
            f"{time_format.format_hhmm(sleep_start)}-{time_format.format_hhmm(sleep_end)}  Sleep"
        )
        sleep_item.setIcon(self._make_icon(sleep_color))
        sleep_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._events_list.addItem(sleep_item)

        for e in event_items:
            try:
                start = datetime.fromisoformat(e.starts_at)
                end = datetime.fromisoformat(e.ends_at)
                s_hhmm = time_format.format_hhmm(start.strftime("%H:%M"))
                e_hhmm = time_format.format_hhmm(end.strftime("%H:%M"))
                text = f"{s_hhmm}-{e_hhmm}  {e.title}"
            except ValueError:
                text = f"{e.starts_at} - {e.starts_at}  {e.title}"
            if e.description:
                text += f"\n{e.description}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, e.id)
            item.setIcon(self._make_icon(e.color or events_color))
            self._events_list.addItem(item)

        for slot in slot_items:
            sched = self._schedules.get(slot.schedule_id)
            sched_name = sched.name if sched else "?"
            label = slot.title if slot.title else sched_name
            item = QListWidgetItem(f"{time_format.format_hhmm(slot.start_time)}-{time_format.format_hhmm(slot.end_time)}  {label}")
            item.setIcon(self._make_icon(slot.color or events_color))
            self._events_list.addItem(item)

    def _make_icon(self, hex_color: str) -> QIcon:
        pix = QPixmap(14, 14)
        pix.fill(QColor(hex_color))
        return QIcon(pix)

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