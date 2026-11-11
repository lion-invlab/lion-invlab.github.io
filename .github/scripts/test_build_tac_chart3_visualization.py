#!/usr/bin/env python3
import csv,gzip,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name("build_tac_chart3_visualization.py")
SPEC=importlib.util.spec_from_file_location("chart_builder",SCRIPT)
BUILDER=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(BUILDER)

def gz_csv(path,fields,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 with gzip.open(path,"wt",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 return hashlib.sha256(path.read_bytes()).hexdigest()

class ChartBuilderTests(unittest.TestCase):
 def test_native_dates_missing_values_and_hash_checks(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for sid,meta in BUILDER.SERIES_META.items():
    sd=root/"series"/sid;sd.mkdir(parents=True)
    current=[{"series_id":sid,"observation_date":"2026-01-02","value":"1.25","realtime_start":"2026-01-05","realtime_end":"9999-12-31","retrieved_at":"2026-02-01T00:00:00Z","source_method":"fixture","license_status":"review_required_before_redistribution","quality_flags":""},
             {"series_id":sid,"observation_date":"2026-01-09","value":".","realtime_start":"2026-01-12","realtime_end":"9999-12-31","retrieved_at":"2026-02-01T00:00:00Z","source_method":"fixture","license_status":"review_required_before_redistribution","quality_flags":"source_missing_value"}]
    current_sha=gz_csv(sd/"current.csv.gz",["series_id","observation_date","value","realtime_start","realtime_end","retrieved_at","source_method","license_status","quality_flags"],current)
    event_sha=gz_csv(sd/"vintage_events.csv.gz",["series_id","observation_date","vintage_date","value"],[])
    initial_sha=gz_csv(sd/"initial_release.csv.gz",["series_id","observation_date","value"],[])
    vd={"series_id":sid,"vintage_dates":["2026-01-05","2026-01-12"],"count":2,"source_endpoint":"fixture"}
    (sd/"vintage_dates.json").write_text(json.dumps(vd))
    vd_sha=hashlib.sha256((sd/"vintage_dates.json").read_bytes()).hexdigest()
    (sd/"state.json").write_text(json.dumps({"series_id":sid,"last_vintage_date":"2026-01-12","current_rows":2,"current_sha256":current_sha,"events_sha256":event_sha,"initial_release_sha256":initial_sha,"vintage_dates_sha256":vd_sha,"last_success_at":"2026-02-01T00:00:00Z","event_count":0,"initial_release_rows":0}))
   report=BUILDER.build(root)
   self.assertEqual(report["status"],"PASS")
   first_sha=report["sha256"]
   second_report=BUILDER.build(root)
   self.assertEqual(second_report["sha256"],first_sha,"No-data rebuild must be byte-identical and must not force a commit.")
   data=json.loads((root/"chart3_market_stress.json").read_text())
   self.assertEqual(len(data["series"]),4)
   self.assertEqual(data["series"][0]["observations"][1]["value"],None)
   self.assertEqual(data["series"][0]["missing_observations"],1)
   self.assertFalse(data["method"]["interpolation"])
   self.assertFalse(data["method"]["forward_fill"])

 def test_bad_hash_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for sid in BUILDER.SERIES_META:
    sd=root/"series"/sid;sd.mkdir(parents=True)
    for f in ["current.csv.gz","vintage_events.csv.gz","initial_release.csv.gz"]:(sd/f).write_bytes(b"bad")
    (sd/"vintage_dates.json").write_text('{"vintage_dates":["2026-01-01"]}')
    (sd/"state.json").write_text(json.dumps({"current_sha256":"wrong","events_sha256":"wrong","initial_release_sha256":"wrong","vintage_dates_sha256":"wrong","last_vintage_date":"2026-01-01","current_rows":0}))
   with self.assertRaises(RuntimeError):BUILDER.build(root)

if __name__=="__main__":unittest.main(verbosity=2)
