#!/usr/bin/env python3
"""Create a fresh main-branch Run context and blank-first 44-row market fixture."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from stage2_market_fixture_bootstrap import blank_fixture
from builder_approval import current_governance_blob_shas

ROOT=Path(__file__).resolve().parents[2]
TZ=ZoneInfo("Asia/Taipei")

def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_blob(path:Path)->str:
    return subprocess.check_output(["git","hash-object",str(path)],cwd=ROOT,text=True).strip()

def last_nyse_session(report_date:date)->date:
    try:
        import pandas_market_calendars as mcal
    except ImportError as exc:
        raise RuntimeError("pandas-market-calendars is required for Stage 1 trading-date resolution") from exc
    cal=mcal.get_calendar("NYSE")
    end=report_date-timedelta(days=1)
    start=end-timedelta(days=14)
    schedule=cal.schedule(start_date=start.isoformat(),end_date=end.isoformat())
    if schedule.empty:
        raise RuntimeError(f"No completed NYSE session found before Taiwan report date {report_date}")
    return schedule.index[-1].date()

def week_id(day:date)->str:
    iso=day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def previous_week_start(day:date)->date:
    monday=day-timedelta(days=day.weekday())
    return monday-timedelta(days=7)

def build(report_date:date, run_id:str, trading_date:date|None=None)->dict:
    if report_date.weekday()>4:
        raise ValueError(f"Weekend report date is not allowed: {report_date}")
    trading_date=trading_date or last_nyse_session(report_date)
    if trading_date>=report_date:
        raise ValueError("trading_date must precede Taiwan report_date")
    manifest_path=ROOT/"production/config/mother-template-manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    template_key="monday" if report_date.weekday()==0 else "weekdays"
    template=manifest["templates"][template_key]
    mother_path=ROOT/template["path"]
    actual_mother_sha=git_blob(mother_path)
    if actual_mother_sha!=template["blob_sha"]:
        raise ValueError(f"Mother SHA mismatch: {actual_mother_sha} != {template['blob_sha']}")
    base_path=ROOT/"production/config/report-data-template.json"
    data=json.loads(base_path.read_text(encoding="utf-8"))
    data["report_date"]=report_date.isoformat()
    data["trading_date"]=trading_date.isoformat()
    data["timezone"]="Asia/Taipei"
    data["report_cutoff_taipei"]=f"{report_date.isoformat()} 05:25"
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for item in (data.get(group) or {}).values():
            source=item.setdefault("source",{})
            source["data_date"]=trading_date.isoformat()
    for source in (data.get("sector_sources") or {}).values():
        source["data_date"]=trading_date.isoformat()
    # Blank all quote values and apply only this report-date's SHA-verified screenshot inputs.
    data=blank_fixture(data,apply_screenshots=True)
    iso=report_date.isocalendar()
    weeks=[week_id(report_date),week_id(previous_week_start(report_date))]
    calendar_receipts=[]
    for wid in dict.fromkeys(weeks):
        path=ROOT/f"data/calendar/weeks/{wid}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Required read-only calendar database is missing: {path.relative_to(ROOT)}")
        json.loads(path.read_text(encoding="utf-8"))
        calendar_receipts.append({"path":str(path.relative_to(ROOT)),"sha256":sha256(path),"git_blob_sha":git_blob(path)})
    screenshot_path=ROOT/f"production/input/market-screenshot-observations-{report_date.isoformat()}.json"
    screenshot_receipt={"present":screenshot_path.is_file(),"path":str(screenshot_path.relative_to(ROOT))}
    if screenshot_path.is_file():
        screenshot_receipt["sha256"]=sha256(screenshot_path)
    data["run_metadata"]={"run_id":run_id,"main_commit_sha":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()}
    main_commit_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    run_context={
      "schema_version":"1.0","run_id":run_id,"report_date":report_date.isoformat(),
      "trading_date":trading_date.isoformat(),"timezone":"Asia/Taipei",
      "started_at":datetime.now(TZ).isoformat(),
      "repository":"lion-invlab/lion-invlab.github.io","branch":"main",
      "main_commit_sha":main_commit_sha,
      "governance":{"commit_sha":main_commit_sha,"blob_shas":current_governance_blob_shas(ROOT)},
      "workflow_run_id":os.environ.get("GITHUB_RUN_ID","LOCAL"),
      "workflow_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT","1"),
      "mother":{"key":template_key,"path":template["path"],"blob_sha":actual_mother_sha},
      "manifest":{"path":"production/config/mother-template-manifest.json","sha256":sha256(manifest_path),"git_blob_sha":git_blob(manifest_path)},
      "base_fixture":{"path":"production/config/report-data-template.json","sha256":sha256(base_path)},
      "calendar_read_receipts":calendar_receipts,
      "screenshot_input":screenshot_receipt,
      "stage2_bootstrap":data["stage2_market_bootstrap"],
      "market_universe_count":44
    }
    return {"run_context":run_context,"market_fixture":data}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report-date",required=True)
    ap.add_argument("--trading-date")
    ap.add_argument("--run-id")
    ap.add_argument("--output-dir")
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
    expected=runs_lexical.resolve()
    if output.resolve().parent!=expected or not output.name.startswith(f"TAC-{report_date.isoformat()}-"):
        raise SystemExit("Output must be a direct child of production/runs named TAC-<report_date>-<run_id>")
    if output.is_symlink(): raise SystemExit("Run output directory must not be a symlink")
    output.mkdir(parents=True,exist_ok=True)
    result=build(report_date,run_id,date.fromisoformat(args.trading_date) if args.trading_date else None)
    result["market_fixture"].setdefault("run_metadata",{}).update({
      "run_id":run_id,"run_dir":str(output.relative_to(ROOT)),
      "fixture_path":str((output/"report-data.json").relative_to(ROOT)),
      "main_commit_sha":result["run_context"]["main_commit_sha"]
    })
    (output/"run-context.json").write_text(json.dumps(result["run_context"],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fixture_path=output/"report-data.json"
    fixture_path.write_text(json.dumps(result["market_fixture"],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={"status":"PASS","run_id":run_id,"report_date":args.report_date,"trading_date":result["run_context"]["trading_date"],
             "fixture_path":str(fixture_path.relative_to(ROOT)),"fixture_sha256":sha256(fixture_path),
             "market_rows":44,"preexisting_market_values_used":False,
             "screenshot_fields":result["market_fixture"]["stage2_market_bootstrap"]["screenshot_field_count"]}
    (output/"stage1-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
