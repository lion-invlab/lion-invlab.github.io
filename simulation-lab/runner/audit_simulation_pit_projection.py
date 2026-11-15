#!/usr/bin/env python3
"""Read-only projection audit: compare released earnings using practical TAC numerical rules."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from earnings_judgment import ENGINE_VERSION, migrate_legacy_record

DIRECTIONAL = {"beat", "miss", "inline"}

def observed_after_event(record: dict, source_key: str) -> bool:
    source=record.get(source_key) or {}
    observed,event=source.get("observed_at"),record.get("event_date")
    if not observed or not event: return False
    try:
        from datetime import datetime
        a=datetime.fromisoformat(str(observed).replace("Z","+00:00"))
        b=datetime.fromisoformat(str(event).replace("Z","+00:00"))
        return a.tzinfo is not None and b.tzinfo is not None and a>=b
    except ValueError: return False

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    payload=json.loads(Path(args.input).read_text(encoding="utf-8"))
    released=[x for x in payload.get("events",{}).get("earnings",[]) if str(x.get("status","")).lower()=="released"]
    rows=[]
    for item in released:
        projected=migrate_legacy_record(item)
        eps_snapshot=bool(item.get("consensus_source",{}).get("snapshot_id")) and bool(item.get("eps_consensus_snapshots"))
        rev_snapshot=bool(item.get("revenue_consensus_source",{}).get("snapshot_id")) and bool(item.get("revenue_consensus_snapshots"))
        rows.append({
            "ticker":item.get("ticker"),"event_date":item.get("event_date"),
            "old_eps_status":item.get("eps_comparison_status"),"new_eps_status":projected.get("eps_comparison_status"),
            "old_revenue_status":item.get("revenue_comparison_status"),"new_revenue_status":projected.get("revenue_comparison_status"),
            "eps_numeric_pair_present":item.get("eps_actual") is not None and item.get("eps_estimate") is not None,
            "revenue_numeric_pair_present":item.get("revenue_actual") is not None and item.get("revenue_estimate") is not None,
            "eps_has_linked_snapshot":eps_snapshot,"revenue_has_linked_snapshot":rev_snapshot,
            "eps_source_observed_after_event":observed_after_event(item,"consensus_source"),
            "revenue_source_observed_after_event":observed_after_event(item,"revenue_consensus_source"),
            "eps_data_as_of_present":bool(item.get("consensus_source",{}).get("data_as_of")),
            "revenue_data_as_of_present":bool(item.get("revenue_consensus_source",{}).get("data_as_of")),
        })
    pairs=sum(x["eps_numeric_pair_present"]+x["revenue_numeric_pair_present"] for x in rows)
    judged=sum(int(x["eps_numeric_pair_present"] and x["new_eps_status"] in DIRECTIONAL)+int(x["revenue_numeric_pair_present"] and x["new_revenue_status"] in DIRECTIONAL) for x in rows)
    summary={
        "engine_version":ENGINE_VERSION,"input":args.input,"released_events":len(released),
        "old_eps_directional":sum(x["old_eps_status"] in DIRECTIONAL for x in rows),
        "new_eps_directional":sum(x["new_eps_status"] in DIRECTIONAL for x in rows),
        "old_revenue_directional":sum(x["old_revenue_status"] in DIRECTIONAL for x in rows),
        "new_revenue_directional":sum(x["new_revenue_status"] in DIRECTIONAL for x in rows),
        "eps_without_linked_snapshot":sum(not x["eps_has_linked_snapshot"] for x in rows),
        "revenue_without_linked_snapshot":sum(not x["revenue_has_linked_snapshot"] for x in rows),
        "directional_without_pit_snapshot":sum(int(x["new_eps_status"] in DIRECTIONAL and not x["eps_has_linked_snapshot"])+int(x["new_revenue_status"] in DIRECTIONAL and not x["revenue_has_linked_snapshot"]) for x in rows),
        "comparison_pairs_present":pairs,"comparison_pairs_judged":judged,
        "calendar_write":False,"html_write":False,"main_write":False,"records":rows,
    }
    summary["verdict"]="PASS_PRACTICAL_NUMERICAL_JUDGMENT" if pairs==judged else "FAIL_NUMERICAL_PAIR_NOT_JUDGED"
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="records"},ensure_ascii=False,indent=2))
    return 0 if pairs==judged else 1

if __name__=="__main__": raise SystemExit(main())
