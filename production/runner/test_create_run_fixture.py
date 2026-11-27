#!/usr/bin/env python3
import unittest
from datetime import date
from create_run_fixture import build, write_run_files

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
            self.assertEqual(result["run_context"]["screenshot_input"]["status"],"NOT_READ_AT_STAGE1")
            working_data=json.loads(working.read_text())
            working_data["run_metadata"]["retry_marker"]="changed"
            working.write_text(json.dumps(working_data),encoding="utf-8")
            self.assertEqual(hashlib.sha256(stage1.read_bytes()).hexdigest(),receipt["fixture_sha256"])

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

    def test_rejects_weekend_report_date(self):
        with self.assertRaises(ValueError):
            build(date(2026,11,28),"TAC-2026-11-28-test-1",date(2026,11,27))

if __name__=="__main__":
    unittest.main()
