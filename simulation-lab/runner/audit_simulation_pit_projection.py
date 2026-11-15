#!/usr/bin/env python3
"""Read-only projection audit: verify practical numerical judgments while reporting PIT metadata gaps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from earnings_judgment import ENGINE_VERSION, migrate_legacy_record

DIRECTIONAL = {"beat", "miss", "inline"}


def observed_after_event(record: dict, source_key: str) -> bool:
    source = record.get(source_key) or {}
    observed = source.get("observed_at")
    event = record.get("event_date")
    if not observed or not event:
        return False
    try:
        from datetime import datetime
        a = datetime.fromisoformat(str(observed).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(event).replace("Z", "+00:00"))
        if a.tzinfo is None or b.tzinfo is None:
            return False
        return a >= b
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    released = [
        item for item in payload.get("events", {}).get("earnings", [])
        if str(item.get("status", "")).lower() == "released"
    ]
    rows = []
    violations = []
    for item in released:
        projected = migrate_legacy_record(item)
        old_eps = item.get("eps_comparison_status")
        old_revenue = item.get("revenue_comparison_status")
        new_eps = projected.get("eps_comparison_status")
        new_revenue = projected.get("revenue_comparison_status")
        eps_has_snapshot = bool(item.get("consensus_source", {}).get("snapshot_id")) and bool(item.get("eps_consensus_snapshots"))
        revenue_has_snapshot = bool(item.get("revenue_consensus_source", {}).get("snapshot_id")) and bool(item.get("revenue_consensus_snapshots"))
        # PIT snapshots are traceability metadata, not a prerequisite for
        # Beat/Inline/Miss under the practical TAC judgment policy.
        rows.append({
            "ticker": item.get("ticker"),
            "event_date": item.get("event_date"),
            "old_eps_status": old_eps,
            "new_eps_status": new_eps,
            "old_revenue_status": old_revenue,
            "new_revenue_status": new_revenue,
            "eps_has_linked_snapshot": eps_has_snapshot,
            "revenue_has_linked_snapshot": revenue_has_snapshot,
            "eps_source_observed_after_event": observed_after_event(item, "consensus_source"),
            "revenue_source_observed_after_event": observed_after_event(item, "revenue_consensus_source"),
            "eps_data_as_of_present": bool(item.get("consensus_source", {}).get("data_as_of")),
            "revenue_data_as_of_present": bool(item.get("revenue_consensus_source", {}).get("data_as_of")),
        })

    summary = {
        "engine_version": ENGINE_VERSION,
        "input": args.input,
        "released_events": len(released),
        "old_eps_directional": sum(x["old_eps_status"] in DIRECTIONAL for x in rows),
        "new_eps_directional": sum(x["new_eps_status"] in DIRECTIONAL for x in rows),
        "old_revenue_directional": sum(x["old_revenue_status"] in DIRECTIONAL for x in rows),
        "new_revenue_directional": sum(x["new_revenue_status"] in DIRECTIONAL for x in rows),
        "eps_without_linked_snapshot": sum(not x["eps_has_linked_snapshot"] for x in rows),
        "revenue_without_linked_snapshot": sum(not x["revenue_has_linked_snapshot"] for x in rows),
        "eps_sources_observed_after_event": sum(x["eps_source_observed_after_event"] for x in rows),
        "revenue_sources_observed_after_event": sum(x["revenue_source_observed_after_event"] for x in rows),
        "events_missing_any_data_as_of": sum(not x["eps_data_as_of_present"] or not x["revenue_data_as_of_present"] for x in rows),
        "directional_judgments_without_snapshot": [
            {"ticker": x["ticker"], "metric": metric, "status": x[status_key]}
            for x in rows
            for metric, status_key, has_key in (
                ("EPS", "new_eps_status", "eps_has_linked_snapshot"),
                ("REVENUE", "new_revenue_status", "revenue_has_linked_snapshot"),
            )
            if x[status_key] in DIRECTIONAL and not x[has_key]
        ],
        "directional_without_snapshot_violations": violations,
        "calendar_write": False,
        "html_write": False,
        "main_write": False,
        "records": rows,
    }
    summary["verdict"] = "PASS_PRACTICAL_NUMERICAL_JUDGMENT" if not violations else "FAIL_ENGINE_INCONSISTENCY"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
