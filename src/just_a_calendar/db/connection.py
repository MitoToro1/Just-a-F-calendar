"""SQLite connection helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _read_schema() -> str:
    return _SCHEMA_PATH.read_text(encoding="utf-8")


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (or create) a SQLite database and apply the schema.

    Pass ``":memory:"`` for an in-memory database (useful in tests).
    """
    if db_path == ":memory:":
        target = ":memory:"
    else:
        p = Path(db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        target = str(p)

    conn = sqlite3.connect(target, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_read_schema())
    return conn