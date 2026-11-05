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
    _apply_migrations(conn)
    return conn


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Add columns to legacy tables created before the current schema.

    Idempotent: missing columns are added with safe defaults, existing
    columns are left untouched, existing data is preserved.
    """
    cur = conn.execute("PRAGMA table_info(schedule_slots)")
    cols = {row[1] for row in cur.fetchall()}
    additions = [
        ("title", "TEXT NOT NULL DEFAULT ''"),
        ("description", "TEXT NOT NULL DEFAULT ''"),
        ("reminder_amount", "INTEGER NOT NULL DEFAULT 0"),
        ("reminder_unit", "TEXT NOT NULL DEFAULT 'hours'"),
        ("color", "TEXT"),
    ]
    for name, decl in additions:
        if name not in cols:
            conn.execute(f"ALTER TABLE schedule_slots ADD COLUMN {name} {decl}")