#!/usr/bin/env python3
import hashlib, json, tempfile, unittest
from pathlib import Path
from validate_stage2_run_handoff import validate_stage2_run_handoff
from run_state import initial_run_state, transition_state

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def make_run(root):
    report,trading="2026-11-27","2026-11-26"
    run_id="TAC-2026-11-27-123456789"
    run=root/"production"/"runs"/run_id; run.mkdir(parents=True)
    fixture={"report_date":report,"trading_date":trading,"run_metadata":{"run_id":run_id},
      "global_markets":{f"i{i}":{} for i in range(17)},"bonds":{f"b{i}":{} for i in range(3)},
      "fx":{f"f{i}":{} for i in range(6)},"energy":{f"e{i}":{} for i in range(2)},
      "metals":{f"m{i}":{} for i in range(2)},"risk":{f"r{i}":{} for i in range(3)},
      "sectors":{f"ETF{i}":"待擷取" for i in range(11)}}
    cp,stage1_fp,working_fp,rp=run/"run-context.json",run/"stage1-fixture.json",run/"report-data.json",run/"stage1-receipt.json"
    cp.write_text(json.dumps({"run_id":run_id,"report_date":report,"trading_date":trading},sort_keys=True))
    stage1_fp.write_text(json.dumps(fixture,sort_keys=True))
    working_fp.write_text(json.dumps(fixture,sort_keys=True))
    rp.write_text(json.dumps({"status":"PASS","run_id":run_id,"report_date":report,"trading_date":trading,
      "run_context_sha256":digest(cp),"fixture_sha256":digest(stage1_fp)},sort_keys=True))
    binding={"schema_version":"1.1","run_id":run_id,"report_date":report,"trading_date":trading,"stage2_wr_sha256":"a"*64,
      "stage1_receipt_sha256":digest(rp),"run_context_sha256":digest(cp),
      "stage1_fixture_sha256":digest(stage1_fp),"captured_at_utc":"2026-11-27T00:51:42Z"}
    rows=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk","sectors"):
        rows.extend({
            "group":group,"name":name,"source_url":"https://www.investing.com/",
            "target_date":trading,"observed_date":trading,"page_title":name,
            "instrument_identity":name,"read_method":"BROWSER_HISTORICAL_DATA",
            "observed_value_field":"Price","observed_change_field":"Change %",
            "observed_headers":["Date","Price","Change %"],"observed_row_text":f"{trading} | {name}",
            "read_status":"PAGE_CONTENT_READ_SUCCESS","captured_at_utc":binding["captured_at_utc"],
            "finished_at_utc":binding["captured_at_utc"]
        } for name in fixture[group])
    fedwatch={
        "status":"SOURCE_NO_DATA","source_name":"Investing.com Fed Rate Monitor",
        "source_url":"https://www.investing.com/central-banks/fed-rate-monitor",
        "report_date":report,"trading_date":trading,"captured_at_utc":binding["captured_at_utc"],
        "target_meeting":None,"current_target_range":None,"updated_at_tw":None,
        "probabilities":[],"web_reader_ref":None,"web_line_start":None,"web_line_end":None,
        "reason":"Test fixture only","stage2_wr_sha256":"a"*64
    }
    web=run/"market-history-web-observations.json"
    web.write_text(json.dumps({**binding,"observations":rows,"fedwatch":fedwatch}))
    context=json.loads(cp.read_text())
    stage1_receipt=json.loads(rp.read_text())
    state=initial_run_state(context,stage1_receipt,digest(rp),now="2026-11-27T00:00:00Z")
    state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="READY",new_status="RUNNING",now="2026-11-27T00:01:00Z",lease_owner="chatgpt-stage2",lease_expires_at="2026-11-27T00:16:00Z")
    state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="RUNNING",new_status="SUBMITTED",now="2026-11-27T00:02:00Z",output_sha256=digest(web))
    (run/"run-state.json").write_text(json.dumps(state))
    return run

class RunHandoffTests(unittest.TestCase):
    def test_accepts_exact_same_run_and_stage1_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); out=validate_stage2_run_handoff(run,Path(tmp))
            self.assertEqual(out["status"],"PASS"); self.assertEqual(out["run_id"],run.name)
            self.assertEqual(out["bundle_sha256"],digest(run/"market-history-web-observations.json"))
    def test_mutable_working_fixture_does_not_change_stage1_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp))
            working=run/"report-data.json"
            value=json.loads(working.read_text())
            value["run_metadata"]["stage2_attempt"]="partial-retry"
            working.write_text(json.dumps(value))
            out=validate_stage2_run_handoff(run,Path(tmp))
            self.assertEqual(out["status"],"PASS")
            self.assertEqual(out["stage1_fixture_sha256"],json.loads((run/"market-history-web-observations.json").read_text())["stage1_fixture_sha256"])

    def test_rejects_wrong_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); p=run/"market-history-web-observations.json"
            x=json.loads(p.read_text()); x["run_id"]="TAC-OTHER"; p.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,"run_id"): validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_wrong_stage1_receipt_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); p=run/"market-history-web-observations.json"
            x=json.loads(p.read_text()); x["stage1_receipt_sha256"]="0"*64; p.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,"stage1_receipt_sha256"): validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_wrong_context_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); p=run/"market-history-web-observations.json"
            x=json.loads(p.read_text()); x["run_context_sha256"]="0"*64; p.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,"run_context_sha256"): validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_wrong_fixture_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); p=run/"market-history-web-observations.json"
            x=json.loads(p.read_text()); x["stage1_fixture_sha256"]="0"*64; p.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,"stage1_fixture_sha256"): validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_missing_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); (run/"market-history-web-observations.json").unlink()
            with self.assertRaisesRegex(ValueError,"Missing or symlinked Run bundle"): validate_stage2_run_handoff(run,Path(tmp))
    def test_rejects_incomplete_44_row_universe(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); p=run/"market-history-web-observations.json"
            x=json.loads(p.read_text()); x["observations"].pop(); p.write_text(json.dumps(x))
            with self.assertRaisesRegex(ValueError,"exact 44-row"): validate_stage2_run_handoff(run,Path(tmp))
    def test_accepts_optional_run_bound_cnn_and_screenshot_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp))
            base=json.loads((run/"market-history-web-observations.json").read_text())
            (run/"cnn-fear-greed-observation.json").write_text(json.dumps({**base,"observations":[]}))
            screenshot={key:base[key] for key in ("schema_version","run_id","report_date","trading_date","captured_at_utc",
                "stage1_receipt_sha256","run_context_sha256","stage1_fixture_sha256")}
            screenshot["observations"]=[]
            (run/"market-screenshot-observations.json").write_text(json.dumps(screenshot))
            out=validate_stage2_run_handoff(run,Path(tmp))
            self.assertEqual(out["screenshot"],{"row_count":0,"field_count":0})
            self.assertEqual(set(out["optional_bundle_sha256"]),{
                "cnn-fear-greed-observation.json","market-screenshot-observations.json"
            })

    def test_rejects_optional_bundle_without_run_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp))
            (run/"cnn-fear-greed-observation.json").write_text(json.dumps({
                "schema_version":"1.1","report_date":"2026-11-27","trading_date":"2026-11-26",
                "captured_at_utc":"2026-11-27T00:51:42Z","observations":[]
            }))
            with self.assertRaisesRegex(ValueError,"run_id"):
                validate_stage2_run_handoff(run,Path(tmp))

    def test_rejects_cross_run_screenshot_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=make_run(Path(tmp)); base=json.loads((run/"market-history-web-observations.json").read_text())
            base["run_id"]="TAC-OTHER"; base["observations"]=[]
            (run/"market-screenshot-observations.json").write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError,"run_id"): validate_stage2_run_handoff(run,Path(tmp))

if __name__=="__main__": unittest.main()
