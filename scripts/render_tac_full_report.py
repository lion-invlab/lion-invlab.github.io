#!/usr/bin/env python3
"""Orchestrate the TAC market snapshot renderer and editorial content renderer."""
from __future__ import annotations
import argparse, json, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTECTED={ROOT/"index.html",ROOT/"TAC_WORK_RULES.md",
 ROOT/"母版專區"/"TAC_母版_週一_2026-10-28_最終定版.html",
 ROOT/"母版專區"/"TAC_母版_週二至週五_2026-10-28_最終定版.html",
 ROOT/"母版專區"/"mother-template-manifest.json"}

def render_full(snapshot_path:Path,content_path:Path,output_path:Path,require_complete:bool=False)->dict:
    if output_path.resolve() in PROTECTED: raise ValueError("full report output cannot target a protected file")
    if not snapshot_path.is_file() or not content_path.is_file():
        raise ValueError("both snapshot JSON and editorial content JSON must exist")
    snapshot_data=json.loads(snapshot_path.read_text(encoding="utf-8"))
    content_data=json.loads(content_path.read_text(encoding="utf-8"))
    for field in ("report_date","trading_date"):
        if snapshot_data["meta"][field]!=content_data["meta"][field]:
            raise ValueError("snapshot/editorial "+field+" mismatch: "+str(snapshot_data["meta"][field])+" != "+str(content_data["meta"][field]))
    from render_tac_daily_report import render as render_market
    from render_tac_daily_content import render as render_editorial
    with tempfile.TemporaryDirectory(prefix="tac-full-render-") as tmp:
        market_html=Path(tmp)/"market-rendered.html"
        market_result=render_market(snapshot_path,market_html)
        editorial_result=render_editorial(content_path,market_html,output_path)
    content=json.loads(content_path.read_text(encoding="utf-8"))
    pending=list(editorial_result["incomplete_coverage"])
    if market_result["pending_records"]:
        pending.append("market_snapshot.pending_records="+str(market_result["pending_records"]))
    for group in ("economic_calendar","earnings_calendar","previous_economic_calendar","previous_earnings_calendar"):
        for item in content[group]:
            if item["status"]=="pending_verification":
                pending.append(group+"."+item["id"]+".status")
            if group in {"economic_calendar","previous_economic_calendar"}:
                if item["status"]=="upcoming" and (item.get("previous") is None or item.get("forecast") is None):
                    pending.append(group+"."+item["id"]+".previous_or_forecast")
            elif item["status"]=="upcoming":
                # Upcoming calendar cards are schedule records. EPS/revenue forecasts are
                # optional and must not block review; WR §20.2–20.3 applies after release.
                pass
            elif item["status"]=="released":
                required=("eps_estimate","eps_actual","revenue_estimate","revenue_actual",
                  "stock_price_reaction","stock_price_reaction_window","industry","reporting_period",
                  "eps_basis","eps_currency","revenue_currency","revenue_unit",
                  "eps_comparison_status","revenue_comparison_status","financial_judgment","eps_note","revenue_note",
                  "consensus_source","price_reaction_source")
                missing=[key for key in required if item.get(key) is None or item.get(key)==""]
                if missing:
                    pending.append(group+"."+item["id"]+".earnings_results_missing_"+",".join(missing))
                # WR §20: published cards have a separate, richer contract than upcoming cards.
                published_fields = (
                    "industry", "reporting_period", "eps_basis", "eps_currency",
                    "revenue_currency", "revenue_unit", "financial_judgment",
                    "stock_price_reaction_window", "consensus_source",
                    "price_reaction_source", "eps_note", "revenue_note"
                )
                for field in published_fields:
                    if item.get(field) is None or item.get(field) == "":
                        pending.append(group+"."+item["id"]+"."+field)
                if item.get("time_known") is not True:
                    pending.append(group+"."+item["id"]+".release_time")
                if item.get("eps_comparison_status") not in {"beat", "met", "miss"}:
                    pending.append(group+"."+item["id"]+".eps_comparison")
                if item.get("revenue_comparison_status") not in {"beat", "met", "miss"}:
                    pending.append(group+"."+item["id"]+".revenue_comparison")
    for key,item in content["analysis"].items():
        if isinstance(item,dict) and item.get("status") not in (None,"verified"):
            pending.append("analysis."+key)
        if key=="market_observation_highlights":
            for tab,value in item.items():
                if value.get("status")!="verified": pending.append("analysis.market_observation_highlights."+tab)
    status="ready_for_human_review" if not pending else "review_with_pending_items"
    if require_complete and pending:
        output_path.unlink(missing_ok=True)
        raise ValueError("complete-report gate failed: "+", ".join(sorted(set(pending))))
    return {"report_date":editorial_result["report_date"],"template_type":editorial_result["template_type"],
      "output":str(output_path),"status":status,"pending_items":sorted(set(pending)),
      "market":market_result,"editorial":editorial_result}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--content",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--require-complete",action="store_true",help="delete output and fail unless every editorial group is verified")
    a=p.parse_args()
    try:
        print(json.dumps(render_full(a.snapshot,a.content,a.output,a.require_complete),ensure_ascii=False,indent=2))
        return 0
    except Exception as exc:
        print("ERROR: "+str(exc),file=sys.stderr)
        return 2
if __name__=="__main__": raise SystemExit(main())
