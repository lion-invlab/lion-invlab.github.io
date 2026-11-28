#!/usr/bin/env python3
# [capture-tac-report:2026-11-27] Re-run after persisted Stage 2 receipt summary binding.
"""Execute Stage 2 from a Stage 1 run directory and freeze the 44-row snapshot."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path

from stage_wr_preflight import stage_wr_preflight, require_stage_wr_receipt
from run_state import transition_state, validate_state

ROOT=Path(__file__).resolve().parents[2]
RUNNER=Path(__file__).resolve().parent

def load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def run(cmd:list[str])->dict:
    proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        lines=[x for x in proc.stdout.splitlines() if x.strip()]
        if lines:
            try: return json.loads(lines[-1])
            except json.JSONDecodeError: pass
        return {"stdout":proc.stdout.strip()}

def validate_stage2_worker_wr_attestation(payload:dict,wr_preflight:dict)->dict:
    """Record that the Stage 2 worker received its instructions; do not gate on a WR hash."""
    return {"status":"LOADED","stage":"STAGE_2","wr_path":wr_preflight.get("wr_path"),
            "wr_loaded":wr_preflight.get("wr_loaded") is True}

FEDWATCH_SOURCE_URL = "https://www.investing.com/central-banks/fed-rate-monitor"
FEDWATCH_SOURCE_NAME = "Investing.com Fed Rate Monitor"

def validate_fedwatch_observation(payload:dict,wr_preflight:dict,context:dict)->dict:
    """Validate the independent FedWatch snapshot without blocking the 44 market rows."""
    if not isinstance(payload,dict):
        raise ValueError("Stage 2 capture is missing the independent FedWatch observation object")
    if payload.get("report_date") != context.get("report_date") or payload.get("trading_date") != context.get("trading_date"):
        raise ValueError("FedWatch observation dates do not match the current Run")
    if payload.get("source_url") != FEDWATCH_SOURCE_URL or payload.get("source_name") != FEDWATCH_SOURCE_NAME:
        raise ValueError("FedWatch must be read from the approved Investing.com Fed Rate Monitor page")
    if not payload.get("captured_at_utc"):
        raise ValueError("FedWatch observation captured_at_utc is required")
    status=payload.get("status")
    if status not in ("VERIFIED","SOURCE_NO_DATA","TOOL_READ_FAILURE"):
        raise ValueError(f"Unsupported FedWatch observation status: {status!r}")
    probabilities=payload.get("probabilities")
    if not isinstance(probabilities,list):
        raise ValueError("FedWatch probabilities must be an array")
    if status == "VERIFIED":
        for field in ("target_meeting","current_target_range","updated_at_tw","web_reader_ref"):
            if not isinstance(payload.get(field),str) or not payload[field].strip():
                raise ValueError(f"Verified FedWatch observation requires {field}")
        start,end=payload.get("web_line_start"),payload.get("web_line_end")
        if not isinstance(start,int) or isinstance(start,bool) or not isinstance(end,int) or isinstance(end,bool) or start<1 or end<start:
            raise ValueError("Verified FedWatch observation requires a valid direct web reader line range")
        if not 1 <= len(probabilities) <= 8:
            raise ValueError("Verified FedWatch observation must retain 1–8 observed rate outcomes")
        total=0.0
        allowed={"hold","cut","hike","維持不變","升息","降息"}
        for item in probabilities:
            if not isinstance(item,dict) or item.get("outcome") not in allowed:
                raise ValueError("FedWatch outcome must be explicitly classified as hold, cut or hike")
            if not isinstance(item.get("rate_range"),str) or not item["rate_range"].strip():
                raise ValueError("FedWatch rate_range is required for every outcome")
            value=item.get("probability")
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0 <= value <= 100:
                raise ValueError("FedWatch probability must be numeric and between 0 and 100")
            total += float(value)
        if abs(total-100.0)>0.2:
            raise ValueError(f"FedWatch observed probabilities total {total:.3f}, not 100%")
    else:
        if probabilities:
            raise ValueError("Unverified FedWatch status must not carry unverified probability values")
        if not isinstance(payload.get("reason"),str) or not payload["reason"].strip():
            raise ValueError("Unavailable FedWatch observation requires a concrete reason")
    result={key:payload.get(key) for key in (
        "status","source_name","source_url","report_date","trading_date","captured_at_utc",
        "target_meeting","current_target_range","updated_at_tw","probabilities",
        "web_reader_ref","web_line_start","web_line_end","reason"
    )}
    result["probabilities"]=probabilities
    result["observation_sha256"]=hashlib.sha256(
        json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    ).hexdigest()
    return result

def append_chart3_sp500_increment(fixture_path:Path,output_path:Path|None=None)->dict:
    """Append only the already-verified Run S&P 500 close using the existing Chart 3 writer."""
    command=[sys.executable,str(RUNNER/"handoff_sp500_to_chart3.py"),
             "--data",str(Path(fixture_path).resolve().relative_to(ROOT))]
    if output_path is not None:
        command.extend(["--output",str(Path(output_path).resolve())])
    return run(command)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--timeout-ms",type=int,default=15000)
    ap.add_argument("--concurrency",type=int,default=4)
    ap.add_argument("--reuse-observations",action="store_true",help="Reuse exact browser observations restored from a failed capture artifact; do not reopen source pages.")
    args=ap.parse_args()
    if not 1<=args.concurrency<=4: raise SystemExit("--concurrency must be between 1 and 4")
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute(): run_dir=ROOT/run_dir
    runs_lexical=ROOT/"production/runs"
    if runs_lexical.is_symlink() or runs_lexical.resolve()!=runs_lexical.absolute():
        raise SystemExit("production/runs must not be a symlink")
    if run_dir.is_symlink():raise SystemExit("Stage 2 run directory must not be a symlink")
    runs_root=runs_lexical.resolve()
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs_root:
        raise SystemExit("Stage 2 run directory must be a direct, non-symlink child of production/runs")
    context_path=run_dir/"run-context.json"
    fixture_path=run_dir/"report-data.json"
    stage1_fixture_path=run_dir/"stage1-fixture.json"
    stage1_receipt_path=run_dir/"stage1-receipt.json"
    if not context_path.is_file() or not stage1_fixture_path.is_file() or not stage1_receipt_path.is_file():
        raise SystemExit("Stage 1 run-context.json, stage1-fixture.json and stage1-receipt.json are required")
    context=load(context_path)
    wr_preflight=stage_wr_preflight("STAGE_2",context)
    stage1_receipt=load(stage1_receipt_path)
    require_stage_wr_receipt(stage1_receipt,"STAGE_1",context)
    stage1_fixture_sha256=hashlib.sha256(stage1_fixture_path.read_bytes()).hexdigest()
    if stage1_receipt.get("fixture_sha256")!=stage1_fixture_sha256:
        raise SystemExit("Stage 1 fixture SHA does not match the immutable Stage 1 receipt")
    if stage1_receipt.get("run_id")!=context.get("run_id"):
        raise SystemExit("Stage 1 receipt Run ID does not match run-context")
    if stage1_receipt.get("report_date")!=context.get("report_date") or stage1_receipt.get("trading_date")!=context.get("trading_date"):
        raise SystemExit("Stage 1 receipt dates do not match run-context")
    # Same-Run retries always rebuild the mutable Stage 2 working fixture from
    # the exact blank-first Stage 1 fixture; partial prior writes are discarded.
    fixture_path.write_bytes(stage1_fixture_path.read_bytes())
    if context.get("run_id")!=run_dir.name:
        raise SystemExit("Run ID does not match run directory")
    report_date=context["report_date"]
    observations_path=run_dir/"market-history-browser-observations.json"
    audit_path=run_dir/"market-snapshot-audit.json"
    manifest_path=run_dir/"market-source-verification-manifest.json"
    receipt_path=run_dir/"stage2-market-snapshot-receipt.json"
    started=time.monotonic()
    # Import the observation only after Stage 1 is committed. The shared
    # report/trading anchors bind the Run; each row carries its own actual
    # market-session target_date and the worker supplies Stage 1 SHA bindings.
    web_bundle=run_dir/"market-history-web-observations.json"
    if not web_bundle.is_file():
        raise SystemExit("Missing Run-scoped market-history-web-observations.json; date-global fallback is prohibited.")
    web_payload=load(web_bundle)
    if web_payload.get("report_date")!=report_date or web_payload.get("trading_date")!=context.get("trading_date"):
        raise SystemExit("Run-scoped observations do not match this Run's report/trading dates")
    from datetime import datetime, timezone, date
    captured=datetime.fromisoformat(str(web_payload.get("captured_at_utc","")).replace("Z","+00:00"))
    age=(datetime.now(timezone.utc)-captured).total_seconds()
    if age < -300 or age > 24*3600:
        raise SystemExit("Run-scoped observations are outside the 24-hour freshness window")
    expected=set()
    stage1_fixture=load(stage1_fixture_path)
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        expected.update((group,str(name)) for name in (stage1_fixture.get(group) or {}))
    expected.update(("sectors",str(name)) for name in (stage1_fixture.get("sectors") or {}))
    rows=web_payload.get("observations")
    keys={(x.get("group"),str(x.get("name"))) for x in rows if isinstance(x,dict)}
    if len(rows or [])!=44 or len(keys)!=44 or keys!=expected:
        raise SystemExit("Run-scoped observations do not match the exact 44-row Stage 1 universe")
    report_day=date.fromisoformat(report_date)
    for row in rows:
        try:
            target_day=date.fromisoformat(str(row.get("target_date")))
        except ValueError as exc:
            raise SystemExit(f"Invalid per-instrument target_date: {row.get('name')}") from exc
        if target_day > report_day:
            raise SystemExit(f"Observation target_date is later than report_date: {row.get('name')}")
    state_path=run_dir/"run-state.json"
    state=load(state_path)
    validate_state(state,expected_run_id=context["run_id"])
    if state["stages"]["STAGE_2"]["status"]!="SUBMITTED":
        raise SystemExit("Stage 2 worker must submit the Run-scoped bundle before GitHub validation")
    web_bundle_sha256=hashlib.sha256(web_bundle.read_bytes()).hexdigest()
    if state["stages"]["STAGE_2"].get("output_sha256")!=web_bundle_sha256:
        raise SystemExit("Stage 2 submitted state SHA does not match the exact Run-scoped observation file")
    handoff=run([sys.executable,str(RUNNER/"validate_stage2_run_handoff.py"),
        "--run-dir",str(run_dir.relative_to(ROOT))])
    cnn_observation=run_dir/"cnn-fear-greed-observation.json"
    if not web_bundle.is_file():
        raise SystemExit("Missing Run-scoped market-history-web-observations.json; Stage 2 is blocked.")
    web_payload=load(web_bundle)
    worker_wr_attestation=validate_stage2_worker_wr_attestation(web_payload,wr_preflight)
    fedwatch_observation=validate_fedwatch_observation(web_payload.get("fedwatch"),wr_preflight,context)
    if not cnn_observation.is_file():
        cnn_observation.write_text(json.dumps({
            "schema_version":"1.0", "run_id":context["run_id"],
            "report_date":report_date, "trading_date":context["trading_date"],
            "captured_at_utc":load(web_bundle)["captured_at_utc"], "observations":[]
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Re-run the handoff gate after creating the optional empty CNN packet so
    # every input consumed below is bound to the same Stage 1 receipt.
    handoff=run([sys.executable,str(RUNNER/"validate_stage2_run_handoff.py"),
        "--run-dir",str(run_dir.relative_to(ROOT))])
    run([sys.executable,str(RUNNER/"validate_chatgpt_web_observations.py"),
        "--data",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--input",str(web_bundle.relative_to(ROOT)),
        "--cnn-observation",str(cnn_observation.relative_to(ROOT)),
        "--output",str(observations_path.relative_to(ROOT))])
    input_mode="RUN_SCOPED_CHATGPT_WEB_OBSERVATIONS"
    audit=run([sys.executable,str(RUNNER/"validate_market_snapshot.py"),
        "--data",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--output",str(audit_path.relative_to(ROOT))])
    manifest=run([sys.executable,str(RUNNER/"build_market_source_verification_manifest.py"),
        "--data",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--observations",str(observations_path.relative_to(ROOT)),
        "--output",str(manifest_path.relative_to(ROOT))])
    fixture=load(fixture_path)
    fixture["fedwatch"]=fedwatch_observation
    metadata=fixture.setdefault("run_metadata",{})
    metadata.update({
      "market_audit_path":str(audit_path.relative_to(ROOT)),
      "market_manifest_path":str(manifest_path.relative_to(ROOT)),
      "observations_path":str(observations_path.relative_to(ROOT)),
      "stage2_receipt_path":str(receipt_path.relative_to(ROOT))
    })
    fixture_path.write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt=run([sys.executable,str(RUNNER/"build_stage2_receipt.py"),
        "--report-date",report_date,"--data",str(fixture_path.relative_to(ROOT)),
        "--audit",str(audit_path.relative_to(ROOT)),"--manifest",str(manifest_path.relative_to(ROOT)),
        "--observations",str(observations_path.relative_to(ROOT)),"--output",str(receipt_path.relative_to(ROOT)),
        "--run-id",str(context["run_id"]),"--workflow-run-id",str(context.get("workflow_run_id","LOCAL")),
        "--commit-sha",str(context.get("main_commit_sha","UNKNOWN")),"--branch","main"])
    stage2_receipt_doc=load(receipt_path)
    stage2_receipt_doc["wr_preflight"]=wr_preflight
    stage2_receipt_doc["worker_wr_attestation"]=worker_wr_attestation
    stage2_receipt_doc["fedwatch_observation"]={key:fedwatch_observation.get(key) for key in ("status","target_meeting","current_target_range","updated_at_tw","observation_sha256")}
    receipt_path.write_text(json.dumps(stage2_receipt_doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt=stage2_receipt_doc
    fixture=load(fixture_path)
    market_groups={k:fixture.get(k) for k in ("global_markets","sectors","sector_sources","bonds","fx","energy","metals","risk","fedwatch")}
    market_snapshot_sha256=hashlib.sha256(json.dumps(market_groups,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    sp500=(fixture.get("global_markets") or {}).get("標普500指數") or {}
    chart3={"status":"SKIPPED_UNVERIFIED","reason":"S&P 500 cash-index close is not VERIFIED; no Chart 3 increment is written."}
    ledger_path=ROOT/"data/tac-chart3/sp500_daily_increment.jsonl"
    if (sp500.get("source") or {}).get("verification_status")=="VERIFIED":
        try:
            chart3=append_chart3_sp500_increment(fixture_path)
        except Exception as exc:
            chart3={"status":"FAILED_NON_BLOCKING","reason":f"Chart 3 increment failed after Stage 2 capture: {type(exc).__name__}: {exc}"}
        chart3["ledger_path"]=str(ledger_path.relative_to(ROOT))
    elapsed=round(time.monotonic()-started,3)
    observations=load(observations_path)
    output_files=[fixture_path,observations_path,audit_path,manifest_path,receipt_path]
    if ledger_path.is_file() and chart3.get("status") in ("APPENDED","NOOP_IDENTICAL_OBSERVATION"):
        output_files.append(ledger_path)
    summary={
      "schema_version":"1.0","stage":"STAGE_2_MARKET","market_snapshot_sha256":market_snapshot_sha256,
      "status":"PASS" if receipt.get("status")=="PASS" else "PARTIAL",
      "run_id":context["run_id"],"stage1_fixture_sha256":stage1_fixture_sha256,
      "wr_preflight":wr_preflight,
      "worker_wr_attestation":worker_wr_attestation,
      "fedwatch_status":fedwatch_observation["status"],
      "fedwatch_observation_sha256":fedwatch_observation["observation_sha256"],
      "fedwatch_target_meeting":fedwatch_observation.get("target_meeting"),
      "report_date":report_date,"trading_date":context["trading_date"],
      "input_mode":input_mode,"concurrency":args.concurrency,"timeout_ms":args.timeout_ms,"elapsed_seconds":elapsed,
      "stage2_handoff":handoff,
      "web_observation_bundle_sha256":hashlib.sha256(web_bundle.read_bytes()).hexdigest(),
      "cnn_observation_sha256":hashlib.sha256(cnn_observation.read_bytes()).hexdigest() if cnn_observation.is_file() else None,
      "historical_page_read_count":observations.get("historical_page_read_count"),
      "screenshot_only_count":observations.get("screenshot_only_count"),
      "mixed_field_count":observations.get("mixed_field_count"),
      "status_counts":observations.get("status_counts"),
      "verified_count":receipt.get("verified_count"),"pending_count":receipt.get("pending_count"),
      "closed_count":receipt.get("closed_count"),"market_status_counts":json.loads(receipt_path.read_text(encoding="utf-8")).get("market_status_counts"),"chart3_handoff":chart3,
      "outputs":{p.name:{"path":str(p.relative_to(ROOT)),"sha256":__import__("hashlib").sha256(p.read_bytes()).hexdigest()}
                 for p in output_files}
    }
    summary_path=run_dir/"stage2-run-summary.json"
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state=load(state_path)
    stage2_status="PASS" if summary["status"]=="PASS" else "PARTIAL"
    state=transition_state(state,stage="STAGE_2",expected_version=state["state_version"],expected_status="SUBMITTED",new_status=stage2_status,
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        input_sha256=web_bundle_sha256,output_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        receipt_path=str(receipt_path.relative_to(ROOT)))
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary["run_state"]={"state_version":state["state_version"],"stage2_status":state["stages"]["STAGE_2"]["status"],"next_stage":state["current_stage"]}
    summary["outputs"]["run-state.json"]={"path":str(state_path.relative_to(ROOT)),"sha256":hashlib.sha256(state_path.read_bytes()).hexdigest()}
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary["status"] not in ("PASS","PARTIAL"):
        raise SystemExit("Stage 2 did not produce a valid handoff")

if __name__=="__main__": main()
