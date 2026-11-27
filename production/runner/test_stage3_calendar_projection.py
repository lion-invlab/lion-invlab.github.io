#!/usr/bin/env python3
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
from builder_approval import current_governance_blob_shas
from stage_wr_preflight import stage_wr_preflight
RUNNER=ROOT/"production/runner"

class Stage3CalendarTests(unittest.TestCase):
    def test_read_only_projection_uses_pinned_main_commit(self):
        commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        before=subprocess.check_output(["git","diff","--","data/calendar/weeks"],cwd=ROOT,text=True)
        (ROOT/"production/runs").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="TAC-2026-11-26-stage3-",dir=ROOT/"production/runs") as td:
            run_dir=Path(td)
            context={"run_id":run_dir.name,"report_date":"2026-11-26","main_commit_sha":commit,
                "governance":{"commit_sha":commit,"blob_shas":current_governance_blob_shas(ROOT,commit)}}
            (run_dir/"run-context.json").write_text(json.dumps(context),encoding="utf-8")
            stage2_wr=stage_wr_preflight("STAGE_2",context)
            (run_dir/"stage2-market-snapshot-receipt.json").write_text(json.dumps({"status":"PASS","wr_preflight":stage2_wr,"worker_wr_attestation":{"status":"PASS","stage2_wr_sha256":stage2_wr["wr_sha256"]}}),encoding="utf-8")
            subprocess.run([sys.executable,str(RUNNER/"run_stage3.py"),"--run-dir",str(run_dir.relative_to(ROOT))],cwd=ROOT,check=True,capture_output=True,text=True)
            receipt=json.loads((run_dir/"stage3-calendar-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"],"PASS")
            self.assertEqual(receipt["main_commit_sha"],commit)
            self.assertEqual(receipt["current_week"]["week_id"],"2026-W48")
            self.assertEqual(receipt["previous_week"]["week_id"],"2026-W47")
            self.assertTrue(receipt["source_json_read_only"])
            self.assertTrue((run_dir/"calendar.json").is_file())
            self.assertTrue((run_dir/"earnings.json").is_file())
        after=subprocess.check_output(["git","diff","--","data/calendar/weeks"],cwd=ROOT,text=True)
        self.assertEqual(before,after)

if __name__=="__main__":unittest.main()
