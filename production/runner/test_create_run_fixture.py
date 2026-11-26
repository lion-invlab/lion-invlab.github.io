#!/usr/bin/env python3
import unittest
from datetime import date
from create_run_fixture import build

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

    def test_rejects_weekend_report_date(self):
        with self.assertRaises(ValueError):
            build(date(2026,11,28),"TAC-2026-11-28-test-1",date(2026,11,27))

if __name__=="__main__":
    unittest.main()
