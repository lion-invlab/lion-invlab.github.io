#!/usr/bin/env python3
"""Execute Stage 2 from a Stage 1 run directory and freeze the 44-row snapshot."""
from __future__ import annotations
import argparse, json, subprocess, sys, time
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--timeout-ms",type=int,default=15000)
    ap.add_argument("--concurrency",type=int,default=4)
    args=ap.parse_args()
    if not 1<=args.concurrency<=4: raise SystemExit("--concurrency must be between 1 and 4")
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute(): run_dir=ROOT/run_dir
    run_dir=run_dir.resolve()
    runs_lexical=ROOT/"production/runs"
    if runs_lexical.is_symlink() or runs_lexical.resolve()!=runs_lexical.absolute():
        raise SystemExit("production/runs must not be a symlink")
    runs_root=runs_lexical.resolve()
    if run_dir.parent!=runs_root or run_dir.is_symlink():
        raise SystemExit("Stage 2 run directory must be a direct, non-symlink child of production/runs")
    context_path=run_dir/"run-context.json"
    fixture_path=run_dir/"report-data.json"
    if not context_path.is_file() or not fixture_path.is_file():
        raise SystemExit("Stage 1 run-context.json and report-data.json are required")
    context=load(context_path)
    if context.get("run_id")!=run_dir.name:
        raise SystemExit("Run ID does not match run directory")
    report_date=context["report_date"]
    observations_path=run_dir/"market-history-browser-observations.json"
    audit_path=run_dir/"market-snapshot-audit.json"
    manifest_path=run_dir/"market-source-verification-manifest.json"
    receipt_path=run_dir/"stage2-market-snapshot-receipt.json"
    started=time.monotonic()
    browser=run([sys.executable,str(RUNNER/"browser_verify_market_history.py"),
        "--fixture",str(fixture_path.relative_to(ROOT)),"--report-date",report_date,
        "--output",str(observations_path.relative_to(ROOT)),
        "--timeout-ms",str(args.timeout_ms),"--concurrency",str(args.concurrency)])
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
    sp500=(fixture.get("global_markets") or {}).get("標普500指數") or {}
    chart3={"status":"SKIPPED_UNVERIFIED","reason":"S&P 500 cash-index close is not VERIFIED; no Chart 3 ledger write attempted."}
    if (sp500.get("source") or {}).get("verification_status")=="VERIFIED":
        try:
            chart3=run([sys.executable,str(RUNNER/"handoff_sp500_to_chart3.py"),
                "--data",str(fixture_path.relative_to(ROOT)),
                "--output","data/tac-chart3/sp500_daily_increment.jsonl"])
        except Exception as exc:
            chart3={"status":"BLOCKED","reason":str(exc)}
    elapsed=round(time.monotonic()-started,3)
    observations=load(observations_path)
    summary={
      "schema_version":"1.0","stage":"STAGE_2_MARKET",
      "status":"PASS" if receipt.get("status")=="PASS" and chart3.get("status") in ("APPENDED","NOOP_IDENTICAL_OBSERVATION","PASS") else "PARTIAL",
      "run_id":context["run_id"],"report_date":report_date,"trading_date":context["trading_date"],
      "concurrency":args.concurrency,"timeout_ms":args.timeout_ms,"elapsed_seconds":elapsed,
      "historical_page_read_count":observations.get("historical_page_read_count"),
      "screenshot_only_count":observations.get("screenshot_only_count"),
      "mixed_field_count":observations.get("mixed_field_count"),
      "status_counts":observations.get("status_counts"),
      "verified_count":receipt.get("verified_count"),"pending_count":receipt.get("pending_count"),
      "closed_count":receipt.get("closed_count"),"chart3_handoff":chart3,
      "outputs":{p.name:{"path":str(p.relative_to(ROOT)),"sha256":__import__("hashlib").sha256(p.read_bytes()).hexdigest()}
                 for p in (fixture_path,observations_path,audit_path,manifest_path,receipt_path)}
    }
    (run_dir/"stage2-run-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary["status"] not in ("PASS","PARTIAL"):
        raise SystemExit("Stage 2 did not produce a valid handoff")

if __name__=="__main__": main()
