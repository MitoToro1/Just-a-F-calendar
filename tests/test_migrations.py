"""Tests for schema migrations on legacy databases."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from just_a_calendar.db.connection import connect


class MigrationTests(unittest.TestCase):
    def test_legacy_schedule_slots_gain_new_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "old.db"
            old = sqlite3.connect(str(db), isolation_level=None)
            try:
                old.executescript("""
                    CREATE TABLE schedules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        active INTEGER NOT NULL DEFAULT 1,
                        parity TEXT NOT NULL DEFAULT 'both',
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE schedule_slots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id INTEGER NOT NULL,
                        weekday INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL
                    );
                    INSERT INTO schedules (name, active, parity, created_at)
                        VALUES ('Old', 1, 'both', '2026-01-01');
                    INSERT INTO schedule_slots (schedule_id, weekday, start_time, end_time)
                        VALUES (1, 0, '09:00', '10:00');
                """)
            finally:
                old.close()

            conn = connect(db)
            try:
                row = conn.execute("SELECT * FROM schedule_slots WHERE id=1").fetchone()
                self.assertEqual(row["start_time"], "09:00")
                self.assertEqual(row["end_time"], "10:00")
                self.assertEqual(row["title"], "")
                self.assertEqual(row["description"], "")
                self.assertEqual(row["reminder_amount"], 0)
                self.assertEqual(row["reminder_unit"], "hours")
                self.assertIsNone(row["color"])
            finally:
                conn.close()

    def test_connect_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "fresh.db"
            conn = connect(db)
            conn.close()
            conn = connect(db)
            try:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(schedule_slots)").fetchall()}
                for c in ("title", "description", "reminder_amount", "reminder_unit", "color"):
                    self.assertIn(c, cols)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()