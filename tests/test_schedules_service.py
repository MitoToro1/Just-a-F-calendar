"""Unit tests for SchedulesService."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import SchedulesRepo
from just_a_calendar.services.schedules import SchedulesService


class SchedulesServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self._tmp.name) / "test.db")
        self.svc = SchedulesService(SchedulesRepo(self.conn))

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_create_and_get(self):
        s = self.svc.create(name="University", parity="even")
        self.assertIsNotNone(s.id)
        got = self.svc.get(s.id)
        self.assertEqual(got.name, "University")
        self.assertEqual(got.parity, "even")
        self.assertTrue(got.active)

    def test_create_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create(name="   ")

    def test_create_invalid_parity_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.create(name="Uni", parity="wrong")

    def test_partial_update(self):
        s = self.svc.create(name="Uni", parity="even")
        updated = self.svc.update(s.id, name="University")
        self.assertEqual(updated.name, "University")
        self.assertEqual(updated.parity, "even")
        updated2 = self.svc.update(s.id, active=False)
        self.assertFalse(updated2.active)
        self.assertEqual(updated2.name, "University")

    def test_update_missing_raises(self):
        with self.assertRaises(KeyError):
            self.svc.update(9999, name="X")

    def test_set_active_and_delete(self):
        s = self.svc.create(name="Uni")
        self.svc.set_active(s.id, False)
        self.assertFalse(self.svc.get(s.id).active)
        self.svc.delete(s.id)
        self.assertIsNone(self.svc.get(s.id))

    def test_slots_crud(self):
        s = self.svc.create(name="Uni")
        slot = self.svc.add_slot(s.id, weekday=0, start_time="09:00", end_time="10:30")
        self.assertIsNotNone(slot.id)
        self.assertEqual(len(self.svc.list_slots(s.id)), 1)
        updated = self.svc.update_slot(slot.id, weekday=1, start_time="11:00", end_time="12:00")
        self.assertEqual(updated.weekday, 1)
        self.assertEqual(updated.start_time, "11:00")
        self.assertEqual(updated.end_time, "12:00")
        self.svc.delete_slot(slot.id)
        self.assertEqual(len(self.svc.list_slots(s.id)), 0)

    def test_overnight_slot_rejected(self):
        s = self.svc.create(name="Uni")
        with self.assertRaises(ValueError):
            self.svc.add_slot(s.id, weekday=0, start_time="22:00", end_time="06:00")
        with self.assertRaises(ValueError):
            self.svc.add_slot(s.id, weekday=0, start_time="09:00", end_time="09:00")

    def test_invalid_time_rejected(self):
        s = self.svc.create(name="Uni")
        with self.assertRaises(ValueError):
            self.svc.add_slot(s.id, weekday=0, start_time="25:00", end_time="26:00")
        with self.assertRaises(ValueError):
            self.svc.add_slot(s.id, weekday=7, start_time="09:00", end_time="10:00")

    def test_active_for_parity(self):
        self.svc.create(name="Both", parity="both")
        self.svc.create(name="Even", parity="even")
        self.svc.create(name="Odd", parity="odd")
        self.svc.create(name="Even inactive", parity="even", active=False)

        even_names = {s.name for s in self.svc.active_schedules_for_parity("even")}
        self.assertEqual(even_names, {"Both", "Even"})
        odd_names = {s.name for s in self.svc.active_schedules_for_parity("odd")}
        self.assertEqual(odd_names, {"Both", "Odd"})

    def test_slots_for_day_filter(self):
        even = self.svc.create(name="Even Uni", parity="even")
        odd = self.svc.create(name="Odd Uni", parity="odd")
        self.svc.add_slot(even.id, weekday=0, start_time="09:00", end_time="10:00")
        self.svc.add_slot(odd.id, weekday=0, start_time="11:00", end_time="12:00")

        monday = date(2026, 11, 2)
        self.assertEqual(monday.weekday(), 0, "test assumption: 2026-11-02 is Monday")

        even_slots = self.svc.slots_for_day(monday, "even")
        self.assertEqual([s.start_time for s in even_slots], ["09:00"])
        odd_slots = self.svc.slots_for_day(monday, "odd")
        self.assertEqual([s.start_time for s in odd_slots], ["11:00"])

        tuesday = date(2026, 11, 3)
        self.assertEqual(self.svc.slots_for_day(tuesday, "even"), [])

    def test_slot_with_event_fields(self):
        s = self.svc.create(name="Uni")
        slot = self.svc.add_slot(
            s.id, weekday=0, start_time="09:00", end_time="10:30",
            title="Math", description="Room 101",
            reminder_amount=15, reminder_unit="days", color="#FF0000",
        )
        self.assertEqual(slot.title, "Math")
        self.assertEqual(slot.description, "Room 101")
        self.assertEqual(slot.reminder_amount, 15)
        self.assertEqual(slot.reminder_unit, "days")
        self.assertEqual(slot.color, "#FF0000")

        updated = self.svc.update_slot(
            slot.id, weekday=1, start_time="10:00", end_time="11:30",
            title="Math (moved)", description="Room 202",
            reminder_amount=30, reminder_unit="hours", color="#00FF00",
        )
        self.assertEqual(updated.weekday, 1)
        self.assertEqual(updated.title, "Math (moved)")
        self.assertEqual(updated.color, "#00FF00")
        self.assertEqual(updated.reminder_unit, "hours")

    def test_slot_with_invalid_reminder_unit_rejected(self):
        s = self.svc.create(name="Uni")
        with self.assertRaises(ValueError):
            self.svc.add_slot(
                s.id, weekday=0, start_time="09:00", end_time="10:00",
                reminder_amount=1, reminder_unit="weeks",
            )


if __name__ == "__main__":
    unittest.main()