"""System tray icon for Just a Calendar."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from ..db.repositories import SettingsRepo
from ..services.palette import PaletteService

_HINT_KEY = "tray_hint_shown"


def _build_icon(color_hex: str) -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(1.0, 1.0, 30.0, 30.0, 6.0, 6.0)
        painter.fillPath(path, QColor(color_hex))
        white = QColor("#FFFFFF")
        painter.fillRect(6, 9, 20, 2, white)
        painter.fillRect(6, 14, 6, 12, white)
        painter.fillRect(14, 14, 6, 4, white)
        painter.fillRect(22, 14, 4, 4, white)
        painter.fillRect(6, 22, 6, 4, white)
        painter.fillRect(14, 20, 6, 6, white)
    finally:
        painter.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    open_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        settings: SettingsRepo,
        palette: PaletteService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._palette = palette
        self._icon = _build_icon(self._palette.get("events"))
        self.setIcon(self._icon)
        self.setToolTip("Just a Calendar")

        menu = QMenu()
        act_open = QAction("Open", menu)
        act_open.triggered.connect(self.open_requested.emit)
        menu.addAction(act_open)
        menu.addSeparator()
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)
        self._menu = menu
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_requested.emit()

    def refresh_color(self) -> None:
        self._icon = _build_icon(self._palette.get("events"))
        self.setIcon(self._icon)

    def show_once_hint(self) -> None:
        if self._settings.get(_HINT_KEY) == "1":
            return
        self.showMessage(
            "Just a Calendar",
            "Still running in tray. Right-click the icon to quit.",
            QSystemTrayIcon.MessageIcon.Information,
            8000,
        )
        self._settings.set(_HINT_KEY, "1")