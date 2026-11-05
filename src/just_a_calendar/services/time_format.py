"""Time format preference (24-hour vs AM/PM).

This module holds a single global setting that affects how times are
displayed in the UI. Storage always uses ``HH:MM`` strings; only display
uses this preference.

Pure helpers (``format_hhmm``, ``qt_time_format``, ``qt_datetime_format``)
accept an explicit ``fmt`` argument so they can be tested without touching
global state. The module-level ``_current`` acts as a convenience default.
"""
from __future__ import annotations

from typing import Optional

_VALID = ("24h", "12h")
_DEFAULT = "24h"
_KEY = "time_format"
_current = _DEFAULT


def set_current(fmt: str) -> None:
    global _current
    if fmt not in _VALID:
        raise ValueError(f"time_format must be one of {_VALID}, got {fmt!r}")
    _current = fmt


def current() -> str:
    return _current


def qt_time_format(fmt: Optional[str] = None) -> str:
    f = fmt or _current
    return "HH:mm" if f == "24h" else "h:mm AP"


def qt_datetime_format(fmt: Optional[str] = None) -> str:
    f = fmt or _current
    return "yyyy-MM-dd HH:mm" if f == "24h" else "yyyy-MM-dd h:mm AP"


def current_qt_time() -> str:
    return qt_time_format()


def current_qt_datetime() -> str:
    return qt_datetime_format()


def format_hhmm(hhmm: str, fmt: Optional[str] = None) -> str:
    f = fmt or _current
    h, m = hhmm.split(":")
    hi = int(h)
    mi = int(m)
    if f == "24h":
        return f"{hi:02d}:{mi:02d}"
    if hi == 24:
        hi = 0
    suffix = "AM" if hi < 12 else "PM"
    h12 = hi % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{mi:02d} {suffix}"


def load_from_settings(settings) -> None:
    raw = settings.get(_KEY)
    if raw in _VALID:
        set_current(raw)
    else:
        set_current(_DEFAULT)


def save_to_settings(settings, fmt: str) -> None:
    if fmt not in _VALID:
        raise ValueError(f"time_format must be one of {_VALID}, got {fmt!r}")
    settings.set(_KEY, fmt)
    set_current(fmt)