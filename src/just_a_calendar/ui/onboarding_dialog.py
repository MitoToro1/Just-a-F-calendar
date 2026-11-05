"""First-run onboarding dialog for sleep configuration."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ..services.sleep import SleepService
from ..services import time_format


class SleepOnboardingDialog(QDialog):
    def __init__(self, sleep_service: SleepService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._svc = sleep_service
        self.setWindowTitle("Welcome")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Welcome to Just a Calendar")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        layout.addWidget(title)

        hint = QLabel(
            "To help compute your free time we need to know your sleep window. "
            "You can adjust it later in Settings → Sleep, or set different times "
            "per weekday."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        form = QFormLayout()
        self._bed = QTimeEdit(QTime(23, 0))
        self._bed.setDisplayFormat(time_format.current_qt_time())
        form.addRow("Bedtime", self._bed)
        self._wake = QTimeEdit(QTime(7, 0))
        self._wake.setDisplayFormat(time_format.current_qt_time())
        form.addRow("Wake up", self._wake)
        layout.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #E74C3C;")
        self._error.setVisible(False)
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._on_save)
        layout.addWidget(buttons)

    def _on_save(self) -> None:
        start = self._bed.time().toString("HH:mm")
        end = self._wake.time().toString("HH:mm")
        if start == end:
            self._error.setText("Bedtime and wake up must differ.")
            self._error.setVisible(True)
            return
        try:
            self._svc.set_fixed(start, end)
        except ValueError as e:
            self._error.setText(str(e))
            self._error.setVisible(True)
            return
        self.accept()