"""Tests for time_format helpers."""
from __future__ import annotations

import unittest

from just_a_calendar.services import time_format


class TimeFormatTests(unittest.TestCase):
    def tearDown(self):
        time_format.set_current("24h")

    def test_format_24h(self):
        self.assertEqual(time_format.format_hhmm("09:05", "24h"), "09:05")
        self.assertEqual(time_format.format_hhmm("23:59", "24h"), "23:59")
        self.assertEqual(time_format.format_hhmm("00:00", "24h"), "00:00")
        self.assertEqual(time_format.format_hhmm("24:00", "24h"), "24:00")

    def test_format_12h(self):
        self.assertEqual(time_format.format_hhmm("00:00", "12h"), "12:00 AM")
        self.assertEqual(time_format.format_hhmm("09:05", "12h"), "9:05 AM")
        self.assertEqual(time_format.format_hhmm("12:00", "12h"), "12:00 PM")
        self.assertEqual(time_format.format_hhmm("13:30", "12h"), "1:30 PM")
        self.assertEqual(time_format.format_hhmm("23:59", "12h"), "11:59 PM")
        self.assertEqual(time_format.format_hhmm("24:00", "12h"), "12:00 AM")

    def test_qt_formats(self):
        self.assertEqual(time_format.qt_time_format("24h"), "HH:mm")
        self.assertEqual(time_format.qt_time_format("12h"), "h:mm AP")
        self.assertEqual(time_format.qt_datetime_format("24h"), "yyyy-MM-dd HH:mm")
        self.assertEqual(time_format.qt_datetime_format("12h"), "yyyy-MM-dd h:mm AP")

    def test_current_aliases(self):
        time_format.set_current("24h")
        self.assertEqual(time_format.current_qt_time(), "HH:mm")
        self.assertEqual(time_format.current_qt_datetime(), "yyyy-MM-dd HH:mm")
        time_format.set_current("12h")
        self.assertEqual(time_format.current_qt_time(), "h:mm AP")
        self.assertEqual(time_format.current_qt_datetime(), "yyyy-MM-dd h:mm AP")

    def test_set_current_invalid(self):
        with self.assertRaises(ValueError):
            time_format.set_current("bad")


if __name__ == "__main__":
    unittest.main()