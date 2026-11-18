#!/usr/bin/env python3
import base64, datetime as dt, json, tempfile, unittest, zlib
from pathlib import Path
from run_tac_chart3_synchronized_release import run, DEFAULT_SP500_COMPACT, DEFAULT_SP500_PROVENANCE
from prepare_sp500_research_import import convert

def varint(n):
    out=bytearray()
    while n>=128: out.append((n&127)|128); n >>= 7
    out.append(n); return out

def compact(rows):
    packed=bytearray(); prev_day=dt.date.fromisoformat(rows[0][0]).toordinal(); prev_close=0
    for day,value in rows:
        ordinal=dt.date.fromisoformat(day).toordinal()
        packed.extend(varint(ordinal-prev_day))
        cents=round(value*100); delta=cents-prev_close
        packed.extend(varint(2*delta if delta>=0 else -2*delta-1))
        prev_day,prev_close=ordinal,cents
    return {"schema_version":"1.0.0","encoding":"zlib+base64","start":rows[0][0],
            "end":rows[-1][0],"rows":len(rows),
            "payload":base64.b64encode(zlib.compress(bytes(packed))).decode(),
            "source_dataset_sha256":"a"*64}

def fred(days):
    return {"series":[{"series_id":sid,"observations":[{"date":d,"value":1.0} for d in days],
                       "label":sid,"retrieved_at":"2026-11-18T00:00:00+00:00"}
                      for sid in ("VIXCLS","NFCI","NFCICREDIT","STLFSI4")]}

def prov():
    return {"source_url":"https://www.investing.com/indices/us-spx-500-historical-data",
            "retrieved_at":"2026-11-18T00:00:00+00:00","source_sha256":"a"*64,
            "method":"manual_csv_export_import"}

class RunnerTests(unittest.TestCase):
    def test_default_inputs_match_investing_import_outputs(self):
        self.assertEqual(DEFAULT_SP500_COMPACT.as_posix(), "data/tac-chart3/sp500_investing_daily.compact.json")
        self.assertEqual(DEFAULT_SP500_PROVENANCE.as_posix(), "data/tac-chart3/sp500_investing_daily.provenance.json")

    def setup_inputs(self,root,days=("2026-11-13",)):
        f=root/"fred.json"; s=root/"sp500.json"; p=root/"prov.json"
        f.write_text(json.dumps(fred(list(days))))
        s.write_text(json.dumps(compact([(d,6000) for d in days])))
        p.write_text(json.dumps(prov()))
        return f,s,p
    def test_investing_csv_import_to_atomic_release_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            csv_path=root/"investing_sp500.csv"
            csv_path.write_text(
                'Date,Price\n"Nov 12, 2026","6,700.25"\n"Nov 13, 2026","6,720.50"\n',
                encoding="utf-8")
            compact_path=root/"sp500.compact.json"
            provenance_path=root/"sp500.provenance.json"
            convert(csv_path,compact_path,provenance_path,
                    "https://www.investing.com/indices/us-spx-500-historical-data",
                    "2026-11-18T12:00:00+00:00")
            fred_path=root/"fred.json"
            fred_path.write_text(json.dumps(fred(["2026-11-12","2026-11-13"])))
            rc=run(fred_path,compact_path,provenance_path,root/"release",root/"status")
            self.assertEqual(rc,0)
            manifest=json.loads((root/"release"/"active_manifest.json").read_text())
            self.assertEqual(manifest["common_observation_date"],"2026-11-13")
            snapshot=json.loads((root/"release"/manifest["snapshot_file"]).read_text())
            self.assertEqual(snapshot["common_observation_date"],"2026-11-13")
            self.assertEqual(snapshot["source_provenance"]["sp500"]["method"],"manual_csv_export_import")

    def test_missing_sp500_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f=root/"fred.json"; f.write_text(json.dumps(fred(["2026-11-13"])))
            status=root/"status.json"; rc=run(f,root/"missing.json",root/"missing-prov.json",root/"release",status)
            self.assertEqual(rc,2); self.assertEqual(json.loads(status.read_text())["status"],"BLOCKED_MISSING_INPUT")
            self.assertFalse((root/"release"/"active_manifest.json").exists())
    def test_success_writes_snapshot_then_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f,s,p=self.setup_inputs(root)
            rc=run(f,s,p,root/"release",root/"status")
            self.assertEqual(rc,0)
            m=json.loads((root/"release"/"active_manifest.json").read_text())
            snap=root/"release"/m["snapshot_file"]
            self.assertTrue(snap.is_file())
            self.assertEqual(json.loads(snap.read_text())["snapshot_id"],m["snapshot_id"])
    def test_invalid_common_date_keeps_last_good_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f,s,p=self.setup_inputs(root)
            run(f,s,p,root/"release",root/"status")
            manifest=root/"release"/"active_manifest.json"; before=manifest.read_bytes()
            f.write_text(json.dumps(fred(["2026-11-14"])))
            rc=run(f,s,p,root/"release",root/"status")
            self.assertEqual(rc,2); self.assertEqual(manifest.read_bytes(),before)
    def test_same_date_is_noop(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f,s,p=self.setup_inputs(root)
            run(f,s,p,root/"release",root/"status")
            before=(root/"release"/"active_manifest.json").read_bytes()
            rc=run(f,s,p,root/"release",root/"status")
            self.assertEqual(rc,0); self.assertEqual((root/"release"/"active_manifest.json").read_bytes(),before)
            self.assertEqual(json.loads((root/"status").read_text())["status"],"NO_NEW_COMMON_DATE")

    def test_tampered_last_good_snapshot_blocks_advance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f,s,p=self.setup_inputs(root)
            run(f,s,p,root/"release",root/"status")
            manifest=json.loads((root/"release"/"active_manifest.json").read_text())
            snap=root/"release"/manifest["snapshot_file"]
            snap.write_text("{}")
            f.write_text(json.dumps(fred(["2026-11-14"])))
            before=(root/"release"/"active_manifest.json").read_bytes()
            rc=run(f,s,p,root/"release",root/"status")
            self.assertEqual(rc,2)
            self.assertEqual((root/"release"/"active_manifest.json").read_bytes(),before)
            self.assertEqual(json.loads((root/"status").read_text())["status"],"BLOCKED_LAST_GOOD_HASH_MISMATCH")

    def test_manifest_path_traversal_blocks_advance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f,s,p=self.setup_inputs(root)
            release=root/"release"; release.mkdir()
            (release/"active_manifest.json").write_text(json.dumps({
                "snapshot_id":"abc","snapshot_file":"snapshots/../../outside.json",
                "common_observation_date":"2026-11-12","snapshot_sha256":"0"*64}))
            rc=run(f,s,p,release,root/"status")
            self.assertEqual(rc,2)
            self.assertEqual(json.loads((root/"status").read_text())["status"],"BLOCKED_BROKEN_LAST_GOOD_MANIFEST")

if __name__=="__main__": unittest.main()
