#!/usr/bin/env python3
"""Renderer contract: display persisted judgment only and guard editorial claims."""
from earnings_judgment import ENGINE_VERSION
from build_review_html import earnings_comparison_status, earnings_commentary
from calendar_source_guard import _earnings_records


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
        "event_date": "2026-11-12T21:00:00+08:00",
        "status": "released",
        "reporting_period": "Q3 2026",
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
        "consensus_source": evidence_source("EPS consensus"),
        "revenue_consensus_source": evidence_source("Revenue consensus"),
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
    assert result["consensus_source"]["name"] == "EPS consensus"
    assert result["revenue_consensus_source"]["name"] == "Revenue consensus"
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
