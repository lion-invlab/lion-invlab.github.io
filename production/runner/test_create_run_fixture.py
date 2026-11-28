#!/usr/bin/env python3
import unittest
from datetime import date
from create_run_fixture import build, write_run_files, report_cutoff_taipei, report_target_date, report_template_key, stable_run_id

class RunFixtureFactoryTests(unittest.TestCase):
    def test_creates_fresh_blank_first_44_row_fixture(self):
        result=build(date(2026,11,26),"TAC-2026-11-26-test-1",date(2026,11,25))
        data=result["market_fixture"]
        self.assertEqual(data["stage2_market_bootstrap"]["preexisting_market_values_used"],False)
        self.assertEqual(data["stage2_market_bootstrap"]["row_count"],44)
        self.assertEqual(data["trading_date"],"2026-11-25")
        self.assertEqual(data["summary"],"")
        self.assertEqual(data["focus_news"],[])
        for group in ("global_markets","bonds","fx","energy","metals","risk"):
            for item in data[group].values():
                self.assertEqual(item["display"],"待擷取")
                self.assertNotIn("change_basis_points",item)
                self.assertNotIn("change_points",item)
                self.assertNotIn("band",item)
                source=item["source"]
                self.assertEqual(source["data_date"],"2026-11-25")
                self.assertEqual(source["verification_status"],"PENDING")
                for stale in ("observed_date","cross_check","official_settlement_cross_check","volume","close","observation_bundle_blob_sha"):
                    self.assertNotIn(stale,source)
        self.assertEqual(len(data["global_markets"]),17)
        self.assertEqual(len(data["sectors"]),11)
        self.assertEqual(result["run_context"]["mother"]["key"],"weekdays")
        governance=result["run_context"]["governance"]
        self.assertEqual(governance["commit_sha"],result["run_context"]["main_commit_sha"])
        self.assertIn("production/config/builder-approval.json",governance["blob_shas"])
        self.assertIn("production/runner/run_stage5.py",governance["blob_shas"])
        self.assertIn("production/runner/stage_wr_preflight.py",governance["blob_shas"])
        self.assertTrue(result["run_context"]["stage_wr_preflight"]["wr_loaded"])
        self.assertEqual(len(result["run_context"]["calendar_read_receipts"]),1)


    def test_writes_immutable_stage1_fixture_and_working_copy(self):
        import hashlib, json, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            report=date(2026,11,27); run_id="TAC-2026-11-27-test-immutable-1"
            result=build(report,run_id,date(2026,11,26))
            output=Path(tmp)/"production"/"runs"/run_id
            receipt=write_run_files(output,run_id,result,Path(tmp))
            stage1=output/"stage1-fixture.json"; working=output/"report-data.json"
            self.assertEqual(stage1.read_bytes(),working.read_bytes())
            self.assertEqual(hashlib.sha256(stage1.read_bytes()).hexdigest(),receipt["fixture_sha256"])
            self.assertEqual(receipt["fixture_path"],f"production/runs/{run_id}/stage1-fixture.json")
            self.assertEqual(receipt["working_fixture_path"],f"production/runs/{run_id}/report-data.json")
            self.assertEqual(receipt["screenshot_fields"],0)
            state=json.loads((output/"run-state.json").read_text())
            self.assertEqual(state["run_id"],run_id)
            self.assertEqual(state["stages"]["STAGE_1"]["status"],"PASS")
            self.assertEqual(state["stages"]["STAGE_2"]["status"],"READY")
            self.assertEqual(state["stages"]["STAGE_1"]["output_sha256"],hashlib.sha256((output/"stage1-receipt.json").read_bytes()).hexdigest())
            self.assertEqual(result["run_context"]["screenshot_input"]["status"],"NOT_READ_AT_STAGE1")
            working_data=json.loads(working.read_text())
            working_data["run_metadata"]["retry_marker"]="changed"
            working.write_text(json.dumps(working_data),encoding="utf-8")
            self.assertEqual(hashlib.sha256(stage1.read_bytes()).hexdigest(),receipt["fixture_sha256"])

    def test_records_explicit_superseded_run_without_mutating_it(self):
        result=build(date(2026,11,27),"TAC-2026-11-27-new-1",date(2026,11,26),supersedes_run_id="TAC-2026-11-27-old-1")
        self.assertEqual(result["run_context"]["supersedes_run_id"],"TAC-2026-11-27-old-1")

    def test_legacy_runs_are_recorded_but_never_reused_or_mutated(self):
        import json, tempfile
        from pathlib import Path
        import create_run_fixture as factory
        with tempfile.TemporaryDirectory() as tmp:
            runs_root=Path(tmp)
            legacy=runs_root/"TAC-2026-11-27-legacy-1"
            legacy.mkdir()
            (legacy/"run-context.json").write_text(json.dumps({"run_id":legacy.name}),encoding="utf-8")
            protected=legacy/"stage1-fixture.json"
            protected.write_text("LEGACY DATA MUST NOT BE READ OR REUSED",encoding="utf-8")
            original_runs=factory.RUNS
            factory.RUNS=runs_root
            try:
                result=factory.build(date(2026,11,27),"TAC-2026-11-27-new-1",date(2026,11,26))
            finally:
                factory.RUNS=original_runs
            self.assertEqual(result["run_context"]["legacy_prior_run_ids"],[legacy.name])
            self.assertEqual(protected.read_text(encoding="utf-8"),"LEGACY DATA MUST NOT BE READ OR REUSED")
            self.assertFalse((legacy/"run-state.json").exists())

    def test_workflow_retry_attempt_does_not_change_run_id(self):
        self.assertEqual(stable_run_id(date(2026,11,30),"46069359215"),"TAC-2026-11-30-46069359215")
        self.assertEqual(stable_run_id(date(2026,11,30),"TAC-2026-11-30-46069359215"),"TAC-2026-11-30-46069359215")

    def test_report_cutoff_tracks_new_york_dst(self):
        self.assertEqual(report_cutoff_taipei(date(2026,11,30)),"2026-11-28 05:25")
        self.assertEqual(report_cutoff_taipei(date(2026,7,6)),"2026-07-04 04:25")

    def test_defaults_to_previous_calendar_day_for_thursday_market_holiday(self):
        result=build(date(2026,11,27),"TAC-2026-11-27-test-default")
        self.assertEqual(result["run_context"]["trading_date"],"2026-11-26")
        for group in ("global_markets","bonds","fx","energy","metals","risk"):
            for item in result["market_fixture"][group].values():
                self.assertEqual(item["source"]["data_date"],"2026-11-26")
        for source in result["market_fixture"]["sector_sources"].values():
            self.assertEqual(source["data_date"],"2026-11-26")

    def test_monday_targets_previous_friday(self):
        result=build(date(2026,11,23),"TAC-2026-11-23-test-default")
        self.assertEqual(result["run_context"]["trading_date"],"2026-11-20")
        self.assertEqual(len(result["run_context"]["calendar_read_receipts"]),2)

    def test_saturday_production_uses_monday_report_and_monday_mother(self):
        report=date(2026,11,30)
        self.assertEqual(report_target_date(report),date(2026,11,27))
        self.assertEqual(report_template_key(report),"monday")
        self.assertEqual(report_cutoff_taipei(report),"2026-11-28 05:25")

    def test_rejects_saturday_report_date(self):
        with self.assertRaises(ValueError):
            build(date(2026,11,28),"TAC-2026-11-28-test-1",date(2026,11,27))

if __name__=="__main__":
    unittest.main()
