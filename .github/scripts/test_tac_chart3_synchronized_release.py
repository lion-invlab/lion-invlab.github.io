#!/usr/bin/env python3
import base64, datetime as dt, json, tempfile, unittest, zlib
from pathlib import Path
from build_tac_chart3_synchronized_release import build_candidate, publish

def varint(n):
    out=bytearray()
    while n>=128:
        out.append((n&127)|128); n >>= 7
    out.append(n)
    return out

def compact(rows):
    packed=bytearray()
    prev_day=dt.date.fromisoformat(rows[0][0]).toordinal()
    prev_close=0
    for day, value in rows:
        ordinal=dt.date.fromisoformat(day).toordinal()
        packed.extend(varint(ordinal-prev_day))
        cents=round(value*100); delta=cents-prev_close
        packed.extend(varint(2*delta if delta>=0 else -2*delta-1))
        prev_day,prev_close=ordinal,cents
    return {"schema_version":"1.0.0","encoding":"zlib+base64","start":rows[0][0],
            "end":rows[-1][0],"rows":len(rows),"payload":base64.b64encode(zlib.compress(bytes(packed))).decode(),
            "source_dataset_sha256":"test-source-hash"}

def fred(dates):
    return {"series":[{"series_id":sid,"label":sid,"observations":[{"date":d,"value":1.25} for d in dates],
                       "retrieved_at":"2026-11-18T00:00:00+00:00","source_file_sha256":"fred-hash"}
                      for sid in ("VIXCLS","NFCI","NFCICREDIT","STLFSI4")]}

def provenance():
    return {"source_url":"https://www.investing.com/indices/us-spx-500-historical-data",
            "retrieved_at":"2026-11-18T00:00:00+00:00","source_sha256":"test-source-hash","method":"licensed data feed","authorization_reference":"fixture-only-test-authorization"}

class SynchronizedReleaseTests(unittest.TestCase):
    def test_publishes_latest_exact_common_date(self):
        dates=["2026-11-12","2026-11-13"]
        candidate=build_candidate(fred(dates),compact([(d,6000+i) for i,d in enumerate(dates)]),provenance())
        self.assertEqual(candidate["common_observation_date"],"2026-11-13")
        self.assertEqual(len(candidate["series"]),5)
        self.assertTrue(all(s["observations"][-1]["date"]=="2026-11-13" for s in candidate["series"]))
    def test_no_common_date_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"No exact common"):
            build_candidate(fred(["2026-11-12"]),compact([("2026-11-13",6000)]),provenance())
    def test_rejects_non_investing_source(self):
        p=provenance();p["source_url"]="https://example.com/sp500.csv"
        with self.assertRaisesRegex(ValueError,"Investing.com"):
            build_candidate(fred(["2026-11-13"]),compact([("2026-11-13",6000)]),p)
    def test_does_not_replace_with_same_or_older_common_date(self):
        candidate=build_candidate(fred(["2026-11-13"]),compact([("2026-11-13",6000)]),provenance())
        with tempfile.TemporaryDirectory() as td:
            prev=Path(td)/"previous.json";out=Path(td)/"release.json"
            prev.write_text(json.dumps({"common_observation_date":"2026-11-13"}))
            result=publish(candidate,out,prev)
            self.assertFalse(result["published"])
            self.assertFalse(out.exists())

if __name__=="__main__":
    unittest.main()
