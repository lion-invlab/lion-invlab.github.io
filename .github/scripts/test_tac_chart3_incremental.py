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
    def test_fred_observations_pagination_reads_all_pages(self):
        original=INC.request_json
        calls=[]
        first=[{"date":f"2000-01-{(i%28)+1:02d}","value":"1"} for i in range(100000)]
        second=[{"date":"2000-02-01","value":"2"},{"date":"2000-02-02","value":"3"}]
        def fake(endpoint,params,key,retries=5):
            calls.append(params["offset"])
            return {"count":100002,"observations":first if params["offset"]==0 else second}
        INC.request_json=fake
        try:rows=INC.fetch_all_observations({"series_id":"VIXCLS","output_type":1},"fake")
        finally:INC.request_json=original
        self.assertEqual(calls,[0,100000])
        self.assertEqual(len(rows),100002)

    def test_fred_observations_pagination_fails_on_truncation(self):
        original=INC.request_json
        def fake(endpoint,params,key,retries=5):
            return {"count":100001,"observations":[{"date":"2000-01-01","value":"1"}]}
        INC.request_json=fake
        try:
            with self.assertRaises(RuntimeError):
                INC.fetch_all_observations({"series_id":"VIXCLS","output_type":1},"fake")
        finally:INC.request_json=original

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

    def test_initial_release_query_uses_vintage_window(self):
        original=INC.request_json
        calls=[]
        def fake(endpoint,params,key,retries=5):
            calls.append(params.copy())
            return {"observations":[{"date":"2026-02-01","value":"19.8","realtime_start":"2026-02-05","realtime_end":"9999-12-31"}]}
        INC.request_json=fake
        try:
            rows=INC.fetch_initial_release("VIXCLS","fake","2026-02-20T00:00:00Z",["2026-02-05","2026-02-12"])
        finally:
            INC.request_json=original
        self.assertEqual(len(calls),4)
        self.assertTrue(all(c["realtime_start"]=="2026-02-05" and c["realtime_end"]=="2026-02-12" and c["output_type"]==4 for c in calls))
        self.assertEqual(rows[0]["value"],"19.8")

    def test_initial_release_additive_merge_and_conflict_guard(self):
        fields=INC.INITIAL_FIELDS
        def row(date,value):
            return {"series_id":"VIXCLS","observation_date":date,"value":value,"realtime_start":"2026-02-05","realtime_end":"9999-12-31","release_date":"","release_date_status":"exact_release_date_not_supplied_by_observations_endpoint","retrieved_at":"2026-02-20T00:00:00Z","source_method":"FRED API output_type=4 initial release only","license_status":"review_required_before_redistribution"}
        with tempfile.TemporaryDirectory() as td:
            old=Path(td)/"old.csv.gz";merged=Path(td)/"merged.csv.gz"
            INC.write_gzip_csv(old,fields,[row("2026-02-01","19.8")])
            added,_,count=INC.merge_initial_release(old,[row("2026-02-01","19.8"),row("2026-02-08","20.1")],merged)
            self.assertEqual((added,count),(1,2))
            with self.assertRaises(RuntimeError):
                INC.merge_initial_release(old,[row("2026-02-01","20.0")],merged)

    def test_no_change_merge_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            old=Path(td)/"old.csv.gz";merged=Path(td)/"merged.csv.gz"
            INC.write_gzip_csv(old,INC.EVENT_FIELDS,[event("2026-02-01","2026-02-05",".")])
            INC.merge_event_gzip(old,[],merged)
            self.assertEqual(INC.sha_file(old),INC.sha_file(merged))

if __name__=="__main__":unittest.main(verbosity=2)
