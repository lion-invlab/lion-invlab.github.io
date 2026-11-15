#!/usr/bin/env python3
"""Project immutable Yahoo Finance TAC-observed captures onto W47 events (simulation only)."""
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from pathlib import Path
from consensus_snapshot_store import build_consensus_snapshot
from earnings_judgment import consensus_evidence_label, evaluate_metric

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",required=True)
    p.add_argument("--capture",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--expected-calendar-blob-sha",required=True)
    a=p.parse_args()
    calendar_bytes=Path(a.calendar).read_bytes()
    git_blob_sha=hashlib.sha1(b"blob "+str(len(calendar_bytes)).encode()+bytes([0])+calendar_bytes).hexdigest()
    if git_blob_sha != a.expected_calendar_blob_sha:
        raise SystemExit(f"source W47 calendar blob SHA mismatch: {git_blob_sha}")
    calendar=json.loads(calendar_bytes.decode("utf-8"))
    capture=json.loads(Path(a.capture).read_text(encoding="utf-8"))
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
        if event.get("reporting_period") not in (item.get("reporting_period"), "2026 Q3" if item["ticker"]=="BIDU" else "FY2027 Q3"):
            raise SystemExit(f"fiscal period mismatch for {item['ticker']}")
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
            "eps_analyst_count":item["eps"]["analyst_count"],"eps_snapshot":snapshots["EPS"],
            "eps_evidence_label":labels["eps"],"eps_status":statuses["eps"],
            "revenue_estimate":projected["revenue_estimate"],"revenue_currency":projected["revenue_estimate_currency"],
            "revenue_unit":projected["revenue_estimate_unit"],"revenue_analyst_count":item["revenue"]["analyst_count"],
            "revenue_snapshot":snapshots["REVENUE"],"revenue_evidence_label":labels["revenue"],"revenue_status":statuses["revenue"],
        })
    report={"schema_version":"tac-w47-consensus-projection-v1","branch_scope":capture["branch_scope"],"source_calendar":"main:data/calendar/weeks/2026-W47.json (read-only)","capture_file":a.capture,"records":output,"counts":{"events":len(output),"eps_reference":sum(x["eps_estimate"] is not None for x in output),"revenue_reference":sum(x["revenue_estimate"] is not None for x in output),"directional_eps":sum(x["eps_status"] in {"beat","miss","inline"} for x in output),"directional_revenue":sum(x["revenue_status"] in {"beat","miss","inline"} for x in output)}}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report["counts"],ensure_ascii=False))
if __name__=="__main__": main()
