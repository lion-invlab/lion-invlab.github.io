#!/usr/bin/env python3
import json, tempfile, unittest
from pathlib import Path
from run_stage2 import append_chart3_sp500_increment

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/"production/testdata/report-data-2026-11-23.json"

class Stage2Chart3GuardTests(unittest.TestCase):
    def test_verified_sp500_uses_existing_append_writer_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp)/"sp500_daily_increment.jsonl"
            first=append_chart3_sp500_increment(FIXTURE,ledger)
            second=append_chart3_sp500_increment(FIXTURE,ledger)
            rows=[json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(first["status"],"APPENDED")
            self.assertEqual(second["status"],"NOOP_IDENTICAL_OBSERVATION")
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["observation_date"],"2026-11-20")
            self.assertEqual(rows[0]["close"],6910.39)
            self.assertEqual(first["ledger_sha256"],second["ledger_sha256"])

if __name__=="__main__":
    unittest.main()
