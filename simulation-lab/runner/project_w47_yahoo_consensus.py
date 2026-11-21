#!/usr/bin/env python3
"""Project immutable Yahoo Finance TAC-observed captures onto W47 events (simulation only)."""
# Validates quarter-end, fiscal period, exact New York release date and raw SHA for every ticker.
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from consensus_snapshot_store import build_consensus_snapshot, select_first_available_estimate
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
        projected["revenue_estimate"]=item["revenue"]["estimate"]/1_000_000_000
        projected["revenue_estimate_currency"]=item["revenue"]["currency"]
        projected["revenue_estimate_period"]=event["reporting_period"]
        projected["revenue_estimate_unit"]="B"
        projected["revenue_estimate_basis_code"]=None
        snapshots={}
        selected_attempts={}
        for metric,key in (("EPS","eps"),("REVENUE","revenue")):
            m=item[key]
            attempt={
                "source_level":1,"provider":"Yahoo Finance","url":item["source_url"],
                "observed_at":item["observed_at"],"data_as_of":None,"published_at":None,
                "period":event["reporting_period"],"period_end_date":m["period_end_date"],
                "value":m["estimate"],"currency":m["currency"],
                "unit":m["unit"] if metric=="REVENUE" else None,
                "basis_code":None,"statistic":m["statistic"],"analyst_count":m["analyst_count"],
            }
            candidates=[attempt]+item.get("provider_attempts",{}).get(metric,[])
            selected=select_first_available_estimate(candidates,event["reporting_period"])
            if selected is not None:
                attempt=selected
            selected_attempts[metric]=attempt
            raw_selected=attempt.get("raw_response",item["raw_response"])
            ref_selected=attempt.get("raw_response_ref",item["raw_response_ref"])
            snap=build_consensus_snapshot(event,metric,attempt,raw_selected,ref_selected)
            if metric=="EPS":
                projected["eps_estimate"]=attempt.get("value")
                projected["eps_estimate_currency"]=attempt.get("currency")
                projected["eps_analyst_count"]=attempt.get("analyst_count")
            else:
                val=attempt.get("value")
                unit=str(attempt.get("unit") or "").upper()
                projected["revenue_estimate"]=(float(val) if val is not None and (unit.endswith("_BILLION") or unit in {"B","BILLION"}) else float(val)/1000 if val is not None and (unit.endswith("_MILLION") or unit in {"M","MILLION"}) else float(val)/1_000_000_000 if val is not None else None)
                projected["revenue_estimate_currency"]=attempt.get("currency")
                projected["revenue_analyst_count"]=attempt.get("analyst_count")
            snapshots[metric]=snap
            skey="eps_consensus_snapshots" if metric=="EPS" else "revenue_consensus_snapshots"
            projected[skey]=[snap]
            source_key="consensus_source" if metric=="EPS" else "revenue_consensus_source"
            projected[source_key]={"snapshot_id":snap["snapshot_id"],"url":item["source_url"],"observed_at":item["observed_at"],"notes":"TAC公告前觀測；Yahoo Finance未揭露EPS會計口徑／Revenue精確指標定義，依SIM-1.4以同期間實際值與平均預期值作數值比較；僅在幣別、單位或期間明確不相容時標記資料尚未齊備，來源口徑保留註記。"}
        method_row=methodology_by_ticker.get(item["ticker"],{})
        method_raw=method_row.get("raw_response") if isinstance(method_row,dict) else None
        method_digest=hashlib.sha256(json.dumps(method_raw,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest() if isinstance(method_raw,dict) else None
        default_eps=method_raw.get("earnings_estimate_default",{}) if isinstance(method_raw,dict) else {}
        eps_method=(default_eps.get("methodology",{}).get("0q") if isinstance(default_eps,dict) else None)
        method_observed=method_row.get("observed_at")
        method_pre_release=False
        if method_observed:
            method_pre_release=datetime.fromisoformat(method_observed.replace("Z","+00:00")) < datetime.fromisoformat(event["event_date"])
        eps_method_verified=(
            method_row.get("status")=="ok"
            and method_row.get("eps_matches_captured_value") is True
            and method_row.get("revenue_matches_captured_value") is True
            and method_row.get("raw_response_sha256")==method_digest
            and method_row.get("source_url")==item["source_url"]
            and method_pre_release
            and eps_method in ("gaap","normalized")
        )
        eps_basis_display=(
            ("GAAP" if eps_method=="gaap" else "Normalized（非 GAAP）")+
            "；Basic／Diluted 細節未完整揭露"
            if eps_method_verified else "Yahoo 平台 EPS 預期（GAAP／Normalized 細節未完整揭露）"
        )
        revenue_basis_display="Yahoo 平台 Revenue 預期（營收細項定義未完整揭露）"
        labels={k.lower():consensus_evidence_label(projected,k.lower()) for k in ("EPS","REVENUE")}
        statuses={k.lower():evaluate_metric(projected,k.lower())["status"] for k in ("EPS","REVENUE")}
        if any(v not in (None,"TAC 公告前觀測共識") for v in labels.values()):
            raise SystemExit(f"unexpected evidence label for {item['ticker']}: {labels}")
        if event.get("status") in {"upcoming", "scheduled"} and any(v in {"beat","miss","inline"} for v in statuses.values()):
            raise SystemExit(f"upcoming event unexpectedly has actual-result judgment for {item['ticker']}")
        output.append({
            "ticker":item["ticker"],"event_id":event["id"],"event_date":event["event_date"],
            "reporting_period":event["reporting_period"],
            "eps_estimate":projected["eps_estimate"],"eps_currency":projected["eps_estimate_currency"],
            "eps_estimate_display":f'{projected["eps_estimate_currency"]} {projected["eps_estimate"]:.2f}',
            "eps_analyst_count":selected_attempts["EPS"].get("analyst_count"),"eps_snapshot":snapshots["EPS"],
            "eps_evidence_label":labels["eps"],"eps_status":statuses["eps"],
            "eps_methodology":eps_method if eps_method_verified else None,
            "eps_basis_display":eps_basis_display,"eps_methodology_matches_capture":eps_method_verified,
            "eps_methodology_observed_at":method_observed if eps_method_verified else None,
            "eps_methodology_sha256":method_digest if eps_method_verified else None,
            "revenue_estimate":projected["revenue_estimate"],"revenue_currency":projected["revenue_estimate_currency"],
            "revenue_unit":projected["revenue_estimate_unit"],
            "revenue_estimate_display":f'{projected["revenue_estimate_currency"]} {projected["revenue_estimate"]:.2f}B',
            "revenue_analyst_count":selected_attempts["REVENUE"].get("analyst_count"),
            "source_url":selected_attempts["EPS"].get("url"),"source_name":selected_attempts["EPS"].get("provider"),
            "eps_source_url":selected_attempts["EPS"].get("url"),"eps_source_name":selected_attempts["EPS"].get("provider"),
            "revenue_source_url":selected_attempts["REVENUE"].get("url"),"revenue_source_name":selected_attempts["REVENUE"].get("provider"),
            "revenue_basis_display":revenue_basis_display,
            "revenue_snapshot":snapshots["REVENUE"],"revenue_evidence_label":labels["revenue"],"revenue_status":statuses["revenue"],
        })
    source_calendar=json.loads(Path("simulation-lab/fixtures/source-calendar-2026-W47.json").read_text(encoding="utf-8"))
    expected_tickers={x.get("ticker") for x in source_calendar.get("events",{}).get("earnings",[])}
    captured_tickers={x.get("ticker") for x in output}
    if expected_tickers != captured_tickers:
        raise SystemExit(f"W47 source-capture coverage mismatch; missing={sorted(expected_tickers-captured_tickers)} unexpected={sorted(captured_tickers-expected_tickers)}")
    report={"schema_version":"tac-w47-consensus-projection-v1","week_id":"2026-W47","branch_scope":capture["branch_scope"],"source_calendar":"main:data/calendar/weeks/2026-W47.json (read-only)","calendar_blob_sha":a.expected_calendar_blob_sha,"capture_file":a.capture,"yfinance_methodology_file":a.yfinance_methodology,"records":output,"counts":{"events":len(output),"eps_reference":sum(x["eps_estimate"] is not None for x in output),"revenue_reference":sum(x["revenue_estimate"] is not None for x in output),"released_events":sum(events[x["ticker"]].get("status") in {"released","published","completed"} for x in output),"upcoming_events":sum(events[x["ticker"]].get("status") in {"upcoming","scheduled"} for x in output),"directional_eps":sum(x["eps_status"] in {"beat","miss","inline"} for x in output),"directional_revenue":sum(x["revenue_status"] in {"beat","miss","inline"} for x in output),"eps_methodology_verified":sum(x.get("eps_methodology_matches_capture") is True for x in output),"eps_gaap":sum(x.get("eps_methodology")=="gaap" for x in output),"eps_normalized":sum(x.get("eps_methodology")=="normalized" for x in output)}}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"
",encoding="utf-8")
    print(json.dumps(report["counts"],ensure_ascii=False))
if __name__=="__main__": main()
