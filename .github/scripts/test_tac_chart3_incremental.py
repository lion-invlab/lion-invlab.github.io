#!/usr/bin/env python3
import csv, gzip, importlib.util, tempfile, unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name("tac_chart3_incremental.py")
SPEC=importlib.util.spec_from_file_location("tac_chart3_incremental",SCRIPT)
INC=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(INC)

def event(date,vintage,value):
    return {"series_id":"VIXCLS","observation_date":date,"vintage_date":vintage,"value":value,
      "value_status":"source_missing_value" if value=="." else "source_value","release_date":"",
      "release_date_status":"exact_release_date_not_supplied_by_observations_endpoint",
      "source_method":"FRED API output_type=3 (new_and_revised_only)","source_chunk":"fixture",
      "artifact_created_at":"2026-11-11T00:00:00Z","license_status":"review_required_before_redistribution"}

class IncrementalTests(unittest.TestCase):
    def test_vintage_overlap(self):
        dates=["2026-01-01","2026-01-08","2026-01-15","2026-01-22","2026-01-29","2026-02-05","2026-02-12"]
        self.assertEqual(INC.choose_vintages(dates,"2026-02-05",5),dates[1:])

    def test_dot_is_a_real_missing_value_event(self):
        payload={"observations":[{"date":"2026-02-01","VIXCLS_20260205":".","VIXCLS_20260212":"20.1","VIXCLS_20260219":""}]}
        rows=INC.parse_event_matrix("VIXCLS",payload,"2026-02-20T00:00:00Z","fixture")
        self.assertEqual([r["value"] for r in rows],[".","20.1"])
        self.assertEqual(rows[0]["value_status"],"source_missing_value")

    def test_idempotent_merge_and_conflict_guard(self):
        with tempfile.TemporaryDirectory() as td:
            old=Path(td)/"old.csv.gz";merged=Path(td)/"merged.csv.gz"
            INC.write_gzip_csv(old,INC.EVENT_FIELDS,[event("2026-02-01","2026-02-05","19.8")])
            stats=INC.merge_event_gzip(old,[event("2026-02-01","2026-02-05","19.8"),event("2026-02-01","2026-02-12","20.1")],merged)
            self.assertEqual(stats,{"added":1,"overlap_duplicates":1})
            with gzip.open(merged,"rt",encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),2)
            with self.assertRaises(RuntimeError):
                INC.merge_event_gzip(old,[event("2026-02-01","2026-02-05","20.0")],merged)

    def test_no_change_merge_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            old=Path(td)/"old.csv.gz";merged=Path(td)/"merged.csv.gz"
            INC.write_gzip_csv(old,INC.EVENT_FIELDS,[event("2026-02-01","2026-02-05",".")])
            INC.merge_event_gzip(old,[],merged)
            self.assertEqual(INC.sha_file(old),INC.sha_file(merged))

if __name__=="__main__":unittest.main(verbosity=2)
