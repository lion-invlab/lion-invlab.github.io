#!/usr/bin/env python3
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
from builder_approval import current_governance_blob_shas
from stage_wr_loader import load_stage_wr
RUNNER=ROOT/"production/runner"

class Stage3CalendarTests(unittest.TestCase):
    def run_projection(self, report_date):
        commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        before=subprocess.check_output(["git","diff","--","data/calendar/weeks"],cwd=ROOT,text=True)
        (ROOT/"production/runs").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"TAC-{report_date}-stage3-",dir=ROOT/"production/runs") as td:
            run_dir=Path(td)
            from run_state import initial_run_state, transition_state
            trading_date="2026-11-20" if report_date=="2026-11-23" else "2026-11-25"
            context={"run_id":run_dir.name,"report_date":report_date,"trading_date":trading_date,
                "production_date":"2026-11-21" if report_date=="2026-11-23" else report_date,
                "workflow_run_id":"test","main_commit_sha":commit,
                "governance":{"commit_sha":commit,"blob_shas":current_governance_blob_shas(ROOT,commit)}}
            (run_dir/"run-context.json").write_text(json.dumps(context),encoding="utf-8")
            stage1_receipt={"status":"PASS","run_id":run_dir.name,"report_date":report_date,"trading_date":trading_date}
            (run_dir/"stage1-receipt.json").write_text(json.dumps(stage1_receipt),encoding="utf-8")
            import hashlib
            state=initial_run_state(context,stage1_receipt,hashlib.sha256((run_dir/"stage1-receipt.json").read_bytes()).hexdigest())
            stage2_wr=load_stage_wr("STAGE_2",context)
            stage2_receipt={"status":"PASS","run_id":run_dir.name,"stage_wr_loaded":stage2_wr}
            (run_dir/"stage2-market-snapshot-receipt.json").write_text(json.dumps(stage2_receipt),encoding="utf-8")
            state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="READY",
                new_status="RUNNING",lease_owner="test-stage2",lease_expires_at="2026-11-28T00:10:00Z")
            state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="RUNNING",
                new_status="SUBMITTED",output_sha256="a"*64)
            state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="SUBMITTED",
                new_status="PASS",output_sha256=hashlib.sha256((run_dir/"stage2-market-snapshot-receipt.json").read_bytes()).hexdigest(),
                receipt_path=f"production/runs/{run_dir.name}/stage2-market-snapshot-receipt.json")
            (run_dir/"run-state.json").write_text(json.dumps(state),encoding="utf-8")
            env=os.environ.copy()
            # The candidate branch is exercising Main production code; Stage 3's
            # production source guard must see the simulated Main execution ref.
            env["GITHUB_REF"]="refs/heads/main"
            subprocess.run([sys.executable,str(RUNNER/"run_stage3.py"),"--run-dir",str(run_dir.relative_to(ROOT))],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
            receipt=json.loads((run_dir/"stage3-calendar-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"],"PASS")
            self.assertEqual(receipt["main_commit_sha"],commit)
            self.assertEqual(receipt["current_week"]["week_id"],"2026-W48")
            self.assertTrue(receipt["source_json_read_only"])
            self.assertTrue((run_dir/"calendar.json").is_file())
            self.assertTrue((run_dir/"earnings.json").is_file())
            source_bundle=json.loads((run_dir/"calendar-source-bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(source_bundle["main_commit_sha"],commit)
            after=subprocess.check_output(["git","diff","--","data/calendar/weeks"],cwd=ROOT,text=True)
            self.assertEqual(before,after)
            return receipt, source_bundle

    def test_monday_projection_reads_previous_week_from_pinned_main_commit(self):
        receipt, bundle=self.run_projection("2026-11-23")
        self.assertEqual(receipt["previous_week"]["week_id"],"2026-W47")
        self.assertEqual(bundle["previous"]["week_id"],"2026-W47")

    def test_weekday_projection_does_not_read_previous_week(self):
        receipt, bundle=self.run_projection("2026-11-26")
        self.assertIsNone(receipt["previous_week"])
        self.assertIsNone(bundle["previous"])

if __name__=="__main__":unittest.main()
