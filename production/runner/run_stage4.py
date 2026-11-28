#!/usr/bin/env python3
"""Stage 4: validate current-run editorial research and merge it without changing market data."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

from stage_wr_loader import load_stage_wr
from run_state import transition_state, validate_state

ROOT=Path(__file__).resolve().parents[2]
LAYERS=("political","policy_industry","macro","markets","strategy")
DOMAINS=("us_policy","us_china","geopolitics","trade_sanctions","major_economies","energy_resources")

def sha_bytes(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def sha(path:Path)->str:return sha_bytes(path.read_bytes())

def read_json(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def market_snapshot_digest(data:dict)->str:
    groups={k:data.get(k) for k in ("global_markets","sectors","sector_sources","bonds","fx","energy","metals","risk","fedwatch")}
    return sha_bytes(json.dumps(groups,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())

def read_json(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--content")
    args=ap.parse_args()
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs_root=ROOT/"production/runs"
    if runs_root.is_symlink() or runs_root.resolve()!=runs_root.absolute() or run_dir.is_symlink():
        raise SystemExit("Stage 4 run directory must be a direct non-symlink child of production/runs")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs_root.resolve():
        raise SystemExit("Stage 4 run directory must be a direct non-symlink child of production/runs")
    context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
    wr_loaded=load_stage_wr("STAGE_4",context)
    state_path=run_dir/"run-state.json"
    state=read_json(state_path)
    validate_state(state,expected_run_id=context["run_id"])
    stage2_status=state["stages"]["STAGE_2"]["status"]
    if stage2_status not in ("PASS","PARTIAL") or state["stages"]["STAGE_3"]["status"]!="PASS" or state["stages"]["STAGE_4"]["status"]!="SUBMITTED":
        raise SystemExit("Stage 4 requires completed Stage 2/3 work and a submitted editorial artifact for this Run")
    fixture_path=run_dir/"report-data.json"
    content_path=Path(args.content) if args.content else run_dir/"stage4-editorial-content.json"
    if not content_path.is_absolute():content_path=ROOT/content_path
    content_path=content_path.resolve()
    if content_path.parent!=run_dir or content_path.name!="stage4-editorial-content.json" or content_path.is_symlink():
        raise SystemExit("Stage 4 content must be the exact Run-scoped stage4-editorial-content.json file")
    if not content_path.is_file():
        raise SystemExit("Missing Run-scoped Stage 4 editorial content; date-global fallback is prohibited")
    content_sha256=sha(content_path)
    editorial_parse_error=None
    try:
        editorial=json.loads(content_path.read_text(encoding="utf-8"))
        if not isinstance(editorial,dict): editorial={}
    except (json.JSONDecodeError,UnicodeDecodeError) as exc:
        editorial={}
        editorial_parse_error=str(exc)
    timestamp_repairs=[]
    data=json.loads(fixture_path.read_text(encoding="utf-8"))
    bundle_path=run_dir/"stage4-research-bundle.json"
    bundle_sha256=sha(bundle_path) if bundle_path.is_file() and not bundle_path.is_symlink() else None
    before=market_snapshot_digest(data)
    summary_points=editorial.get("summary_points") or []
    focus_news=editorial.get("focus_news") or []
    headlines=editorial.get("headlines") or []
    sentiment=editorial.get("sentiment") or ""
    market_analysis=editorial.get("market_analysis") or {}
    political_scan=editorial.get("political_scan") or {}
    data.update({
      "summary_title":editorial.get("summary_title",""),
      "summary_points":summary_points,
      "summary":"\\n\\n".join(f"{x.get('label','')}｜{x.get('text','')}" for x in summary_points if isinstance(x,dict)),
      "focus_news":focus_news,"headlines":headlines,
      "sentiment":sentiment,"market_sentiment":editorial.get("market_sentiment",sentiment),
      "market_analysis":market_analysis,"political_scan":political_scan,
      "core_observation":editorial.get("core_observation",[]),"observation":editorial.get("observation",[]),
      "key_levels":editorial.get("key_levels",[]),"market_comments":editorial.get("market_comments",{}),
      "news_cutoff_taipei":editorial.get("news_cutoff_taipei",""),
      "news_window_taipei":editorial.get("news_window_taipei",""),
      "warning_note":editorial.get("warning_note",""),"quality_note":editorial.get("quality_note","")
    })
    if "earnings_health" in editorial:
        data["earnings_health"]=editorial["earnings_health"]
    if "pending_items" in editorial:
        data["pending_items"]=editorial["pending_items"]
    after=market_snapshot_digest(data)
    if before!=after:raise SystemExit("Stage 4 modified the frozen Stage 2 market snapshot")
    fixture_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    analysis={
      "schema_version":"1.0","run_id":context["run_id"],"report_date":context["report_date"],
      "market_snapshot_sha256":before,"research_bundle_sha256":bundle_sha256,
      "summary_points":summary_points,"focus_news":focus_news,"headlines":headlines,
      "market_analysis":market_analysis,"political_scan":political_scan,
      "core_observation":data.get("core_observation"),"observation":data.get("observation"),
      "key_levels":data.get("key_levels"),"market_comments":data.get("market_comments"),
      "earnings_health":data.get("earnings_health"),
      "news_cutoff_taipei":data.get("news_cutoff_taipei"),
      "news_window_taipei":data.get("news_window_taipei")
    }
    analysis_path=run_dir/"analysis-data.json"
    analysis_path.write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={
      "schema_version":"1.0","stage":"STAGE_4_NEWS_ANALYSIS","status":"PASS",
      "run_id":context["run_id"],"report_date":context["report_date"],"trading_date":context["trading_date"],
      "news_counts":{"focus_news":len(focus_news),"headlines":len(headlines)},
      "publication_timestamp_normalizations":timestamp_repairs,"summary_points":len(summary_points),
      "analysis_layers":list(LAYERS),"political_domains":list(DOMAINS),
      "market_snapshot_sha256_before":before,"market_snapshot_sha256_after":after,
      "market_snapshot_unchanged":True,
      "editorial_run_binding":{"run_id":context["run_id"],"market_snapshot_sha256":before,"research_bundle_sha256":bundle_sha256},
      "research_bundle":{"sha256":bundle_sha256},
      "editorial_input":{"path":str(content_path.relative_to(ROOT)),"sha256":content_sha256,
          "parse_status":"INVALID_JSON" if editorial_parse_error else "PARSED",
          "parse_error":editorial_parse_error},
      "stage_wr_loaded":wr_loaded,"state_version_before":state["state_version"],
      "research_bundle_sha256":bundle_sha256,
      "outputs":{"analysis-data.json":sha(analysis_path),"report-data.json":sha(fixture_path)}
    }
    receipt_path=run_dir/"stage4-analysis-receipt.json"
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state=read_json(state_path)
    state=transition_state(state,stage="STAGE_4",expected_version=state["state_version"],expected_status="SUBMITTED",new_status="PASS",
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),input_sha256=content_sha256,
        output_sha256=sha(receipt_path),receipt_path=str(receipt_path.relative_to(ROOT)))
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
