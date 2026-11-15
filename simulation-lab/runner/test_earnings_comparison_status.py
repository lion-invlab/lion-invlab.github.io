#!/usr/bin/env python3
"""Tests for the TAC practical earnings status renderer."""
from build_review_html import earnings_comparison_status, earnings_commentary, recalculate_released_earnings
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

    # Recalculation must replace stale directional prose rather than append
    # a second copy of the current engine verdicts.
    item["judgment"] = "EPS：優於預期；營收：低於預期；EPS：優於預期"
    commentary = earnings_commentary(item)
    assert commentary.count("EPS：優於預期") == 1
    assert commentary.count("營收：低於預期") == 1

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
    # Monday's previous-week cards must be recalculated too; they were previously
    # rendered from stale legacy statuses because only the current week was processed.
    prior = make(4.56, 2.66, 6.77, 6.80)
    prior["eps_comparison_status"] = "pending"
    prior["revenue_comparison_status"] = "miss"
    data = {
        "earnings": {"events": [make(1.20, 1.00, 8.0, 8.7)]},
        "last_week_earnings": {"events": [prior]},
    }
    counts = recalculate_released_earnings(data, "2026-11-16T05:00:00+08:00")
    assert counts == {"earnings": 1, "last_week_earnings": 1}
    assert earnings_comparison_status(data["last_week_earnings"]["events"][0], "eps") == "beat"
    assert earnings_comparison_status(data["last_week_earnings"]["events"][0], "revenue") == "inline"

    # Explicitly mismatched currencies must not be mechanically compared.
    item=make(0.54,0.69,0.9314,1.14)
    item["revenue_currency"]="CHF actual; USD estimate (not comparable)"
    apply_judgment(item,"2026-11-15T13:00:00+08:00")
    assert earnings_comparison_status(item,"revenue") == "incomparable"

    # Brookfield's official note explicitly says the legacy EPS/revenue
    # estimates are not proven comparable with reported IFRS/consolidated values.
    item=make(0.54,0.69,20.691,1.8)
    item["financial_judgment"]="EPS／revenue estimates 未證明與 IFRS diluted EPS／consolidated revenue 同口徑，不判 beat/miss。"
    apply_judgment(item,"2026-11-15T13:00:00+08:00")
    assert earnings_comparison_status(item,"eps") == "incomparable"
    assert earnings_comparison_status(item,"revenue") == "incomparable"

    # Ordinary numeric pairs continue to use the 1% practical threshold.
    item=make(1.02,1.00,8.0,8.7)
    apply_judgment(item,"2026-11-15T13:00:00+08:00")
    assert earnings_comparison_status(item,"eps") == "beat"
    assert earnings_comparison_status(item,"revenue") == "miss"

    print("PASS: practical numerical judgment, explicit non-comparable exceptions, and retrospective recalculation")

if __name__ == "__main__":
    main()
