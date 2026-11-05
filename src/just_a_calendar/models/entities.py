"""Data entities for Just a Calendar."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Event:
    id: Optional[int]
    title: str
    description: str
    starts_at: str
    ends_at: str
    reminder_amount: int
    reminder_unit: str
    color: Optional[str]
    reminder_fired_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class Schedule:
    id: Optional[int]
    name: str
    active: bool
    parity: str
    created_at: str


@dataclass
class ScheduleSlot:
    id: Optional[int]
    schedule_id: int
    weekday: int
    start_time: str
    end_time: str
    title: str = ""
    description: str = ""
    reminder_amount: int = 0
    reminder_unit: str = "hours"
    color: Optional[str] = None


@dataclass
class SleepWindow:
    weekday: int
    start_time: str
    end_time: str