#!/usr/bin/env python3
import base64, datetime as dt, hashlib, json, tempfile, unittest, zlib
from pathlib import Path
from merge_sp500_existing_history_with_d4_incremental import merge
from build_tac_chart3_synchronized_release import decode_sp500, build_candidate

def varint(n):
    out=bytearray()
    while n>=128:
        out.append((n&127)|128); n >>= 7
    out.append(n)
    return bytes(out)

def compact(rows):
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
        "source_details":{
            "long_history_source":"https://raw.githubusercontent.com/example/sp500.csv",
            "recent_snapshot_source":"Previously validated compact history",
            "boundary_overlap_date":"2026-11-16"
        },
        "payload":base64.b64encode(zlib.compress(bytes(packed))).decode("ascii")
    }

def record(day, close):
    body={
        "schema_version":"1.0","series_id":"SP500","instrument":"S&P 500 cash price index",
        "report_date":"2026-11-18","observation_date":day,"close":close,
        "source_name":"Yahoo Finance ^SPX cash index",
        "source_url":"https://finance.yahoo.com/quote/%5ESPX/history/",
        "source_note":"S&P 500 cash index; non-CFD",
        "retrieved_at":"2026-11-18T05:15:00+08:00",
        "retrieval_method":"tac_report_verified_market_close_source_record"
    }
    body["record_sha256"]=hashlib.sha256(json.dumps(
        {k:v for k,v in body.items() if k!="record_sha256"},
        ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return body

def fred(dates):
    return {"series":[{"series_id":sid,"label":sid,"observations":[{"date":d,"value":1.0} for d in dates]}
                      for sid in ("VIXCLS","NFCI","NFCICREDIT","STLFSI4")]}

class MergeExistingHistoryTests(unittest.TestCase):
    def test_preserves_baseline_and_appends_new_close_with_range_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            baseline=root/"baseline.json"
            inc=root/"daily.jsonl"
            compact_out=root/"merged.json"
            prov_out=root/"merged.provenance.json"
            baseline.write_text(json.dumps(compact([
                ("2026-11-13",7561.67),("2026-11-16",7416.59)
            ])))
            inc.write_text(json.dumps(record("2026-11-17",7340.53))+"\n")
            result=merge(baseline,inc,compact_out,prov_out)
            packed=json.loads(compact_out.read_text())
            prov=json.loads(prov_out.read_text())
            rows=decode_sp500(packed)
            self.assertEqual(result["baseline_rows"],2)
            self.assertEqual(result["incremental_rows"],1)
            self.assertEqual([(x["date"],x["value"]) for x in rows],
                             [("2026-11-13",7561.67),("2026-11-16",7416.59),("2026-11-17",7340.53)])
            self.assertEqual(prov["historical_baseline"]["start"],"2026-11-13")
            self.assertEqual(prov["historical_baseline"]["end"],"2026-11-16")
            self.assertEqual(prov["observations"][0]["source_name"],"Yahoo Finance ^SPX cash index")
            candidate=build_candidate(fred(["2026-11-17"]),packed,prov)
            sp=next(x for x in candidate["series"] if x["series_id"]=="SP500")
            self.assertEqual(sp["source_provenance_mode"],"historical_baseline_range_plus_per_observation")
            self.assertEqual(sp["observations"][0]["provenance_granularity"],"dataset_range")
            self.assertIsNone(sp["observations"][0]["retrieved_at"])
            self.assertEqual(sp["observations"][-1]["source_name"],"Yahoo Finance ^SPX cash index")

    def test_merges_against_real_existing_1927_to_2026_baseline(self):
        baseline_path = Path("data/tac-chart3/sp500_daily_close_1927-2026.compact.json")
        if not baseline_path.is_file():
            self.skipTest("Existing historical compact baseline is not present in this checkout")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            inc=root/"daily.jsonl"
            compact_out=root/"merged.json"
            prov_out=root/"merged.provenance.json"
            inc.write_text(json.dumps(record("2026-11-17",7340.53))+"\n")
            result=merge(baseline_path,inc,compact_out,prov_out)
            baseline=json.loads(baseline_path.read_text())
            merged=json.loads(compact_out.read_text())
            provenance=json.loads(prov_out.read_text())
            rows=decode_sp500(merged)
            self.assertEqual(result["baseline_rows"],baseline["rows"])
            self.assertEqual(result["incremental_rows"],1)
            self.assertEqual(rows[0]["date"],"1927-12-30")
            self.assertEqual(rows[-2]["date"],"2026-11-10")
            self.assertEqual(rows[-1]["date"],"2026-11-17")
            self.assertEqual(rows[-1]["value"],7340.53)
            self.assertEqual(provenance["historical_baseline"]["source_details"],baseline["source_details"])
            self.assertEqual(provenance["historical_baseline"]["start"],"1927-12-30")
            self.assertEqual(provenance["historical_baseline"]["end"],"2026-11-10")

    def test_rejects_incremental_overlap_with_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); baseline=root/"baseline.json"; inc=root/"daily.jsonl"
            baseline.write_text(json.dumps(compact([("2026-11-16",7416.59)])))
            inc.write_text(json.dumps(record("2026-11-16",7416.59))+"\n")
            with self.assertRaisesRegex(ValueError,"overlap"):
                merge(baseline,inc,root/"out.json",root/"prov.json")

    def test_rejects_conflicting_or_nonascending_input(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); baseline=root/"baseline.json"; inc=root/"daily.jsonl"
            baseline.write_text(json.dumps(compact([("2026-11-16",7416.59)])))
            inc.write_text(json.dumps(record("2026-11-15",7400.0))+"\n")
            with self.assertRaisesRegex(ValueError,"strictly newer"):
                merge(baseline,inc,root/"out.json",root/"prov.json")

if __name__=="__main__":
    unittest.main()
