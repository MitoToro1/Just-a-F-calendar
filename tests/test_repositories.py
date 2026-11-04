"""Unit tests for the repository layer."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from just_a_calendar.db.connection import connect
from just_a_calendar.db.repositories import (
    EventsRepo,
    SchedulesRepo,
    SettingsRepo,
    SleepRepo,
)


class RepoTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.db"
        self.conn = connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()


class EventsRepoTests(RepoTestBase):
    def test_create_and_get(self):
        repo = EventsRepo(self.conn)
        e = repo.create(
            title="Lecture",
            description="Math",
            starts_at="2026-11-05T10:00:00+00:00",
            ends_at="2026-11-05T11:30:00+00:00",
            reminder_amount=15,
            reminder_unit="hours",
        )
        self.assertIsNotNone(e.id)
        got = repo.get(e.id)
        self.assertEqual(got.title, "Lecture")
        self.assertEqual(got.reminder_unit, "hours")

    def test_invalid_unit(self):
        repo = EventsRepo(self.conn)
        with self.assertRaises(ValueError):
            repo.create(
                title="x",
                description="",
                starts_at="2026-11-05T10:00:00+00:00",
                ends_at="2026-11-05T11:00:00+00:00",
                reminder_amount=1,
                reminder_unit="weeks",
            )

    def test_update_resets_reminder_fired_at(self):
        repo = EventsRepo(self.conn)
        e = repo.create(
            title="Lecture",
            description="",
            starts_at="2026-11-05T10:00:00+00:00",
            ends_at="2026-11-05T11:00:00+00:00",
            reminder_amount=1,
            reminder_unit="days",
        )
        repo.mark_reminder_fired(e.id)
        self.assertIsNotNone(repo.get(e.id).reminder_fired_at)
        repo.update(e.id, title="Lecture 2")
        got2 = repo.get(e.id)
        self.assertEqual(got2.title, "Lecture 2")
        self.assertIsNone(got2.reminder_fired_at)

    def test_delete(self):
        repo = EventsRepo(self.conn)
        e = repo.create(
            title="x",
            description="",
            starts_at="2026-11-05T10:00:00+00:00",
            ends_at="2026-11-05T11:00:00+00:00",
            reminder_amount=0,
            reminder_unit="hours",
        )
        repo.delete(e.id)
        self.assertIsNone(repo.get(e.id))


class SchedulesRepoTests(RepoTestBase):
    def test_create_with_slots_and_cascade_delete(self):
        sched_repo = SchedulesRepo(self.conn)
        s = sched_repo.create(name="University", parity="even")
        sched_repo.add_slot(s.id, weekday=0, start_time="09:00", end_time="10:30")
        sched_repo.add_slot(s.id, weekday=2, start_time="14:00", end_time="15:30")
        self.assertEqual(len(sched_repo.list_slots(s.id)), 2)

        sched_repo.delete(s.id)
        row = self.conn.execute(
            "SELECT COUNT(*) AS c FROM schedule_slots WHERE schedule_id=?",
            (s.id,),
        ).fetchone()
        self.assertEqual(row["c"], 0)

    def test_invalid_parity(self):
        sched_repo = SchedulesRepo(self.conn)
        with self.assertRaises(ValueError):
            sched_repo.create(name="Bad", parity="wrong")

    def test_toggle_active(self):
        sched_repo = SchedulesRepo(self.conn)
        s = sched_repo.create(name="Uni", parity="both")
        self.assertTrue(s.active)
        sched_repo.set_active(s.id, False)
        self.assertFalse(sched_repo.get(s.id).active)


class SettingsRepoTests(RepoTestBase):
    def test_upsert_and_get(self):
        repo = SettingsRepo(self.conn)
        self.assertIsNone(repo.get("theme"))
        repo.set("theme", "dark")
        self.assertEqual(repo.get("theme"), "dark")
        repo.set("theme", "light")
        self.assertEqual(repo.get("theme"), "light")


class SleepRepoTests(RepoTestBase):
    def test_set_and_list(self):
        repo = SleepRepo(self.conn)
        repo.set_day(0, "23:00", "07:00")
        repo.set_day(5, "01:00", "09:00")
        days = {w.weekday: w for w in repo.list_all()}
        self.assertIn(0, days)
        self.assertEqual(days[0].start_time, "23:00")
        self.assertEqual(days[5].end_time, "09:00")

    def test_invalid_time(self):
        repo = SleepRepo(self.conn)
        with self.assertRaises(ValueError):
            repo.set_day(0, "25:00", "07:00")


if __name__ == "__main__":
    unittest.main()