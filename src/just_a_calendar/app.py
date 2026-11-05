"""Main application entry point."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .db.connection import connect
from .db.repositories import EventsRepo, SchedulesRepo, SettingsRepo, SleepRepo
from .paths import db_path
from .services.events import EventsService
from .services.free_time import FreeTimeService
from .services.palette import PaletteService
from .services.parity import ParityService
from .services.reminders import ReminderService
from .services.schedules import SchedulesService
from .services.sleep import SleepService
from PySide6.QtWidgets import QSystemTrayIcon

from .ui.main_window import MainWindow
from .ui.onboarding_dialog import SleepOnboardingDialog
from .ui.tray import TrayIcon


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Just a Calendar")
    app.setQuitOnLastWindowClosed(False)
    conn = connect(db_path())
    settings_repo = SettingsRepo(conn)
    events_repo = EventsRepo(conn)
    events_svc = EventsService(events_repo)
    palette_svc = PaletteService(settings_repo)
    schedules_svc = SchedulesService(SchedulesRepo(conn))
    parity_svc = ParityService(settings_repo)
    sleep_svc = SleepService(settings_repo, SleepRepo(conn))
    free_time_svc = FreeTimeService(events_svc, schedules_svc, sleep_svc, palette_svc)
    reminder_svc = ReminderService(events_repo)

    if not sleep_svc.is_configured():
        dlg = SleepOnboardingDialog(sleep_svc)
        dlg.exec()
        sleep_svc.ensure_default_if_missing()

    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = TrayIcon(settings_repo, palette_svc)
        tray.show()

    window = MainWindow(
        events_svc, palette_svc, schedules_svc, parity_svc,
        sleep_svc, free_time_svc, reminder_svc, tray,
    )
    if tray is not None:
        tray.open_requested.connect(window.show_from_tray)
        tray.quit_requested.connect(app.quit)
    window.show()
    return app.exec()