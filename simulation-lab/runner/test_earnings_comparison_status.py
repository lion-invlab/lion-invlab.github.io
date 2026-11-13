#!/usr/bin/env python3
"""Renderer contract: display persisted judgment only; never derive Beat/Miss."""
from earnings_judgment import ENGINE_VERSION
from build_review_html import earnings_comparison_status


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

    print("PASS: HTML renderer only displays versioned judgment-engine output")


if __name__ == "__main__":
    main()
