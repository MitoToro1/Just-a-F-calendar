"""Main application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .db.connection import connect
from .db.repositories import EventsRepo, SchedulesRepo, SettingsRepo, SleepRepo
from .paths import db_path
from .services.events import EventsService
from .services.palette import PaletteService
from .services.parity import ParityService
from .services.schedules import SchedulesService
from .services.sleep import SleepService
from .ui.main_window import MainWindow
from .ui.onboarding_dialog import SleepOnboardingDialog


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Just a Calendar")
    conn = connect(db_path())
    settings_repo = SettingsRepo(conn)
    events_svc = EventsService(EventsRepo(conn))
    palette_svc = PaletteService(settings_repo)
    schedules_svc = SchedulesService(SchedulesRepo(conn))
    parity_svc = ParityService(settings_repo)
    sleep_svc = SleepService(settings_repo, SleepRepo(conn))

    if not sleep_svc.is_configured():
        dlg = SleepOnboardingDialog(sleep_svc)
        dlg.exec()
        sleep_svc.ensure_default_if_missing()

    window = MainWindow(events_svc, palette_svc, schedules_svc, parity_svc, sleep_svc)
    window.show()
    return app.exec()