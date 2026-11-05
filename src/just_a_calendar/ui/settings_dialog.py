"""Palette settings dialog."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIntValidator
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..services.palette import DEFAULT_PALETTE, PaletteService

_ORDER = ("events", "schedule", "sleep", "free_time")
_LABELS = {
    "events":    "Events",
    "schedule":  "Schedule blocks",
    "sleep":     "Sleep",
    "free_time": "Free time",
}


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


class PaletteSettingsDialog(QDialog):
    def __init__(self, palette_service: PaletteService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._palette = palette_service
        self._rows: dict[str, _ColorRow] = {}
        self.setWindowTitle("Palette settings")
        self.setMinimumWidth(600)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        current = self._palette.all()
        for key in _ORDER:
            row = _ColorRow(current[key], DEFAULT_PALETTE[key])
            self._rows[key] = row
            form.addRow(_LABELS[key], row)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self) -> None:
        for key, row in self._rows.items():
            if not row.is_valid():
                QMessageBox.warning(
                    self, "Invalid color",
                    f"{_LABELS[key]}: RGB values must be integers 0-255."
                )
                return
        for key, row in self._rows.items():
            self._palette.set(key, row.hex())
        self.accept()