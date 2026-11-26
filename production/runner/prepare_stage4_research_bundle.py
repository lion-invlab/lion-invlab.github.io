#!/usr/bin/env python3
"""Build a deterministic, Run-bound research packet for Stage 4 editorial generation."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MARKET_GROUPS=("global_markets","sectors","sector_sources","bonds","fx","energy","metals","risk","fedwatch")
POLITICAL_DOMAINS=("us_policy","us_china","geopolitics","trade_sanctions","major_economies","energy_resources")

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def market_digest(data:dict)->str:
    groups={key:data.get(key) for key in MARKET_GROUPS}
    raw=json.dumps(groups,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def market_rows(data:dict)->tuple[list[dict],list[dict]]:
    rows=[]; unresolved=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for name,item in (data.get(group) or {}).items():
            source=item.get("source") or {}
            row={"group":group,"name":name,"display":item.get("display"),
                 "change_display":item.get("change_display"),
                 "verification_status":source.get("verification_status","MISSING"),
                 "data_date":source.get("data_date"),"quote_type":source.get("quote_type"),
                 "source_name":source.get("name"),"source_url":source.get("url"),
                 "instrument_identity":source.get("instrument_identity")}
            rows.append(row)
            if row["verification_status"] not in ("VERIFIED","BACKUP_VERIFIED"):
                unresolved.append(row)
    for name,value in (data.get("sectors") or {}).items():
        source=(data.get("sector_sources") or {}).get(name) or {}
        row={"group":"sectors","name":name,"display":value,
             "change_display":source.get("change_display"),
             "verification_status":source.get("verification_status","MISSING"),
             "data_date":source.get("data_date"),"quote_type":source.get("quote_type"),
             "source_name":source.get("name"),"source_url":source.get("url"),
             "instrument_identity":source.get("instrument_identity")}
        rows.append(row)
        if row["verification_status"] not in ("VERIFIED","BACKUP_VERIFIED"):
            unresolved.append(row)
    return rows,unresolved

def build_bundle(run_dir:Path,root:Path=ROOT)->dict:
    context=read_json(run_dir/"run-context.json")
    stage1=read_json(run_dir/"stage1-receipt.json")
    data=read_json(run_dir/"report-data.json")
    stage2=read_json(run_dir/"stage2-market-snapshot-receipt.json")
    stage2_summary=read_json(run_dir/"stage2-run-summary.json")
    stage3=read_json(run_dir/"stage3-calendar-receipt.json")
    if context.get("run_id")!=run_dir.name or stage1.get("run_id")!=context.get("run_id") or stage1.get("status")!="PASS":
        raise ValueError("Research bundle Stage 1 receipt/Run ID differs from its run directory")
    report_date=date.fromisoformat(context["report_date"])
    if data.get("report_date")!=context["report_date"] or data.get("trading_date")!=context["trading_date"]:
        raise ValueError("Research bundle fixture dates differ from Stage 1 context")
    if stage2.get("status") not in ("PASS","PARTIAL") or stage2.get("workflow_run_id") not in (context.get("workflow_run_id"),context["run_id"]) or stage2_summary.get("run_id")!=context["run_id"]:
        raise ValueError("Research bundle Stage 2 receipt/summary is not bound to this Run")
    if stage3.get("status")!="PASS" or stage3.get("run_id")!=context["run_id"] or stage3.get("main_commit_sha")!=context["main_commit_sha"]:
        raise ValueError("Research bundle Stage 3 receipt is not bound to the pinned Run")
    snapshot_sha=market_digest(data)
    if stage2_summary.get("market_snapshot_sha256")!=snapshot_sha:
        raise ValueError("Research bundle market snapshot digest differs from Stage 2 receipt")
    required={
      "run-context.json":run_dir/"run-context.json",
      "stage1-receipt.json":run_dir/"stage1-receipt.json",
      "report-data.json":run_dir/"report-data.json",
      "stage2-market-snapshot-receipt.json":run_dir/"stage2-market-snapshot-receipt.json",
      "stage2-run-summary.json":run_dir/"stage2-run-summary.json",
      "market-history-browser-observations.json":run_dir/"market-history-browser-observations.json",
      "market-source-verification-manifest.json":run_dir/"market-source-verification-manifest.json",
      "market-snapshot-audit.json":run_dir/"market-snapshot-audit.json",
      "stage3-calendar-receipt.json":run_dir/"stage3-calendar-receipt.json",
      "calendar-source-bundle.json":run_dir/"calendar-source-bundle.json",
      "calendar.json":run_dir/"calendar.json",
      "earnings.json":run_dir/"earnings.json",
      "last-week-calendar.json":run_dir/"last-week-calendar.json",
      "last-week-earnings.json":run_dir/"last-week-earnings.json"
    }
    for label,path in required.items():
        if not path.is_file():
            if label.startswith("last-week-") and report_date.weekday()!=0:
                continue
            raise FileNotFoundError(f"Research bundle input missing: {path.relative_to(root)}")
    rows,unresolved=market_rows(data)
    window_start_date=report_date-timedelta(days=3 if report_date.weekday()==0 else 1)
    window_start=datetime.combine(window_start_date,time(12,0)).isoformat(timespec="minutes")
    cutoff_target=datetime.combine(report_date,time(5,25)).isoformat(timespec="minutes")
    cutoff_latest=datetime.combine(report_date,time(5,55)).isoformat(timespec="minutes")
    inputs={label:{"path":str(path.relative_to(root)),"sha256":sha(path)}
            for label,path in required.items() if path.is_file()}
    bundle={
      "schema_version":"1.0","bundle_type":"TAC_STAGE4_EDITORIAL_RESEARCH",
      "run_id":context["run_id"],"report_date":context["report_date"],
      "trading_date":context["trading_date"],"timezone":"Asia/Taipei",
      "main_commit_sha":context["main_commit_sha"],
      "market_snapshot_sha256":snapshot_sha,
      "news_window":{"start_taipei":window_start,"target_cutoff_taipei":cutoff_target,
                     "latest_allowed_cutoff_taipei":cutoff_latest,
                     "rule":"Monday starts Friday 12:00; Tue-Fri starts previous calendar day 12:00; original publication time is mandatory."},
      "market_snapshot":{"row_count":len(rows),"rows":rows,"unresolved_rows":unresolved,
                         "fedwatch":data.get("fedwatch")},
      "summary_source_data":{"global_markets":data.get("global_markets"),
                             "market_comments":data.get("market_comments"),
                             "earnings_health":data.get("earnings_health")},
      "calendar":{"current_week":read_json(run_dir/"calendar.json"),
                  "previous_week":read_json(run_dir/"last-week-calendar.json") if (run_dir/"last-week-calendar.json").is_file() else None},
      "earnings":{"current_week":read_json(run_dir/"earnings.json"),
                  "previous_week":read_json(run_dir/"last-week-earnings.json") if (run_dir/"last-week-earnings.json").is_file() else None},
      "editorial_contract":{
        "summary_points":3,"focus_news":5,"headlines":10,"market_analysis_layers":["political","policy_industry","macro","markets","strategy"],
        "political_scan_domains":list(POLITICAL_DOMAINS),"weekday_core_observation_points":4,
        "focus_news_scope":"Macro, central bank, policy and global economic events; prioritize Cnyes and Investing.com.",
        "headline_scope":"Market, company and industry events; summaries about 3-4 lines; do not repeat index quote tables.",
        "evidence":"Preserve original publication timestamp, source timezone, canonical HTTPS URL, checked time and source for every claim. Never invent missing facts."
      },
      "input_refs":inputs,
      "generated_at_utc":datetime.utcnow().isoformat(timespec="seconds")+"Z"
    }
    return bundle

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    args=ap.parse_args()
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs=ROOT/"production/runs"
    if runs.is_symlink() or runs.resolve()!=runs.absolute() or run_dir.is_symlink():
        raise SystemExit("Research bundle run directory must be a direct non-symlink child of production/runs")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs.resolve():
        raise SystemExit("Research bundle run directory must be a direct child of production/runs")
    bundle=build_bundle(run_dir)
    output=run_dir/"stage4-research-bundle.json"
    output.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={"status":"PASS","run_id":bundle["run_id"],"report_date":bundle["report_date"],
             "market_snapshot_sha256":bundle["market_snapshot_sha256"],
             "input_count":len(bundle["input_refs"]),"bundle_path":str(output.relative_to(ROOT)),
             "bundle_sha256":sha(output),"market_rows":bundle["market_snapshot"]["row_count"],
             "unresolved_market_rows":len(bundle["market_snapshot"]["unresolved_rows"])}
    (run_dir/"stage4-research-bundle-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
