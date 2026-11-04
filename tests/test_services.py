"""Unit tests for the service layer."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import EventsRepo, SettingsRepo
from just_a_calendar.services.events import EventsService
from just_a_calendar.services.palette import DEFAULT_PALETTE, PaletteService


class PaletteServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.svc = PaletteService(SettingsRepo(self.conn))

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_defaults(self):
        self.assertEqual(self.svc.get("events"), DEFAULT_PALETTE["events"])

    def test_set_with_hex(self):
        self.svc.set("events", "#FF0000")
        self.assertEqual(self.svc.get("events"), "#FF0000")

    def test_set_with_rgb_tuple(self):
        self.svc.set("events", (10, 20, 30))
        self.assertEqual(self.svc.get("events"), "#0A141E")

    def test_invalid_rgb(self):
        with self.assertRaises(ValueError):
            self.svc.set("events", (256, 0, 0))

    def test_invalid_hex(self):
        with self.assertRaises(ValueError):
            self.svc.set("events", "#XYZXYZ")

    def test_unknown_key(self):
        with self.assertRaises(KeyError):
            self.svc.get("nope")


class EventsServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.svc = EventsService(EventsRepo(self.conn))

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_create_and_list_for_day(self):
        e = self.svc.create(
            title="Lecture",
            description="",
            starts_at=datetime(2026, 11, 5, 10, 0),
            ends_at=datetime(2026, 11, 5, 11, 0),
            reminder_amount=1,
            reminder_unit="hours",
        )
        self.assertIsNotNone(e.id)
        day_items = self.svc.list_for_day(date(2026, 11, 5))
        self.assertEqual(len(day_items), 1)
        self.assertEqual(self.svc.list_for_day(date(2026, 11, 6)), [])

    def test_ends_before_starts_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create(
                title="Bad",
                description="",
                starts_at=datetime(2026, 11, 5, 11, 0),
                ends_at=datetime(2026, 11, 5, 10, 0),
                reminder_amount=1,
                reminder_unit="hours",
            )

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create(
                title="   ",
                description="",
                starts_at=datetime(2026, 11, 5, 10, 0),
                ends_at=datetime(2026, 11, 5, 11, 0),
                reminder_amount=1,
                reminder_unit="hours",
            )

    def test_update_and_delete(self):
        e = self.svc.create(
            title="Lecture",
            description="",
            starts_at=datetime(2026, 11, 5, 10, 0),
            ends_at=datetime(2026, 11, 5, 11, 0),
            reminder_amount=1,
            reminder_unit="hours",
        )
        updated = self.svc.update(e.id, title="Lecture 2")
        self.assertEqual(updated.title, "Lecture 2")
        self.svc.delete(e.id)
        self.assertEqual(len(self.svc.list_all()), 0)


if __name__ == "__main__":
    unittest.main()