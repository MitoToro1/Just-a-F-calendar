"""Schedules service with parity-aware helpers."""
from __future__ import annotations

from datetime import date
from typing import Optional

from ..db.repositories import SchedulesRepo
from ..models.entities import Schedule, ScheduleSlot

_PARITIES = ("both", "even", "odd")


def _validate_parity(p: str) -> str:
    if p not in _PARITIES:
        raise ValueError(f"parity must be one of {_PARITIES}, got {p!r}")
    return p


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    return name.strip()


def _is_hhmm(t: str) -> bool:
    if not isinstance(t, str) or len(t) != 5 or t[2] != ":":
        return False
    if not (t[:2].isdigit() and t[3:].isdigit()):
        return False
    return 0 <= int(t[:2]) < 24 and 0 <= int(t[3:]) < 60


class SchedulesService:
    def __init__(self, repo: SchedulesRepo) -> None:
        self._r = repo

    def create(self, *, name: str, parity: str = "both", active: bool = True) -> Schedule:
        _validate_parity(parity)
        return self._r.create(name=_validate_name(name), parity=parity, active=active)

    def get(self, sid: int) -> Optional[Schedule]:
        return self._r.get(sid)

    def list_all(self):
        return self._r.list_all()

    def update(
        self,
        sid: int,
        *,
        name: Optional[str] = None,
        parity: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Schedule:
        current = self._r.get(sid)
        if current is None:
            raise KeyError(f"Schedule {sid} not found")
        new_name = _validate_name(name) if name is not None else current.name
        new_parity = _validate_parity(parity) if parity is not None else current.parity
        new_active = current.active if active is None else bool(active)
        return self._r.update(sid, name=new_name, parity=new_parity, active=new_active)

    def set_active(self, sid: int, active: bool) -> None:
        self._r.set_active(sid, active)

    def delete(self, sid: int) -> None:
        self._r.delete(sid)

    def add_slot(
        self,
        sid: int,
        *,
        weekday: int,
        start_time: str,
        end_time: str,
        title: str = "",
        description: str = "",
        reminder_amount: int = 0,
        reminder_unit: str = "hours",
        color: Optional[str] = None,
    ) -> ScheduleSlot:
        self._validate_slot(weekday, start_time, end_time)
        return self._r.add_slot(
            sid, weekday=weekday, start_time=start_time, end_time=end_time,
            title=title, description=description,
            reminder_amount=reminder_amount, reminder_unit=reminder_unit,
            color=color,
        )

    def list_slots(self, sid: int):
        return self._r.list_slots(sid)

    def update_slot(
        self,
        slot_id: int,
        *,
        weekday: int,
        start_time: str,
        end_time: str,
        title: str = "",
        description: str = "",
        reminder_amount: int = 0,
        reminder_unit: str = "hours",
        color: Optional[str] = None,
    ) -> ScheduleSlot:
        self._validate_slot(weekday, start_time, end_time)
        return self._r.update_slot(
            slot_id, weekday=weekday, start_time=start_time, end_time=end_time,
            title=title, description=description,
            reminder_amount=reminder_amount, reminder_unit=reminder_unit,
            color=color,
        )

    def delete_slot(self, slot_id: int) -> None:
        self._r.delete_slot(slot_id)

    @staticmethod
    def _validate_slot(weekday: int, start_time: str, end_time: str) -> None:
        if isinstance(weekday, bool) or not isinstance(weekday, int) or not (0 <= weekday <= 6):
            raise ValueError(f"weekday must be int 0..6, got {weekday!r}")
        if not _is_hhmm(start_time):
            raise ValueError(f"start_time must be 'HH:MM', got {start_time!r}")
        if not _is_hhmm(end_time):
            raise ValueError(f"end_time must be 'HH:MM', got {end_time!r}")
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time (overnight slots are not supported yet)")

    def active_schedules_for_parity(self, parity: str) -> list[Schedule]:
        _validate_parity(parity)
        return [
            s for s in self._r.list_all()
            if s.active and (s.parity == "both" or s.parity == parity)
        ]

    def slots_for_day(self, day: date, current_parity: str) -> list[ScheduleSlot]:
        _validate_parity(current_parity)
        out: list[ScheduleSlot] = []
        for sched in self.active_schedules_for_parity(current_parity):
            for slot in self._r.list_slots(sched.id):
                if slot.weekday == day.weekday():
                    out.append(slot)
        return out