PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    starts_at         TEXT NOT NULL,
    ends_at           TEXT NOT NULL,
    reminder_amount   INTEGER NOT NULL CHECK (reminder_amount >= 0),
    reminder_unit     TEXT NOT NULL CHECK (reminder_unit IN ('hours','days','months','years')),
    color             TEXT,
    reminder_fired_at TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    parity     TEXT NOT NULL DEFAULT 'both' CHECK (parity IN ('both','even','odd')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_slots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    weekday     INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_time  TEXT NOT NULL,
    end_time    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schedule_slots_schedule
    ON schedule_slots(schedule_id);

CREATE TABLE IF NOT EXISTS sleep_per_day (
    weekday    INTEGER PRIMARY KEY CHECK (weekday BETWEEN 0 AND 6),
    start_time TEXT NOT NULL,
    end_time   TEXT NOT NULL
);