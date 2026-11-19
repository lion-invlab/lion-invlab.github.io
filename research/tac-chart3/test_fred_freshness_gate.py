#!/usr/bin/env python3
"""Unit tests for the Chart 3 FRED current-snapshot freshness gate."""
import importlib.util
from datetime import date
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("tac_fred_alfred_download.py")
SPEC = importlib.util.spec_from_file_location("tac_fred_alfred_download", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class FreshnessGateTests(unittest.TestCase):
    def test_daily_vix_recent_close_passes(self):
        rows = [{"date": "2026-11-17", "value": "25.46"}]
        result = MODULE.validate_observation_freshness("VIXCLS", rows, date(2026, 11, 19))
        self.assertEqual(result["latest_valid_observation"], "2026-11-17")

    def test_weekly_series_recent_friday_passes(self):
        rows = [{"date": "2026-11-13", "value": "-0.478"}]
        result = MODULE.validate_observation_freshness("NFCI", rows, date(2026, 11, 19))
        self.assertEqual(result["age_days"], 6)

    def test_stale_vix_fails(self):
        rows = [{"date": "2026-11-09", "value": "19.92"}]
        with self.assertRaisesRegex(RuntimeError, "STALE current data"):
            MODULE.validate_observation_freshness("VIXCLS", rows, date(2026, 11, 19))

    def test_stale_weekly_series_fails(self):
        rows = [{"date": "2026-10-30", "value": "-0.459"}]
        with self.assertRaisesRegex(RuntimeError, "STALE current data"):
            MODULE.validate_observation_freshness("NFCI", rows, date(2026, 11, 19))

    def test_missing_values_do_not_count_as_fresh(self):
        rows = [{"date": "2026-11-19", "value": "."}]
        with self.assertRaisesRegex(RuntimeError, "no valid observations"):
            MODULE.validate_observation_freshness("VIXCLS", rows, date(2026, 11, 19))

if __name__ == "__main__":
    unittest.main()
