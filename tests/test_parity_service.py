"""Unit tests for ParityService."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import SettingsRepo
from just_a_calendar.services.parity import ParityService


class ParityServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.svc = ParityService(SettingsRepo(self.conn))

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_default_anchor_is_current_week_even(self):
        today = date.today()
        self.assertEqual(self.svc.current_week_parity(), "even")
        self.assertEqual(self.svc.week_parity_for(today), "even")

    def test_anchor_set_changes_week_parity(self):
        today = date.today()
        self.svc.set_anchor(today, "odd")
        self.assertEqual(self.svc.week_parity_for(today), "odd")
        next_week = today + timedelta(days=7)
        self.assertEqual(self.svc.week_parity_for(next_week), "even")
        prev_week = today - timedelta(days=7)
        self.assertEqual(self.svc.week_parity_for(prev_week), "even")

    def test_week_boundaries(self):
        today = date.today()
        self.svc.set_anchor(today, "even")
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        self.assertEqual(self.svc.week_parity_for(monday), "even")
        self.assertEqual(self.svc.week_parity_for(sunday), "even")
        next_monday = monday + timedelta(days=7)
        self.assertEqual(self.svc.week_parity_for(next_monday), "odd")

    def test_invalid_parity_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.set_anchor(date.today(), "wrong")


if __name__ == "__main__":
    unittest.main()