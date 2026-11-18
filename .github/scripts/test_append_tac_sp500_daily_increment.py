#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from append_tac_sp500_daily_increment import append_handoff, extract_handoff, load_existing


def handoff(day="2026-11-17", close=7340.53, observed_at="2026-11-18T05:12:44+08:00",
            quote_type="daily_close", instrument="美國標準普爾500指數 (SPX)",
            source_name="Investing.com 香港站歷史數據"):
    return {
        "report_date": "2026-11-18",
        "trading_date": day,
        "sp500": {
            "value": close,
            "status": "verified",
            "notes": "S&P 500現貨指數每日收盤，非 CFD。",
            "source": {
                "name": source_name,
                "url": "https://hk.investing.com/indices/us-spx-500-historical-data",
                "observed_at": observed_at,
                "data_date": day,
                "quote_type": quote_type,
                "instrument": instrument
            }
        }
    }


class Sp500IncrementTests(unittest.TestCase):
    def test_appends_one_verified_daily_close_with_source_timestamp_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sp500.jsonl"
            result = append_handoff(handoff(), path)
            self.assertEqual(result["status"], "APPENDED")
            row = result["record"]
            self.assertEqual(row["observation_date"], "2026-11-17")
            self.assertEqual(row["close"], 7340.53)
            self.assertEqual(row["observed_at"], "2026-11-18T05:12:44+08:00")
            self.assertEqual(row["retrieved_at"], "2026-11-17T21:12:44+00:00")
            self.assertEqual(row["source_name"], "Investing.com 香港站歷史數據")
            self.assertEqual(len(row["record_sha256"]), 64)
            self.assertEqual(len(load_existing(path)[0]), 1)

    def test_accepts_existing_normalized_snapshot_shape(self):
        payload = {
            "meta": {"report_date": "2026-11-18", "trading_date": "2026-11-17"},
            "global_indices": {
                "sp500": {
                    "value": 7340.53, "status": "verified",
                    "source": {
                        "name": "Yahoo Finance ^SPX",
                        "url": "https://finance.yahoo.com/quote/%5ESPX/history/",
                        "observed_at": "2026-11-18T05:12:44+08:00",
                        "data_date": "2026-11-17", "quote_type": "daily_close",
                        "instrument": "S&P 500 cash index"
                    }
                }
            }
        }
        record = extract_handoff(payload)
        self.assertEqual(record["close"], 7340.53)
        self.assertEqual(record["source_name"], "Yahoo Finance ^SPX")

    def test_same_date_same_observation_is_idempotent_even_if_rechecked_later(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sp500.jsonl"
            first = append_handoff(handoff(), path)
            second = append_handoff(handoff(observed_at="2026-11-18T05:20:00+08:00"), path)
            self.assertEqual(first["status"], "APPENDED")
            self.assertEqual(second["status"], "NOOP_IDENTICAL_OBSERVATION")
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_conflicting_same_day_close_or_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sp500.jsonl"
            append_handoff(handoff(), path)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                append_handoff(handoff(close=7341.00), path)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                append_handoff(handoff(source_name="Yahoo Finance ^SPX"), path)

    def test_rejects_wrong_data_date(self):
        payload = handoff()
        payload["sp500"]["source"]["data_date"] = "2026-11-16"
        with self.assertRaisesRegex(ValueError, "match trading_date"):
            extract_handoff(payload)

    def test_rejects_missing_or_naive_observed_at(self):
        payload = handoff()
        payload["sp500"]["source"]["observed_at"] = "2026-11-18T05:12:44"
        with self.assertRaisesRegex(ValueError, "timezone"):
            extract_handoff(payload)

    def test_rejects_non_taipei_timestamp_and_wrong_report_day(self):
        payload = handoff()
        payload["sp500"]["source"]["observed_at"] = "2026-11-17T21:12:44+00:00"
        with self.assertRaisesRegex(ValueError, "Asia/Taipei"):
            extract_handoff(payload)
        payload = handoff()
        payload["sp500"]["source"]["observed_at"] = "2026-11-17T23:59:00+08:00"
        with self.assertRaisesRegex(ValueError, "match report_date"):
            extract_handoff(payload)

    def test_rejects_unverified_or_cfd_or_non_sp500(self):
        payload = handoff()
        payload["sp500"]["status"] = "pending_verification"
        with self.assertRaisesRegex(ValueError, "verified"):
            extract_handoff(payload)
        payload = handoff()
        payload["sp500"]["source"]["quote_type"] = "CFD close"
        with self.assertRaisesRegex(ValueError, "CFD"):
            extract_handoff(payload)
        payload = handoff()
        payload["sp500"]["source"]["instrument"] = "NASDAQ 100"
        with self.assertRaisesRegex(ValueError, "identify the S&P 500"):
            extract_handoff(payload)

    def test_rejects_non_https_source(self):
        payload = handoff()
        payload["sp500"]["source"]["url"] = "http://example.com/spx"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            extract_handoff(payload)

    def test_rejects_corrupt_ledger_hash_and_nonascending_dates(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sp500.jsonl"
            append_handoff(handoff(), path)
            raw = path.read_text()
            path.write_text(raw.replace("7340.53", "7341.00"))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_existing(path)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sp500.jsonl"
            append_handoff(handoff(day="2026-11-17"), path)
            with self.assertRaisesRegex(ValueError, "later than"):
                append_handoff(handoff(day="2026-11-16"), path)


