#!/usr/bin/env python3
import hashlib, json, tempfile, unittest
from pathlib import Path
from run_stage2 import build_chart3_handoff_candidate

class Stage2Chart3GuardTests(unittest.TestCase):
    def test_verified_sp500_is_preserved_as_run_candidate_without_ledger_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            run_dir=root/"production"/"runs"/"TAC-2026-11-30-123-1"
            run_dir.mkdir(parents=True)
            snapshot=run_dir/"report-data.json"
            snapshot.write_text(json.dumps({"global_markets":{"sp500":1}}),encoding="utf-8")
            context={"run_id":run_dir.name,"report_date":"2026-11-30","trading_date":"2026-11-27"}
            sp500={"display":"6800.00","source":{"verification_status":"VERIFIED","data_date":"2026-11-27"}}
            result=build_chart3_handoff_candidate(run_dir,context,snapshot,"a"*64,"b"*64,sp500)
            candidate=run_dir/"chart3-sp500-handoff-candidate.json"
            self.assertEqual(result["status"],"DEFERRED_R3_WRITER_NOT_APPROVED")
            self.assertTrue(candidate.is_file())
            payload=json.loads(candidate.read_text())
            self.assertEqual(payload["run_id"],run_dir.name)
            self.assertEqual(payload["stage1_fixture_sha256"],"a"*64)
            self.assertEqual(payload["market_snapshot_sha256"],"b"*64)
            self.assertEqual(payload["source_data"],sp500)
            self.assertEqual(result["candidate_sha256"],hashlib.sha256(candidate.read_bytes()).hexdigest())
            self.assertFalse((root/"data"/"tac-chart3"/"sp500_daily_increment.jsonl").exists())

if __name__=="__main__": unittest.main()
