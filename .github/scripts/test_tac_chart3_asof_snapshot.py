#!/usr/bin/env python3
import csv,gzip,importlib.util,tempfile,unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name("build_tac_chart3_asof_snapshot.py")
SPEC=importlib.util.spec_from_file_location("chart3_asof",SCRIPT)
ASOF=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ASOF)

FIELDS=["series_id","observation_date","vintage_date","value","value_status","release_date","release_date_status","source_method","source_chunk","artifact_created_at","license_status"]
def write_events(path,rows):
    with gzip.open(path,"wt",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
def ev(obs,vin,val):
    return {"series_id":"VIXCLS","observation_date":obs,"vintage_date":vin,"value":val,
      "value_status":"source_missing_value" if val=="." else "source_value","release_date":"",
      "release_date_status":"exact_release_date_not_supplied_by_observations_endpoint",
      "source_method":"fixture","source_chunk":"fixture","artifact_created_at":"2026-01-30T00:00:00Z",
      "license_status":"review_required_before_redistribution"}

class AsOfSnapshotTests(unittest.TestCase):
    def test_strict_prior_vintage_cutoff_and_no_future_observations(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"events.csv.gz"
            write_events(path,[
              ev("2026-01-01","2026-01-05","10"),
              ev("2026-01-01","2026-01-12","12"),
              ev("2026-01-08","2026-01-12","20"),
              ev("2026-01-15","2026-01-20","."),
              ev("2026-01-30","2026-01-12","99")
            ])
            result=ASOF.reconstruct_series(path,"VIXCLS","2026-01-20")
            values={x["date"]:x for x in result["observations"]}
            self.assertEqual(values["2026-01-01"]["value"],12.0)
            self.assertEqual(values["2026-01-08"]["value"],20.0)
            self.assertNotIn("2026-01-15",values,"Same-day vintage must be excluded.")
            self.assertNotIn("2026-01-30",values,"Future observation date must be excluded.")
            self.assertEqual(result["latest_available_vintage_before_as_of"],"2026-01-12")

    def test_dot_missing_event_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"events.csv.gz"
            write_events(path,[ev("2026-01-01","2026-01-05",".")])
            result=ASOF.reconstruct_series(path,"VIXCLS","2026-01-06")
            self.assertEqual(result["observations"][0]["value"],None)
            self.assertEqual(result["missing_observations"],1)
            self.assertEqual(result["observations"][0]["value_status"],"source_missing_value")

    def test_unsorted_or_duplicate_event_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"events.csv.gz"
            write_events(path,[ev("2026-01-01","2026-01-12","12"),ev("2026-01-01","2026-01-05","10")])
            with self.assertRaises(RuntimeError):ASOF.reconstruct_series(path,"VIXCLS","2026-01-20")

    def test_as_of_date_resolves_after_latest_vintage_across_all_series(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            dates={"VIXCLS":"2026-11-09","NFCI":"2026-11-04","NFCICREDIT":"2026-11-04","STLFSI4":"2026-11-04"}
            for sid,last in dates.items():
                sd=root/"series"/sid;sd.mkdir(parents=True)
                (sd/"vintage_dates.json").write_text(__import__("json").dumps({"vintage_dates":["2026-01-01",last]}))
            self.assertEqual(ASOF.resolve_as_of_latest_plus_one(root),"2026-11-10")

    def test_current_snapshot_reconciliation(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"current.csv.gz"
            with gzip.open(path,"wt",encoding="utf-8-sig",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["observation_date","value"]);w.writeheader()
                w.writerow({"observation_date":"2026-01-01","value":"12"})
                w.writerow({"observation_date":"2026-01-08","value":"20"})
            observations=[{"date":"2026-01-01","value_raw":"12"},{"date":"2026-01-08","value_raw":"20"}]
            result=ASOF.reconcile_current_snapshot(path,observations)
            self.assertEqual(result["status"],"PASS")
            observations[0]["value_raw"]="11"
            with self.assertRaises(RuntimeError):ASOF.reconcile_current_snapshot(path,observations)

if __name__=="__main__":unittest.main(verbosity=2)
