#!/usr/bin/env python3
"""Stage 3: read-only calendar and earnings projection from the Stage 1 pinned main commit."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from calendar_source_guard import load_authoritative_calendar, project_calendar_data
from stage_wr_preflight import stage_wr_preflight, require_stage_wr_receipt

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
    wr_preflight=stage_wr_preflight("STAGE_3",context)
    stage2_receipt_path=run_dir/"stage2-market-snapshot-receipt.json"
    if not stage2_receipt_path.is_file():raise SystemExit("Stage 3 requires the Stage 2 snapshot receipt")
    require_stage_wr_receipt(json.loads(stage2_receipt_path.read_text(encoding="utf-8")),"STAGE_2")
    report_date=context["report_date"]
    pinned=context["main_commit_sha"]
    bundle=load_authoritative_calendar(report_date,expected_commit=pinned)
    if bundle["main_commit_sha"]!=pinned:
        raise SystemExit("Calendar main commit differs from Stage 1 pinned commit")
    for label in ("current","previous"):
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
      "previous_week":{"week_id":bundle["previous"]["week_id"],"path":bundle["previous"]["path"],
                       "blob_sha":bundle["previous"]["blob_sha"],
                       "economic_count":bundle["previous"]["economic_count"],
                       "earnings_count":bundle["previous"]["earnings_count"]},
      "source_json_read_only":True,"projection_is_in_memory":True,
      "wr_preflight":wr_preflight,"outputs":outputs
    }
    rp=run_dir/"stage3-calendar-receipt.json"
    rp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
