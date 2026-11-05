"""Entry script for PyInstaller build."""
from __future__ import annotations

import sys

from just_a_calendar.app import run


if __name__ == "__main__":
    sys.exit(run())