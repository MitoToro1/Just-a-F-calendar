"""Unit tests for FreeTimeService."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import (
    EventsRepo,
    SchedulesRepo,
    SettingsRepo,
    SleepRepo,
)
from just_a_calendar.services.events import EventsService
from just_a_calendar.services.free_time import FreeTimeService
from just_a_calendar.services.schedules import SchedulesService
from just_a_calendar.services.sleep import SleepService


_MONDAY = date(2026, 11, 2)


class FreeTimeServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.events = EventsService(EventsRepo(self.conn))
        self.schedules = SchedulesService(SchedulesRepo(self.conn))
        self.sleep = SleepService(SettingsRepo(self.conn), SleepRepo(self.conn))
        self.svc = FreeTimeService(self.events, self.schedules, self.sleep)

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def _event(self, title, start_h, start_m, end_h, end_m, day=_MONDAY, color=None):
        return self.events.create(
            title=title,
            description="",
            starts_at=datetime(day.year, day.month, day.day, start_h, start_m),
            ends_at=datetime(day.year, day.month, day.day, end_h, end_m),
            reminder_amount=0,
            reminder_unit="hours",
            color=color,
        )

    def test_empty_day_all_free(self):
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=False)
        self.assertEqual(intervals, [(0, 1440, "00:00", "24:00")])

    def test_single_event_splits_day(self):
        self._event("A", 9, 0, 10, 0)
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=False)
        self.assertEqual(
            intervals,
            [(0, 540, "00:00", "09:00"), (600, 1440, "10:00", "24:00")],
        )

    def test_back_to_back_events_merge(self):
        self._event("A", 9, 0, 10, 0)
        self._event("B", 10, 0, 11, 0)
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=False)
        self.assertEqual(
            intervals,
            [(0, 540, "00:00", "09:00"), (660, 1440, "11:00", "24:00")],
        )

    def test_sleep_fixed_wraps_midnight(self):
        self.sleep.set_fixed("23:00", "07:00")
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=True)
        self.assertEqual(intervals, [(420, 1380, "07:00", "23:00")])

    def test_event_inside_sleep_no_extra_busy(self):
        self.sleep.set_fixed("23:00", "07:00")
        self._event("Early", 5, 0, 6, 0)
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=True)
        self.assertEqual(intervals, [(420, 1380, "07:00", "23:00")])

    def test_slot_parity_filter(self):
        s = self.schedules.create(name="Uni", parity="even")
        self.schedules.add_slot(s.id, weekday=0, start_time="09:00", end_time="10:00")
        even = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=False)
        self.assertEqual(
            even,
            [(0, 540, "00:00", "09:00"), (600, 1440, "10:00", "24:00")],
        )
        odd = self.svc.free_intervals_for_day(_MONDAY, "odd", include_sleep=False)
        self.assertEqual(odd, [(0, 1440, "00:00", "24:00")])

    def test_additional_if_no_sleep(self):
        self.sleep.set_fixed("23:00", "07:00")
        extra = self.svc.additional_minutes_if_no_sleep(_MONDAY, "even")
        self.assertEqual(extra, 480)

    def test_min_minutes_filter_drops_short_gap(self):
        self._event("A", 9, 0, 10, 0)
        self._event("B", 10, 15, 11, 0)
        intervals = self.svc.free_intervals_for_day(
            _MONDAY, "even", include_sleep=False, min_minutes=30
        )
        self.assertEqual(
            intervals,
            [(0, 540, "00:00", "09:00"), (660, 1440, "11:00", "24:00")],
        )

    def test_event_spanning_midnight_from_prev_day(self):
        prev = date(2026, 11, 1)
        self.events.create(
            title="Late",
            description="",
            starts_at=datetime(prev.year, prev.month, prev.day, 23, 0),
            ends_at=datetime(_MONDAY.year, _MONDAY.month, _MONDAY.day, 1, 0),
            reminder_amount=0,
            reminder_unit="hours",
        )
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=False)
        self.assertEqual(intervals, [(60, 1440, "01:00", "24:00")])

    def test_fully_busy_day_no_free(self):
        self.sleep.set_fixed("23:00", "07:00")
        for hour in range(7, 23):
            self._event(f"E{hour}", hour, 0, hour + 1, 0)
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=True)
        self.assertEqual(intervals, [])

    def test_sleep_per_day_mode(self):
        self.sleep.set_per_day(0, "01:00", "05:00")
        intervals = self.svc.free_intervals_for_day(_MONDAY, "even", include_sleep=True)
        self.assertEqual(
            intervals,
            [(0, 60, "00:00", "01:00"), (300, 1440, "05:00", "24:00")],
        )


if __name__ == "__main__":
    unittest.main()