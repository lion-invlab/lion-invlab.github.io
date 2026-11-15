#!/usr/bin/env python3
"""Tests that the SHA-pinned W47 consensus projection reaches upcoming cards only."""
# [build-tac-report] simulation-only visual integration verification; assert estimate values and methodology disclosures remain neutral.
from build_review_html import apply_consensus_projection

def main():
    row={
        "event_id":"earn-1","event_date":"2026-11-18T05:20:00+08:00","ticker":"NVDA",
        "eps_estimate":2.47,"eps_estimate_display":"USD 2.47","eps_currency":"USD",
        "eps_analyst_count":43,"eps_evidence_label":"TAC 公告前觀測共識｜比較口徑待核實",
        "eps_basis_display":"Normalized（非 GAAP）；Basic／Diluted 股數口徑未揭露",
        "revenue_estimate":108731903900,"revenue_estimate_display":"USD 108.73B",
        "revenue_currency":"USD","revenue_unit":"USD","revenue_analyst_count":45,
        "revenue_evidence_label":"TAC 公告前觀測共識｜比較口徑待核實",
        "revenue_basis_display":"Revenue 指標定義未揭露；暫不與實際營收方向比較",
        "source_url":"https://finance.yahoo.com/quote/NVDA/analysis/","source_name":"Yahoo Finance",
        "eps_snapshot":{"observed_at":"2026-11-15T05:50:45Z"},
    }
    projection={"branch_scope":"simulation/tac-process-lab-2026-11-06","records":[row],"calendar_blob_sha":"abc"}
    data={"earnings":{"week_id":"2026-W47","events":[{"id":"earn-1","event_date":row["event_date"],"status":"upcoming"}]}}
    calendar={"current":{"blob_sha":"abc"}}
    apply_consensus_projection(data,projection,calendar)
    got=data["earnings"]["events"][0]
    assert got["eps_estimate"]==2.47 and got["eps_analyst_count"]==43
    assert got["revenue_estimate"]==108731903900 and got["revenue_analyst_count"]==45
    assert got["eps_estimate_basis_code"] is None and got["revenue_estimate_basis_code"] is None
    assert got["eps_evidence_label"].endswith("比較口徑待核實")
    assert got["eps_basis_display"].startswith("Normalized")
    assert got["revenue_basis_display"].startswith("Revenue 指標定義未揭露")
    bad={"current":{"blob_sha":"different"}}
    try: apply_consensus_projection(data,projection,bad)
    except ValueError as exc: assert "blob SHA" in str(exc)
    else: raise AssertionError("wrong source calendar SHA must be rejected")
    released={"earnings":{"week_id":"2026-W47","events":[{"id":"earn-1","event_date":row["event_date"],"status":"released"}]}}
    try: apply_consensus_projection(released,projection,calendar)
    except ValueError as exc: assert "post-release" in str(exc)
    else: raise AssertionError("post-release event must not be overwritten")
    print("PASS: synthetic projection assigns estimates and analyst counts; wrong SHA/post-release rejected")
    # Real W47 capture regression: all 21 events have immutable, pre-release
    # TAC observations. Yahoo does not declare EPS accounting basis or exact
    # revenue metric basis, so the projection must remain non-directional.
    import hashlib, json
    from datetime import datetime
    from pathlib import Path
    capture = json.loads(Path("simulation-lab/output/yahoo-finance-pre-release-capture-20261115.json").read_text(encoding="utf-8"))
    source_calendar = json.loads(Path("simulation-lab/fixtures/source-calendar-2026-W47.json").read_text(encoding="utf-8"))
    entries = capture["entries"]
    expected = {x["ticker"]: x for x in source_calendar["events"]["earnings"]}
    assert capture["branch_scope"] == "simulation/tac-process-lab-2026-11-06"
    assert len(entries) == 21 and {x["ticker"] for x in entries} == set(expected)
    for entry in entries:
        event = expected[entry["ticker"]]
        assert entry["event_id"] == event["id"]
        assert entry["event_date"] == event["event_date"]
        assert entry["reporting_period"] == event["reporting_period"]
        observed = datetime.fromisoformat(entry["observed_at"].replace("Z", "+00:00"))
        release = datetime.fromisoformat(entry["event_date"])
        assert observed < release, f"{entry['ticker']} capture is not pre-release"
        raw = json.dumps(entry["raw_response"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        assert hashlib.sha256(raw).hexdigest() == entry["raw_response_sha256"], entry["ticker"]
        assert entry["eps"]["basis_code"] is None
        assert entry["revenue"]["basis_code"] is None
        assert entry["eps"]["estimate"] is not None and entry["revenue"]["estimate"] is not None
        assert entry["eps"]["analyst_count"] and entry["revenue"]["analyst_count"]
    print("PASS: actual W47 capture covers 21/21 events with pre-release immutable evidence; unresolved bases remain non-directional")


if __name__=="__main__": main()
