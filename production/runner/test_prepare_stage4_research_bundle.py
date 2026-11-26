import json, tempfile, unittest, hashlib
from pathlib import Path
from prepare_stage4_research_bundle import build_bundle, market_digest

class Stage4ResearchBundleTests(unittest.TestCase):
    def test_builds_exact_run_bound_bundle_and_marks_unresolved_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/"TAC-2026-11-26-test-1"; run.mkdir()
            context={"run_id":run.name,"report_date":"2026-11-26","trading_date":"2026-11-25","main_commit_sha":"abc"}
            data={"report_date":"2026-11-26","trading_date":"2026-11-25",
                  "global_markets":{"標普500指數":{"display":"100","change_display":"+1.0%","source":{"verification_status":"VERIFIED","data_date":"2026-11-25","quote_type":"cash_index_close","url":"https://hk.investing.com/indices/us-spx-500-historical-data"}}},
                  "sectors":{},"sector_sources":{},"bonds":{},"fx":{},"energy":{},"metals":{},
                  "risk":{"fear_greed":{"display":"待核實","change_display":"待核實","source":{"verification_status":"PENDING"}}},
                  "fedwatch":{"status":"PENDING"}}
            for name,doc in {
                "run-context.json":context,"stage1-receipt.json":{"status":"PASS","run_id":run.name},"report-data.json":data,
                "stage2-market-snapshot-receipt.json":{"status":"PARTIAL"},
                "stage2-run-summary.json":{"run_id":run.name,"market_snapshot_sha256":market_digest(data)},
                "stage3-calendar-receipt.json":{"status":"PASS","run_id":run.name,"main_commit_sha":"abc"},
                "calendar-source-bundle.json":{},"calendar.json":{"events":[]},"earnings.json":{"events":[]},
                "last-week-calendar.json":{"events":[]},"last-week-earnings.json":{"events":[]},
                "market-history-browser-observations.json":{},"market-source-verification-manifest.json":{},
                "market-snapshot-audit.json":{}
            }.items():
                (run/name).write_text(json.dumps(doc),encoding="utf-8")
            bundle=build_bundle(run,root)
            self.assertEqual(bundle["run_id"],run.name)
            self.assertEqual(bundle["market_snapshot"]["row_count"],2)
            self.assertEqual(len(bundle["market_snapshot"]["unresolved_rows"]),1)
            self.assertEqual(bundle["market_snapshot_sha256"],market_digest(data))
            self.assertEqual(bundle["editorial_contract"]["summary_points"],3)
    def test_rejects_cross_run_stage3_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/"TAC-2026-11-26-test-1"; run.mkdir()
            data={"report_date":"2026-11-26","trading_date":"2026-11-25"}
            context={"run_id":run.name,"report_date":"2026-11-26","trading_date":"2026-11-25","main_commit_sha":"abc"}
            for name,doc in {
                "run-context.json":context,"report-data.json":data,
                "stage2-market-snapshot-receipt.json":{"status":"PASS"},
                "stage2-run-summary.json":{"run_id":run.name,"market_snapshot_sha256":market_digest(data)},
                "stage3-calendar-receipt.json":{"status":"PASS","run_id":"other","main_commit_sha":"abc"}
            }.items():
                (run/name).write_text(json.dumps(doc),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Stage 3 receipt"):
                build_bundle(run,root)

if __name__=="__main__":unittest.main()
