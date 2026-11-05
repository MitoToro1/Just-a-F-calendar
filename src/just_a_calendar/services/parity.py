"""Week parity service with configurable anchor."""
from __future__ import annotations

from datetime import date, timedelta

from ..db.repositories import SettingsRepo

_PARITIES = ("even", "odd")
_ANCHOR_DATE_KEY = "parity_anchor_date"
_ANCHOR_VALUE_KEY = "parity_anchor_value"


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


class ParityService:
    def __init__(self, settings: SettingsRepo) -> None:
        self._s = settings

    def _get_anchor(self) -> tuple[date, str]:
        raw_date = self._s.get(_ANCHOR_DATE_KEY)
        raw_value = self._s.get(_ANCHOR_VALUE_KEY)
        if raw_date is None or raw_value not in _PARITIES:
            monday = _monday_of(date.today())
            self._s.set(_ANCHOR_DATE_KEY, monday.isoformat())
            self._s.set(_ANCHOR_VALUE_KEY, "even")
            return monday, "even"
        try:
            anchor = date.fromisoformat(raw_date)
        except ValueError:
            anchor = _monday_of(date.today())
            self._s.set(_ANCHOR_DATE_KEY, anchor.isoformat())
        return _monday_of(anchor), raw_value

    def week_parity_for(self, day: date) -> str:
        anchor, anchor_value = self._get_anchor()
        weeks = abs((_monday_of(day) - anchor).days // 7)
        if weeks % 2 == 0:
            return anchor_value
        return "odd" if anchor_value == "even" else "even"

    def current_week_parity(self) -> str:
        return self.week_parity_for(date.today())

    def set_anchor(self, day: date, value: str) -> None:
        if value not in _PARITIES:
            raise ValueError(f"parity must be one of {_PARITIES}, got {value!r}")
        self._s.set(_ANCHOR_DATE_KEY, _monday_of(day).isoformat())
        self._s.set(_ANCHOR_VALUE_KEY, value)