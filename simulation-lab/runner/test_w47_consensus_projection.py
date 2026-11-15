#!/usr/bin/env python3
"""Tests that the SHA-pinned W47 consensus projection reaches upcoming cards only."""
# [build-tac-report] simulation-only visual integration verification; assert estimate values remain neutral.
from build_review_html import apply_consensus_projection

def main():
    row={
        "event_id":"earn-1","event_date":"2026-11-18T05:20:00+08:00","ticker":"NVDA",
        "eps_estimate":2.47,"eps_estimate_display":"USD 2.47","eps_currency":"USD",
        "eps_analyst_count":43,"eps_evidence_label":"TAC 公告前觀測共識｜比較口徑待核實",
        "revenue_estimate":108731903900,"revenue_estimate_display":"USD 108.73B",
        "revenue_currency":"USD","revenue_unit":"USD","revenue_analyst_count":45,
        "revenue_evidence_label":"TAC 公告前觀測共識｜比較口徑待核實",
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
    bad={"current":{"blob_sha":"different"}}
    try: apply_consensus_projection(data,projection,bad)
    except ValueError as exc: assert "blob SHA" in str(exc)
    else: raise AssertionError("wrong source calendar SHA must be rejected")
    released={"earnings":{"week_id":"2026-W47","events":[{"id":"earn-1","event_date":row["event_date"],"status":"released"}]}}
    try: apply_consensus_projection(released,projection,calendar)
    except ValueError as exc: assert "post-release" in str(exc)
    else: raise AssertionError("post-release event must not be overwritten")
    print("PASS: W47 estimates and analyst counts project to upcoming cards; basis stays pending; wrong SHA/post-release rejected")

if __name__=="__main__": main()
