"""Reminder scheduling.

``next_fire_at`` computes when a reminder should fire for an event:
``starts_at - reminder_amount reminder_unit``. Months and years follow
calendar arithmetic: if the target day does not exist (e.g. 31 March minus
one month), the result is clamped to the last day of the target month
(28/29 February).
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Iterable, Optional

from ..db.repositories import EventsRepo
from ..models.entities import Event

_UNITS = ("hours", "days", "months", "years")


def _subtract_months(dt: datetime, months: int) -> datetime:
    year = dt.year
    month = dt.month - months
    while month <= 0:
        month += 12
        year -= 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)


def _subtract_years(dt: datetime, years: int) -> datetime:
    year = dt.year - years
    last_day = calendar.monthrange(year, dt.month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, day=day)


class ReminderService:
    def __init__(self, events_repo: EventsRepo) -> None:
        self._r = events_repo

    def next_fire_at(self, event: Event) -> datetime:
        if event.reminder_unit not in _UNITS:
            raise ValueError(f"Unknown reminder_unit {event.reminder_unit!r}")
        if event.reminder_amount < 0:
            raise ValueError("reminder_amount must be >= 0")
        starts = datetime.fromisoformat(event.starts_at)
        n = event.reminder_amount
        if n == 0:
            return starts
        if event.reminder_unit == "hours":
            return starts - timedelta(hours=n)
        if event.reminder_unit == "days":
            return starts - timedelta(days=n)
        if event.reminder_unit == "months":
            return _subtract_months(starts, n)
        return _subtract_years(starts, n)

    def due_reminders(self, now: Optional[datetime] = None) -> Iterable[Event]:
        if now is None:
            now = datetime.now()
        out = []
        for event in self._r.list_all():
            if event.reminder_fired_at is not None:
                continue
            try:
                starts = datetime.fromisoformat(event.starts_at)
            except ValueError:
                continue
            if starts <= now:
                continue
            try:
                fire = self.next_fire_at(event)
            except ValueError:
                continue
            if fire <= now:
                out.append(event)
        out.sort(key=lambda e: e.starts_at)
        return out

    def mark_fired(self, event_id: int) -> None:
        self._r.mark_reminder_fired(event_id)