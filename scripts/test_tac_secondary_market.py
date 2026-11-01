#!/usr/bin/env python3
import sys
import unittest
from unittest.mock import Mock
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_tac_secondary_market import (
    INSTRUMENTS, build_fragment, parse_cnn_fear_greed,
    parse_history_page, pending_record, fetch_history_record, self_test,
)

class SecondaryMarketCaptureTests(unittest.TestCase):
    def test_instrument_map_has_all_required_secondary_groups(self):
        self.assertEqual(set(INSTRUMENTS), {"fx", "energy", "precious_metals", "risk_indicators"})
        self.assertEqual(len(INSTRUMENTS["fx"]), 6)
        self.assertEqual(len(INSTRUMENTS["energy"]), 2)
        self.assertEqual(len(INSTRUMENTS["precious_metals"]), 2)
        self.assertEqual(len(INSTRUMENTS["risk_indicators"]), 2)
        for group in INSTRUMENTS.values():
            for url, _instrument, _unit, aliases in group.values():
                self.assertTrue(url.startswith("https://hk.investing.com/"))
                self.assertTrue(aliases)

    def test_investing_hk_is_primary_for_energy_and_precious_metals(self):
        expected = {
            ("energy", "wti"): "https://hk.investing.com/commodities/crude-oil-historical-data",
            ("energy", "brent"): "https://hk.investing.com/commodities/brent-oil-historical-data",
            ("precious_metals", "gold_gc"): "https://hk.investing.com/commodities/gold-historical-data",
            ("precious_metals", "silver_si"): "https://hk.investing.com/commodities/silver-historical-data",
        }
        for (group, key), expected_url in expected.items():
            url, _instrument, _unit, _aliases = INSTRUMENTS[group][key]
            self.assertEqual(url, expected_url)
            self.assertTrue(url.startswith("https://hk.investing.com/"))
            self.assertNotIn("cmegroup.com", url)
            self.assertNotIn("ice.com", url)

    def test_fragment_declares_investing_primary_and_official_crosscheck(self):
        groups = {}
        for group, records in INSTRUMENTS.items():
            groups[group] = {key: pending_record(config[2], "test pending") for key, config in records.items()}
        groups["risk_indicators"]["cnn_fear_greed"] = pending_record("index_score", "test pending")
        fragment = build_fragment(date(2026, 10, 30), date(2026, 11, 2), groups, "2026-11-02T05:00:00+08:00")
        priority = fragment["source_priority"].lower()
        self.assertIn("investing.com", priority)
        self.assertIn("primary", priority)
        self.assertIn("backup or cross-check only", priority)
        self.assertIn("cnn business official", priority)

    def test_exact_date_and_identity_checks(self):
        html = """<html><h1>WTI Crude Oil Futures Historical Data</h1>
        <table><tr><th>Date</th><th>Price</th><th>Open</th><th>High</th><th>Low</th><th>Change %</th></tr>
        <tr><td>Oct 30, 2026</td><td>60.20</td><td>61.00</td><td>61.50</td><td>59.90</td><td>-1.20%</td></tr></table></html>"""
        parsed = parse_history_page(html, ("WTI Crude Oil",), date(2026, 10, 30))
        self.assertEqual(parsed["close"], 60.20)
        self.assertEqual(parsed["change_pct"], -1.20)
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            parse_history_page(html, ("Brent Crude Oil",), date(2026, 10, 30))
        with self.assertRaisesRegex(ValueError, "exact trading-date row"):
            parse_history_page(html, ("WTI Crude Oil",), date(2026, 10, 31))

    def test_investing_primary_capture_records_primary_provenance(self):
        group, key = "energy", "wti"
        url, instrument, unit, aliases = INSTRUMENTS[group][key]
        html = """<html><h1>WTI Crude Oil Futures Historical Data</h1>
        <table><tr><th>Date</th><th>Price</th><th>Open</th><th>High</th><th>Low</th><th>Change %</th></tr>
        <tr><td>Oct 30, 2026</td><td>60.20</td><td>61.00</td><td>61.50</td><td>59.90</td><td>-1.20%</td></tr></table></html>"""
        # The collector intentionally rejects suspiciously short HTTP responses.
        html = html.replace("</html>", "<!--" + ("fixture-padding-" * 400) + "--></html>")
        response = Mock(text=html)
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response
        record = fetch_history_record(
            session, key, url, instrument, unit, aliases,
            date(2026, 10, 30), "2026-11-02T05:00:00+08:00"
        )
        session.get.assert_called_once_with(url, timeout=(10, 30))
        self.assertEqual(record["status"], "verified")
        self.assertEqual(record["source"]["name"], "Investing.com 香港站")
        self.assertEqual(record["source"]["url"], url)
        self.assertFalse(record["fallback_used"])

    def test_investing_primary_failure_stays_pending_without_stale_substitution(self):
        url, instrument, unit, aliases = INSTRUMENTS["energy"]["wti"]
        session = Mock()
        session.get.side_effect = RuntimeError("Investing.com unavailable")
        record = fetch_history_record(
            session, "wti", url, instrument, unit, aliases,
            date(2026, 10, 30), "2026-11-02T05:00:00+08:00"
        )
        self.assertEqual(record["status"], "pending_verification")
        self.assertIsNone(record["value"])
        self.assertIsNone(record["source"])
        self.assertFalse(record["fallback_used"])
        self.assertIn("Investing.com unavailable", record["fallback_reason"])

    def test_cnn_timestamp_and_score_are_verified(self):
        now = __import__("datetime").datetime.fromisoformat("2026-10-30T12:00:00+00:00")
        result = parse_cnn_fear_greed(
            {"fear_and_greed": {"score": 52.5, "timestamp": "2026-10-30T11:00:00Z"}},
            "2026-10-30T12:00:00+00:00", now
        )
        self.assertEqual(result["value"], 52.5)
        self.assertEqual(result["source"]["data_date"], "2026-10-30")
        self.assertEqual(result["source"]["quote_type"], "cnn_fear_greed_current_snapshot")
        with self.assertRaisesRegex(ValueError, "stale or future-dated"):
            parse_cnn_fear_greed(
                {"fear_and_greed": {"score": 52.5, "timestamp": "2026-10-20T11:00:00Z"}},
                "2026-10-30T12:00:00+00:00", now
            )
        with self.assertRaisesRegex(ValueError, "0-100"):
            parse_cnn_fear_greed(
                {"fear_and_greed": {"score": 101, "timestamp": "2026-10-30T11:00:00Z"}},
                "2026-10-30T12:00:00+00:00", now
            )

    def test_fragment_requires_exact_group_fields(self):
        groups = {}
        for group, records in INSTRUMENTS.items():
            groups[group] = {key: pending_record(config[2], "test pending") for key, config in records.items()}
        groups["risk_indicators"]["cnn_fear_greed"] = pending_record("index_score", "test pending")
        fragment = build_fragment(date(2026, 10, 30), date(2026, 11, 2), groups, "2026-11-02T05:00:00+08:00")
        self.assertEqual(fragment["trading_date"], "2026-10-30")
        self.assertEqual(len(fragment["fx"]), 6)
        self.assertEqual(len(fragment["energy"]), 2)
        self.assertEqual(len(fragment["precious_metals"]), 2)
        self.assertEqual(len(fragment["risk_indicators"]), 3)
        with self.assertRaisesRegex(ValueError, "group mismatch"):
            build_fragment(date(2026, 10, 30), date(2026, 11, 2), {"fx": {}}, "2026-11-02T05:00:00+08:00")

    def test_self_test(self):
        self_test()

if __name__ == "__main__":
    unittest.main(verbosity=2)
