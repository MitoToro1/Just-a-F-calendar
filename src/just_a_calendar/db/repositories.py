"""Repository layer for Just a Calendar."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from ..models.entities import Event, Schedule, ScheduleSlot, SleepWindow

_REMINDER_UNITS = ("hours", "days", "months", "years")
_PARITIES = ("both", "even", "odd")
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_unit(u: str) -> str:
    if u not in _REMINDER_UNITS:
        raise ValueError(f"reminder_unit must be one of {_REMINDER_UNITS}, got {u!r}")
    return u


def _validate_parity(p: str) -> str:
    if p not in _PARITIES:
        raise ValueError(f"parity must be one of {_PARITIES}, got {p!r}")
    return p


def _validate_weekday(w: int) -> int:
    if isinstance(w, bool) or not isinstance(w, int) or not (0 <= w <= 6):
        raise ValueError(f"weekday must be int 0..6, got {w!r}")
    return w


def _validate_hhmm(t: str, label: str) -> str:
    if not isinstance(t, str) or not _HHMM_RE.match(t):
        raise ValueError(f"{label} must be 'HH:MM', got {t!r}")
    return t


def _validate_amount(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f"reminder_amount must be a non-negative int, got {n!r}")
    return n


def _row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        starts_at=row["starts_at"],
        ends_at=row["ends_at"],
        reminder_amount=row["reminder_amount"],
        reminder_unit=row["reminder_unit"],
        color=row["color"],
        reminder_fired_at=row["reminder_fired_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_schedule(row: sqlite3.Row) -> Schedule:
    return Schedule(
        id=row["id"],
        name=row["name"],
        active=bool(row["active"]),
        parity=row["parity"],
        created_at=row["created_at"],
    )


def _row_to_slot(row: sqlite3.Row) -> ScheduleSlot:
    return ScheduleSlot(
        id=row["id"],
        schedule_id=row["schedule_id"],
        weekday=row["weekday"],
        start_time=row["start_time"],
        end_time=row["end_time"],
    )


def _row_to_sleep(row: sqlite3.Row) -> SleepWindow:
    return SleepWindow(
        weekday=row["weekday"],
        start_time=row["start_time"],
        end_time=row["end_time"],
    )


class EventsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(
        self,
        *,
        title: str,
        description: str,
        starts_at: str,
        ends_at: str,
        reminder_amount: int,
        reminder_unit: str,
        color: Optional[str] = None,
    ) -> Event:
        _validate_unit(reminder_unit)
        _validate_amount(reminder_amount)
        now = _now_iso()
        cur = self.conn.execute(
            "INSERT INTO events "
            "(title, description, starts_at, ends_at, reminder_amount, "
            " reminder_unit, color, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, description or "", starts_at, ends_at,
             reminder_amount, reminder_unit, color, now, now),
        )
        return self.get(cur.lastrowid)

    def get(self, event_id: int) -> Optional[Event]:
        row = self.conn.execute(
            "SELECT * FROM events WHERE id=?", (event_id,)
        ).fetchone()
        return _row_to_event(row) if row else None

    def list_all(self):
        rows = self.conn.execute(
            "SELECT * FROM events ORDER BY starts_at"
        ).fetchall()
        return [_row_to_event(r) for r in rows]

    def update(self, event_id: int, **fields) -> Event:
        if not fields:
            raise ValueError("update requires at least one field")
        if "reminder_unit" in fields:
            _validate_unit(fields["reminder_unit"])
        if "reminder_amount" in fields:
            _validate_amount(fields["reminder_amount"])
        allowed = {
            "title", "description", "starts_at", "ends_at",
            "reminder_amount", "reminder_unit", "color",
        }
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"Unknown fields: {sorted(bad)}")
        sets = ", ".join(f"{k}=?" for k in fields)
        params = list(fields.values()) + [_now_iso(), event_id]
        cur = self.conn.execute(
            f"UPDATE events SET {sets}, updated_at=?, reminder_fired_at=NULL "
            "WHERE id=?",
            params,
        )
        if cur.rowcount == 0:
            raise KeyError(f"Event {event_id} not found")
        return self.get(event_id)

    def mark_reminder_fired(self, event_id: int) -> None:
        self.conn.execute(
            "UPDATE events SET reminder_fired_at=? WHERE id=?",
            (_now_iso(), event_id),
        )

    def delete(self, event_id: int) -> None:
        self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))


class SchedulesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, name: str, parity: str = "both", active: bool = True) -> Schedule:
        _validate_parity(parity)
        cur = self.conn.execute(
            "INSERT INTO schedules (name, active, parity, created_at) "
            "VALUES (?, ?, ?, ?)",
            (name, 1 if active else 0, parity, _now_iso()),
        )
        return self.get(cur.lastrowid)

    def get(self, sid: int) -> Optional[Schedule]:
        row = self.conn.execute(
            "SELECT * FROM schedules WHERE id=?", (sid,)
        ).fetchone()
        return _row_to_schedule(row) if row else None

    def list_all(self):
        rows = self.conn.execute(
            "SELECT * FROM schedules ORDER BY id"
        ).fetchall()
        return [_row_to_schedule(r) for r in rows]

    def set_active(self, sid: int, active: bool) -> None:
        self.conn.execute(
            "UPDATE schedules SET active=? WHERE id=?",
            (1 if active else 0, sid),
        )

    def delete(self, sid: int) -> None:
        self.conn.execute("DELETE FROM schedules WHERE id=?", (sid,))

    def add_slot(
        self, sid: int, *, weekday: int, start_time: str, end_time: str
    ) -> ScheduleSlot:
        _validate_weekday(weekday)
        _validate_hhmm(start_time, "start_time")
        _validate_hhmm(end_time, "end_time")
        cur = self.conn.execute(
            "INSERT INTO schedule_slots "
            "(schedule_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
            (sid, weekday, start_time, end_time),
        )
        row = self.conn.execute(
            "SELECT * FROM schedule_slots WHERE id=?", (cur.lastrowid,)
        ).fetchone()
        return _row_to_slot(row)

    def list_slots(self, sid: int):
        rows = self.conn.execute(
            "SELECT * FROM schedule_slots WHERE schedule_id=? "
            "ORDER BY weekday, start_time",
            (sid,),
        ).fetchall()
        return [_row_to_slot(r) for r in rows]

    def delete_slot(self, slot_id: int) -> None:
        self.conn.execute(
            "DELETE FROM schedule_slots WHERE id=?", (slot_id,)
        )


class SettingsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, key: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


class SleepRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def set_day(self, weekday: int, start_time: str, end_time: str) -> SleepWindow:
        _validate_weekday(weekday)
        _validate_hhmm(start_time, "start_time")
        _validate_hhmm(end_time, "end_time")
        self.conn.execute(
            "INSERT INTO sleep_per_day (weekday, start_time, end_time) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(weekday) DO UPDATE SET "
            "start_time=excluded.start_time, end_time=excluded.end_time",
            (weekday, start_time, end_time),
        )
        return SleepWindow(weekday=weekday, start_time=start_time, end_time=end_time)

    def list_all(self):
        rows = self.conn.execute(
            "SELECT * FROM sleep_per_day ORDER BY weekday"
        ).fetchall()
        return [_row_to_sleep(r) for r in rows]