#!/usr/bin/env python3
"""[resume-tac-report:2026-11-27] Resume the exact Main Run with official SIFMA MOVE holiday evidence."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUNNER=Path(__file__).resolve().parent

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    if p.returncode: raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    print(p.stdout)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-id",required=True)
    ap.add_argument("--report-date",required=True)
    args=ap.parse_args()
    run_dir=ROOT/"production/runs"/args.run_id
    if run_dir.parent!=(ROOT/"production/runs") or run_dir.is_symlink() or not run_dir.is_dir():
        raise SystemExit("Exact existing Run directory is required; no new Run may be created.")
    context=load(run_dir/"run-context.json")
    if context.get("run_id")!=args.run_id or context.get("report_date")!=args.report_date:
        raise SystemExit("Run ID/report date binding mismatch.")
    if args.report_date!="2026-11-27" or context.get("trading_date")!="2026-11-26":
        raise SystemExit("This evidence patch is explicitly limited to 2026-11-27 report / 2026-11-26 trading date.")
    bundle_path=run_dir/"market-history-web-observations.json"
    bundle=load(bundle_path)
    if bundle.get("run_id")!=args.run_id or bundle.get("report_date")!=args.report_date or bundle.get("trading_date")!="2026-11-26":
        raise SystemExit("Run-scoped browser observation bundle mismatch.")
    rows=bundle.get("observations") or []
    move=[r for r in rows if (r.get("group"),r.get("name"))==("risk","move")]
    if len(rows)!=44 or len(move)!=1: raise SystemExit("Expected exact 44-row universe and one MOVE row.")
    row=move[0]
    if row.get("source_url")!="https://www.investing.com/indices/ice-bofaml-move-historical-data" or row.get("target_date")!="2026-11-26":
        raise SystemExit("MOVE source URL or target date mismatch.")
    if row.get("prior_observation_reused") is not False or row.get("source_page_fetched") is not True:
        raise SystemExit("MOVE must be current-run page read; prior observations cannot be reused.")
    if row.get("instrument_identity")!="ICE BofAML MOVE (MOVE)" or row.get("instrument_identity_status") not in ("MATCH","VERIFIED"):
        raise SystemExit("MOVE instrument identity not confirmed.")
    if row.get("field_mapping_status") not in ("MATCH","VERIFIED") or row.get("observed_value_field")!="收市" or row.get("observed_change_field")!="升跌（%）":
        raise SystemExit("MOVE field mapping not confirmed.")
    if row.get("observed_value") is not None or row.get("observed_change") is not None:
        raise SystemExit("Closed session cannot carry a numeric MOVE observation.")
    if row.get("read_status") not in ("SOURCE_UPDATE_PENDING","MARKET_CLOSED"):
        raise SystemExit("Unexpected MOVE read status; refusing to overwrite.")
    row.update({
      "read_status":"MARKET_CLOSED",
      "status":"MARKET_CLOSED",
      "observed_date":None,
      "observed_value":None,
      "observed_change":None,
      "observed_row_text":"SIFMA confirms a full U.S. fixed-income market close on Thursday, November 26, 2026; the Investing.com MOVE historical page was readable but contains no target-date close row.",
      "closure_evidence_url":"https://www.sifma.org/news/press-releases/sifma-fixed-income-market-close-recommendations-in-the-u-s-the-u-k-and-japan-for-thanksgiving-day-2026",
      "closure_evidence_text":"SIFMA recommends a full market close on Thursday, November 26 and an early close at 2:00 p.m., EST, on Friday, November 27, 2026.",
      "closure_evidence_reader_ref":"turn528755view0",
      "closure_evidence_line_start":15,
      "closure_evidence_line_end":18,
      "closure_evidence_sha256":"WEB_OPEN_REF:turn528755view0:L15-L18",
      "provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
      "finished_at_utc":"2026-11-27T04:20:00Z",
      "finished_at_tw":"2026-11-27T12:20:00+08:00",
    })
    save(bundle_path,bundle)
    run([sys.executable,str(RUNNER/"run_stage2.py"),"--run-dir",str(run_dir.relative_to(ROOT)),"--concurrency","4"])
    run([sys.executable,str(RUNNER/"prepare_stage4_research_bundle.py"),"--run-dir",str(run_dir.relative_to(ROOT))])
    stage2=load(run_dir/"stage2-market-snapshot-receipt.json")
    summary=load(run_dir/"stage2-run-summary.json")
    stage3=load(run_dir/"stage3-calendar-receipt.json")
    bundle_receipt=load(run_dir/"stage4-research-bundle-receipt.json")
    capture={
      "schema_version":"1.0","status":"AWAITING_EDITORIAL_INPUT",
      "capture_trigger":{"event_name":"push","dispatch_mode":"resume_existing_run",
        "workflow_run_id":os.environ.get("GITHUB_RUN_ID"),
        "original_capture_workflow_run_id":"45937649928","resume_existing_run":True},
      "run_id":context["run_id"],"report_date":context["report_date"],
      "market_snapshot_sha256":summary["market_snapshot_sha256"],
      "stage2_status":stage2["status"],"stage2_pending_rows":stage2.get("pending_rows",[]),
      "chart3_handoff":summary.get("chart3_handoff"),
      "research_bundle_path":f"{run_dir.relative_to(ROOT).as_posix()}/stage4-research-bundle.json",
      "research_bundle_sha256":bundle_receipt["bundle_sha256"],
      "research_bundle_unresolved_market_rows":bundle_receipt["unresolved_market_rows"],
      "chart3_merge_workflow_run_id":"NOT_REQUIRED",
      "current_week":stage3["current_week"]["week_id"],"previous_week":stage3["previous_week"]["week_id"],
      "editorial_input_path":f"production/input/report-content-{context['report_date']}.json",
      "next_action":"Read the regenerated exact-Run research bundle; generate Stage 4 editorial content bound to current snapshot and bundle SHA."
    }
    save(run_dir/"capture-stage-receipt.json",capture)
    print(json.dumps(capture,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
