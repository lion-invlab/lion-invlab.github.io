#!/usr/bin/env python3
"""Regression tests for earnings Beat/Miss gating; no unsupported basis inference."""
from build_review_html import earnings_comparison_status


def check(item, metric, expected):
    actual = earnings_comparison_status(item, metric)
    assert actual == expected, f"{metric}: expected {expected!r}, got {actual!r} for {item!r}"


def main():
    for status in ("beat", "miss", "inline"):
        check({f"eps_comparison_status": status}, "eps", status)

    check({
        "revenue_actual": 9.2,
        "revenue_estimate": 8.7,
        "revenue_actual_basis": "GAAP revenue USD bn",
        "revenue_estimate_basis": "GAAP revenue USD bn",
    }, "revenue", "beat")
    check({
        "eps_actual": 0.8,
        "eps_estimate": 1.0,
        "eps_actual_basis": "GAAP diluted EPS",
        "eps_estimate_basis": "GAAP diluted EPS",
    }, "eps", "miss")
    check({
        "eps_actual": 1.2,
        "eps_estimate": 1.0,
        "eps_actual_basis": "GAAP diluted EPS",
        "eps_estimate_basis": "adjusted EPS",
    }, "eps", "pending")
    check({
        "eps_actual": 1.2,
        "eps_estimate": 1.0,
    }, "eps", "pending")
    check({
        "eps_actual": True,
        "eps_estimate": 1.0,
        "eps_actual_basis": "GAAP diluted EPS",
        "eps_estimate_basis": "GAAP diluted EPS",
    }, "eps", "pending")
    print("PASS: earnings Beat/Miss requires an explicit decision or identical verified bases")


if __name__ == "__main__":
    main()
