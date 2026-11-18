#!/usr/bin/env python3
import copy
import tempfile
import unittest
from pathlib import Path
from import_sp500_from_tac_report import build_record, append_record

def fixture():
    return {
        "report_date": "2026-11-17",
        "trading_date": "2026-11-16",
        "key_levels_overrides": {
            "sp500": {
                "trading_date": "2026-11-16",
                "open": 7513.98, "high": 7515.60, "low": 7400.15, "close": 7416.59,
                "source_name": "Yahoo Finance｜S&P 500 Index (^SPX) 現金指數 OHLC",
                "source_url": "https://finance.yahoo.com/quote/%5ESPX/history/?frequency=1d",
                "note": "Yahoo Finance歷史列；S&P 500現金指數^SPX，非CFD。"
            }
        }
    }

class ImportSp500FromTacReportTests(unittest.TestCase):
    def test_extracts_daily_cash_index_close_and_provenance(self):
        rec = build_record(fixture(), "2026-11-17T05:10:00+08:00")
        self.assertEqual(rec["observation_date"], "2026-11-16")
        self.assertEqual(rec["close"], 7416.59)
        self.assertIn("Yahoo Finance", rec["source_name"])
        self.assertEqual(rec["retrieved_at"], "2026-11-16T21:10:00+00:00")
        self.assertEqual(len(rec["record_sha256"]), 64)

    def test_rejects_cfd(self):
        data = fixture()
        data["key_levels_overrides"]["sp500"]["note"] = "S&P 500 CFD"
        with self.assertRaisesRegex(ValueError, "cash index"):
            build_record(data, "2026-11-17T05:10:00+08:00")

    def test_rejects_date_mismatch(self):
        data = fixture()
        data["key_levels_overrides"]["sp500"]["trading_date"] = "2026-11-15"
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_record(data, "2026-11-17T05:10:00+08:00")

    def test_append_and_identical_retry_are_idempotent(self):
        rec = build_record(fixture(), "2026-11-17T05:10:00+08:00")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlc.jsonl"
            self.assertEqual(append_record(path, rec), "APPENDED")
            self.assertEqual(append_record(path, rec), "NOOP_IDENTICAL")
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_conflicting_same_date_is_rejected(self):
        rec = build_record(fixture(), "2026-11-17T05:10:00+08:00")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlc.jsonl"
            append_record(path, rec)
            changed = copy.deepcopy(rec)
            changed["close"] = 7417.00
            with self.assertRaisesRegex(ValueError, "conflicting"):
                append_record(path, changed)

if __name__ == "__main__":
    unittest.main()
