#!/usr/bin/env python3
"""Tests for normalized market snapshot to renderer display adaptation."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adapt_tac_market_snapshot_for_renderer import adapt_market_snapshot
from render_tac_market_safe import SourceTreeParser, render_fedwatch, render_report_meta
from validate_tac_daily_snapshot import sample_snapshot

class MarketSnapshotDisplayAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas/tac-daily-market-snapshot.schema.json").read_text(encoding="utf-8"))
        cls.binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        cls.weekday = (ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html").read_text(encoding="utf-8")


    def test_report_meta_updates_monday_report_date_and_meta_tag(self):
        snapshot = sample_snapshot(self.schema)
        snapshot["meta"].update({"report_date": "2026-11-02", "trading_date": "2026-10-30"})
        parser = SourceTreeParser(self.monday)
        parser.feed(self.monday)
        parser.close()
        edits, used = [], set()
        render_report_meta(self.monday, parser, snapshot, self.binding, edits, used)
        rendered = self.monday
        for start, end, replacement in sorted(edits, reverse=True):
            rendered = rendered[:start] + replacement + rendered[end:]
        self.assertIn("<title>TAC 投資早報｜2026/11/02（一）審核版</title>", rendered)
        self.assertIn('name="report-date" content="2026-11-02"', rendered)
        self.assertIn('class="report-date">｜2026/11/02（一）</span>', rendered)
        self.assertIn('class="status">2026/11/02（一）｜週一版', rendered)

    def test_report_meta_uses_previous_trading_date_on_weekdays(self):
        snapshot = sample_snapshot(self.schema)
        snapshot["meta"].update({"report_date": "2026-11-03", "trading_date": "2026-11-02"})
        parser = SourceTreeParser(self.weekday)
        parser.feed(self.weekday)
        parser.close()
        edits, used = [], set()
        render_report_meta(self.weekday, parser, snapshot, self.binding, edits, used)
        rendered = self.weekday
        for start, end, replacement in sorted(edits, reverse=True):
            rendered = rendered[:start] + replacement + rendered[end:]
        self.assertIn("<title>TAC 投資早報｜2026/11/03（二）審核版</title>", rendered)
        self.assertIn('name="report-date" content="2026-11-03"', rendered)
        self.assertIn('class="report-date">｜2026/11/03（二）</span>', rendered)
        self.assertIn('class="status">2026/11/02（一）｜週二至週五版', rendered)

    def test_verified_numeric_market_fields_are_formatted_by_group(self):
        snapshot = sample_snapshot(self.schema)
        dow = snapshot["global_indices"]["dow"]
        dow.update({"value": 42123.456, "unit": "index_points", "change": -1.25,
                    "change_unit": "percent", "status": "verified"})
        xlk = snapshot["sectors"]["xlk"]
        xlk.update({"value": 100.0, "unit": "percent", "change": 0.65,
                    "change_unit": "percent", "status": "verified"})
        usd_twd = snapshot["fx"]["usd_twd"]
        usd_twd.update({"value": 31.23456, "unit": "currency_pair", "change": 0.1,
                        "change_unit": "percent", "status": "verified"})
        snapshot["global_indices"]["sp500"]["status"] = "pending_verification"
        snapshot["bonds"]["us_10y"]["status"] = "market_closed"
        result = adapt_market_snapshot(snapshot)
        self.assertEqual(result["global_indices"]["dow"]["value"], "42,123.46")
        self.assertEqual(result["global_indices"]["dow"]["change"], "−1.25%")
        self.assertEqual(result["sectors"]["xlk"]["change"], "+0.65%")
        self.assertEqual(result["fx"]["usd_twd"]["value"], "31.2346")
        self.assertEqual(result["global_indices"]["sp500"]["value"], "待核實")
        self.assertEqual(result["bonds"]["us_10y"]["value"], "休市")

    def test_unknown_change_unit_fails_closed(self):
        snapshot = sample_snapshot(self.schema)
        snapshot["global_indices"]["dow"].update({
            "value": 1.0, "change": 1.0, "change_unit": "unknown_unit",
            "status": "verified",
        })
        with self.assertRaisesRegex(ValueError, "unsupported change_unit"):
            adapt_market_snapshot(snapshot)

    def test_verified_fedwatch_requires_explicit_outcome_mapping(self):
        snapshot = sample_snapshot(self.schema)
        snapshot["fedwatch"]["status"] = "verified"
        with self.assertRaisesRegex(ValueError, "explicit outcome-mapped renderer payload"):
            adapt_market_snapshot(snapshot)

    def test_pending_fedwatch_renders_no_implied_probability(self):
        snapshot = sample_snapshot(self.schema)
        result = adapt_market_snapshot(snapshot)
        fedwatch = result["fedwatch"]
        self.assertEqual(fedwatch["status"], "pending_verification")
        parser = SourceTreeParser(self.weekday)
        parser.feed(self.weekday)
        parser.close()
        edits, used = [], set()
        render_fedwatch(self.weekday, parser, {"fedwatch": fedwatch}, self.binding, edits, used)
        rendered = self.weekday
        for start, end, replacement in sorted(edits, reverse=True):
            rendered = rendered[:start] + replacement + rendered[end:]
        self.assertGreaterEqual(rendered.count("待核實"), 8)
        self.assertIn('style="width:0%"', rendered)
        self.assertIn('aria-label="FedWatch 機率待核實"', rendered)
        self.assertNotIn("0.0%", rendered)

if __name__ == "__main__":
    unittest.main(verbosity=2)
