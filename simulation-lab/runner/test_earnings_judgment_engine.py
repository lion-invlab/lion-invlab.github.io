#!/usr/bin/env python3
"""Deterministic tests for the single-source earnings judgment engine."""
from earnings_judgment import (
    ENGINE_VERSION, apply_judgment, audit_record, evaluate_metric,
    migrate_legacy_record, render_status, render_summary,
)


def source(name):
    return {
        "name": name,
        "url": "https://example.com/earnings",
        "observed_at": "2026-11-13T04:30:00+08:00",
    }


def consensus_source(metric):
    return {
        "name": "LSEG I/B/E/S",
        "url": f"https://example.com/{metric.lower()}-consensus",
        "observed_at": "2026-11-13T04:30:00+08:00",
        "source_level": 1,
    }


def consensus_attempt(metric, period, value, currency, basis_code, unit=None):
    item = {
        "source_level": 1,
        "provider": "LSEG I/B/E/S",
        "metric": metric.upper(),
        "url": f"https://example.com/{metric.lower()}-consensus",
        "observed_at": "2026-11-13T04:30:00+08:00",
        "data_as_of": "2026-11-12T20:00:00+08:00",
        "period": period,
        "value": value,
        "currency": currency,
        "basis_code": basis_code,
        "statistic": "primary_consensus",
        "outcome": "adopted",
        "reason": "valid_pre_release_same_basis_consensus",
    }
    if unit is not None:
        item["unit"] = unit
    return item


def base_record():
    return {
        "reporting_period": "Q3 2026",
        "event_date": "2026-11-13T12:00:00+08:00",
        "eps_actual": 1.20,
        "eps_estimate": 1.00,
        "eps_actual_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_estimate_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_actual_currency": "USD",
        "eps_estimate_currency": "USD",
        "eps_actual_period": "Q3 2026",
        "eps_estimate_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": consensus_source("eps"),
        "eps_consensus_attempts": [consensus_attempt("EPS", "Q3 2026", 1.00, "USD", "US_GAAP_DILUTED_EPS")],
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
        "revenue_consensus_source": consensus_source("revenue"),
        "revenue_consensus_attempts": [consensus_attempt("REVENUE", "Q3 2026", 8.7, "USD", "US_GAAP_NET_SALES", "USD_BILLION")],
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
    item["eps_actual_basis_code"] = "UNREGISTERED_BASIS"
    check(evaluate_metric(item, "eps")["status"], "pending", "unregistered basis code is not comparable")

    item = base_record()
    apply_judgment(item, "2026-11-13T13:00:00+08:00")
    check(item["judgment_engine_version"], ENGINE_VERSION, "engine version persisted")
    check(render_status(item, "eps"), "beat", "renderer reads persisted result")
    check("EPS：" in render_summary(item), True, "summary persisted")
    check(audit_record(item), [], "engine output passes audit")
    corrupted = dict(item)
    corrupted["eps_surprise"] = 999
    check(any("eps_stored_surprise_differs_from_engine_result" == x for x in audit_record(corrupted)), True, "audit rejects stale surprise")
    corrupted = dict(item)
    corrupted["eps_comparison_reason"] = "manual_override"
    check(any("eps_stored_reason_differs_from_engine_result" == x for x in audit_record(corrupted)), True, "audit rejects manual reason override")
    corrupted = dict(item)
    corrupted["earnings_comparison_summary"] = "EPS：低於預期；營收：優於預期"
    check(any("stored_summary_differs_from_engine_result" == x for x in audit_record(corrupted)), True, "audit rejects contradictory summary")

    legacy_f = {
        "ticker": "FERG",
        "eps_actual": 3.43,
        "eps_estimate": 3.31,
        "eps_actual_basis": "Adjusted diluted EPS (non-GAAP; USD/share)",
        "eps_estimate_basis": "Adjusted diluted EPS consensus (USD/share)",
        "eps_currency": "USD",
        "reporting_period": "Q3 2026",
        "eps_estimate_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": consensus_source("eps"),
        "eps_consensus_attempts": [consensus_attempt("EPS", "Q3 2026", 3.31, "USD", "NON_GAAP_ADJUSTED_DILUTED_EPS")],
        "revenue_actual": 9.026,
        "revenue_estimate": 8.74,
        "revenue_actual_basis": "GAAP net sales (USD billions)",
        "revenue_estimate_basis": "Net sales/revenue consensus (USD billions)",
        "revenue_currency": "USD",
        "revenue_unit": "B",
        "revenue_consensus_source": source("Revenue consensus"),
    }
    migrated_f = migrate_legacy_record(legacy_f)
    check(migrated_f["eps_actual_basis_code"], "NON_GAAP_ADJUSTED_DILUTED_EPS", "legacy EPS basis mapped")
    check(migrated_f["eps_estimate_period"], "Q3 2026", "explicit consensus period preserved")
    check(migrated_f["eps_comparison_status"], "beat", "legacy EPS comparison migrated only with explicit consensus period")
    period_missing = dict(legacy_f)
    period_missing.pop("eps_estimate_period")
    migrated_period_missing = migrate_legacy_record(period_missing)
    check(migrated_period_missing["eps_actual_period"], "Q3 2026", "issuer reporting period maps only to actual period")
    check(migrated_period_missing["eps_estimate_period"], None, "issuer reporting period is never copied to consensus period")
    check(migrated_period_missing["eps_comparison_status"], "pending", "missing consensus period blocks directional judgment")
    check(migrated_f["revenue_comparison_status"], "pending", "ambiguous legacy revenue basis remains pending")
    check(migrated_f["eps_actual_currency"], "USD", "EPS actual currency parsed from basis evidence")
    check(migrated_f["eps_estimate_currency"], "USD", "EPS estimate currency parsed from basis evidence")
    check(migrated_f["revenue_actual_unit"], "USD_BILLION", "revenue actual unit parsed from basis evidence")
    check(migrated_f["revenue_estimate_unit"], "USD_BILLION", "revenue estimate unit parsed from basis evidence")
    check("eps_actual_basis_code" not in legacy_f, True, "migration preview does not mutate source")

    legacy_q = {
        "ticker": "QBTS",
        "eps_actual": -0.13,
        "eps_estimate": -0.1002,
        "eps_actual_basis": "GAAP net loss per share, basic and diluted (USD/share)",
        "eps_estimate_basis": "GAAP EPS consensus (USD/share)",
        "eps_currency": "USD",
        "reporting_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": source("Consensus"),
    }
    migrated_q = migrate_legacy_record(legacy_q)
    check(migrated_q["eps_comparison_status"], "pending", "ambiguous dilution basis does not inherit legacy Miss")

    currency_only = {
        "eps_actual": 1.2,
        "eps_estimate": 1.0,
        "eps_actual_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_estimate_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_currency": "USD",
        "eps_actual_period": "Q3 2026",
        "eps_estimate_period": "Q3 2026",
        "reporting_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": source("Consensus"),
    }
    migrated_currency_only = migrate_legacy_record(currency_only)
    check(migrated_currency_only["eps_comparison_status"], "pending", "single legacy currency is not duplicated across actual and estimate")

    legacy_onon = {
        "ticker": "ONON",
        "eps_actual": 0.48,
        "eps_estimate": 0.48,
        "eps_actual_basis": "GAAP diluted EPS (USD/share)",
        "eps_estimate_basis": "GAAP diluted EPS consensus (USD/share)",
        "eps_currency": "CHF actual; USD estimate (not comparable)",
        "reporting_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": source("Consensus"),
    }
    migrated_onon = migrate_legacy_record(legacy_onon)
    check(migrated_onon["eps_comparison_status"], "incomparable", "legacy dual-currency field is parsed safely")

    legacy = base_record()
    legacy["eps_comparison_status"] = "beat"
    check(render_status(legacy, "eps"), "pending", "renderer rejects unversioned legacy status")
    check("舊版" in render_summary(legacy), True, "legacy narrative is not treated as a verified verdict")
    check("legacy_or_missing_judgment_engine_version" in audit_record(legacy), True, "legacy record flagged")

    print("PASS: normalized basis, currency, period, unit, sources, consensus conflict, negative EPS, renderer gating")


if __name__ == "__main__":
    main()
