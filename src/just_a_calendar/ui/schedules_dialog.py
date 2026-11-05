"""Schedules management dialog with week-grid view."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ..services.palette import PaletteService
from ..services.schedules import SchedulesService

_WEEKDAYS_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_WEEKDAYS_FULL = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_PARITY_LABELS = (
    ("both", "All weeks"),
    ("even", "Even weeks only"),
    ("odd", "Odd weeks only"),
)
_PARITY_SHORT = {"both": "all", "even": "even", "odd": "odd"}


class _ScheduleEditDialog(QDialog):
    def __init__(self, parent=None, *, name: str = "", parity: str = "both", active: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Schedule")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit(name)
        form.addRow("Name", self._name)
        self._parity = QComboBox()
        for key, label in _PARITY_LABELS:
            self._parity.addItem(label, key)
        idx = self._parity.findData(parity)
        if idx >= 0:
            self._parity.setCurrentIndex(idx)
        form.addRow("Weeks", self._parity)
        self._active = QCheckBox("Active")
        self._active.setChecked(active)
        form.addRow("", self._active)
        layout.addLayout(form)
        self._error = QLabel("")
        self._error.setStyleSheet("color: #E74C3C;")
        self._error.setVisible(False)
        layout.addWidget(self._error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self) -> None:
        if not self._name.text().strip():
            self._error.setText("Name is required.")
            self._error.setVisible(True)
            return
        self.accept()

    def values(self):
        return {
            "name": self._name.text().strip(),
            "parity": self._parity.currentData(),
            "active": self._active.isChecked(),
        }


class _SlotEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        weekday: int = 0,
        start_time: str = "09:00",
        end_time: str = "10:00",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Slot")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._day = QComboBox()
        for i, name in enumerate(_WEEKDAYS_FULL):
            self._day.addItem(name, i)
        self._day.setCurrentIndex(weekday if 0 <= weekday <= 6 else 0)
        form.addRow("Day", self._day)
        self._start = QTimeEdit(QTime.fromString(start_time, "HH:mm"))
        self._start.setDisplayFormat("HH:mm")
        form.addRow("Start", self._start)
        self._end = QTimeEdit(QTime.fromString(end_time, "HH:mm"))
        self._end.setDisplayFormat("HH:mm")
        form.addRow("End", self._end)
        layout.addLayout(form)
        self._error = QLabel("")
        self._error.setStyleSheet("color: #E74C3C;")
        self._error.setVisible(False)
        layout.addWidget(self._error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self) -> None:
        if self._end.time() <= self._start.time():
            self._error.setText("End must be after start.")
            self._error.setVisible(True)
            return
        self.accept()

    def values(self):
        return {
            "weekday": self._day.currentData(),
            "start_time": self._start.time().toString("HH:mm"),
            "end_time": self._end.time().toString("HH:mm"),
        }


class _SlotBlock(QPushButton):
    double_clicked = Signal(int)

    def __init__(self, slot, color: str, parent=None) -> None:
        super().__init__(parent)
        self.slot_id = slot.id
        self.setText(f"{slot.start_time}\n{slot.end_time}")
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 3px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: rgba(255, 255, 255, 100);
            }}
            QPushButton:checked {{
                border-color: white;
            }}
        """)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.slot_id)
            return
        super().mouseDoubleClickEvent(event)


class _DayCell(QWidget):
    def __init__(self, weekday: int, parent=None) -> None:
        super().__init__(parent)
        self.weekday = weekday
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)

    def clear_slots(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self._layout.addStretch(1)

    def add_slot_block(self, block: _SlotBlock) -> None:
        self._layout.insertWidget(self._layout.count() - 1, block)


class SchedulesDialog(QDialog):
    def __init__(self, schedules_service: SchedulesService, palette_service: PaletteService, parent=None) -> None:
        super().__init__(parent)
        self._svc = schedules_service
        self._palette = palette_service
        self._selected_slot_id: Optional[int] = None
        self.setWindowTitle("Schedules")
        self.resize(1000, 560)
        self._build_ui()
        self._reload_schedules()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Schedules"))
        self._schedules_list = QListWidget()
        ll.addWidget(self._schedules_list, 1)
        lb = QHBoxLayout()
        self._btn_new_sched = QPushButton("New...")
        self._btn_del_sched = QPushButton("Delete")
        lb.addWidget(self._btn_new_sched)
        lb.addWidget(self._btn_del_sched)
        ll.addLayout(lb)
        splitter.addWidget(left)

        self._right_stack = QStackedWidget()

        placeholder = QWidget()
        pl = QVBoxLayout(placeholder)
        self._placeholder_label = QLabel("No schedules yet. Click 'New...' to create one.")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setStyleSheet("color: #888; font-size: 14px;")
        pl.addWidget(self._placeholder_label)
        self._right_stack.addWidget(placeholder)

        week_page = QWidget()
        wl = QVBoxLayout(week_page)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addWidget(QLabel("Week grid — click a slot to select, double-click to edit"))
        self._week_container = QWidget()
        self._week_grid = QGridLayout(self._week_container)
        self._week_grid.setContentsMargins(0, 0, 0, 0)
        self._week_grid.setSpacing(4)
        for i, name in enumerate(_WEEKDAYS_SHORT):
            h = QLabel(name)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.setStyleSheet("font-weight: 600; padding: 6px; color: #bbb;")
            self._week_grid.addWidget(h, 0, i)
        self._day_cells = {}
        for i in range(7):
            cell = _DayCell(i)
            cell.setStyleSheet("background-color: rgba(255, 255, 255, 15); border-radius: 6px;")
            cell.setMinimumWidth(60)
            self._week_grid.addWidget(cell, 1, i)
            self._day_cells[i] = cell
        self._week_grid.setRowStretch(0, 0)
        self._week_grid.setRowStretch(1, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._week_container)
        wl.addWidget(scroll, 1)

        sb = QHBoxLayout()
        self._btn_add_slot = QPushButton("Add slot...")
        self._btn_del_slot = QPushButton("Delete slot")
        sb.addWidget(self._btn_add_slot)
        sb.addWidget(self._btn_del_slot)
        sb.addStretch(1)
        wl.addLayout(sb)

        self._right_stack.addWidget(week_page)
        splitter.addWidget(self._right_stack)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([280, 720])

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self._btn_close = QPushButton("Close")
        bottom.addWidget(self._btn_close)
        layout.addLayout(bottom)

        self._btn_new_sched.clicked.connect(self._on_new_schedule)
        self._btn_del_sched.clicked.connect(self._on_delete_schedule)
        self._schedules_list.currentRowChanged.connect(self._on_schedule_selected)
        self._schedules_list.itemDoubleClicked.connect(lambda _i: self._on_edit_schedule())
        self._btn_add_slot.clicked.connect(self._on_add_slot)
        self._btn_del_slot.clicked.connect(self._on_delete_slot)
        self._btn_close.clicked.connect(self.accept)

    def _reload_schedules(self) -> None:
        current_id = self._current_schedule_id()
        self._schedules_list.blockSignals(True)
        self._schedules_list.clear()
        for s in self._svc.list_all():
            label = f"{s.name} [{_PARITY_SHORT.get(s.parity, s.parity)}]"
            if not s.active:
                label += " (inactive)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self._schedules_list.addItem(item)
        self._schedules_list.blockSignals(False)
        if current_id is not None:
            for i in range(self._schedules_list.count()):
                if self._schedules_list.item(i).data(Qt.ItemDataRole.UserRole) == current_id:
                    self._schedules_list.setCurrentRow(i)
                    self._show_week()
                    return
        if self._schedules_list.count() > 0:
            self._schedules_list.setCurrentRow(0)
            self._show_week()
        else:
            self._show_placeholder()

    def _show_week(self) -> None:
        self._right_stack.setCurrentIndex(1)
        self._reload_week()

    def _show_placeholder(self) -> None:
        self._right_stack.setCurrentIndex(0)

    def _current_schedule_id(self) -> Optional[int]:
        item = self._schedules_list.currentItem()
        if item is None:
            return None
        v = item.data(Qt.ItemDataRole.UserRole)
        return int(v) if v is not None else None

    def _on_schedule_selected(self, *_args) -> None:
        self._selected_slot_id = None
        if self._current_schedule_id() is not None:
            self._show_week()
        else:
            self._show_placeholder()

    def _reload_week(self) -> None:
        for cell in self._day_cells.values():
            cell.clear_slots()
        sid = self._current_schedule_id()
        if sid is None:
            return
        color = self._palette.get("events")
        for slot in self._svc.list_slots(sid):
            if 0 <= slot.weekday < 7:
                block = _SlotBlock(slot, slot.color or color)
                block.setChecked(slot.id == self._selected_slot_id)
                block.clicked.connect(lambda _checked=False, slot_id=slot.id: self._on_slot_clicked(slot_id))
                block.double_clicked.connect(self._on_slot_double_clicked)
                self._day_cells[slot.weekday].add_slot_block(block)

    def _on_slot_clicked(self, slot_id: int) -> None:
        self._selected_slot_id = slot_id
        self._reload_week()

    def _on_slot_double_clicked(self, slot_id: int) -> None:
        self._selected_slot_id = slot_id
        self._reload_week()
        self._on_edit_slot()

    def _on_add_slot(self) -> None:
        sid = self._current_schedule_id()
        if sid is None:
            QMessageBox.information(self, "No schedule", "Select a schedule first.")
            return
        dlg = _SlotEditDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            self._svc.add_slot(sid, **v)
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._reload_week()

    def _on_edit_slot(self) -> None:
        if self._selected_slot_id is None:
            QMessageBox.information(self, "No slot", "Select a slot first.")
            return
        sid = self._current_schedule_id()
        if sid is None:
            return
        target = None
        for s in self._svc.list_slots(sid):
            if s.id == self._selected_slot_id:
                target = s
                break
        if target is None:
            return
        dlg = _SlotEditDialog(self, weekday=target.weekday, start_time=target.start_time, end_time=target.end_time)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            self._svc.update_slot(self._selected_slot_id, **v)
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._reload_week()

    def _on_delete_slot(self) -> None:
        if self._selected_slot_id is None:
            QMessageBox.information(self, "No slot", "Select a slot first.")
            return
        sid = self._current_schedule_id()
        if sid is None:
            return
        exists = False
        for s in self._svc.list_slots(sid):
            if s.id == self._selected_slot_id:
                exists = True
                break
        if not exists:
            self._selected_slot_id = None
            self._reload_week()
            QMessageBox.information(
                self, "Slot not found",
                "The selected slot no longer exists. Selection cleared."
            )
            return
        ok = QMessageBox.question(
            self, "Delete slot", "Delete this slot?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        self._svc.delete_slot(self._selected_slot_id)
        self._selected_slot_id = None
        self._reload_week()

    def _on_new_schedule(self) -> None:
        dlg = _ScheduleEditDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            self._svc.create(name=v["name"], parity=v["parity"], active=v["active"])
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._reload_schedules()

    def _on_edit_schedule(self) -> None:
        sid = self._current_schedule_id()
        if sid is None:
            return
        s = self._svc.get(sid)
        if s is None:
            return
        dlg = _ScheduleEditDialog(self, name=s.name, parity=s.parity, active=s.active)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            self._svc.update(sid, name=v["name"], parity=v["parity"], active=v["active"])
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._reload_schedules()

    def _on_delete_schedule(self) -> None:
        sid = self._current_schedule_id()
        if sid is None:
            return
        ok = QMessageBox.question(
            self, "Delete schedule", "Delete this schedule and all of its slots?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        self._svc.delete(sid)
        self._selected_slot_id = None
        self._reload_schedules()