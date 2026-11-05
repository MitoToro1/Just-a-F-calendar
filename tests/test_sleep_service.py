"""Unit tests for SleepService."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import SettingsRepo, SleepRepo
from just_a_calendar.services.sleep import SleepService


class SleepServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.svc = SleepService(SettingsRepo(self.conn), SleepRepo(self.conn))

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_not_configured_by_default(self):
        self.assertFalse(self.svc.is_configured())
        self.assertIsNone(self.svc.get_mode())
        self.assertIsNone(self.svc.get_fixed())

    def test_fixed_roundtrip(self):
        self.svc.set_fixed("23:00", "07:00")
        self.assertTrue(self.svc.is_configured())
        self.assertEqual(self.svc.get_mode(), "fixed")
        self.assertEqual(self.svc.get_fixed(), ("23:00", "07:00"))

    def test_per_day_roundtrip(self):
        self.svc.set_per_day(0, "23:00", "07:00")
        self.svc.set_per_day(5, "01:00", "09:00")
        self.assertEqual(self.svc.get_mode(), "per_day")
        got = self.svc.get_per_day()
        self.assertEqual(got[0], ("23:00", "07:00"))
        self.assertEqual(got[5], ("01:00", "09:00"))

    def test_resolve_for_day_fixed(self):
        self.svc.set_fixed("23:00", "07:00")
        monday = date(2026, 11, 2)
        self.assertEqual(self.svc.resolve_for_day(monday), ("23:00", "07:00"))

    def test_resolve_for_day_per_day_with_fallback(self):
        self.svc.set_per_day(0, "23:30", "06:30")
        self.assertEqual(self.svc.resolve_for_day(date(2026, 11, 2)), ("23:30", "06:30"))
        self.assertEqual(self.svc.resolve_for_day(date(2026, 11, 3)), ("22:00", "08:00"))

    def test_invalid_time_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.set_fixed("25:00", "07:00")
        with self.assertRaises(ValueError):
            self.svc.set_fixed("23:00", "23:00")

    def test_ensure_default_if_missing(self):
        self.svc.ensure_default_if_missing()
        self.assertTrue(self.svc.is_configured())
        self.assertEqual(self.svc.get_fixed(), ("23:00", "07:00"))
        # idempotent
        self.svc.set_fixed("22:00", "06:00")
        self.svc.ensure_default_if_missing()
        self.assertEqual(self.svc.get_fixed(), ("22:00", "06:00"))


if __name__ == "__main__":
    unittest.main()