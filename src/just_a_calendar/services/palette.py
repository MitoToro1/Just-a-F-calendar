"""Global RGB palette service backed by SettingsRepo."""
from __future__ import annotations

import re
from typing import Iterable

from ..db.repositories import SettingsRepo

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFAULT_PALETTE = {
    "events":    "#4A90D9",
    "sleep":     "#2C3E50",
    "free_time": "#27AE60",
}

_PREFIX = "palette."


def _normalize(rgb) -> str:
    if isinstance(rgb, str):
        if not _HEX_RE.match(rgb):
            raise ValueError(f"color must be '#RRGGBB', got {rgb!r}")
        return rgb.upper()
    if isinstance(rgb, Iterable):
        vals = list(rgb)
        if len(vals) != 3:
            raise ValueError(f"RGB tuple must have 3 elements, got {len(vals)}")
        for v in vals:
            if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= 255):
                raise ValueError(f"RGB component must be int 0..255, got {v!r}")
        return "#{0:02X}{1:02X}{2:02X}".format(*vals)
    raise ValueError(f"color must be '#RRGGBB' or (r, g, b), got {rgb!r}")


class PaletteService:
    def __init__(self, settings: SettingsRepo) -> None:
        self._s = settings

    def get(self, key: str) -> str:
        if key not in DEFAULT_PALETTE:
            raise KeyError(f"Unknown palette key: {key}")
        stored = self._s.get(_PREFIX + key)
        return stored.upper() if stored else DEFAULT_PALETTE[key]

    def set(self, key: str, rgb) -> str:
        if key not in DEFAULT_PALETTE:
            raise KeyError(f"Unknown palette key: {key}")
        hex_color = _normalize(rgb)
        self._s.set(_PREFIX + key, hex_color)
        return hex_color

    def reset(self, key: str) -> None:
        if key not in DEFAULT_PALETTE:
            raise KeyError(f"Unknown palette key: {key}")
        self._s.set(_PREFIX + key, DEFAULT_PALETTE[key])

    def all(self) -> dict:
        return {k: self.get(k) for k in DEFAULT_PALETTE}