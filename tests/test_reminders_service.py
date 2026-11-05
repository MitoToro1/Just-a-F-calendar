"""Unit tests for ReminderService."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import EventsRepo
from just_a_calendar.services.reminders import ReminderService


class ReminderServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.repo = EventsRepo(self.conn)
        self.svc = ReminderService(self.repo)

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def _make(self, *, starts_at: str, amount: int, unit: str, ends_at=None):
        return self.repo.create(
            title="X",
            description="",
            starts_at=starts_at,
            ends_at=ends_at or starts_at,
            reminder_amount=amount,
            reminder_unit=unit,
        )

    def test_hours(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=3, unit="hours")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2026, 11, 5, 11, 0))

    def test_days(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=2, unit="days")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2026, 11, 3, 14, 0))

    def test_months_normal(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=1, unit="months")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2026, 10, 5, 14, 0))

    def test_months_clamp_to_last_day(self):
        e = self._make(starts_at="2026-03-31T09:00:00", amount=1, unit="months")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2026, 2, 28, 9, 0))

    def test_months_clamp_leap_year(self):
        e = self._make(starts_at="2028-03-31T09:00:00", amount=1, unit="months")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2028, 2, 29, 9, 0))

    def test_months_cross_year(self):
        e = self._make(starts_at="2026-01-31T09:00:00", amount=1, unit="months")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2025, 12, 31, 9, 0))

    def test_years_normal(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=2, unit="years")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2024, 11, 5, 14, 0))

    def test_years_leap_clamp(self):
        e = self._make(starts_at="2028-02-29T09:00:00", amount=1, unit="years")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2027, 2, 28, 9, 0))

    def test_zero_amount_equals_start(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=0, unit="hours")
        self.assertEqual(self.svc.next_fire_at(e), datetime(2026, 11, 5, 14, 0))

    def test_due_reminders_picks_future_start_with_passed_fire(self):
        self._make(starts_at="2026-11-05T14:00:00", amount=2, unit="hours")
        due = list(self.svc.due_reminders(now=datetime(2026, 11, 5, 13, 0)))
        self.assertEqual(len(due), 1)

    def test_due_reminders_skips_fired(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=2, unit="hours")
        self.repo.mark_reminder_fired(e.id)
        due = list(self.svc.due_reminders(now=datetime(2026, 11, 5, 13, 0)))
        self.assertEqual(due, [])

    def test_due_reminders_skips_past_starts(self):
        self._make(starts_at="2026-11-05T14:00:00", amount=2, unit="hours")
        due = list(self.svc.due_reminders(now=datetime(2026, 11, 5, 14, 30)))
        self.assertEqual(due, [])

    def test_due_reminders_skips_future_fire(self):
        self._make(starts_at="2026-11-05T14:00:00", amount=2, unit="hours")
        due = list(self.svc.due_reminders(now=datetime(2026, 11, 5, 11, 59)))
        self.assertEqual(due, [])

    def test_mark_fired(self):
        e = self._make(starts_at="2026-11-05T14:00:00", amount=1, unit="hours")
        self.svc.mark_fired(e.id)
        self.assertIsNotNone(self.repo.get(e.id).reminder_fired_at)


if __name__ == "__main__":
    unittest.main()