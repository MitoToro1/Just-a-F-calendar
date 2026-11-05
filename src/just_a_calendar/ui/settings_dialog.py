"""Settings dialog with Colors and General tabs."""
from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import QTime, Qt
from PySide6.QtGui import QColor, QIntValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ..services.palette import DEFAULT_PALETTE, PaletteService
from ..services.parity import ParityService
from ..services.sleep import SleepService

_COLOR_ORDER = ("events", "sleep")
_COLOR_LABELS = {
    "events": "Events' default color",
    "sleep":  "Sleep",
}

_WEEKDAYS_FULL = (
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
)


class _ColorRow(QWidget):
    def __init__(self, initial_hex: str, default_hex: str) -> None:
        super().__init__()
        self._hex = initial_hex.upper()
        self._default_hex = default_hex.upper()
        self._validator = QIntValidator(0, 255, self)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self._preview = QLabel()
        self._preview.setFixedSize(28, 28)
        self._r = self._make_edit()
        self._g = self._make_edit()
        self._b = self._make_edit()
        self._btn_pick = QPushButton("Pick...")
        self._btn_reset = QPushButton("Reset")
        h.addWidget(self._preview)
        h.addWidget(QLabel("R")); h.addWidget(self._r)
        h.addWidget(QLabel("G")); h.addWidget(self._g)
        h.addWidget(QLabel("B")); h.addWidget(self._b)
        h.addWidget(self._btn_pick)
        h.addWidget(self._btn_reset)
        h.addStretch(1)

        self._apply_to_fields()
        self._update_preview()
        self._r.textChanged.connect(self._on_edit)
        self._g.textChanged.connect(self._on_edit)
        self._b.textChanged.connect(self._on_edit)
        self._btn_pick.clicked.connect(self._on_pick)
        self._btn_reset.clicked.connect(self._on_reset)

    def _make_edit(self) -> QLineEdit:
        e = QLineEdit()
        e.setValidator(self._validator)
        e.setMaxLength(3)
        e.setFixedWidth(56)
        e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return e

    def hex(self) -> str:
        return self._hex

    def is_valid(self) -> bool:
        for e in (self._r, self._g, self._b):
            t = e.text().strip()
            if not t:
                return False
            try:
                v = int(t)
            except ValueError:
                return False
            if not (0 <= v <= 255):
                return False
        return True

    def _apply_to_fields(self) -> None:
        qc = QColor(self._hex)
        for e, v in ((self._r, qc.red()), (self._g, qc.green()), (self._b, qc.blue())):
            e.blockSignals(True)
            e.setText(str(v))
            e.blockSignals(False)

    def _update_preview(self) -> None:
        self._preview.setStyleSheet(
            f"background-color: {self._hex}; border: 1px solid #888; border-radius: 3px;"
        )

    def _set_hex(self, hex_color: str) -> None:
        self._hex = hex_color.upper()
        self._apply_to_fields()
        self._update_preview()

    def _on_edit(self) -> None:
        if self.is_valid():
            self._hex = "#{0:02X}{1:02X}{2:02X}".format(
                int(self._r.text()), int(self._g.text()), int(self._b.text())
            )
            self._update_preview()

    def _on_pick(self) -> None:
        chosen = QColorDialog.getColor(QColor(self._hex), self, "Pick color")
        if chosen.isValid():
            self._set_hex(chosen.name())

    def _on_reset(self) -> None:
        self._set_hex(self._default_hex)


class SettingsDialog(QDialog):
    def __init__(
        self,
        palette_service: PaletteService,
        parity_service: ParityService,
        sleep_service: SleepService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette_service
        self._parity = parity_service
        self._sleep = sleep_service
        self._rows: dict[str, _ColorRow] = {}
        self._initial_parity = self._parity.current_week_parity()
        self._selected_parity = self._initial_parity
        self._sleep_mode_buttons: dict = {}
        self._fixed_bed = None
        self._fixed_wake = None
        self._per_day_edits: dict = {}
        self.setWindowTitle("Settings")
        self.setMinimumWidth(640)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_colors_tab(), "Colors")
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_sleep_tab(), "Sleep")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_colors_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        current = self._palette.all()
        for key in _COLOR_ORDER:
            row = _ColorRow(current[key], DEFAULT_PALETTE[key])
            self._rows[key] = row
            form.addRow(_COLOR_LABELS[key], row)
        return page

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)

        title = QLabel("Week parity")
        title.setStyleSheet("font-weight: 600;")
        v.addWidget(title)

        hint = QLabel(
            "Set which parity corresponds to the current week. "
            "All other weeks are computed automatically. "
            "You can also right-click a date in the calendar to mark its week."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        v.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("This week is:"))
        self._btn_even = QPushButton("Even")
        self._btn_odd = QPushButton("Odd")
        self._btn_even.setCheckable(True)
        self._btn_odd.setCheckable(True)
        self._parity_group = QButtonGroup(self)
        self._parity_group.setExclusive(True)
        self._parity_group.addButton(self._btn_even)
        self._parity_group.addButton(self._btn_odd)
        if self._selected_parity == "even":
            self._btn_even.setChecked(True)
        else:
            self._btn_odd.setChecked(True)
        self._btn_even.clicked.connect(lambda: self._select_parity("even"))
        self._btn_odd.clicked.connect(lambda: self._select_parity("odd"))
        row.addWidget(self._btn_even)
        row.addWidget(self._btn_odd)
        row.addStretch(1)
        v.addLayout(row)

        v.addStretch(1)
        return page

    def _build_sleep_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)

        title = QLabel("Sleep")
        title.setStyleSheet("font-weight: 600;")
        v.addWidget(title)

        hint = QLabel(
            "Sleep is treated as busy time when computing free hours. "
            "Choose one fixed interval for every day, or set it per weekday."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        v.addWidget(hint)

        mode_row = QHBoxLayout()
        self._sleep_mode_group = QButtonGroup(self)
        self._sleep_mode_group.setExclusive(True)
        self._sleep_mode_buttons["fixed"] = QRadioButton("Fixed (same every day)")
        self._sleep_mode_buttons["per_day"] = QRadioButton("Per day")
        for key in ("fixed", "per_day"):
            self._sleep_mode_group.addButton(self._sleep_mode_buttons[key])
            mode_row.addWidget(self._sleep_mode_buttons[key])
        mode_row.addStretch(1)
        v.addLayout(mode_row)

        current_mode = self._sleep.get_mode() or "fixed"
        if current_mode not in self._sleep_mode_buttons:
            current_mode = "fixed"
        self._sleep_mode_buttons[current_mode].setChecked(True)

        self._sleep_stack = QStackedWidget()

        fixed_page = QWidget()
        ff = QFormLayout(fixed_page)
        fixed_vals = self._sleep.get_fixed() or ("23:00", "07:00")
        self._fixed_bed = QTimeEdit(QTime.fromString(fixed_vals[0], "HH:mm"))
        self._fixed_bed.setDisplayFormat("HH:mm")
        ff.addRow("Bedtime", self._fixed_bed)
        self._fixed_wake = QTimeEdit(QTime.fromString(fixed_vals[1], "HH:mm"))
        self._fixed_wake.setDisplayFormat("HH:mm")
        ff.addRow("Wake up", self._fixed_wake)
        self._sleep_stack.addWidget(fixed_page)

        per_day_page = QWidget()
        g = QGridLayout(per_day_page)
        g.addWidget(QLabel("Day"), 0, 0)
        g.addWidget(QLabel("Bedtime"), 0, 1)
        g.addWidget(QLabel("Wake up"), 0, 2)
        existing = self._sleep.get_per_day()
        for weekday in range(7):
            start, end = existing.get(weekday, ("22:00", "08:00"))
            bed = QTimeEdit(QTime.fromString(start, "HH:mm"))
            bed.setDisplayFormat("HH:mm")
            wake = QTimeEdit(QTime.fromString(end, "HH:mm"))
            wake.setDisplayFormat("HH:mm")
            g.addWidget(QLabel(_WEEKDAYS_FULL[weekday]), weekday + 1, 0)
            g.addWidget(bed, weekday + 1, 1)
            g.addWidget(wake, weekday + 1, 2)
            self._per_day_edits[weekday] = (bed, wake)
        self._sleep_stack.addWidget(per_day_page)

        self._sleep_stack.setCurrentIndex(0 if current_mode == "fixed" else 1)

        v.addWidget(self._sleep_stack, 1)

        self._sleep_mode_buttons["fixed"].toggled.connect(
            lambda checked: checked and self._sleep_stack.setCurrentIndex(0)
        )
        self._sleep_mode_buttons["per_day"].toggled.connect(
            lambda checked: checked and self._sleep_stack.setCurrentIndex(1)
        )

        self._sleep_error = QLabel("")
        self._sleep_error.setStyleSheet("color: #E74C3C;")
        self._sleep_error.setVisible(False)
        v.addWidget(self._sleep_error)

        return page

    def _select_parity(self, value: str) -> None:
        self._selected_parity = value

    def _show_sleep_error(self, msg: str) -> None:
        self._sleep_error.setText(msg)
        self._sleep_error.setVisible(True)

    def _on_save(self) -> None:
        for key, row in self._rows.items():
            if not row.is_valid():
                QMessageBox.warning(
                    self, "Invalid color",
                    f"{_COLOR_LABELS[key]}: RGB values must be integers 0-255."
                )
                return

        mode = "fixed" if self._sleep_mode_buttons["fixed"].isChecked() else "per_day"
        if mode == "fixed":
            s = self._fixed_bed.time().toString("HH:mm")
            e = self._fixed_wake.time().toString("HH:mm")
            if s == e:
                self._show_sleep_error("Bedtime and wake up must differ.")
                return
        else:
            for weekday, (bed, wake) in self._per_day_edits.items():
                if bed.time() == wake.time():
                    self._show_sleep_error(
                        f"{_WEEKDAYS_FULL[weekday]}: bedtime and wake up must differ."
                    )
                    return

        for key, row in self._rows.items():
            self._palette.set(key, row.hex())

        try:
            if mode == "fixed":
                self._sleep.set_fixed(
                    self._fixed_bed.time().toString("HH:mm"),
                    self._fixed_wake.time().toString("HH:mm"),
                )
            else:
                for weekday, (bed, wake) in self._per_day_edits.items():
                    self._sleep.set_per_day(
                        weekday,
                        bed.time().toString("HH:mm"),
                        wake.time().toString("HH:mm"),
                    )
        except ValueError as exc:
            self._show_sleep_error(str(exc))
            return

        if self._selected_parity != self._initial_parity:
            self._parity.set_anchor(date.today(), self._selected_parity)
        self.accept()