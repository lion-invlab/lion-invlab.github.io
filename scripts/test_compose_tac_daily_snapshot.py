#!/usr/bin/env python3
"""Tests for safe market/calendar snapshot composition."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compose_tac_daily_snapshot import MARKET_KEYS, CALENDAR_KEYS, compose


class SnapshotComposerTests(unittest.TestCase):
    def setUp(self):
        self.market = {key: {} for key in MARKET_KEYS}
        self.market["schema_version"] = "3.12"
        self.market["meta"] = {"report_date": "2026-11-03", "trading_date": "2026-11-02"}
        self.calendar = {
            "economic_calendar": {"panels": {"current_week": {"lists": [{"items": []}]}}},
            "earnings_calendar": {"panels": {"current_week": {"lists": [{"items": []}]}}},
        }

    def test_compose_merges_disjoint_market_and_calendar_contracts(self):
        result = compose(self.market, self.calendar)
        self.assertTrue(MARKET_KEYS.issubset(result))
        self.assertEqual(set(result) & CALENDAR_KEYS, CALENDAR_KEYS)
        self.assertEqual(result["economic_calendar"], self.calendar["economic_calendar"])

    def test_optional_content_fragment_is_merged_without_overwrite(self):
        result = compose(self.market, self.calendar, [{"news": {"items": []}}])
        self.assertEqual(result["news"], {"items": []})

    def test_duplicate_top_level_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "collision"):
            compose(self.market, self.calendar, [{"news": {}}, {"news": {"items": []}}])

    def test_missing_market_groups_are_rejected(self):
        broken = dict(self.market)
        broken.pop("global_indices")
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            compose(broken, self.calendar)

    def test_calendar_contract_must_be_exact(self):
        broken = dict(self.calendar)
        broken["news"] = {"items": []}
        with self.assertRaisesRegex(ValueError, "exactly economic_calendar"):
            compose(self.market, broken)

    def test_calendar_panels_must_be_objects(self):
        broken = dict(self.calendar)
        broken["economic_calendar"] = {"panels": []}
        with self.assertRaisesRegex(ValueError, "panels object required"):
            compose(self.market, broken)


if __name__ == "__main__":
    unittest.main(verbosity=2)
