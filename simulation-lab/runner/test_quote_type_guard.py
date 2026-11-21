#!/usr/bin/env python3
"""Regression tests for the SIM-1.4 cash-index versus CFD render boundary."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
from build_review_html import reject_cfd_cash_index_quotes, earnings_status_label, normalize_market_label


def record(value, change, quote_type):
    return {
        "display": value,
        "change_display": change,
        "source": {
            "name": "Investing.com historical data",
            "url": "https://example.invalid/historical",
            "data_date": "2026-11-20",
            "quote_type": quote_type,
        },
    }


def main():
    data = {
        "global_markets": {
            "S&P 500 CFD": record("6,500.00", "-3.70%", "cfd_index_reference_series"),
            "Dow cash index": record("48,147.33", "-1.93%", "cash_index_close"),
            "Nasdaq provider series": record("22,617.73", "-5.28%", "provider_index_reference_series"),
        }
    }
    rejected = reject_cfd_cash_index_quotes(data)
    assert rejected == ["S&P 500 CFD"], rejected
    cfd = data["global_markets"]["S&P 500 CFD"]
    assert cfd["display"] == "待核實" and cfd["change_display"] == "待核實"
    assert cfd["qa_status"] == "cfd_index_reference_rejected"
    assert cfd["rejected_reference"]["display"] == "6,500.00"
    assert data["global_markets"]["Dow cash index"]["display"] == "48,147.33"
    assert data["global_markets"]["Nasdaq provider series"]["display"] == "22,617.73"
    # Idempotence: a second pass must not reintroduce the rejected numeric quote.
    assert reject_cfd_cash_index_quotes(data) == ["S&P 500 CFD"]
    assert cfd["display"] == "待核實"
    assert normalize_market_label("日經225") == normalize_market_label("日經 225")
    assert normalize_market_label("日經　225") == normalize_market_label("日經225")
    assert earnings_status_label({"eps_actual": 2.70, "eps_estimate": None}, "eps", "pending") == "比較資料尚未齊備"
    assert earnings_status_label({"status": "pending_verification"}, "eps", "pending") == "公告已發布；實際值待核實"
    assert earnings_status_label({}, "eps", "pending") == "尚未公布"
    print("PASS: explicit CFD index references are rejected; cash/provider series remain unchanged")


if __name__ == "__main__":
    main()
