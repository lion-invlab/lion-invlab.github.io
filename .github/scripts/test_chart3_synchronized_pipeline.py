#!/usr/bin/env python3
import json, tempfile, unittest
from pathlib import Path
from prepare_sp500_research_import import DEFAULT_COMPACT_PATH, DEFAULT_PROVENANCE_PATH
from build_tac_chart3_synchronized_release import decode_sp500
from test_run_tac_chart3_synchronized_release import fred
from chart3_synchronized_pipeline import run_pipeline

URL = "https://www.investing.com/indices/us-spx-500-historical-data"
STAMP = "2026-11-18T12:00:00+00:00"

class PipelineTests(unittest.TestCase):
    def test_pipeline_imports_and_publishes_using_one_entry_point(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); csv=root/"sp500.csv"
            csv.write_text('Date,Price\n"Nov 12, 2026","6,700.25"\n"Nov 13, 2026","6,720.50"\n',encoding="utf-8")
            f=root/"fred.json"; f.write_text(json.dumps(fred(["2026-11-12","2026-11-13"])))
            r=run_pipeline(csv,URL,STAMP,f,root/"compact.json",root/"prov.json",root/"release",root/"status.json")
            self.assertEqual(r["release_exit_code"],0); self.assertEqual(r["status"]["status"],"PUBLISHED")
            m=json.loads((root/"release"/"active_manifest.json").read_text())
            self.assertEqual(m["common_observation_date"],"2026-11-13")
            self.assertEqual(decode_sp500(json.loads((root/"compact.json").read_text()))[-1]["value"],6720.5)
    def test_no_common_date_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); csv=root/"spx.csv"
            csv.write_text('Date,Price\n"Nov 13, 2026",6720.50\n',encoding="utf-8")
            f=root/"fred.json"; f.write_text(json.dumps(fred(["2026-11-12"])))
            r=run_pipeline(csv,URL,STAMP,f,root/"c.json",root/"p.json",root/"release",root/"status.json")
            self.assertEqual(r["release_exit_code"],2)
            self.assertEqual(r["status"]["status"],"BLOCKED_VALIDATION_FAILURE")
            self.assertFalse((root/"release"/"active_manifest.json").exists())
    def test_missing_fred_blocks_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); csv=root/"spx.csv"
            csv.write_text('Date,Price\n"Nov 13, 2026",6720.50\n',encoding="utf-8")
            r=run_pipeline(csv,URL,STAMP,root/"missing.json",root/"c.json",root/"p.json",root/"release",root/"status.json")
            self.assertEqual(r["release_exit_code"],2); self.assertIsNone(r["import"])
            self.assertFalse((root/"c.json").exists())
            self.assertEqual(r["status"]["status"],"BLOCKED_MISSING_INPUT")
    def test_invalid_source_fails_before_import_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); csv=root/"spx.csv"
            csv.write_text('Date,Price\n"Nov 13, 2026",6720.50\n',encoding="utf-8")
            f=root/"fred.json"; f.write_text(json.dumps(fred(["2026-11-13"])))
            with self.assertRaisesRegex(ValueError,"Investing.com"):
                run_pipeline(csv,"https://example.com/spx.csv",STAMP,f,root/"c.json",root/"p.json",root/"release",root/"status.json")
            self.assertFalse((root/"c.json").exists())
    def test_default_paths_match_investing_csv_importer(self):
        self.assertEqual(DEFAULT_COMPACT_PATH.as_posix(),"data/tac-chart3/sp500_investing_daily.compact.json")
        self.assertEqual(DEFAULT_PROVENANCE_PATH.as_posix(),"data/tac-chart3/sp500_investing_daily.provenance.json")

if __name__=="__main__": unittest.main()
