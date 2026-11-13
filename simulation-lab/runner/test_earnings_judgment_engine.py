#!/usr/bin/env python3
"""Deterministic tests for the single-source earnings judgment engine."""
from earnings_judgment import (
    ENGINE_VERSION, apply_judgment, audit_record, evaluate_metric,
    render_status, render_summary,
)


def source(name):
    return {
        "name": name,
        "url": "https://example.com/earnings",
        "observed_at": "2026-11-13T04:30:00+08:00",
    }


def base_record():
    return {
        "reporting_period": "Q3 2026",
        "eps_actual": 1.20,
        "eps_estimate": 1.00,
        "eps_actual_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_estimate_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_actual_currency": "USD",
        "eps_estimate_currency": "USD",
        "eps_actual_period": "Q3 2026",
        "eps_estimate_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": source("Consensus provider"),
        "revenue_actual": 9.2,
        "revenue_estimate": 8.7,
        "revenue_actual_basis_code": "US_GAAP_NET_SALES",
        "revenue_estimate_basis_code": "US_GAAP_NET_SALES",
        "revenue_actual_currency": "USD",
        "revenue_estimate_currency": "USD",
        "revenue_actual_period": "Q3 2026",
        "revenue_estimate_period": "Q3 2026",
        "revenue_actual_unit": "USD_BILLION",
        "revenue_estimate_unit": "USD_BILLION",
        "revenue_consensus_source": source("Revenue consensus provider"),
    }


def check(actual, expected, label):
    assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"


def main():
    item = base_record()
    check(evaluate_metric(item, "eps")["status"], "beat", "EPS beat")
    check(evaluate_metric(item, "revenue")["status"], "beat", "revenue beat")

    item["eps_actual"] = -0.13
    item["eps_estimate"] = -0.72
    check(evaluate_metric(item, "eps")["status"], "beat", "smaller loss is beat")

    item = base_record()
    item["eps_actual"] = 0.95
    item["eps_estimate"] = 1.00
    check(evaluate_metric(item, "eps")["status"], "miss", "EPS miss")

    item = base_record()
    item["eps_actual"] = 1.001
    item["eps_estimate"] = 1.00
    item["eps_inline_tolerance_abs"] = 0.002
    check(evaluate_metric(item, "eps")["status"], "inline", "declared inline tolerance")

    item = base_record()
    item["eps_estimate_basis_code"] = "NON_GAAP_ADJUSTED_DILUTED_EPS"
    check(evaluate_metric(item, "eps")["status"], "incomparable", "basis mismatch")

    item = base_record()
    item["eps_estimate_currency"] = "EUR"
    check(evaluate_metric(item, "eps")["status"], "incomparable", "currency mismatch")

    item = base_record()
    item["eps_estimate_period"] = "Q2 2026"
    check(evaluate_metric(item, "eps")["status"], "incomparable", "period mismatch")

    item = base_record()
    item["revenue_estimate_unit"] = "USD_MILLION"
    check(evaluate_metric(item, "revenue")["status"], "incomparable", "unit mismatch")

    item = base_record()
    item.pop("eps_actual_basis_code")
    item["eps_comparison_status"] = "beat"
    check(evaluate_metric(item, "eps")["status"], "pending", "legacy status cannot override missing basis")

    item = base_record()
    item["revenue_consensus_source"] = None
    check(evaluate_metric(item, "revenue")["status"], "pending", "missing consensus source")

    item = base_record()
    item["eps_consensus_conflict"] = True
    check(evaluate_metric(item, "eps")["status"], "consensus_divergent", "consensus divergence")

    item = base_record()
    item["eps_actual"] = True
    check(evaluate_metric(item, "eps")["status"], "pending", "boolean is not a numeric result")

    item = base_record()
    apply_judgment(item, "2026-11-13T13:00:00+08:00")
    check(item["judgment_engine_version"], ENGINE_VERSION, "engine version persisted")
    check(render_status(item, "eps"), "beat", "renderer reads persisted result")
    check("EPS：" in render_summary(item), True, "summary persisted")
    check(audit_record(item), [], "engine output passes audit")

    legacy = base_record()
    legacy["eps_comparison_status"] = "beat"
    check(render_status(legacy, "eps"), "pending", "renderer rejects unversioned legacy status")
    check("舊版" in render_summary(legacy), True, "legacy narrative is not treated as a verified verdict")
    check("legacy_or_missing_judgment_engine_version" in audit_record(legacy), True, "legacy record flagged")

    print("PASS: normalized basis, currency, period, unit, sources, consensus conflict, negative EPS, renderer gating")


if __name__ == "__main__":
    main()
