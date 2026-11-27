#!/usr/bin/env python3
"""Execute Stage 2 from a Stage 1 run directory and freeze the 44-row snapshot."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path

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

def build_chart3_handoff_candidate(run_dir:Path,context:dict,fixture_path:Path,
                                  stage1_fixture_sha256:str,market_snapshot_sha256:str,sp500:dict)->dict:
    """Preserve verified S&P 500 input for R3 without invoking the unapproved writer."""
    run_dir=Path(run_dir).resolve()
    candidate_path=run_dir/"chart3-sp500-handoff-candidate.json"
    payload={
      "schema_version":"1.0","status":"CANDIDATE_NOT_APPENDED",
      "reason":"R3 Chart 3 writer/merge contract is not yet approved for Run-scoped ingestion.",
      "run_id":context["run_id"],"report_date":context["report_date"],
      "trading_date":context["trading_date"],
      "stage1_fixture_sha256":stage1_fixture_sha256,
      "market_snapshot_sha256":market_snapshot_sha256,
      "market_snapshot_path":str(Path(fixture_path).resolve().relative_to(run_dir)),
      "market_snapshot_file_sha256":hashlib.sha256(Path(fixture_path).read_bytes()).hexdigest(),
      "symbol":"SP500","source_data":sp500
    }
    candidate_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"status":"DEFERRED_R3_WRITER_NOT_APPROVED",
            "candidate_path":str(candidate_path.relative_to(run_dir)),
            "candidate_sha256":hashlib.sha256(candidate_path.read_bytes()).hexdigest()}


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
    stage1_receipt=load(stage1_receipt_path)
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
    # Stage 2 accepts only this Run's SHA-bound evidence packet. Never fall back
    # to date-global observations, Playwright, TradingView, or a prior Run artifact.
    handoff=run([sys.executable,str(RUNNER/"validate_stage2_run_handoff.py"),
        "--run-dir",str(run_dir.relative_to(ROOT))])
    web_bundle=run_dir/"market-history-web-observations.json"
    cnn_observation=run_dir/"cnn-fear-greed-observation.json"
    if not web_bundle.is_file():
        raise SystemExit("Missing Run-scoped market-history-web-observations.json; Stage 2 is blocked.")
    if not cnn_observation.is_file():
        cnn_observation.write_text(json.dumps({
            "schema_version":"1.0", "run_id":context["run_id"],
            "report_date":report_date, "trading_date":context["trading_date"],
            "stage1_receipt_sha256":handoff["stage1_receipt_sha256"],
            "run_context_sha256":handoff["run_context_sha256"],
            "stage1_fixture_sha256":handoff["stage1_fixture_sha256"],
            "captured_at_utc":load(web_bundle)["captured_at_utc"], "observations":[]
        },ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    # Re-run the handoff gate after creating the optional empty CNN packet so
    # every input consumed below is bound to the same Stage 1 receipt.
    handoff=run([sys.executable,str(RUNNER/"validate_stage2_run_handoff.py"),
        "--run-dir",str(run_dir.relative_to(ROOT))])
    run([sys.executable,str(RUNNER/"validate_chatgpt_web_observations.py"),
        "--data",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--input",str(web_bundle.relative_to(ROOT)),
        "--cnn-observation",str(cnn_observation.relative_to(ROOT)),
        "--output",str(observations_path.relative_to(ROOT)),"--no-fixture-write"])
    input_mode="RUN_SCOPED_SHA_BOUND_CHATGPT_WEB_OBSERVATIONS"
    audit=run([sys.executable,str(RUNNER/"validate_market_snapshot.py"),
        "--data",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--output",str(audit_path.relative_to(ROOT))])
    manifest=run([sys.executable,str(RUNNER/"build_market_source_verification_manifest.py"),
        "--data",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--observations",str(observations_path.relative_to(ROOT)),
        "--output",str(manifest_path.relative_to(ROOT))])
    fixture=load(fixture_path)
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
        "--run-id",str(context.get("workflow_run_id","LOCAL")),
        "--commit-sha",str(context.get("main_commit_sha","UNKNOWN")),"--branch","main"])
    fixture=load(fixture_path)
    market_groups={k:fixture.get(k) for k in ("global_markets","sectors","sector_sources","bonds","fx","energy","metals","risk","fedwatch")}
    market_snapshot_sha256=hashlib.sha256(json.dumps(market_groups,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    sp500=(fixture.get("global_markets") or {}).get("標普500指數") or {}
    chart3={"status":"SKIPPED_UNVERIFIED","reason":"S&P 500 cash-index close is not VERIFIED; no Chart 3 handoff candidate created."}
    candidate_path=None
    if (sp500.get("source") or {}).get("verification_status")=="VERIFIED":
        chart3=build_chart3_handoff_candidate(run_dir,context,fixture_path,
            stage1_fixture_sha256,market_snapshot_sha256,sp500)
        candidate_path=run_dir/"chart3-sp500-handoff-candidate.json"
    elapsed=round(time.monotonic()-started,3)
    observations=load(observations_path)
    output_files=[fixture_path,observations_path,audit_path,manifest_path,receipt_path]
    if candidate_path and candidate_path.is_file(): output_files.append(candidate_path)
    summary={
      "schema_version":"1.0","stage":"STAGE_2_MARKET","market_snapshot_sha256":market_snapshot_sha256,
      "status":"PASS" if receipt.get("status")=="PASS" and chart3.get("status") in ("APPENDED","NOOP_IDENTICAL_OBSERVATION","PASS") else "PARTIAL",
      "run_id":context["run_id"],"stage1_fixture_sha256":stage1_fixture_sha256,
      "report_date":report_date,"trading_date":context["trading_date"],
      "input_mode":input_mode,"concurrency":args.concurrency,"timeout_ms":args.timeout_ms,"elapsed_seconds":elapsed,
      "stage2_handoff":handoff,\n      "web_observation_bundle_sha256":hashlib.sha256(web_bundle.read_bytes()).hexdigest(),
      "cnn_observation_sha256":hashlib.sha256(cnn_observation.read_bytes()).hexdigest() if cnn_observation.is_file() else None,
      "historical_page_read_count":observations.get("historical_page_read_count"),
      "screenshot_only_count":observations.get("screenshot_only_count"),
      "mixed_field_count":observations.get("mixed_field_count"),
      "status_counts":observations.get("status_counts"),
      "verified_count":receipt.get("verified_count"),"pending_count":receipt.get("pending_count"),
      "closed_count":receipt.get("closed_count"),"market_status_counts":receipt.get("market_status_counts"),"chart3_handoff":chart3,
      "outputs":{p.name:{"path":str(p.relative_to(ROOT)),"sha256":__import__("hashlib").sha256(p.read_bytes()).hexdigest()}
                 for p in output_files}
    }
    (run_dir/"stage2-run-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary["status"] not in ("PASS","PARTIAL"):
        raise SystemExit("Stage 2 did not produce a valid handoff")

if __name__=="__main__": main()
