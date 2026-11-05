"""Main application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .db.connection import connect
from .db.repositories import EventsRepo, SchedulesRepo, SettingsRepo
from .paths import db_path
from .services.events import EventsService
from .services.palette import PaletteService
from .services.parity import ParityService
from .services.schedules import SchedulesService
from .ui.main_window import MainWindow


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Just a Calendar")
    conn = connect(db_path())
    settings_repo = SettingsRepo(conn)
    events_svc = EventsService(EventsRepo(conn))
    palette_svc = PaletteService(settings_repo)
    schedules_svc = SchedulesService(SchedulesRepo(conn))
    parity_svc = ParityService(settings_repo)
    window = MainWindow(events_svc, palette_svc, schedules_svc, parity_svc)
    window.show()
    return app.exec()