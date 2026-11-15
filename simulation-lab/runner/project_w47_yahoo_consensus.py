#!/usr/bin/env python3
"""Project immutable Yahoo Finance TAC-observed captures onto W47 events (simulation only)."""
# Validates quarter-end, fiscal period, exact New York release date and raw SHA for every ticker.
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from consensus_snapshot_store import build_consensus_snapshot
from earnings_judgment import consensus_evidence_label, evaluate_metric

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",required=True)
    p.add_argument("--capture",required=True)
    p.add_argument("--yfinance-methodology",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--expected-calendar-blob-sha",required=True)
    a=p.parse_args()
    calendar_bytes=Path(a.calendar).read_bytes()
    git_blob_sha=hashlib.sha1(b"blob "+str(len(calendar_bytes)).encode()+bytes([0])+calendar_bytes).hexdigest()
    if git_blob_sha != a.expected_calendar_blob_sha:
        raise SystemExit(f"source W47 calendar blob SHA mismatch: {git_blob_sha}")
    calendar=json.loads(calendar_bytes.decode("utf-8"))
    capture=json.loads(Path(a.capture).read_text(encoding="utf-8"))
    methodology_doc=json.loads(Path(a.yfinance_methodology).read_text(encoding="utf-8"))
    methodology_by_ticker={x.get("ticker"):x for x in methodology_doc.get("records",[])}
    if calendar.get("week_id")!="2026-W47" or capture.get("branch_scope")!="simulation/tac-process-lab-2026-11-06":
        raise SystemExit("refusing non-W47 calendar or non-simulation capture")
    events={x.get("ticker"):x for x in calendar.get("events",{}).get("earnings",[])}
    output=[]
    for item in capture.get("entries",[]):
        event=events.get(item["ticker"])
        if not event or event.get("id")!=item.get("event_id") or event.get("event_date")!=item.get("event_date"):
            raise SystemExit(f"event identity/time mismatch for {item['ticker']}")
        raw=json.dumps(item["raw_response"],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        digest=hashlib.sha256(raw).hexdigest()
        if digest != item.get("raw_response_sha256"):
            raise SystemExit(f"raw response SHA-256 mismatch for {item['ticker']}")
        if event.get("reporting_period") != item.get("reporting_period"):
            raise SystemExit(f"fiscal period mismatch for {item['ticker']}")
        ny_date=datetime.fromisoformat(event["event_date"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        if item.get("next_earnings_date") != ny_date:
            raise SystemExit(f"Yahoo next earnings date mismatch for {item['ticker']}: {item.get('next_earnings_date')} != {ny_date}")
        current_quarter=next((x for x in item["raw_response"].get("trend",[]) if x.get("period")=="0q"),None)
        if not current_quarter or current_quarter.get("end_date") != item.get("period_end_date"):
            raise SystemExit(f"Yahoo fiscal period-end mismatch for {item['ticker']}")
        projected=copy.deepcopy(event)
        projected["eps_estimate"]=item["eps"]["estimate"]
        projected["eps_estimate_currency"]=item["eps"]["currency"]
        projected["eps_estimate_period"]=event["reporting_period"]
        projected["eps_estimate_basis_code"]=None
        projected["revenue_estimate"]=item["revenue"]["estimate"]
        projected["revenue_estimate_currency"]=item["revenue"]["currency"]
        projected["revenue_estimate_period"]=event["reporting_period"]
        projected["revenue_estimate_unit"]=item["revenue"]["unit"]
        projected["revenue_estimate_basis_code"]=None
        snapshots={}
        for metric,key in (("EPS","eps"),("REVENUE","revenue")):
            m=item[key]
            attempt={
                "source_level":4,"provider":"Yahoo Finance","url":item["source_url"],
                "observed_at":item["observed_at"],"data_as_of":None,"published_at":None,
                "period":event["reporting_period"],"period_end_date":m["period_end_date"],
                "value":m["estimate"],"currency":m["currency"],
                "unit":m["unit"] if metric=="REVENUE" else None,
                "basis_code":None,"statistic":m["statistic"],"analyst_count":m["analyst_count"],
            }
            snap=build_consensus_snapshot(event,metric,attempt,item["raw_response"],item["raw_response_ref"])
            snapshots[metric]=snap
            skey="eps_consensus_snapshots" if metric=="EPS" else "revenue_consensus_snapshots"
            projected[skey]=[snap]
            source_key="consensus_source" if metric=="EPS" else "revenue_consensus_source"
            projected[source_key]={"snapshot_id":snap["snapshot_id"],"url":item["source_url"],"observed_at":item["observed_at"],"notes":"TAC公告前觀測；Yahoo Finance未揭露EPS會計口徑／Revenue精確指標定義，僅作預估參考，不得方向性判讀。"}
        method_row=methodology_by_ticker.get(item["ticker"],{})
        eps_method=method_row.get("eps_methodology")
        eps_method_verified=(method_row.get("status")=="ok" and method_row.get("eps_matches_captured_value") is True)
        if eps_method_verified and eps_method not in ("gaap","normalized"):
            eps_method_verified=False
        eps_basis_display=(
            ("GAAP" if eps_method=="gaap" else "Normalized（非 GAAP）")+
            "；Basic／Diluted 股數口徑未揭露"
            if eps_method_verified else "EPS 會計方法待核實"
        )
        revenue_basis_display="Revenue 指標定義未揭露；暫不與實際營收方向比較"
        labels={k.lower():consensus_evidence_label(projected,k.lower()) for k in ("EPS","REVENUE")}
        statuses={k.lower():evaluate_metric(projected,k.lower())["status"] for k in ("EPS","REVENUE")}
        if any(v not in (None,"TAC 公告前觀測共識｜比較口徑待核實") for v in labels.values()):
            raise SystemExit(f"unexpected evidence label for {item['ticker']}: {labels}")
        if any(v in {"beat","miss","inline"} for v in statuses.values()):
            raise SystemExit(f"directional judgment without basis unexpectedly emitted for {item['ticker']}")
        output.append({
            "ticker":item["ticker"],"event_id":event["id"],"event_date":event["event_date"],
            "reporting_period":event["reporting_period"],
            "eps_estimate":projected["eps_estimate"],"eps_currency":projected["eps_estimate_currency"],
            "eps_estimate_display":f'{projected["eps_estimate_currency"]} {projected["eps_estimate"]:.2f}',
            "eps_analyst_count":item["eps"]["analyst_count"],"eps_snapshot":snapshots["EPS"],
            "eps_evidence_label":labels["eps"],"eps_status":statuses["eps"],
            "eps_methodology":eps_method if eps_method_verified else None,
            "eps_basis_display":eps_basis_display,"eps_methodology_matches_capture":eps_method_verified,
            "revenue_estimate":projected["revenue_estimate"],"revenue_currency":projected["revenue_estimate_currency"],
            "revenue_unit":projected["revenue_estimate_unit"],
            "revenue_estimate_display":f'{projected["revenue_estimate_currency"]} {projected["revenue_estimate"]/1_000_000_000:.2f}B',
            "revenue_analyst_count":item["revenue"]["analyst_count"],
            "source_url":item["source_url"],"source_name":"Yahoo Finance",
            "revenue_basis_display":revenue_basis_display,
            "revenue_snapshot":snapshots["REVENUE"],"revenue_evidence_label":labels["revenue"],"revenue_status":statuses["revenue"],
        })
    expected_tickers={x.get("ticker") for x in calendar.get("events",{}).get("earnings",[])}
    captured_tickers={x.get("ticker") for x in output}
    if expected_tickers != captured_tickers:
        raise SystemExit(f"W47 consensus coverage mismatch; missing={sorted(expected_tickers-captured_tickers)} unexpected={sorted(captured_tickers-expected_tickers)}")
    report={"schema_version":"tac-w47-consensus-projection-v1","week_id":"2026-W47","branch_scope":capture["branch_scope"],"source_calendar":"main:data/calendar/weeks/2026-W47.json (read-only)","calendar_blob_sha":a.expected_calendar_blob_sha,"capture_file":a.capture,"yfinance_methodology_file":a.yfinance_methodology,"records":output,"counts":{"events":len(output),"eps_reference":sum(x["eps_estimate"] is not None for x in output),"revenue_reference":sum(x["revenue_estimate"] is not None for x in output),"directional_eps":sum(x["eps_status"] in {"beat","miss","inline"} for x in output),"directional_revenue":sum(x["revenue_status"] in {"beat","miss","inline"} for x in output)}}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report["counts"],ensure_ascii=False))
if __name__=="__main__": main()
