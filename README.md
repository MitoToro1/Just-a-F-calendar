# Just a Calendar

A local Windows desktop calendar with schedules, reminders, and a free-time view.
Everything is stored on your machine: no accounts, no cloud, no telemetry.

## Features

- **Events** with optional per-event colour and a reminder offset
  (hours / days / months / years before the start).
- **Multiple schedules** (e.g. "University", "Work") with per-weekday time slots,
  each schedule applied to *all / even / odd* weeks.
- **Automatic week parity** — set which week is currently even or odd;
  the app computes the rest from that anchor. Right-click a date in the
  calendar to re-anchor.
- **Sleep** configured once, or per weekday — counted as busy time so free
  hours are realistic.
- **Free time view** — month heat-map (red < 2h, salad 2–4h, light green 4–6h,
  green > 6h), day list of free intervals, and a text mode for the next
  14 days.
- **System reminders** via the Windows tray, even when the main window is hidden.
- **Custom RGB palette** for events and sleep colours.
- **Time format** — 24-hour or AM/PM.
- UI is in English.

## Install

### Option 1: download the ready exe (recommended for users)

1. Open the [Releases](https://github.com/MitoToro1/Just-a-F-calendar/releases) page.
2. Download the latest `JustACalendar-vX.Y.Z.zip`.
3. Unzip anywhere.
4. Run `JustACalendar.exe`.

The app stores its data in `%APPDATA%\JustACalendar\data\app.db`.
On first launch it asks for your sleep window.

### Option 2: run from source (recommended for developers)

Requires **Windows 10/11** and **Python 3.12+**.

```powershell
git clone https://github.com/MitoToro1/Just-a-F-calendar.git
cd Just-a-F-calendar

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

python -m just_a_calendar

## Build a standalone exe

```powershell
pip install -e ".[dev]"
pyinstaller --noconfirm --clean --onedir --windowed `
    --name JustACalendar `
    --icon assets\icon.ico `
    --add-data "src\just_a_calendar\db\schema.sql;just_a_calendar/db" `
    --paths src `
    --collect-submodules just_a_calendar `
    run.py
```

The result appears in `dist\JustACalendar\`.

## Data & privacy

- All data stays on your machine: `app.db` is a local SQLite file.
- No network requests, no analytics, no accounts.
- The app uses the system tray for reminders. Closing the window
  minimises to tray; use **Quit** in the tray menu to exit fully.

## License

MIT — see [LICENSE](LICENSE).