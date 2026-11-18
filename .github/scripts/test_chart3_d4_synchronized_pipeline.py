#!/usr/bin/env python3
import base64, datetime as dt, hashlib, json, tempfile, unittest, zlib
from pathlib import Path
from chart3_d4_synchronized_pipeline import run_pipeline
from build_tac_chart3_synchronized_release import decode_sp500

def varint(n):
    out=bytearray()
    while n>=128:
        out.append((n&127)|128); n >>= 7
    out.append(n)
    return bytes(out)

def baseline_compact(rows):
    packed=bytearray()
    previous_day=dt.date.fromisoformat(rows[0][0]).toordinal()
    previous_close=0
    for day,value in rows:
        ordinal=dt.date.fromisoformat(day).toordinal()
        cents=round(value*100)
        packed.extend(varint(ordinal-previous_day))
        delta=cents-previous_close
        packed.extend(varint(2*delta if delta>=0 else -2*delta-1))
        previous_day,previous_close=ordinal,cents
    return {
        "schema_version":"1.0.0","encoding":"zlib+base64","start":rows[0][0],
        "end":rows[-1][0],"rows":len(rows),"close_scale":100,
        "source_dataset_sha256":"a"*64,
        "source_details":{"long_history_source":"https://raw.githubusercontent.com/example/sp500.csv",
                          "recent_snapshot_source":"inherited compact history"},
        "payload":base64.b64encode(zlib.compress(bytes(packed))).decode("ascii")
    }

def report_data(close=7340.53, with_timestamp=True):
    source={
        "name":"Yahoo Finance｜S&P 500 Index (^SPX)現金指數歷史資料",
        "url":"https://finance.yahoo.com/quote/%5ESPX/history/?frequency=1d",
        "data_date":"2026-11-17","quote_type":"cash_index_close",
        "note":"S&P 500現金指數，非CFD。"
    }
    data={
        "report_date":"2026-11-18","trading_date":"2026-11-17",
        "global_markets":{"標普500指數":{"display":f"{close:,.2f}","source":source}}
    }
    if with_timestamp:
        data["market_data_captured_at"]="2026-11-18T05:12:44+08:00"
    return data

def fred(days):
    return {"series":[{"series_id":sid,"label":sid,
                       "observations":[{"date":d,"value":1.0} for d in days],
                       "retrieved_at":"2026-11-18T00:00:00+00:00"}
                      for sid in ("VIXCLS","NFCI","NFCICREDIT","STLFSI4")]}

class D4SynchronizedPipelineTests(unittest.TestCase):
    def setup_inputs(self,root):
        capture=root/"report.json"
        capture.write_text(json.dumps(report_data()),encoding="utf-8")
        fred_path=root/"fred.json"
        fred_path.write_text(json.dumps(fred(["2026-11-17"])),encoding="utf-8")
        baseline=root/"baseline.json"
        baseline.write_text(json.dumps(baseline_compact([
            ("2026-11-13",7561.67),("2026-11-16",7416.59)
        ])),encoding="utf-8")
        return capture,fred_path,baseline

    def test_daily_report_to_incremental_merge_and_synchronized_release(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); capture,fred_path,baseline=self.setup_inputs(root)
            result=run_pipeline(capture,fred_path,baseline,root/"daily.jsonl",
                                root/"merged.json",root/"provenance.json",
                                root/"release",root/"status.json")
            self.assertEqual(result["exit_code"],0)
            self.assertEqual(result["import_status"],"APPENDED")
            self.assertEqual(result["status"]["status"],"PUBLISHED")
            rows=decode_sp500(json.loads((root/"merged.json").read_text()))
            self.assertEqual(rows[-1]["date"],"2026-11-17")
            self.assertEqual(rows[-1]["value"],7340.53)
            manifest=json.loads((root/"release"/"active_manifest.json").read_text())
            self.assertEqual(manifest["common_observation_date"],"2026-11-17")

    def test_repeated_daily_capture_is_idempotent_and_no_new_release(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); capture,fred_path,baseline=self.setup_inputs(root)
            args=(capture,fred_path,baseline,root/"daily.jsonl",root/"merged.json",
                  root/"provenance.json",root/"release",root/"status.json")
            first=run_pipeline(*args)
            second=run_pipeline(*args)
            self.assertEqual(first["import_status"],"APPENDED")
            self.assertEqual(second["import_status"],"NOOP_IDENTICAL_OBSERVATION")
            self.assertEqual(second["status"]["status"],"NO_NEW_COMMON_DATE")
            self.assertEqual(len((root/"daily.jsonl").read_text().splitlines()),1)

    def test_missing_capture_timestamp_fails_before_append(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); capture,fred_path,baseline=self.setup_inputs(root)
            capture.write_text(json.dumps(report_data(with_timestamp=False)))
            result=run_pipeline(capture,fred_path,baseline,root/"daily.jsonl",
                                root/"merged.json",root/"provenance.json",
                                root/"release",root/"status.json")
            self.assertEqual(result["exit_code"],2)
            self.assertEqual(result["status"]["status"],"BLOCKED_VALIDATION_FAILURE")
            self.assertFalse((root/"daily.jsonl").exists())
            self.assertFalse((root/"release"/"active_manifest.json").exists())

    def test_missing_fred_blocks_before_any_append(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); capture,fred_path,baseline=self.setup_inputs(root)
            result=run_pipeline(capture,root/"missing-fred.json",baseline,root/"daily.jsonl",
                                root/"merged.json",root/"provenance.json",
                                root/"release",root/"status.json")
            self.assertEqual(result["exit_code"],2)
            self.assertEqual(result["status"]["status"],"BLOCKED_MISSING_INPUT")
            self.assertFalse((root/"daily.jsonl").exists())

    def test_conflicting_same_day_close_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); capture,fred_path,baseline=self.setup_inputs(root)
            args=(capture,fred_path,baseline,root/"daily.jsonl",root/"merged.json",
                  root/"provenance.json",root/"release",root/"status.json")
            first=run_pipeline(*args)
            changed=report_data(close=7341.00)
            capture.write_text(json.dumps(changed))
            second=run_pipeline(*args)
            self.assertEqual(first["status"]["status"],"PUBLISHED")
            self.assertEqual(second["exit_code"],2)
            self.assertEqual(second["status"]["status"],"BLOCKED_VALIDATION_FAILURE")
            manifest=json.loads((root/"release"/"active_manifest.json").read_text())
            self.assertEqual(manifest["common_observation_date"],"2026-11-17")
            self.assertEqual(len((root/"daily.jsonl").read_text().splitlines()),1)

if __name__=="__main__":
    unittest.main()
