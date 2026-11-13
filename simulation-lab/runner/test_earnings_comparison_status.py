#!/usr/bin/env python3
"""Renderer contract: display persisted judgment only and guard editorial claims."""
from earnings_judgment import ENGINE_VERSION
from build_review_html import earnings_comparison_status, earnings_commentary
from calendar_source_guard import _earnings_records


def consensus_source(metric):
    return {
        "name": "LSEG I/B/E/S",
        "url": f"https://example.com/{metric.lower()}-consensus",
        "observed_at": "2026-11-13T12:00:00+08:00",
        "source_level": 1,
    }


def consensus_attempt(metric, value, basis_code, unit=None):
    item = {
        "source_level": 1,
        "provider": "LSEG I/B/E/S",
        "metric": metric.upper(),
        "url": f"https://example.com/{metric.lower()}-consensus",
        "observed_at": "2026-11-13T12:00:00+08:00",
        "data_as_of": "2026-11-12T20:00:00+08:00",
        "period": "Q3 2026",
        "value": value,
        "currency": "USD",
        "basis_code": basis_code,
        "statistic": "primary_consensus",
        "outcome": "adopted",
        "reason": "valid_pre_release_same_basis_consensus",
    }
    if unit is not None:
        item["unit"] = unit
    return item


def check(item, metric, expected):
    actual = earnings_comparison_status(item, metric)
    assert actual == expected, f"{metric}: expected {expected!r}, got {actual!r}"



def test_calendar_projection_migrates_legacy_records():
    def evidence_source(name):
        return {
            "name": name,
            "url": "https://example.com/earnings-evidence",
            "observed_at": "2026-11-13T12:00:00+08:00",
        }

    record = {
        "id": "earn-test-1",
        "company": "Example Corp",
        "ticker": "EX",
        "event_date": "2026-11-13T13:00:00+08:00",
        "status": "released",
        "reporting_period": "Q3 2026",
        "eps_estimate_period": "Q3 2026",
        "revenue_estimate_period": "Q3 2026",
        "eps_actual": 1.20,
        "eps_estimate": 1.00,
        "eps_actual_basis": "US GAAP diluted EPS (USD/share)",
        "eps_estimate_basis": "US GAAP diluted EPS consensus (USD/share)",
        "eps_currency": "USD",
        "revenue_actual": 9.2,
        "revenue_estimate": 8.7,
        "revenue_actual_basis": "GAAP total revenue (USD billions)",
        "revenue_estimate_basis": "GAAP total revenue consensus (USD billions)",
        "revenue_currency": "USD",
        "revenue_unit": "B",
        "source": evidence_source("Issuer"),
        "consensus_source": consensus_source("eps"),
        "revenue_consensus_source": consensus_source("revenue"),
        "eps_consensus_attempts": [consensus_attempt("EPS", 1.00, "US_GAAP_DILUTED_EPS")],
        "revenue_consensus_attempts": [consensus_attempt("REVENUE", 8.7, "US_GAAP_TOTAL_REVENUE", "USD_BILLION")],
    }
    payload = {"events": {"earnings": [record]}}
    projected = _earnings_records(payload, observed_at="2026-11-13T13:00:00+08:00")
    result = projected[0]
    assert result["judgment_engine_version"] == ENGINE_VERSION
    assert result["eps_comparison_status"] == "beat"
    assert result["revenue_comparison_status"] == "beat"
    assert result["eps_actual_currency"] == "USD"
    assert result["revenue_actual_unit"] == "USD_BILLION"
    assert result["source"]["name"] == "Issuer"
    assert result["consensus_source"]["name"] == "LSEG I/B/E/S"
    assert result["revenue_consensus_source"]["name"] == "LSEG I/B/E/S"
    assert "judgment_engine_version" not in record, "projection must not mutate calendar source data"

    # The legacy calendar's eps_basis describes the reported actual EPS.
    # The adapter may map it to the actual side, but must not infer the
    # consensus basis or declare a directional result from one shared currency.
    legacy_actual_basis_only = {
        "eps_actual": 0.82,
        "eps_estimate": 0.79,
        "eps_basis": "Adjusted EPS (non-GAAP)",
        "eps_estimate_basis": "Adjusted EPS (non-GAAP) consensus",
        "eps_currency": "USD",
        "reporting_period": "2026 Q3",
        "source": evidence_source("Issuer"),
        "consensus_source": evidence_source("Consensus"),
    }
    migrated_basis = _earnings_records(
        {"events": {"earnings": [legacy_actual_basis_only]}},
        observed_at="2026-11-13T13:00:00+08:00",
    )[0]
    assert migrated_basis["eps_actual_basis_code"] == "NON_GAAP_ADJUSTED_UNSPECIFIED_EPS"
    assert migrated_basis["eps_estimate_basis_code"] == "NON_GAAP_ADJUSTED_UNSPECIFIED_EPS"
    assert migrated_basis["eps_comparison_status"] == "pending", (
        "a shared currency field alone must not authorize Beat/Miss"
    )

    explicit_actual_basis = dict(legacy_actual_basis_only)
    explicit_actual_basis["eps_actual_basis"] = "US GAAP diluted EPS"
    explicit_actual_basis_result = _earnings_records(
        {"events": {"earnings": [explicit_actual_basis]}},
        observed_at="2026-11-13T13:00:00+08:00",
    )[0]
    assert explicit_actual_basis_result["eps_actual_basis_code"] == "US_GAAP_DILUTED_EPS", (
        "an explicit metric-specific actual basis must take precedence over legacy eps_basis"
    )

    ambiguous_basis = dict(legacy_actual_basis_only)
    ambiguous_basis["eps_basis"] = (
        "Adjusted EPS US$0.82; GAAP diluted EPS US$0.80 also disclosed"
    )
    ambiguous_basis_result = _earnings_records(
        {"events": {"earnings": [ambiguous_basis]}},
        observed_at="2026-11-13T13:00:00+08:00",
    )[0]
    assert ambiguous_basis_result["eps_actual_basis_code"] is None, (
        "mixed GAAP and adjusted narrative must not be collapsed into one basis"
    )
    assert ambiguous_basis_result["eps_comparison_status"] == "pending"

    explicit_currency_mismatch = {
        "eps_actual": 0.48,
        "eps_estimate": 0.48,
        "eps_currency": "CHF actual; USD estimate (not comparable)",
        "revenue_actual": 0.9314,
        "revenue_estimate": 1.14,
        "revenue_currency": "CHF actual; USD estimate (not comparable)",
        "reporting_period": "Q3 2026",
        "source": evidence_source("Issuer"),
        "consensus_source": evidence_source("Consensus"),
        "revenue_consensus_source": evidence_source("Revenue consensus"),
    }
    currency_mismatch_result = _earnings_records(
        {"events": {"earnings": [explicit_currency_mismatch]}},
        observed_at="2026-11-13T13:00:00+08:00",
    )[0]
    assert currency_mismatch_result["eps_comparison_status"] == "incomparable"
    assert currency_mismatch_result["eps_comparison_reason"] == "currency_mismatch"
    assert currency_mismatch_result["revenue_comparison_status"] == "incomparable"
    assert currency_mismatch_result["revenue_comparison_reason"] == "currency_mismatch"
    assert currency_mismatch_result["eps_actual_display"] == "CHF 0.48"
    assert currency_mismatch_result["eps_estimate_display"] == "US$0.48"
    assert len(currency_mismatch_result["eps_consensus_attempts"]) == 0

    unresolved_revenue_consensus = {
        "revenue_actual": 9.47,
        "revenue_estimate": 8.42,
        "reporting_period": "2026 Q3",
        "source": evidence_source("Issuer"),
        "revenue_consensus_source": {
            **evidence_source("Finviz"),
            "notes": "營收共識 US$6.72B 與 Finviz US$8.42B 不一致；兩來源定義差異仍未解。",
        },
    }
    divergent_result = _earnings_records(
        {"events": {"earnings": [unresolved_revenue_consensus]}},
        observed_at="2026-11-13T13:00:00+08:00",
    )[0]
    assert divergent_result["revenue_consensus_conflict"] is True
    assert divergent_result["revenue_comparison_status"] == "consensus_divergent"
    assert divergent_result["revenue_comparison_reason"] == "verified_consensus_sources_diverge"

    same_basis_eps = {
        "eps_actual": -0.14,
        "eps_estimate": 0.06,
        "eps_actual_basis": "GAAP diluted loss per share (USD/share)",
        "eps_estimate_basis": "EPS consensus (USD/share; TipRanks reported actual/consensus pair)",
        "eps_currency": "USD",
        "reporting_period": "2026 Q3",
        "eps_estimate_period": "2026 Q3",
        "source": evidence_source("Issuer"),
        "consensus_source": {
            **evidence_source("TipRanks"),
            "notes": "公司 SEC 8-K 確認 GAAP diluted loss/share -US$0.14，採同口徑呈現 EPS Miss。",
        },
    }
    same_basis_result = _earnings_records(
        {"events": {"earnings": [same_basis_eps]}},
        observed_at="2026-11-13T13:00:00+08:00",
    )[0]
    assert same_basis_result["eps_estimate_basis_code"] is None, "free-text notes must not manufacture consensus basis"
    assert same_basis_result["eps_comparison_status"] == "pending"

    # A single shared currency label is display metadata, not proof that both
    # actual and estimate values use the same currency for comparison.
    unsafe = dict(record)
    unsafe["eps_actual_basis"] = "US GAAP diluted EPS"
    unsafe["eps_estimate_basis"] = "US GAAP diluted EPS consensus"
    unsafe["eps_currency"] = "USD"
    unsafe_payload = {"events": {"earnings": [unsafe]}}
    unsafe_result = _earnings_records(
        unsafe_payload, observed_at="2026-11-13T13:00:00+08:00"
    )[0]
    assert unsafe_result["eps_comparison_status"] == "pending"


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

    test_calendar_projection_migrates_legacy_records()
    print("PASS: renderer guard, calendar-to-v2 migration adapter, and earnings commentary consistency")


if __name__ == "__main__":
    main()
