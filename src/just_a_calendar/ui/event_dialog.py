"""Event create/edit dialog."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..models.entities import Event
from ..services.events import EventsService
from ..services.palette import PaletteService

_REMINDER_UNITS = ("hours", "days", "months", "years")


class EventDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget],
        events_service: EventsService,
        palette_service: PaletteService,
        *,
        event: Optional[Event] = None,
        default_start: Optional[QDateTime] = None,
        default_end: Optional[QDateTime] = None,
    ) -> None:
        super().__init__(parent)
        self._events = events_service
        self._palette = palette_service
        self._event = event
        self._color: Optional[str] = event.color if event else None

        self.setWindowTitle("Edit event" if event else "New event")
        self.setMinimumWidth(460)
        self._build_ui()
        self._prefill(default_start, default_end)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._title = QLineEdit()
        self._title.setPlaceholderText("Title")
        form.addRow("Title", self._title)

        self._description = QTextEdit()
        self._description.setPlaceholderText("Description (optional)")
        self._description.setFixedHeight(70)
        form.addRow("Description", self._description)

        self._starts = QDateTimeEdit()
        self._starts.setCalendarPopup(True)
        self._starts.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("Starts at", self._starts)

        self._ends = QDateTimeEdit()
        self._ends.setCalendarPopup(True)
        self._ends.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("Ends at", self._ends)

        reminder_row = QWidget()
        rh = QHBoxLayout(reminder_row)
        rh.setContentsMargins(0, 0, 0, 0)
        self._amount = QSpinBox()
        self._amount.setRange(0, 9999)
        self._unit = QComboBox()
        for u in _REMINDER_UNITS:
            self._unit.addItem(u, u)
        rh.addWidget(self._amount)
        rh.addWidget(self._unit, 1)
        form.addRow("Reminder before", reminder_row)

        color_row = QWidget()
        ch = QHBoxLayout(color_row)
        ch.setContentsMargins(0, 0, 0, 0)
        self._color_preview = QLabel()
        self._color_preview.setFixedSize(24, 24)
        self._btn_color = QPushButton("Pick color...")
        self._btn_color.clicked.connect(self._pick_color)
        self._btn_color_reset = QPushButton("Use default")
        self._btn_color_reset.clicked.connect(self._reset_color)
        ch.addWidget(self._color_preview)
        ch.addWidget(self._btn_color)
        ch.addWidget(self._btn_color_reset, 1)
        form.addRow("Color", color_row)

        layout.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #E74C3C;")
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        if self._event is not None:
            self._btn_delete = buttons.addButton(
                "Delete", QDialogButtonBox.ButtonRole.DestructiveRole
            )
            self._btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(buttons)

    def _prefill(self, default_start, default_end) -> None:
        if self._event is not None:
            self._title.setText(self._event.title)
            self._description.setPlainText(self._event.description)
            s = QDateTime.fromString(self._event.starts_at, Qt.DateFormat.ISODate)
            e = QDateTime.fromString(self._event.ends_at, Qt.DateFormat.ISODate)
            self._starts.setDateTime(s)
            self._ends.setDateTime(e)
            self._amount.setValue(self._event.reminder_amount)
            idx = self._unit.findData(self._event.reminder_unit)
            if idx >= 0:
                self._unit.setCurrentIndex(idx)
        else:
            if default_start is not None:
                self._starts.setDateTime(default_start)
                self._ends.setDateTime(default_end or default_start.addSecs(3600))
            else:
                now = QDateTime.currentDateTime()
                self._starts.setDateTime(now)
                self._ends.setDateTime(now.addSecs(3600))
            idx = self._unit.findData("hours")
            if idx >= 0:
                self._unit.setCurrentIndex(idx)
        self._refresh_color_preview()

    def _effective_color(self) -> str:
        return self._color or self._palette.get("events")

    def _refresh_color_preview(self) -> None:
        c = QColor(self._effective_color())
        self._color_preview.setStyleSheet(
            f"background-color: {c.name()}; border: 1px solid #888; border-radius: 3px;"
        )

    def _pick_color(self) -> None:
        initial = QColor(self._effective_color())
        chosen = QColorDialog.getColor(initial, self, "Event color")
        if chosen.isValid():
            self._color = chosen.name().upper()
            self._refresh_color_preview()

    def _reset_color(self) -> None:
        self._color = None
        self._refresh_color_preview()

    def _show_error(self, msg: str) -> None:
        self._error_label.setText(msg)
        self._error_label.setVisible(True)

    def _on_save(self) -> None:
        self._error_label.setVisible(False)
        title = self._title.text().strip()
        if not title:
            self._show_error("Title is required.")
            return
        sqdt = self._starts.dateTime()
        eqdt = self._ends.dateTime()
        starts = datetime(
            sqdt.date().year(), sqdt.date().month(), sqdt.date().day(),
            sqdt.time().hour(), sqdt.time().minute(), sqdt.time().second(),
        )
        ends = datetime(
            eqdt.date().year(), eqdt.date().month(), eqdt.date().day(),
            eqdt.time().hour(), eqdt.time().minute(), eqdt.time().second(),
        )
        if ends <= starts:
            self._show_error("End must be after start.")
            return
        try:
            if self._event is None:
                self._events.create(
                    title=title,
                    description=self._description.toPlainText(),
                    starts_at=starts,
                    ends_at=ends,
                    reminder_amount=self._amount.value(),
                    reminder_unit=self._unit.currentData(),
                    color=self._color,
                )
            else:
                self._events.update(
                    self._event.id,
                    title=title,
                    description=self._description.toPlainText(),
                    starts_at=starts,
                    ends_at=ends,
                    reminder_amount=self._amount.value(),
                    reminder_unit=self._unit.currentData(),
                    color=self._color,
                )
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.accept()

    def _on_delete(self) -> None:
        if self._event is None:
            return
        ok = QMessageBox.question(
            self, "Delete event", "Delete this event?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            self._events.delete(self._event.id)
            self.accept()