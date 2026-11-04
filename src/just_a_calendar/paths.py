"""Filesystem paths for Just a Calendar.

During development (editable install), the database lives under the
repository in ``data/app.db``. When frozen by PyInstaller
(``sys.frozen`` is set), it moves to ``%APPDATA%\\JustACalendar\\app.db``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_root() -> Path:
    """Return the root folder where user data is stored."""
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA")
        if not base:
            base = str(Path.home())
        return Path(base) / "JustACalendar"
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    d = app_data_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "app.db"