#!/usr/bin/env python3
"""Stage 3: read-only calendar and earnings projection from the Stage 1 pinned main commit."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from calendar_source_guard import load_authoritative_calendar, project_calendar_data
from stage_wr_loader import load_stage_wr
from run_state import transition_state, validate_state

ROOT=Path(__file__).resolve().parents[2]

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    args=ap.parse_args()
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs_root=ROOT/"production/runs"
    if runs_root.is_symlink() or runs_root.resolve()!=runs_root.absolute() or run_dir.is_symlink():
        raise SystemExit("Stage 3 run directory must be a direct non-symlink child of production/runs")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs_root.resolve():
        raise SystemExit("Stage 3 run directory must be a direct non-symlink child of production/runs")
    context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
    wr_preflight=load_stage_wr("STAGE_3",context)
    state_path=run_dir/"run-state.json"
    state=json.loads(state_path.read_text(encoding="utf-8"))
    validate_state(state,expected_run_id=context["run_id"])
    if state["stages"]["STAGE_2"]["status"] not in ("PASS","PARTIAL"):
        raise SystemExit("Stage 3 requires Stage 2 PASS/PARTIAL in the authoritative Run state")
    if state["stages"]["STAGE_3"]["status"]=="FAILED":
        state=transition_state(state,stage="STAGE_3",expected_version=state["state_version"],expected_status="FAILED",new_status="READY",recovery=True)
    elif state["stages"]["STAGE_3"]["status"]=="DEFERRED":
        state=transition_state(state,stage="STAGE_3",expected_version=state["state_version"],expected_status="DEFERRED",new_status="READY")
    if state["stages"]["STAGE_3"]["status"]!="READY":
        raise SystemExit("Stage 3 is not READY in the authoritative Run state")
    state=transition_state(state,stage="STAGE_3",expected_version=state["state_version"],expected_status="READY",new_status="RUNNING",
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),lease_owner="github-actions-stage3",
        lease_expires_at=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat().replace("+00:00","Z"),
        input_sha256=hashlib.sha256((run_dir/"stage2-market-snapshot-receipt.json").read_bytes()).hexdigest())
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    stage2_receipt_path=run_dir/"stage2-market-snapshot-receipt.json"
    if not stage2_receipt_path.is_file():raise SystemExit("Stage 3 requires the Stage 2 snapshot receipt")
    stage2_receipt=json.loads(stage2_receipt_path.read_text(encoding="utf-8"))
        if stage2_receipt.get("run_id")!=context["run_id"] or stage2_receipt.get("status") not in ("PASS","PARTIAL"):
        raise SystemExit("Stage 3 Stage 2 receipt identity/status does not match the current Run")
    report_date=context["report_date"]
    pinned=context["main_commit_sha"]
    bundle=load_authoritative_calendar(report_date,expected_commit=pinned)
    if bundle["main_commit_sha"]!=pinned:
        raise SystemExit("Calendar main commit differs from Stage 1 pinned commit")
    labels=("current","previous") if bundle.get("previous") is not None else ("current",)
    for label in labels:
        item=bundle[label]
        if item.get("commit_sha")!=pinned or item.get("branch")!="main":
            raise SystemExit(f"{label} calendar week is not from pinned main commit")
    projection=project_calendar_data(bundle)
    outputs={}
    for key,value in projection.items():
        path=run_dir/f"{key.replace('last_week_','last-week-')}.json"
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        outputs[path.name]={"path":str(path.relative_to(ROOT)),"sha256":sha(path)}
    source_path=run_dir/"calendar-source-bundle.json"
    source_path.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    outputs[source_path.name]={"path":str(source_path.relative_to(ROOT)),"sha256":sha(source_path)}
    receipt={
      "schema_version":"1.0","stage":"STAGE_3_CALENDAR","status":"PASS",
      "run_id":context["run_id"],"report_date":report_date,"main_commit_sha":pinned,
      "current_week":{"week_id":bundle["current"]["week_id"],"path":bundle["current"]["path"],
                      "blob_sha":bundle["current"]["blob_sha"],
                      "economic_count":bundle["current"]["economic_count"],
                      "earnings_count":bundle["current"]["earnings_count"]},
      "previous_week":({
          "week_id":bundle["previous"]["week_id"],"path":bundle["previous"]["path"],
          "blob_sha":bundle["previous"]["blob_sha"],
          "economic_count":bundle["previous"]["economic_count"],
          "earnings_count":bundle["previous"]["earnings_count"]
      } if bundle.get("previous") is not None else None),
      "source_json_read_only":True,"projection_is_in_memory":True,
      "stage_wr_loaded":wr_preflight,"state_version_before":state["state_version"],"outputs":outputs
    }
    rp=run_dir/"stage3-calendar-receipt.json"
    rp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state=json.loads(state_path.read_text(encoding="utf-8"))
    state=transition_state(state,stage="STAGE_3",expected_version=state["state_version"],expected_status="RUNNING",new_status="PASS",
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),input_sha256=None,
        output_sha256=sha(rp),receipt_path=str(rp.relative_to(ROOT)))
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
