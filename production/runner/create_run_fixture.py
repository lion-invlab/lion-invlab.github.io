#!/usr/bin/env python3
"""Create a fresh main-branch Run context and immutable blank-first Stage 1 fixture."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, uuid
from datetime import date, datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

from stage2_market_fixture_bootstrap import blank_fixture
from builder_approval import current_governance_blob_shas
from stage_wr_preflight import stage_wr_preflight

ROOT=Path(__file__).resolve().parents[2]
TZ=ZoneInfo("Asia/Taipei")
NY_TZ=ZoneInfo("America/New_York")

def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_blob(path:Path, commit_sha:str="HEAD")->str:
    return subprocess.check_output(["git","rev-parse",f"{commit_sha}:{path.relative_to(ROOT).as_posix()}"],cwd=ROOT,text=True).strip()

def report_cutoff_taipei(report_date:date)->str:
    """16:25 New York close-window cutoff converted to Taiwan local time for this report date."""
    ny_date=report_date-timedelta(days=3 if report_date.weekday()==0 else 1)
    ny_cutoff=datetime.combine(ny_date,time(16,25),NY_TZ)
    taipei_clock="04:25" if ny_cutoff.dst() and ny_cutoff.dst().total_seconds() else "05:25"
    production_date=report_date-timedelta(days=2) if report_date.weekday()==0 else report_date
    return f"{production_date.isoformat()} {taipei_clock}"

def report_template_key(report_date:date)->str:
    """Select the Monday mother for Monday-dated reports produced on Saturday."""
    return "monday" if report_date.weekday()==0 else "weekdays"

def report_target_date(report_date:date)->date:
    """Resolve the shared target date from Taiwan production cadence."""
    offset=3 if report_date.weekday()==0 else 1
    return report_date-timedelta(days=offset)

def week_id(day:date)->str:
    iso=day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def previous_week_start(day:date)->date:
    monday=day-timedelta(days=day.weekday())
    return monday-timedelta(days=7)

def build(report_date:date, run_id:str, trading_date:date|None=None, supersedes_run_id:str|None=None)->dict:
    stage1_wr = stage_wr_preflight("STAGE_1")
    main_commit_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    if report_date.weekday() not in (0,1,2,3,4): raise ValueError(f"Report date must be Monday (produced Saturday) or Tuesday-Friday: {report_date}")
    production_date=report_date-timedelta(days=2) if report_date.weekday()==0 else report_date
    trading_date=trading_date or report_target_date(report_date)
    if trading_date>=report_date: raise ValueError("trading_date must precede Taiwan report_date")
    manifest_path=ROOT/"production/config/mother-template-manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    template_key=report_template_key(report_date)
    template=manifest["templates"][template_key]
    mother_path=ROOT/template["path"]
    actual_mother_sha=git_blob(mother_path,main_commit_sha)
    if actual_mother_sha!=template["blob_sha"]:
        raise ValueError(f"Mother SHA mismatch: {actual_mother_sha} != {template['blob_sha']}")
    base_path=ROOT/"production/config/report-data-template.json"
    data=json.loads(base_path.read_text(encoding="utf-8"))
    data["report_date"]=report_date.isoformat()
    data["trading_date"]=trading_date.isoformat()
    data["timezone"]="Asia/Taipei"
    data["report_cutoff_taipei"]=report_cutoff_taipei(report_date)
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for item in (data.get(group) or {}).values():
            item.setdefault("source",{})["data_date"]=trading_date.isoformat()
    for source in (data.get("sector_sources") or {}).values():
        source["data_date"]=trading_date.isoformat()
    # Stage 1 is always blank-first. User screenshots belong to the Run-scoped Stage 2 handoff.
    data=blank_fixture(data,apply_screenshots=False)
    weeks=[week_id(report_date)]
    if report_date.weekday()==0:
        weeks.append(week_id(previous_week_start(report_date)))
    calendar_receipts=[]
    for wid in dict.fromkeys(weeks):
        path=ROOT/f"data/calendar/weeks/{wid}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Required read-only calendar database is missing: {path.relative_to(ROOT)}")
        json.loads(path.read_text(encoding="utf-8"))
        calendar_receipts.append({"path":str(path.relative_to(ROOT)),"sha256":sha256(path),"git_blob_sha":git_blob(path,main_commit_sha)})
    run_context={
      "schema_version":"1.0","run_id":run_id,"production_date":production_date.isoformat(),"report_date":report_date.isoformat(),
      "supersedes_run_id":supersedes_run_id,
      "trading_date":trading_date.isoformat(),"timezone":"Asia/Taipei",
      "started_at":datetime.now(TZ).isoformat(),
      "repository":"lion-invlab/lion-invlab.github.io","branch":"main",
      "main_commit_sha":main_commit_sha,
      "governance":{"commit_sha":main_commit_sha,"blob_shas":current_governance_blob_shas(ROOT,main_commit_sha)},
      "workflow_run_id":os.environ.get("GITHUB_RUN_ID","LOCAL"),
      "workflow_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT","1"),
      "mother":{"key":template_key,"path":template["path"],"blob_sha":actual_mother_sha},
      "manifest":{"path":"production/config/mother-template-manifest.json","sha256":sha256(manifest_path),"git_blob_sha":git_blob(manifest_path,main_commit_sha)},
      "base_fixture":{"path":"production/config/report-data-template.json","sha256":sha256(base_path),"git_blob_sha":git_blob(base_path,main_commit_sha)},
      "calendar_read_receipts":calendar_receipts,
      "screenshot_input":{"status":"NOT_READ_AT_STAGE1","handoff_stage":"STAGE2"},
      "stage2_bootstrap":data["stage2_market_bootstrap"],
      "market_universe_count":44,
      "stage_wr_preflight":stage1_wr
    }
    stage1_wr["stage1_pinned_commit"] = main_commit_sha
    stage1_pinned_blob = run_context["governance"]["blob_shas"].get(stage1_wr["wr_path"])
    if stage1_wr["wr_git_blob_sha"] != stage1_pinned_blob:
        raise ValueError("Stage 1 WR changed while creating its governance snapshot")
    stage1_wr["stage1_pinned_git_blob_sha"] = stage1_pinned_blob
    return {"run_context":run_context,"market_fixture":data}

def write_run_files(output:Path,run_id:str,result:dict,repo_root:Path=ROOT)->dict:
    repo_root=Path(repo_root).resolve()
    output=Path(output)
    if not output.is_absolute(): output=repo_root/output
    output.mkdir(parents=True,exist_ok=True)
    rel=lambda p:str(Path(p).resolve().relative_to(repo_root))
    data=result["market_fixture"]
    data.setdefault("run_metadata",{}).update({
      "run_id":run_id,"run_dir":rel(output),
      "fixture_path":rel(output/"report-data.json"),
      "stage1_fixture_path":rel(output/"stage1-fixture.json"),
      "main_commit_sha":result["run_context"]["main_commit_sha"]
    })
    context=result["run_context"]
    context["stage1_fixture_path"]=rel(output/"stage1-fixture.json")
    context["working_fixture_path"]=rel(output/"report-data.json")
    context_path=output/"run-context.json"
    context_path.write_text(json.dumps(context,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fixture_text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    stage1_fixture_path=output/"stage1-fixture.json"
    working_fixture_path=output/"report-data.json"
    stage1_fixture_path.write_text(fixture_text,encoding="utf-8")
    working_fixture_path.write_text(fixture_text,encoding="utf-8")
    receipt={"status":"PASS","run_id":run_id,"report_date":context["report_date"],"trading_date":context["trading_date"],
             "fixture_path":rel(stage1_fixture_path),"working_fixture_path":rel(working_fixture_path),
             "fixture_sha256":sha256(stage1_fixture_path),"run_context_sha256":sha256(context_path),
             "governance_commit_sha":context["governance"]["commit_sha"],
             "governance_file_count":len(context["governance"]["blob_shas"]),
             "market_rows":44,"preexisting_market_values_used":False,"screenshot_fields":0,
             "screenshot_input_receipt":{"status":"NOT_READ_AT_STAGE1","handoff_stage":"STAGE2","fields":[]},
             "wr_preflight":context["stage_wr_preflight"],
             "supersedes_run_id":context.get("supersedes_run_id")}
    (output/"stage1-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return receipt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report-date",required=True)
    ap.add_argument("--trading-date")
    ap.add_argument("--run-id")
    ap.add_argument("--output-dir")
    ap.add_argument("--supersedes-run-id")
    args=ap.parse_args()
    report_date=date.fromisoformat(args.report_date)
    run_token=args.run_id or os.environ.get("GITHUB_RUN_ID") or uuid.uuid4().hex[:12]
    attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    run_id=f"TAC-{report_date.isoformat()}-{run_token}-{attempt}"
    output=Path(args.output_dir) if args.output_dir else ROOT/"production/runs"/run_id
    if not output.is_absolute(): output=ROOT/output
    runs_lexical=ROOT/"production/runs"
    if runs_lexical.is_symlink() or runs_lexical.resolve()!=runs_lexical.absolute():
        raise SystemExit("production/runs must not be a symlink")
    if output.resolve().parent!=runs_lexical.resolve() or not output.name.startswith(f"TAC-{report_date.isoformat()}-"):
        raise SystemExit("Output must be a direct child of production/runs named TAC-<report_date>-<run_id>")
    if output.is_symlink(): raise SystemExit("Run output directory must not be a symlink")
    result=build(report_date,run_id,date.fromisoformat(args.trading_date) if args.trading_date else None,args.supersedes_run_id)
    receipt=write_run_files(output,run_id,result,ROOT)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
