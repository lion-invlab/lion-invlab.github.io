#!/usr/bin/env python3
import json, tempfile, unittest
from pathlib import Path
from import_sp500_from_d4_capture import build_record, append_record

def capture():
    return {
        "report_date": "2026-11-18",
        "trading_date": "2026-11-17",
        "captured_at_taipei": "2026-11-18T05:15:03+08:00",
        "timezone": "Asia/Taipei",
        "key_levels": {
            "baseline_date": "2026-11-17",
            "items": [{
                "key": "sp500", "name": "S&P 500", "symbol": "^SPX",
                "trading_date": "2026-11-17", "quote_type": "cash_index",
                "ohlc": "H 7,401.20｜L 7,315.10｜C 7,340.53",
                "source_name": "Yahoo Finance historical data",
                "url": "https://finance.yahoo.com/quote/%5ESPX/history/?frequency=1d"
            }]
        }
    }

class D4IncrementalImportTests(unittest.TestCase):
    def test_extracts_close_and_preserves_exact_d4_capture_timestamp(self):
        row = build_record(capture())
        self.assertEqual(row["observation_date"], "2026-11-17")
        self.assertEqual(row["close"], 7340.53)
        self.assertEqual(row["symbol"], "^SPX")
        self.assertEqual(row["retrieved_at"], "2026-11-17T21:15:03+00:00")
        self.assertIn("Yahoo Finance", row["source_name"])
        self.assertEqual(len(row["record_sha256"]), 64)

    def test_imports_close_from_tac_report_market_card(self):
        data = {
            "report_date": "2026-11-18",
            "trading_date": "2026-11-17",
            "market_data_captured_at": "2026-11-18T05:12:44+08:00",
            "global_markets": {
                "標普500指數": {
                    "display": "7,340.53",
                    "source": {
                        "name": "Yahoo Finance｜S&P 500 Index (^SPX)現金指數歷史資料",
                        "url": "https://finance.yahoo.com/quote/%5ESPX/history/?frequency=1d",
                        "data_date": "2026-11-17",
                        "quote_type": "cash_index_close",
                        "note": "S&P 500現金指數，非CFD。"
                    }
                }
            }
        }
        row = build_record(data)
        self.assertEqual(row["observation_date"], "2026-11-17")
        self.assertEqual(row["close"], 7340.53)
        self.assertIn("Yahoo Finance", row["source_name"])
        self.assertEqual(row["retrieved_at"], "2026-11-17T21:12:44+00:00")
        self.assertIn("TAC market-data capture timestamp", row["retrieval_timestamp_semantics"])

    def test_report_data_without_explicit_capture_timestamp_fails_closed(self):
        data = {
            "report_date": "2026-11-18", "trading_date": "2026-11-17",
            "global_markets": {"標普500指數": {
                "display": "7,340.53",
                "source": {
                    "name": "AP", "url": "https://apnews.com/article/example",
                    "data_date": "2026-11-17", "quote_type": "cash_index_close",
                    "note": "S&P 500現金指數收盤。"
                }
            }}
        }
        with self.assertRaisesRegex(ValueError, "exact retrieved_at"):
            build_record(data)

    def test_prefers_d4_ohlc_override_when_report_has_both(self):
        data = {
            "report_date": "2026-11-17", "trading_date": "2026-11-16",
            "key_levels_overrides": {"sp500": {
                "trading_date": "2026-11-16", "open": 7513.98, "high": 7515.60,
                "low": 7400.15, "close": 7416.59,
                "source_name": "Yahoo Finance ^SPX cash index",
                "source_url": "https://finance.yahoo.com/quote/%5ESPX/history/",
                "note": "S&P 500現金指數，非CFD。",
                "retrieved_at": "2026-11-17T05:10:00+08:00"
            }},
            "global_markets": {"標普500指數": {"display": "7,416.59"}}
        }
        row = build_record(data)
        self.assertEqual(row["close"], 7416.59)
        self.assertIn("Yahoo Finance", row["source_name"])
        self.assertEqual(row["retrieval_method"], "tac_report_verified_ohlc_source_record")

    def test_accepts_numeric_close_field(self):
        data = capture()
        data["key_levels"]["items"][0]["close"] = 7340.53
        row = build_record(data)
        self.assertEqual(row["close"], 7340.53)

    def test_rejects_missing_capture_timestamp(self):
        data = capture()
        del data["captured_at_taipei"]
        with self.assertRaisesRegex(ValueError, "timestamp"):
            build_record(data)

    def test_rejects_non_cash_index(self):
        data = capture()
        data["key_levels"]["items"][0]["quote_type"] = "cfd"
        with self.assertRaisesRegex(ValueError, "cash-index"):
            build_record(data)

    def test_rejects_wrong_symbol_and_source_mismatch(self):
        data = capture()
        data["key_levels"]["items"][0]["symbol"] = "^ES"
        with self.assertRaisesRegex(ValueError, "symbol"):
            build_record(data)
        data = capture()
        data["key_levels"]["items"][0]["source_name"] = "Investing.com"
        with self.assertRaisesRegex(ValueError, "Yahoo URL/source_name mismatch"):
            build_record(data)

    def test_append_is_idempotent_and_conflicts_fail(self):
        row = build_record(capture())
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sp500.jsonl"
            self.assertEqual(append_record(path, row), "APPENDED")
            self.assertEqual(append_record(path, row), "NOOP_IDENTICAL_OBSERVATION")
            self.assertEqual(len(path.read_text().splitlines()), 1)
            changed = dict(row)
            changed["close"] = 7341.00
            self.assertEqual(len(path.read_text().splitlines()), 1)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                append_record(path, changed)

if __name__ == "__main__":
    unittest.main()
