"""Sleep settings service.

A user can either define one fixed sleep interval applied every day
(``mode = fixed``) or set sleep windows per weekday (``mode = per_day``).
Night intervals such as ``23:00-07:00`` (start after end) are allowed:
the window wraps around midnight.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from ..db.repositories import SettingsRepo, SleepRepo

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_MODES = ("fixed", "per_day")
_DEFAULT_FIXED = ("23:00", "07:00")
_FALLBACK_PER_DAY = ("22:00", "08:00")
_MODE_KEY = "sleep_mode"
_FIXED_START_KEY = "sleep_fixed_start"
_FIXED_END_KEY = "sleep_fixed_end"


def _validate_hhmm(value: str, label: str) -> str:
    if not isinstance(value, str) or not _HHMM_RE.match(value):
        raise ValueError(f"{label} must be 'HH:MM', got {value!r}")
    return value


def _validate_weekday(weekday: int) -> int:
    if isinstance(weekday, bool) or not isinstance(weekday, int) or not (0 <= weekday <= 6):
        raise ValueError(f"weekday must be int 0..6, got {weekday!r}")
    return weekday


class SleepService:
    def __init__(self, settings: SettingsRepo, sleep_repo: SleepRepo) -> None:
        self._s = settings
        self._r = sleep_repo

    def is_configured(self) -> bool:
        return self.get_mode() is not None

    def get_mode(self) -> Optional[str]:
        mode = self._s.get(_MODE_KEY)
        return mode if mode in _MODES else None

    def set_fixed(self, start: str, end: str) -> tuple[str, str]:
        _validate_hhmm(start, "start")
        _validate_hhmm(end, "end")
        if start == end:
            raise ValueError("start and end must differ")
        self._s.set(_MODE_KEY, "fixed")
        self._s.set(_FIXED_START_KEY, start)
        self._s.set(_FIXED_END_KEY, end)
        return start, end

    def get_fixed(self) -> Optional[tuple[str, str]]:
        start = self._s.get(_FIXED_START_KEY)
        end = self._s.get(_FIXED_END_KEY)
        if start is None or end is None:
            return None
        return start, end

    def set_per_day(self, weekday: int, start: str, end: str) -> None:
        _validate_weekday(weekday)
        _validate_hhmm(start, "start")
        _validate_hhmm(end, "end")
        if start == end:
            raise ValueError("start and end must differ")
        self._s.set(_MODE_KEY, "per_day")
        self._r.set_day(weekday, start, end)

    def get_per_day(self) -> dict:
        return {w.weekday: (w.start_time, w.end_time) for w in self._r.list_all()}

    def resolve_for_day(self, _day: date) -> tuple[str, str]:
        mode = self.get_mode()
        if mode == "per_day":
            per_day = self.get_per_day()
            return per_day.get(_day.weekday(), _FALLBACK_PER_DAY)
        fixed = self.get_fixed()
        if fixed is not None:
            return fixed
        return _DEFAULT_FIXED

    def ensure_default_if_missing(self) -> None:
        if self.is_configured():
            return
        self.set_fixed(_DEFAULT_FIXED[0], _DEFAULT_FIXED[1])