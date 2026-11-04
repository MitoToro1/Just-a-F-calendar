"""Domain-level events service (datetime handling and validation)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from ..db.repositories import EventsRepo
from ..models.entities import Event


class EventsService:
    def __init__(self, repo: EventsRepo) -> None:
        self._r = repo

    def create(
        self,
        *,
        title: str,
        description: str,
        starts_at: datetime,
        ends_at: datetime,
        reminder_amount: int,
        reminder_unit: str,
        color: Optional[str] = None,
    ) -> Event:
        if not title or not title.strip():
            raise ValueError("title must be non-empty")
        if ends_at <= starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self._r.create(
            title=title.strip(),
            description=description or "",
            starts_at=starts_at.replace(microsecond=0).isoformat(),
            ends_at=ends_at.replace(microsecond=0).isoformat(),
            reminder_amount=reminder_amount,
            reminder_unit=reminder_unit,
            color=color,
        )

    def list_all(self):
        return self._r.list_all()

    def list_for_day(self, day: date):
        out = []
        for e in self._r.list_all():
            if datetime.fromisoformat(e.starts_at).date() == day:
                out.append(e)
        return out

    def update(self, event_id: int, **fields) -> Event:
        if "starts_at" in fields and isinstance(fields["starts_at"], datetime):
            fields["starts_at"] = fields["starts_at"].replace(microsecond=0).isoformat()
        if "ends_at" in fields and isinstance(fields["ends_at"], datetime):
            fields["ends_at"] = fields["ends_at"].replace(microsecond=0).isoformat()
        return self._r.update(event_id, **fields)

    def delete(self, event_id: int) -> None:
        self._r.delete(event_id)