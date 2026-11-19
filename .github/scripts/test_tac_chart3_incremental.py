#!/usr/bin/env python3
import csv, gzip, importlib.util, json, tempfile, unittest
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

    def test_sparse_output_type3_can_have_zero_rows_with_nonzero_count(self):
        original=INC.request_json
        def fake(endpoint,params,key,retries=5):
            return {"count":2609,"observations":[]}
        INC.request_json=fake
        try:
            rows=INC.fetch_all_observations({"series_id":"NFCI","output_type":3},"fake",validate_count=False)
        finally:INC.request_json=original
        self.assertEqual(rows,[])

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

    def test_initial_release_skips_when_no_new_vintages(self):
        original=INC.request_json
        def fail(*args,**kwargs):raise AssertionError("No API request expected without new vintage dates")
        INC.request_json=fail
        try:rows=INC.fetch_initial_release("VIXCLS","fake","2026-02-20T00:00:00Z",[])
        finally:INC.request_json=original
        self.assertEqual(rows,[])

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

    def test_release_schedule_noop_ignores_retrieval_timestamps(self):
        previous={"source":"FRED official release calendar","retrieved_at":"2026-11-14T00:00:00Z","series":[
            {"series_id":"VIXCLS","release_id":200,"release_name":"CBOE Market Statistics","next_release_date":"2026-11-16","source":"FRED API series/release + release/dates","retrieved_at":"2026-11-14T00:00:00Z"}
        ]}
        refreshed={"source":"FRED official release calendar","retrieved_at":"2026-11-16T00:00:00Z","series":[
            {"series_id":"VIXCLS","release_id":200,"release_name":"CBOE Market Statistics","next_release_date":"2026-11-16","source":"FRED API series/release + release/dates","retrieved_at":"2026-11-16T00:00:00Z"}
        ]}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"release_schedule.json"
            original=json.dumps(previous,ensure_ascii=False,indent=2)
            path.write_text(original,encoding="utf-8")
            changed=INC.write_release_schedule_if_changed(path,refreshed)
            self.assertFalse(changed)
            self.assertEqual(path.read_text(encoding="utf-8"),original)

    def test_release_schedule_fact_change_is_written(self):
        previous={"source":"FRED official release calendar","retrieved_at":"2026-11-14T00:00:00Z","series":[
            {"series_id":"NFCI","release_id":221,"release_name":"Chicago Fed National Financial Conditions Index","next_release_date":"2026-11-18","source":"FRED API series/release + release/dates","retrieved_at":"2026-11-14T00:00:00Z"}
        ]}
        refreshed={"source":"FRED official release calendar","retrieved_at":"2026-11-16T00:00:00Z","series":[
            {"series_id":"NFCI","release_id":221,"release_name":"Chicago Fed National Financial Conditions Index","next_release_date":"2026-11-19","source":"FRED API series/release + release/dates","retrieved_at":"2026-11-16T00:00:00Z"}
        ]}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"release_schedule.json"
            path.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding="utf-8")
            changed=INC.write_release_schedule_if_changed(path,refreshed)
            self.assertTrue(changed)
            saved=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["series"][0]["next_release_date"],"2026-11-19")
            self.assertEqual(saved["retrieved_at"],"2026-11-16T00:00:00Z")


    def test_current_freshness_accepts_recent_daily_and_weekly_observations(self):
        self.assertEqual(INC.validate_current_freshness("VIXCLS",[{"date":"2026-11-17","value":"25.46"}],"2026-11-19")["age_days"],2)
        self.assertEqual(INC.validate_current_freshness("NFCI",[{"date":"2026-11-13","value":"-0.478"}],"2026-11-19")["age_days"],6)
        self.assertEqual(INC.validate_current_freshness("NFCICREDIT",[{"date":"2026-11-13","value":"-0.013"}],"2026-11-19")["age_days"],6)
        self.assertEqual(INC.validate_current_freshness("STLFSI4",[{"date":"2026-11-13","value":"-0.8655"}],"2026-11-19")["age_days"],6)

    def test_current_freshness_rejects_stale_daily_and_weekly_observations(self):
        with self.assertRaises(RuntimeError):
            INC.validate_current_freshness("VIXCLS",[{"date":"2026-11-09","value":"25.46"}],"2026-11-19")
        for sid in ("NFCI","NFCICREDIT","STLFSI4"):
            with self.assertRaises(RuntimeError):
                INC.validate_current_freshness(sid,[{"date":"2026-10-30","value":"-0.4"}],"2026-11-19")

    def test_current_freshness_rejects_missing_and_future_observations(self):
        with self.assertRaises(RuntimeError):
            INC.validate_current_freshness("VIXCLS",[{"date":"2026-11-18","value":"."}],"2026-11-19")
        with self.assertRaises(RuntimeError):
            INC.validate_current_freshness("VIXCLS",[{"date":"2026-11-20","value":"25.0"}],"2026-11-19")

    def test_current_freshness_rejects_unconfigured_series(self):
        with self.assertRaises(RuntimeError):
            INC.validate_current_freshness("SP500",[{"date":"2026-11-19","value":"6800"}],"2026-11-19")

if __name__=="__main__":unittest.main(verbosity=2)
