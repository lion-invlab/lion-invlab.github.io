#!/usr/bin/env python3
"""Deterministic tests for the single-source earnings judgment engine."""
from earnings_judgment import (
    ENGINE_VERSION, apply_judgment, audit_record, evaluate_metric,
    migrate_legacy_record, render_status, render_summary, consensus_evidence_label,
)


def source(name):
    return {
        "name": name,
        "url": "https://example.com/earnings",
        "observed_at": "2026-11-13T04:30:00+08:00",
    }


def pit_snapshot(metric, value, basis, unit=None, snapshot_id="a" * 64):
    source_url = "https://example.com/earnings"
    observed_at = "2026-11-13T04:30:00+08:00"
    return {
        "snapshot_id": snapshot_id,
        "event_id": "earn-test-1",
        "ticker": "EX",
        "metric": metric,
        "source_level": 3,
        "provider": "Investing.com",
        "source_url": source_url,
        "observed_at": observed_at,
        "data_as_of": "2026-11-12",
        "published_at": None,
        "event_date": "2026-11-14T10:00:00+08:00",
        "period": "Q3 2026",
        "period_end_date": "2026-09-30",
        "value": value,
        "statistic": "mean",
        "currency": "USD",
        "unit": unit,
        "basis_code": basis,
        "analyst_count": 12,
        "raw_response_ref": "raw/earnings/example.json",
        "raw_response_sha256": "c" * 64,
        "snapshot_status": "pre_release_eligible",
        "reason": "data_as_of_and_observed_at_before_event",
    }


def base_record():
    eps_id = "a" * 64
    revenue_id = "b" * 64
    return {
        "id": "earn-test-1",
        "ticker": "EX",
        "event_date": "2026-11-14T10:00:00+08:00",
        "eps_consensus_snapshots": [pit_snapshot("EPS", 1.00, "US_GAAP_DILUTED_EPS", snapshot_id=eps_id)],
        "revenue_consensus_snapshots": [pit_snapshot("REVENUE", 8.7, "US_GAAP_NET_SALES", "USD_BILLION", revenue_id)],
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
        "consensus_source": {**source("Consensus provider"), "snapshot_id": eps_id},
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
        "revenue_consensus_source": {**source("Revenue consensus provider"), "snapshot_id": revenue_id},
    }


def check(actual, expected, label):
    assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"


def main():
    item = base_record()
    check(evaluate_metric(item, "eps")["status"], "beat", "EPS beat")
    check(evaluate_metric(item, "revenue")["status"], "beat", "revenue beat")
    check(consensus_evidence_label(item, "eps"), "Provider PIT 公告前共識", "provider evidence label")
    tac_label_item = base_record()
    tac_label_item["eps_consensus_snapshots"][0]["snapshot_status"] = "tac_observed_pre_release_eligible"
    tac_label_item["eps_consensus_snapshots"][0]["data_as_of"] = None
    check(consensus_evidence_label(tac_label_item, "eps"), "TAC 公告前觀測共識", "TAC observed evidence label")

    tac_item = base_record()
    tac_observed = dict(tac_item["eps_consensus_snapshots"][0], data_as_of=None,
                        snapshot_status="tac_observed_pre_release_eligible",
                        reason="immutable_tac_capture_before_event_without_provider_as_of")
    tac_item["eps_consensus_snapshots"] = [tac_observed]
    check(evaluate_metric(tac_item, "eps")["status"], "beat",
          "immutable TAC-observed pre-release capture can support a tiered judgment")

    late_item = base_record()
    post_release_tac_capture = dict(late_item["eps_consensus_snapshots"][0],
                                    data_as_of=None,
                                    observed_at="2026-11-15T04:30:00+08:00",
                                    snapshot_status="tac_observed_pre_release_eligible")
    late_item["eps_consensus_snapshots"] = [post_release_tac_capture]
    check(evaluate_metric(late_item, "eps")["status"], "pending",
          "post-release TAC capture cannot support a directional judgment")

    item["eps_actual"] = -0.13
    item["eps_estimate"] = -0.72
    adjusted_snapshot_id = "d" * 64
    item["eps_consensus_snapshots"][0]["snapshot_id"] = adjusted_snapshot_id
    item["eps_consensus_snapshots"][0]["value"] = -0.72
    item["consensus_source"]["snapshot_id"] = adjusted_snapshot_id
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
    missing_snapshot = dict(item)
    missing_snapshot.pop("eps_consensus_snapshots")
    check(evaluate_metric(missing_snapshot, "eps")["status"], "pending", "directional status requires linked PIT snapshot")

    item = base_record()
    published_after_event = dict(item["eps_consensus_snapshots"][0], published_at="2026-11-15T00:00:00+08:00")
    item["eps_consensus_snapshots"] = [published_after_event]
    check(evaluate_metric(item, "eps")["status"], "pending", "known post-release publication cannot authorize Beat/Miss")

    item = base_record()
    future_asof = dict(item["eps_consensus_snapshots"][0], data_as_of="2026-11-14T12:00:00+08:00")
    item["eps_consensus_snapshots"] = [future_asof]
    check(evaluate_metric(item, "eps")["status"], "pending", "provider as-of cannot postdate collector observation")

    item = base_record()
    late_snapshot = dict(item["eps_consensus_snapshots"][0], observed_at="2026-11-15T04:30:00+08:00")
    item["eps_consensus_snapshots"] = [late_snapshot]
    check(evaluate_metric(item, "eps")["status"], "pending", "post-release capture cannot authorize Beat/Miss")

    item = base_record()
    mismatched_snapshot = dict(item["eps_consensus_snapshots"][0], value=1.01)
    item["eps_consensus_snapshots"] = [mismatched_snapshot]
    check(evaluate_metric(item, "eps")["status"], "pending", "snapshot value must match rendered estimate")

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

    legacy_f = {
        "ticker": "FERG",
        # This synthetic case explicitly supplies the consensus fiscal period;
        # without it the corrected migration must leave the judgment pending.
        "eps_estimate_period": "Q3 2026",
        "eps_actual": 3.43,
        "eps_estimate": 3.31,
        "eps_actual_basis": "Adjusted diluted EPS (non-GAAP; USD/share)",
        "eps_estimate_basis": "Adjusted diluted EPS consensus (USD/share)",
        "eps_currency": "USD",
        "reporting_period": "Q3 2026",
        "source": source("Issuer"),
        "consensus_source": source("Consensus"),
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
    check(migrated_f["eps_comparison_status"], "pending", "legacy consensus without immutable PIT snapshot cannot authorize Beat/Miss")
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
