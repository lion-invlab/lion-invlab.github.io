"""Tests for Stage 2's trading-date-bound close wait."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from wait_for_trading_date_close import seconds_until_trading_close

NY = ZoneInfo("America/New_York")


class TradingDateCloseWaitTests(unittest.TestCase):
    def test_before_close_on_target_date_waits_until_1600(self):
        now = datetime(2026, 11, 27, 15, 45, tzinfo=NY)
        self.assertEqual(seconds_until_trading_close("2026-11-27", now), 15 * 60)

    def test_after_close_on_target_date_does_not_wait(self):
        now = datetime(2026, 11, 27, 16, 5, tzinfo=NY)
        self.assertEqual(seconds_until_trading_close("2026-11-27", now), 0)

    def test_later_calendar_date_does_not_wait_for_next_days_close(self):
        now = datetime(2026, 11, 28, 0, 40, tzinfo=NY)
        self.assertEqual(seconds_until_trading_close("2026-11-27", now), 0)

    def test_timezone_aware_now_is_converted_to_new_york(self):
        from datetime import timezone
        now = datetime(2026, 11, 27, 20, 45, tzinfo=timezone.utc)
        self.assertEqual(seconds_until_trading_close("2026-11-27", now), 15 * 60)

    def test_naive_now_is_rejected(self):
        with self.assertRaises(ValueError):
            seconds_until_trading_close("2026-11-27", datetime(2026, 11, 27, 15, 45))


if __name__ == "__main__":
    unittest.main()
