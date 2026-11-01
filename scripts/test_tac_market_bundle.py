#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from capture_tac_market_bundle import merge_treasury_fragments

def record(value, status="verified", fallback=False):
    return {
        "value": value, "unit": "%", "change": 0.01,
        "change_unit": "percentage_point", "status": status,
        "source": {"name": "test", "url": "https://example.com"},
        "fallback_used": fallback, "fallback_reason": None, "notes": "test",
    }

class MarketBundleTests(unittest.TestCase):
    def test_primary_treasury_values_are_never_overwritten(self):
        primary = {"bonds": {
            "us_2y": record(3.5),
            "us_10y": record(None, "missing"),
            "us_30y": record(None, "missing"),
        }}
        fallback = {"bonds": {
            "us_2y": record(9.9),
            "us_10y": record(4.1),
            "us_30y": record(None, "missing"),
        }}
        merged = merge_treasury_fragments(primary, fallback, "2026-11-02", "2026-10-30")
        self.assertEqual(merged["bonds"]["us_2y"]["value"], 3.5)
        self.assertFalse(merged["bonds"]["us_2y"]["fallback_used"])
        self.assertEqual(merged["bonds"]["us_10y"]["value"], 4.1)
        self.assertTrue(merged["bonds"]["us_10y"]["fallback_used"])
        self.assertIn("FRED DGS", merged["bonds"]["us_10y"]["fallback_reason"])
        self.assertEqual(merged["bonds"]["us_30y"]["status"], "missing")

    def test_unavailable_primary_and_fallback_stay_pending(self):
        merged = merge_treasury_fragments(None, None, "2026-11-02", "2026-10-30", "network down")
        self.assertEqual(set(merged["bonds"]), {"us_2y", "us_10y", "us_30y"})
        self.assertTrue(all(item["status"] == "pending_verification" for item in merged["bonds"].values()))
        self.assertTrue(all(item["value"] is None for item in merged["bonds"].values()))

if __name__ == "__main__":
    unittest.main(verbosity=2)
