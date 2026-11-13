#!/usr/bin/env python3
"""Tests for rendering and commentary consistency with persisted engine results."""
from tac_earnings_judgment import ENGINE_VERSION
from tac_earnings_render import earnings_comparison_status, earnings_commentary


def main():
    for metric in ("eps", "revenue"):
        for status in ("beat", "miss", "inline", "pending", "incomparable", "consensus_divergent"):
            assert earnings_comparison_status({
                f"{metric}_comparison_status": status,
                "judgment_engine_version": ENGINE_VERSION,
            }, metric) == status
        assert earnings_comparison_status({f"{metric}_comparison_status": "beat"}, metric) == "pending"

    pending = {
        "judgment": "EPS US$1.20 高於 MarketBeat 共識，EPS 優於預期；Revenue US$8B 低於市場共識，營收低於預期。公司現金流維持穩健。",
    }
    safe = earnings_commentary(pending)
    assert "EPS 優於預期" not in safe
    assert "營收低於預期" not in safe
    assert "公司現金流維持穩健" in safe
    assert "EPS：比較口徑待核實" in safe
    assert "營收：比較口徑待核實" in safe

    conflict = {
        "judgment_engine_version": ENGINE_VERSION,
        "eps_comparison_status": "beat",
        "revenue_comparison_status": "pending",
        "judgment": "EPS 低於市場共識；Revenue 高於 Finviz 共識，營收優於預期。公司擴大資本支出。",
    }
    safe = earnings_commentary(conflict)
    assert "EPS 低於市場共識" not in safe
    assert "營收優於預期" not in safe
    assert "公司擴大資本支出" in safe
    assert "EPS：優於預期" in safe
    assert "營收：比較口徑待核實" in safe
    print("PASS: earnings renderer status and commentary consistency")


if __name__ == "__main__":
    main()
