#!/usr/bin/env python3
"""Tests for the TAC practical earnings status renderer."""
from build_review_html import earnings_comparison_status, earnings_commentary
from earnings_judgment import ENGINE_VERSION, apply_judgment

def make(actual_eps, estimate_eps, actual_rev, estimate_rev):
    return {
        "id":"earn-1","ticker":"TEST","status":"released",
        "eps_actual":actual_eps,"eps_estimate":estimate_eps,
        "revenue_actual":actual_rev,"revenue_estimate":estimate_rev,
    }

def main():
    item=make(1.20,1.00,8.0,8.7)
    apply_judgment(item,"2026-11-15T13:00:00+08:00")
    assert item["judgment_engine_version"] == ENGINE_VERSION
    assert earnings_comparison_status(item,"eps") == "beat"
    assert earnings_comparison_status(item,"revenue") == "miss"
    commentary=earnings_commentary(item)
    assert "EPS：優於預期" in commentary
    assert "營收：低於預期" in commentary

    # Undisclosed GAAP/Adjusted or PIT metadata does not suppress comparison.
    item=make(-0.13,-0.72,108.73,105.0)
    apply_judgment(item,"2026-11-15T13:00:00+08:00")
    assert earnings_comparison_status(item,"eps") == "beat"
    assert earnings_comparison_status(item,"revenue") == "beat"

    # Each metric stands on its own; not-yet-reported actual values are not a
    # judgment outcome and must not be mislabeled as "待核實".
    item=make(0.82,0.79,None,4.0)
    apply_judgment(item,"2026-11-15T13:00:00+08:00")
    assert earnings_comparison_status(item,"eps") == "beat"
    assert earnings_comparison_status(item,"revenue") == "pending"
    commentary=earnings_commentary(item)
    assert "EPS：優於預期" in commentary
    assert "營收：尚未公布／數值尚未齊備" in commentary
    assert "待核實" not in commentary
    print("PASS: renderer uses practical numerical judgments; no basis/PIT gate or pending-verification copy")

if __name__ == "__main__":
    main()
