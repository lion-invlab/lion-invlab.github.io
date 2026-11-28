#!/usr/bin/env python3
import hashlib,json,tempfile,unittest
from pathlib import Path
from validate_stage2_run_handoff import validate_stage2_run_handoff
from run_state import initial_run_state,transition_state

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,sort_keys=True))
def make_run(root):
    report,trading="2026-11-27","2026-11-26";run_id="TAC-2026-11-27-123456789"
    run=root/"production"/"runs"/run_id;run.mkdir(parents=True)
    fixture={"run_id":run_id,"report_date":report,"trading_date":trading,
      "global_markets":{f"i{i}":{} for i in range(17)},"bonds":{f"b{i}":{} for i in range(3)},
      "fx":{f"f{i}":{} for i in range(6)},"energy":{f"e{i}":{} for i in range(2)},
      "metals":{f"m{i}":{} for i in range(2)},"risk":{f"r{i}":{} for i in range(3)},
      "sectors":{f"ETF{i}":"待擷取" for i in range(11)}}
    context={"run_id":run_id,"report_date":report,"trading_date":trading}
    put(run/"run-context.json",context);put(run/"stage1-fixture.json",fixture);put(run/"report-data.json",fixture)
    stage1={"status":"PASS","run_id":run_id,"report_date":report,"trading_date":trading}
    put(run/"stage1-receipt.json",stage1)
    state=initial_run_state(context,stage1,digest(run/"stage1-receipt.json"),now="2026-11-27T00:00:00Z")
    rows=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk","sectors"):
      rows.extend({"group":group,"name":name,"target_date":trading} for name in fixture[group])
    web=run/"market-history-web-observations.json"
    put(web,{"schema_version":"1.1","run_id":run_id,"report_date":report,"trading_date":trading,
      "captured_at_utc":"2026-11-27T00:51:42Z","observations":rows,
      "fedwatch":{"status":"SOURCE_NO_DATA","source_name":"Investing.com Fed Rate Monitor",
      "source_url":"https://www.investing.com/central-banks/fed-rate-monitor","report_date":report,
      "trading_date":trading,"captured_at_utc":"2026-11-27T00:51:42Z","probabilities":[],"reason":"Test fixture"}})
    state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="READY",
      new_status="RUNNING",now="2026-11-27T00:01:00Z",lease_owner="worker",lease_expires_at="2026-11-27T00:10:00Z")
    state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="RUNNING",
      new_status="SUBMITTED",now="2026-11-27T00:02:00Z",output_sha256=digest(web))
    put(run/"run-state.json",state)
    return run
class RunHandoffTests(unittest.TestCase):
    def test_accepts_same_run_by_identity_and_dates_without_upstream_sha_chain(self):
      with tempfile.TemporaryDirectory() as tmp:
        run=make_run(Path(tmp));out=validate_stage2_run_handoff(run,Path(tmp))
        self.assertEqual(out["status"],"PASS");self.assertEqual(out["run_id"],run.name)
    def test_rejects_wrong_run_id(self):
      with tempfile.TemporaryDirectory() as tmp:
        run=make_run(Path(tmp));p=run/"market-history-web-observations.json";x=json.loads(p.read_text());x["run_id"]="TAC-OTHER";put(p,x)
        with self.assertRaisesRegex(ValueError,"run_id"):validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_wrong_dates(self):
      with tempfile.TemporaryDirectory() as tmp:
        run=make_run(Path(tmp));p=run/"market-history-web-observations.json";x=json.loads(p.read_text());x["trading_date"]="2026-11-25";put(p,x)
        with self.assertRaisesRegex(ValueError,"dates"):validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_incomplete_44_row_universe(self):
      with tempfile.TemporaryDirectory() as tmp:
        run=make_run(Path(tmp));p=run/"market-history-web-observations.json";x=json.loads(p.read_text());x["observations"].pop();put(p,x)
        with self.assertRaisesRegex(ValueError,"exact 44-row"):validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_missing_bundle(self):
      with tempfile.TemporaryDirectory() as tmp:
        run=make_run(Path(tmp));(run/"market-history-web-observations.json").unlink()
        with self.assertRaisesRegex(ValueError,"Missing or symlinked"):validate_stage2_run_handoff(run,Path(tmp))
if __name__=="__main__":unittest.main()
