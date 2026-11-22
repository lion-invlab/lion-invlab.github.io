#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

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
                "source_name": "Yahoo Finance S&P 500 (^GSPC) Historical Data",
                "source_url": "https://finance.yahoo.com/quote/%5EGSPC/history/",
                "source_note": "S&P 500現金指數；非CFD；quote_type=daily_close；instrument=S&P 500 cash index",
                "observed_at": "2026-11-19T09:18:19+08:00",
                "retrieved_at": "2026-11-19T01:18:19+00:00",
                "retrieval_method": "tac_daily_report_direct_source_check",
                "retrieval_timestamp_semantics": "source.observed_at records the actual Taipei-local time the daily report producer checked the source page",
            }
            row["record_sha256"] = hashlib.sha256(canonical(row)).hexdigest()
            ledger.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            merged, _, increments = merge_recent(recent, ledger)
            self.assertEqual(merged["end"], "2026-11-11")
            self.assertEqual(merged["rows"], 2)
            self.assertEqual(increments, [("2026-11-11", 761938)])


    def test_reprocessing_already_merged_ledger_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            recent = root / "recent.json"
            ledger = root / "increment.jsonl"
            baseline = [("2026-11-10", 752093), ("2026-11-11", 761938)]
            compact = encode_compact(baseline, {"fields": "varint day-gap; zigzag close cents"})
            compact["schema_version"] = "1.0.0"
            compact["encoding"] = "zlib+base64"
            recent.write_text(json.dumps(compact), encoding="utf-8")
            row = {
                "schema_version": "1.0", "series_id": "SP500",
                "instrument": "S&P 500 cash price index",
                "report_date": "2026-11-19", "observation_date": "2026-11-11",
                "close": 7619.38,
                "source_name": "Yahoo Finance S&P 500 (^GSPC) Historical Data",
                "source_url": "https://finance.yahoo.com/quote/%5EGSPC/history/",
                "source_note": "S&P 500現金指數；非CFD；quote_type=daily_close",
                "observed_at": "2026-11-19T09:18:19+08:00",
                "retrieved_at": "2026-11-19T01:18:19+00:00",
                "retrieval_method": "tac_daily_report_direct_source_check",
                "retrieval_timestamp_semantics": "source.observed_at records the actual Taipei-local time the daily report producer checked the source page",
            }
            row["record_sha256"] = hashlib.sha256(canonical(row)).hexdigest()
            ledger.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            before = recent.read_text(encoding="utf-8")
            merged, _, increments = merge_recent(recent, ledger)
            self.assertEqual(merged["end"], "2026-11-11")
            self.assertEqual(len(increments), 1)
            self.assertEqual(recent.read_text(encoding="utf-8"), before)

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
