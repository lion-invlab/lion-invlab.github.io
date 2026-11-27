#!/usr/bin/env python3
import copy, hashlib, json, tempfile
from pathlib import Path
from types import SimpleNamespace
from build_stage2_receipt import build_receipt, canonical_sha
from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture
from test_stage2_market_fixture_bootstrap import fixture, observation_rows

def make_inputs():
    blank=blank_fixture(fixture())
    obs_rows=observation_rows(blank,pending=("risk","move"))
    for index,row in enumerate(obs_rows):
        row["read_status"]="SOURCE_NO_DATA" if row["status"]=="SOURCE_NO_DATA" else "PAGE_CONTENT_READ_SUCCESS"
        row["instrument_identity"]=row["name"]
        if index == 0:
            row["target_date"]="2026-11-24"
            row["observed_date"]="2026-11-24"
        row["observation_record_sha256"]=canonical_sha(row)
    obs={"report_date":"2026-11-26","trading_date":"2026-11-25","observations":obs_rows}
    populated=populate_fixture(blank,obs)
    manifest_rows=[]
    for row in obs_rows:
        status="VERIFIED" if row["status"]=="VERIFIED" else "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"
        record={"source_url":row["source_url"],"data_date":row["target_date"],
            "observed_date":row.get("observed_date"),"instrument_identity":row.get("instrument_identity"),
            "observed_value":row.get("observed_value"),"observed_change":row.get("observed_change"),
            "checked_at_tw":row.get("finished_at_tw"),"evidence_method":row.get("read_method"),
            "provenance":"CURRENT_RUN_BROWSER_OBSERVATION","read_status":row.get("read_status"),
            "field_evidence":row.get("field_evidence") or {},"quote_type":"spot_daily_close","source_role":"PRIMARY"}
        manifest_rows.append({"group":row["group"],"name":row["name"],"source_url":row["source_url"],
            "data_date":row["target_date"],"verification_status":status,
            "display_value_matches_saved_observation":status=="VERIFIED",
            "observation_provenance":"CURRENT_RUN_BROWSER_OBSERVATION",
            "browser_observation_record":record if status=="VERIFIED" else None,
            "observation_record_sha256":canonical_sha(record) if status=="VERIFIED" else None,
            "source_page_fetched":bool(row.get("source_page_fetched")),
            "display_value_reconciled":status=="VERIFIED"})
    manifest={"status":"PARTIAL","report_date":"2026-11-26","trading_date":"2026-11-25",
        "verification_scope":"CURRENT_REPORT_SESSION_SOURCE_OBSERVATIONS","source_pages_fetched":True,
        "displayed_values_reconciled":False,"displayed_values_independently_reconciled":False,
        "screenshot_row_count":0,"screenshot_field_count":0,"mixed_field_row_count":0,
        "historical_page_only_row_count":43,"prior_observation_reused_count":0,
        "row_count":44,"pending_count":1,"closed_count":0,"verified_count":43,
        "observation_record_hash_missing_count":0,"rows":manifest_rows}
    audit={"status":"PASS","verification_scope":"METADATA_AND_DATE_ONLY","report_date":"2026-11-26",
        "trading_date":"2026-11-25","indicator_count":44,"group_counts":{
            "global_markets":17,"sectors":11,"bonds":3,"fx":6,"energy":2,"metals":2,"risk":3},
        "source_pages_fetched":False,"displayed_values_independently_reconciled":False}
    return populated,audit,manifest,obs

def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    data,audit,manifest,obs=make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        paths={k:Path(tmp)/f"{k}.json" for k in ("data","audit","manifest","obs")}
        write_json(paths["data"],data);write_json(paths["audit"],audit)
        write_json(paths["manifest"],manifest);write_json(paths["obs"],obs)
        args=SimpleNamespace(report_date="2026-11-26",data=str(paths["data"]),audit=str(paths["audit"]),
            manifest=str(paths["manifest"]),observations=str(paths["obs"]),output=str(Path(tmp)/"receipt.json"),
            run_id="12345",commit_sha="a"*40,branch="main")
        receipt=build_receipt(args)
        assert receipt["status"]=="PARTIAL"
        assert receipt["row_count"]==44 and receipt["verified_count"]==43 and receipt["pending_count"]==1
        assert receipt["pending_rows"][0]["name"]=="move"
        assert sum(receipt["market_status_counts"].values())==44
        assert all("market_data_status" in row for row in receipt["rows"])
        assert len({row["data_date"] for row in receipt["rows"]}) == 2
        assert receipt["preexisting_market_values_used"] is False
        assert all(len(x["sha256"])==64 for x in receipt["input_files"].values())

        bad_manifest=copy.deepcopy(manifest)
        bad_manifest["rows"][0]["observation_record_sha256"]="0"*64
        with_bad=copy.deepcopy(args)
        bad_path=Path(tmp)/"bad-manifest.json";write_json(bad_path,bad_manifest);with_bad.manifest=str(bad_path)
        try: build_receipt(with_bad)
        except ValueError as exc: assert "manifest record SHA mismatch" in str(exc)
        else: raise AssertionError("manifest record SHA mismatch must fail")

        stale=copy.deepcopy(data)
        stale["risk"]["move"]["source"]["close_value"]=97.54
        stale["risk"]["move"]["display"]="97.54"
        stale_path=Path(tmp)/"stale-data.json";write_json(stale_path,stale)
        with_stale=copy.deepcopy(args);with_stale.data=str(stale_path)
        try: build_receipt(with_stale)
        except ValueError as exc: assert "retained an old numeric value" in str(exc)
        else: raise AssertionError("pending MOVE must not carry stale 97.54")

        wrong_sha=copy.deepcopy(obs)
        wrong_sha["observations"][0]["observation_record_sha256"]="f"*64
        wrong_sha_path=Path(tmp)/"wrong-obs.json";write_json(wrong_sha_path,wrong_sha)
        with_wrong=copy.deepcopy(args);with_wrong.observations=str(wrong_sha_path)
        try: build_receipt(with_wrong)
        except ValueError as exc: assert "observation canonical SHA mismatch" in str(exc)
        else: raise AssertionError("observation canonical SHA mismatch must fail")

    print("PASS: Stage 2 receipt binds 44-row blank-input fixture, audit, manifest and observation SHA")
    print("PASS: PARTIAL status reconciles 43 verified + 1 pending")
    print("PASS: bad manifest SHA, bad observation SHA and stale pending MOVE value are rejected")

if __name__=="__main__": main()
