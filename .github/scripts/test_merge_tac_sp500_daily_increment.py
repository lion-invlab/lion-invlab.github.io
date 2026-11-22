#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from merge_tac_sp500_daily_increment import canonical, encode_compact, merge_recent

class MergeIncrementTests(unittest.TestCase):
    def test_merges_only_verified_non_cfd_increment_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            recent = root / "recent.json"
            ledger = root / "increment.jsonl"
            baseline = [("2026-11-10", 752093)]
            compact = encode_compact(baseline, {"fields": "varint day-gap; zigzag close cents"})
            compact["schema_version"] = "1.0.0"
            compact["encoding"] = "zlib+base64"
            recent.write_text(json.dumps(compact), encoding="utf-8")
            row = {
                "schema_version": "1.0", "series_id": "SP500",
                "instrument": "S&P 500 cash price index",
                "report_date": "2026-11-19", "observation_date": "2026-11-11",
                "close": 7619.38,
                "source_name": "Investing.com｜S&P 500 歷史數據（Real-time derived）",
                "source_url": "https://www.investing.com/indices/us-spx-500-historical-data",
                "source_note": "S&P 500現金指數；非CFD；歷史數據表 Close/Price",
                "quote_type": "cash_index_close",
                "observed_at": "2026-11-18T09:18:19+08:00",
                "retrieved_at": "2026-11-18T01:18:19+00:00",
                "retrieval_method": "tac_daily_report_direct_source_check",
                "retrieval_timestamp_semantics": "source.observed_at records the actual Taipei-local time the daily report producer checked the source page",
            }
            row["record_sha256"] = hashlib.sha256(canonical(row)).hexdigest()
            ledger.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            merged, _, increments = merge_recent(recent, ledger)
            self.assertEqual(merged["end"], "2026-11-11")
            self.assertEqual(merged["rows"], 2)
            self.assertEqual(increments, [("2026-11-11", 761938)])

    def test_preserves_historical_ledger_rows_and_merges_only_new_dates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            recent = root / "recent.json"
            ledger = root / "increment.jsonl"
            baseline = [("2026-11-10", 752093), ("2026-11-11", 761938)]
            compact = encode_compact(baseline, {"fields": "varint day-gap; zigzag close cents"})
            compact["schema_version"] = "1.0.0"
            compact["encoding"] = "zlib+base64"
            recent.write_text(json.dumps(compact), encoding="utf-8")

            def sealed(day, close, observed_at):
                row = {
                    "schema_version": "1.0", "series_id": "SP500",
                    "instrument": "S&P 500 cash price index",
                    "report_date": "2026-11-13", "observation_date": day,
                    "close": close,
                    "source_name": "Investing.com｜S&P 500 歷史數據（Real-time derived）",
                    "source_url": "https://www.investing.com/indices/us-spx-500-historical-data",
                    "source_note": "S&P 500現金指數；非CFD；歷史數據表 Close/Price",
                    "quote_type": "cash_index_close",
                    "observed_at": observed_at, "retrieved_at": "2026-11-12T01:00:00+00:00",
                    "retrieval_method": "tac_daily_report_direct_source_check",
                    "retrieval_timestamp_semantics": "source.observed_at records the actual Taipei-local time the daily report producer checked the source page",
                }
                row["record_sha256"] = hashlib.sha256(canonical(row)).hexdigest()
                return row

            rows = [
                sealed("2026-11-10", 7520.93, "2026-11-11T09:00:00+08:00"),
                sealed("2026-11-11", 7619.38, "2026-11-12T09:00:00+08:00"),
                sealed("2026-11-12", 7700.00, "2026-11-13T09:00:00+08:00"),
            ]
            ledger.write_text("".join(json.dumps(row, ensure_ascii=False) + "\\n" for row in rows), encoding="utf-8")
            merged, _, pending = merge_recent(recent, ledger)
            self.assertEqual(merged["end"], "2026-11-12")
            self.assertEqual(merged["rows"], 3)
            self.assertEqual(pending, [("2026-11-12", 770000)])

    def test_rejects_historical_ledger_value_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            recent = root / "recent.json"
            ledger = root / "increment.jsonl"
            compact = encode_compact([("2026-11-10", 752093)], {"fields": "varint"})
            compact["schema_version"] = "1.0.0"
            compact["encoding"] = "zlib+base64"
            recent.write_text(json.dumps(compact), encoding="utf-8")
            row = {
                "schema_version": "1.0", "series_id": "SP500",
                "instrument": "S&P 500 cash price index",
                "report_date": "2026-11-11", "observation_date": "2026-11-10",
                "close": 7521.00,
                "source_name": "Investing.com｜S&P 500 歷史數據（Real-time derived）",
                "source_url": "https://www.investing.com/indices/us-spx-500-historical-data",
                "source_note": "S&P 500現金指數；非CFD；歷史數據表 Close/Price",
                "quote_type": "cash_index_close",
                "observed_at": "2026-11-11T09:00:00+08:00", "retrieved_at": "2026-11-11T01:00:00+00:00",
                "retrieval_method": "tac_daily_report_direct_source_check",
                "retrieval_timestamp_semantics": "source.observed_at records the actual Taipei-local time the daily report producer checked the source page",
            }
            row["record_sha256"] = hashlib.sha256(canonical(row)).hexdigest()
            ledger.write_text(json.dumps(row, ensure_ascii=False) + "\\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match the compact baseline"):
                merge_recent(recent, ledger)

    def test_rejects_corrupted_increment_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            recent = root / "recent.json"
            ledger = root / "increment.jsonl"
            compact = encode_compact([("2026-11-10", 752093)], {"fields": "test"})
            compact["schema_version"] = "1.0.0"
            compact["encoding"] = "zlib+base64"
            recent.write_text(json.dumps(compact), encoding="utf-8")
            ledger.write_text('{"observation_date":"2026-11-11","record_sha256":"bad"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                merge_recent(recent, ledger)

if __name__ == "__main__":
    unittest.main()
