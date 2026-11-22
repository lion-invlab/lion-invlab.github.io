#!/usr/bin/env python3
"""Validate 11/23 report-layer overrides against immutable authoritative main W47/W48 JSON."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from calendar_source_guard import load_authoritative_calendar, project_calendar_data
from build_review_html import (
    apply_calendar_impact_overrides,
    apply_last_week_economic_overrides,
    apply_last_week_earnings_actuals,
)

FIXTURE = ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json"
EXPECTED = {
    "2026-W47": {
        "blob_sha": "727ea2be1c04688d3c4f98d36c452561bbab6821",
        "economic_count": 25,
        "earnings_count": 23,
    },
    "2026-W48": {
        "blob_sha": "9bb842ab475fa38ca6407304990d1cd3fae42c63",
        "economic_count": 27,
        "earnings_count": 11,
    },
}


def main():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = load_authoritative_calendar(data["report_date"])
    projection_path = ROOT / "simulation-lab" / "fixtures" / "earnings-consensus-projection-2026-11-23.json"
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    require(projection.get("calendar_blob_sha") == bundle["current"]["blob_sha"],
            "W48 earnings consensus projection calendar blob SHA mismatch")
    require(projection.get("calendar_main_commit_sha") == bundle["main_commit_sha"],
            "W48 earnings consensus projection main commit SHA mismatch")
    main_earnings = {
        str(item.get("id")): item
        for item in bundle["current"]["payload"]["events"]["earnings"]
    }
    for row in projection.get("records", []):
        event = main_earnings.get(str(row.get("event_id")))
        require(event is not None, f"consensus projection event missing from authoritative W48: {row.get('event_id')}")
        require(row.get("event_date") == event.get("event_date"),
                f"consensus projection event timestamp differs from authoritative W48: {row.get('event_id')}")
        require(row.get("reporting_period") == event.get("reporting_period"),
                f"consensus projection reporting period differs from authoritative W48: {row.get('event_id')}")
    for key in ("current", "previous"):
        item = bundle[key]
        expected = EXPECTED[item["week_id"]]
        assert item["blob_sha"] == expected["blob_sha"], (
            item["week_id"], item["blob_sha"], expected["blob_sha"]
        )
        assert item["economic_count"] == expected["economic_count"]
        assert item["earnings_count"] == expected["earnings_count"]

    data.update(project_calendar_data(bundle))
    econ_count = apply_last_week_economic_overrides(data)
    earnings_count = apply_last_week_earnings_actuals(data)
    impact_count = apply_calendar_impact_overrides(data)
    assert (econ_count, earnings_count, impact_count) == (6, 3, 4)

    prior_econ = {x["id"]: x for x in data["last_week_calendar"]["events"]}
    for row in data["last_week_economic_overrides"]:
        event = prior_econ[row["event_id"]]
        assert event["status"] == "released"
        assert event["actual"] == row["actual"]
        assert event["source_url"] == row["source_url"]
        assert event["report_layer_only"] is True

    prior_earnings = {x["id"]: x for x in data["last_week_earnings"]["events"]}
    for row in data["last_week_earnings_actuals"]:
        event = prior_earnings[row["event_id"]]
        assert event["status"] == "released"
        assert event["eps_actual"] == row["eps_actual"]
        assert event["revenue_actual"] == row["revenue_actual"]
        assert event["source_url"] == row["actual_source"]["url"]
        assert event["report_layer_only"] is True
        assert event.get("eps_estimate") is None or event.get("judgment", "").find("不判定Beat/Miss") >= 0

    current_econ = {x["id"]: x for x in data["calendar"]["events"]}
    for row in data["calendar_impact_overrides"]:
        event = current_econ[row["event_id"]]
        assert event["impact"] == row["impact"]
        assert not event["impact"].startswith("http")
        assert event["source_url"].startswith("https://")

    print("PASS: authoritative main W47/W48 blob SHA and event counts unchanged")
    print("PASS: 6 W47 economic actuals projected; main JSON untouched")
    print("PASS: 3 W47 earnings actuals projected; PIT Beat/Miss not inferred")
    print("PASS: 4 remaining W48 impact fields corrected in HTML projection only")
    print(f"PASS: main commit {bundle['main_commit_sha']}")


if __name__ == "__main__":
    main()
