"""Main application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .db.connection import connect
from .db.repositories import EventsRepo, SettingsRepo
from .paths import db_path
from .services.events import EventsService
from .services.palette import PaletteService
from .ui.main_window import MainWindow


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Just a Calendar")
    conn = connect(db_path())
    events_svc = EventsService(EventsRepo(conn))
    palette_svc = PaletteService(SettingsRepo(conn))
    window = MainWindow(events_svc, palette_svc)
    window.show()
    return app.exec()