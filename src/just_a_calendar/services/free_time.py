"""Free time computation.

Busy intervals for a day are the union of:
  - events (clipped to the day boundaries),
  - active schedule slots for the day's parity,
  - sleep window (start > end is allowed and wraps midnight).

Free intervals are the complement within [00:00, 24:00], optionally
filtered by a minimum length. ``additional_minutes_if_no_sleep`` tells how
many minutes would become free if the sleep window were ignored.
"""
from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta
from typing import Optional

from .events import EventsService
from .palette import DEFAULT_PALETTE, PaletteService
from .schedules import SchedulesService
from .sleep import SleepService

_DAY_MINUTES = 24 * 60


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(minutes: int) -> str:
    minutes = max(0, min(_DAY_MINUTES, minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _merge(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    out = [list(intervals[0][:2])]
    for s, e, *_rest in intervals[1:]:
        if s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1][1] = e
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def _complement(busy, day_start: int = 0, day_end: int = _DAY_MINUTES):
    result = []
    cur = day_start
    for s, e in busy:
        if s > cur:
            result.append((cur, s))
        cur = max(cur, e)
    if cur < day_end:
        result.append((cur, day_end))
    return result


class FreeTimeService:
    def __init__(
        self,
        events: EventsService,
        schedules: SchedulesService,
        sleep: SleepService,
        palette: Optional[PaletteService] = None,
    ) -> None:
        self._events = events
        self._schedules = schedules
        self._sleep = sleep
        self._palette = palette

    def _color(self, key: str) -> str:
        if self._palette is not None:
            return self._palette.get(key)
        return DEFAULT_PALETTE.get(key, "#888888")

    def busy_details_for_day(self, day: date, parity: str, include_sleep: bool = True):
        day_start = datetime.combine(day, dtime.min)
        day_end = day_start + timedelta(days=1)
        out = []

        for e in self._events.list_all():
            try:
                s_dt = datetime.fromisoformat(e.starts_at)
                e_dt = datetime.fromisoformat(e.ends_at)
            except ValueError:
                continue
            s = max(s_dt, day_start)
            en = min(e_dt, day_end)
            if s >= en:
                continue
            out.append({
                "start_min": int((s - day_start).total_seconds() // 60),
                "end_min": int((en - day_start).total_seconds() // 60),
                "kind": "event",
                "label": e.title,
                "color": e.color or self._color("events"),
            })

        for slot in self._schedules.slots_for_day(day, parity):
            sched = self._schedules.get(slot.schedule_id)
            label = slot.title or (sched.name if sched else "")
            out.append({
                "start_min": _to_min(slot.start_time),
                "end_min": _to_min(slot.end_time),
                "kind": "slot",
                "label": label,
                "color": slot.color or self._color("events"),
            })

        if include_sleep:
            start_str, end_str = self._sleep.resolve_for_day(day)
            s = _to_min(start_str)
            en = _to_min(end_str)
            sleep_color = self._color("sleep")
            if s < en:
                out.append({"start_min": s, "end_min": en, "kind": "sleep",
                            "label": "Sleep", "color": sleep_color})
            else:
                out.append({"start_min": s, "end_min": _DAY_MINUTES, "kind": "sleep",
                            "label": "Sleep", "color": sleep_color})
                if en > 0:
                    out.append({"start_min": 0, "end_min": en, "kind": "sleep",
                                "label": "Sleep", "color": sleep_color})

        out.sort(key=lambda x: (x["start_min"], x["end_min"]))
        return out

    def free_intervals_for_day(
        self,
        day: date,
        parity: str,
        *,
        include_sleep: bool = True,
        min_minutes: int = 30,
    ):
        details = self.busy_details_for_day(day, parity, include_sleep=include_sleep)
        busy = [(d["start_min"], d["end_min"]) for d in details]
        merged = _merge(busy)
        raw = _complement(merged)
        return [
            (s, e, _to_hhmm(s), _to_hhmm(e))
            for s, e in raw
            if (e - s) >= min_minutes
        ]

    def free_minutes_for_day(
        self,
        day: date,
        parity: str,
        *,
        include_sleep: bool = True,
    ) -> int:
        return sum(
            e - s
            for s, e, _a, _b in self.free_intervals_for_day(
                day, parity, include_sleep=include_sleep, min_minutes=0
            )
        )

    def additional_minutes_if_no_sleep(self, day: date, parity: str) -> int:
        with_sleep = sum(
            e - s
            for s, e, _a, _b in self.free_intervals_for_day(
                day, parity, include_sleep=True, min_minutes=0
            )
        )
        no_sleep = sum(
            e - s
            for s, e, _a, _b in self.free_intervals_for_day(
                day, parity, include_sleep=False, min_minutes=0
            )
        )
        return no_sleep - with_sleep