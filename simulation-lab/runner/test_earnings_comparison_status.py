#!/usr/bin/env python3
"""Renderer contract: display persisted judgment only and guard editorial claims."""
from earnings_judgment import ENGINE_VERSION
from build_review_html import earnings_comparison_status, earnings_commentary


def check(item, metric, expected):
    actual = earnings_comparison_status(item, metric)
    assert actual == expected, f"{metric}: expected {expected!r}, got {actual!r}"


def main():
    for metric in ("eps", "revenue"):
        for status in ("beat", "miss", "inline", "pending", "incomparable", "consensus_divergent"):
            check({
                f"{metric}_comparison_status": status,
                "judgment_engine_version": ENGINE_VERSION,
            }, metric, status)
        check({f"{metric}_comparison_status": "beat"}, metric, "pending")
        check({
            f"{metric}_actual": 2.0,
            f"{metric}_estimate": 1.0,
            f"{metric}_actual_basis": "GAAP EPS",
            f"{metric}_estimate_basis": "GAAP EPS",
        }, metric, "pending")

    pending = {
        "judgment": "EPS US$1.20 高於 MarketBeat 共識，EPS 優於預期；Revenue US$8B 低於市場共識，營收低於預期。公司現金流維持穩健。",
    }
    safe_pending = earnings_commentary(pending)
    assert "EPS 優於預期" not in safe_pending
    assert "營收低於預期" not in safe_pending
    assert "高於 MarketBeat 共識" not in safe_pending
    assert "低於市場共識" not in safe_pending
    assert "公司現金流維持穩健" in safe_pending
    assert "EPS：比較口徑待核實" in safe_pending
    assert "營收：比較口徑待核實" in safe_pending

    contradictory = {
        "judgment_engine_version": ENGINE_VERSION,
        "eps_comparison_status": "beat",
        "revenue_comparison_status": "pending",
        "judgment": "EPS 低於市場共識；Revenue 高於 Finviz 共識，營收優於預期。公司擴大資本支出。",
    }
    safe_contradictory = earnings_commentary(contradictory)
    assert "EPS 低於市場共識" not in safe_contradictory
    assert "營收優於預期" not in safe_contradictory
    assert "高於 Finviz 共識" not in safe_contradictory
    assert "公司擴大資本支出" in safe_contradictory
    assert "EPS：優於預期" in safe_contradictory
    assert "營收：比較口徑待核實" in safe_contradictory

    print("PASS: renderer version gating and earnings commentary consistency guard")


if __name__ == "__main__":
    main()
