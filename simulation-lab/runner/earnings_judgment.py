#!/usr/bin/env python3
"""Single-source TAC earnings comparison engine.

This module is the only component allowed to calculate EPS/revenue Beat/Miss.
HTML assembly must call render_status/render_summary only; it must never infer a
comparison from raw numbers or free-text basis descriptions.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import datetime
import re
from typing import Any

ENGINE_VERSION = "1.0.0"
VALID_STATUSES = {
    "beat", "miss", "inline", "pending", "incomparable", "consensus_divergent"
}
DIRECTIONAL_STATUSES = {"beat", "miss", "inline"}
STATUS_LABELS = {
    "beat": "優於預期",
    "miss": "低於預期",
    "inline": "符合預期",
    "pending": "資料／比較口徑待核實",
    "incomparable": "比較口徑不相容",
    "consensus_divergent": "市場共識來源分歧",
}
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
EPS_BASIS_CODES = frozenset({
    "US_GAAP_DILUTED_EPS",
    "US_GAAP_BASIC_EPS",
    "US_GAAP_BASIC_AND_DILUTED_EPS",
    "IFRS_DILUTED_EPS",
    "IFRS_BASIC_EPS",
    "IFRS_ATTRIBUTABLE_EPS",
    "IFRS_ADJUSTED_DILUTED_EPS",
    "IFRS_ADJUSTED_BASIC_EPS",
    "NON_GAAP_ADJUSTED_DILUTED_EPS",
    "NON_GAAP_ADJUSTED_BASIC_EPS",
    "NON_GAAP_ADJUSTED_UNSPECIFIED_EPS",
    "NON_GAAP_DILUTED_EPS",
    "NON_GAAP_BASIC_EPS",
    "ISSUER_DEFINED_ADJUSTED_EPS",
})
REVENUE_BASIS_CODES = frozenset({
    "US_GAAP_TOTAL_REVENUE",
    "US_GAAP_NET_SALES",
    "US_GAAP_OPERATING_REVENUE",
    "IFRS_TOTAL_REVENUE",
    "IFRS_NET_SALES",
    "IFRS_REVENUE",
    "ISSUER_DEFINED_REVENUE_METRIC",
})


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def _valid_code(value: Any, metric: str) -> bool:
    registry = EPS_BASIS_CODES if metric == "eps" else REVENUE_BASIS_CODES
    return isinstance(value, str) and value in registry


def _valid_currency(value: Any) -> bool:
    return isinstance(value, str) and bool(_CURRENCY_RE.fullmatch(value))


def _valid_source(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    url = value.get("url")
    observed_at = value.get("observed_at")
    return (
        isinstance(url, str)
        and url.startswith("https://")
        and _parse_aware_datetime(observed_at) is not None
    )



_SOURCE_LEVELS = {
    1: "LSEG I/B/E/S",
    2: "FactSet Estimates",
    3: "Investing.com",
}


def _parse_aware_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _consensus_attempt_issue(record: dict, metric: str, estimate: Decimal) -> str | None:
    """Enforce the SIM-1.2 source ladder and bind the selected estimate to its evidence."""
    attempts = record.get(f"{metric}_consensus_attempts")
    if not isinstance(attempts, list) or not attempts:
        return "missing_consensus_source_attempt_history"
    if len(attempts) > 3:
        return "too_many_consensus_source_attempts"

    expected_metric = "EPS" if metric == "eps" else "REVENUE"
    levels = []
    adopted = []
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            return "invalid_consensus_source_attempt_record"
        level = attempt.get("source_level")
        if level not in _SOURCE_LEVELS or attempt.get("provider") != _SOURCE_LEVELS[level]:
            return "consensus_source_level_provider_mismatch"
        levels.append(level)
        if attempt.get("metric") != expected_metric:
            return "consensus_attempt_metric_mismatch"
        if _parse_aware_datetime(attempt.get("observed_at")) is None:
            return "consensus_attempt_missing_aware_observed_at"
        outcome = attempt.get("outcome")
        if outcome not in {"adopted", "unavailable", "unreadable", "not_pre_release", "missing_required_fields", "incompatible"}:
            return "invalid_consensus_attempt_outcome"
        if not isinstance(attempt.get("reason"), str) or not attempt["reason"].strip():
            return "consensus_attempt_missing_reason"
        if outcome == "adopted":
            adopted.append((index, attempt))

    if levels != list(range(1, len(levels) + 1)):
        return "consensus_source_levels_not_sequential"
    if len(adopted) > 1:
        return "multiple_consensus_sources_adopted"
    if adopted:
        index, selected = adopted[0]
        if index != len(attempts) - 1:
            return "source_search_continued_after_valid_consensus"
        if not isinstance(selected.get("url"), str) or not selected["url"].startswith("https://"):
            return "adopted_consensus_missing_source_url"
        as_of = _parse_aware_datetime(selected.get("data_as_of"))
        event_time = _parse_aware_datetime(record.get("event_date"))
        if as_of is None:
            return "adopted_consensus_missing_aware_data_as_of"
        if event_time is None:
            return "missing_aware_earnings_event_time_for_point_in_time_consensus"
        if as_of >= event_time:
            return "consensus_snapshot_not_before_earnings_release"
        if str(selected.get("period") or "").strip().casefold() != str(record.get(f"{metric}_estimate_period") or "").strip().casefold():
            return "consensus_attempt_period_differs_from_estimate_period"
        if _decimal(selected.get("value")) != estimate:
            return "consensus_attempt_value_differs_from_selected_estimate"
        if selected.get("currency") != record.get(f"{metric}_estimate_currency"):
            return "consensus_attempt_currency_differs_from_estimate"
        if selected.get("basis_code") != record.get(f"{metric}_estimate_basis_code"):
            return "consensus_attempt_basis_differs_from_estimate"
        if metric == "revenue" and selected.get("unit") != record.get("revenue_estimate_unit"):
            return "consensus_attempt_unit_differs_from_estimate"
        source_key = "consensus_source" if metric == "eps" else "revenue_consensus_source"
        selected_source = record.get(source_key)
        if not isinstance(selected_source, dict):
            return "missing_selected_consensus_source_object"
        if selected_source.get("url") != selected.get("url"):
            return "selected_consensus_url_differs_from_attempt_history"
        if selected_source.get("name") != selected.get("provider"):
            return "selected_consensus_provider_differs_from_attempt_history"
        if selected_source.get("source_level") != selected.get("source_level"):
            return "selected_consensus_level_differs_from_attempt_history"
        return None

    if len(attempts) != 3:
        return "consensus_source_ladder_stopped_before_all_unavailable"
    source_key = "consensus_source" if metric == "eps" else "revenue_consensus_source"
    if record.get(source_key) is not None:
        return "selected_consensus_source_present_without_adopted_attempt"
    return "no_usable_consensus_after_all_priority_sources"

def _result(status: str, reason: str, actual=None, estimate=None) -> dict:
    difference = actual - estimate if actual is not None and estimate is not None else None
    surprise_pct = None
    if difference is not None and estimate != 0:
        surprise_pct = float((difference / abs(estimate)) * Decimal("100"))
    return {
        "status": status,
        "reason": reason,
        "surprise": float(difference) if difference is not None else None,
        "surprise_pct": surprise_pct,
    }


def audit_consensus_attempts(record: dict, metric: str) -> str | None:
    """Audit the required source ladder even when actual/estimate values are missing."""
    if metric not in {"eps", "revenue"}:
        raise ValueError(f"unsupported earnings metric: {metric!r}")
    estimate = _decimal(record.get(f"{metric}_estimate"))
    return _consensus_attempt_issue(record, metric, estimate if estimate is not None else Decimal("0"))

def evaluate_metric(record: dict, metric: str) -> dict:
    """Evaluate one metric using explicit normalized evidence only.

    Required v2 fields:
      {metric}_actual_basis_code, {metric}_estimate_basis_code
      {metric}_actual_currency, {metric}_estimate_currency
      {metric}_actual_period, {metric}_estimate_period
      {metric}_actual, {metric}_estimate
      source / consensus_source (or revenue_consensus_source)
    Revenue additionally requires revenue_actual_unit/revenue_estimate_unit.
    """
    if metric not in {"eps", "revenue"}:
        raise ValueError(f"unsupported earnings metric: {metric!r}")

    actual = _decimal(record.get(f"{metric}_actual"))
    estimate = _decimal(record.get(f"{metric}_estimate"))
    if actual is None or estimate is None:
        return _result("pending", "missing_or_invalid_actual_or_consensus")

    # Explicit non-comparability evidence outranks missing metadata. A known
    # currency, period, or unit mismatch is sufficient to prohibit a directional
    # judgment even when the accounting-basis code is not yet available.
    actual_currency = record.get(f"{metric}_actual_currency")
    estimate_currency = record.get(f"{metric}_estimate_currency")
    currencies_valid = _valid_currency(actual_currency) and _valid_currency(estimate_currency)
    if currencies_valid and actual_currency != estimate_currency:
        return _result("incomparable", "currency_mismatch", actual, estimate)

    actual_period = record.get(f"{metric}_actual_period")
    estimate_period = record.get(f"{metric}_estimate_period")
    periods_valid = (
        isinstance(actual_period, str) and bool(actual_period.strip())
        and isinstance(estimate_period, str) and bool(estimate_period.strip())
    )
    if periods_valid and actual_period.strip().casefold() != estimate_period.strip().casefold():
        return _result("incomparable", "reporting_period_mismatch", actual, estimate)

    actual_unit = estimate_unit = None
    units_valid = True
    if metric == "revenue":
        actual_unit = record.get("revenue_actual_unit")
        estimate_unit = record.get("revenue_estimate_unit")
        units_valid = (
            isinstance(actual_unit, str) and bool(actual_unit.strip())
            and isinstance(estimate_unit, str) and bool(estimate_unit.strip())
        )
        if units_valid and actual_unit.strip().casefold() != estimate_unit.strip().casefold():
            return _result("incomparable", "revenue_unit_mismatch", actual, estimate)

    # A verified, unresolved disagreement between consensus sources must
    # not be collapsed into a directional result or hidden behind missing basis.
    consensus_key = "consensus_source" if metric == "eps" else "revenue_consensus_source"
    if record.get(f"{metric}_consensus_conflict") is True:
        if _valid_source(record.get("source")) and _valid_source(record.get(consensus_key)):
            return _result("consensus_divergent", "verified_consensus_sources_diverge", actual, estimate)

    actual_basis = record.get(f"{metric}_actual_basis_code")
    estimate_basis = record.get(f"{metric}_estimate_basis_code")
    if not _valid_code(actual_basis, metric) or not _valid_code(estimate_basis, metric):
        return _result("pending", "missing_or_unrecognized_normalized_basis_code", actual, estimate)
    if actual_basis != estimate_basis:
        return _result("incomparable", "basis_code_mismatch", actual, estimate)

    if not currencies_valid:
        return _result("pending", "missing_or_invalid_separate_currency", actual, estimate)
    if not periods_valid:
        if not isinstance(actual_period, str) or not actual_period.strip():
            return _result("pending", "missing_actual_reporting_period", actual, estimate)
        return _result("pending", "missing_consensus_reporting_period", actual, estimate)
    if metric == "revenue" and not units_valid:
        if not isinstance(actual_unit, str) or not actual_unit.strip():
            return _result("pending", "missing_actual_revenue_unit", actual, estimate)
        return _result("pending", "missing_consensus_revenue_unit", actual, estimate)

    actual_source = record.get("source")
    consensus_key = "consensus_source" if metric == "eps" else "revenue_consensus_source"
    consensus_source = record.get(consensus_key)
    if not _valid_source(actual_source):
        return _result("pending", "missing_actual_source_url_or_observed_at", actual, estimate)

    attempt_issue = _consensus_attempt_issue(record, metric, estimate)
    if attempt_issue:
        return _result("pending", attempt_issue, actual, estimate)
    if not _valid_source(consensus_source):
        return _result("pending", "missing_consensus_source_url_or_observed_at", actual, estimate)

    tolerance = _decimal(record.get(f"{metric}_inline_tolerance_abs"))
    if tolerance is None:
        tolerance = Decimal("0")
    if tolerance < 0:
        return _result("pending", "invalid_negative_inline_tolerance", actual, estimate)

    difference = actual - estimate
    if abs(difference) <= tolerance:
        return _result("inline", "within_declared_source_precision_tolerance", actual, estimate)
    if difference > 0:
        return _result("beat", "actual_above_comparable_consensus", actual, estimate)
    return _result("miss", "actual_below_comparable_consensus", actual, estimate)


def _legacy_basis_code(metric: str, label: Any) -> str | None:
    """Conservatively map a descriptive v1 basis label to a controlled v2 code."""
    if not isinstance(label, str) or not label.strip():
        return None
    text = re.sub(r"[^a-z0-9]+", " ", label.casefold()).strip()

    if metric == "eps":
        # Narrative summaries sometimes mention both the selected EPS and a
        # separately disclosed GAAP/adjusted alternative. Such mixed labels
        # are not a single comparable basis and must never be guessed.
        plain_gaap_text = text.replace("non gaap", "")
        if (
            ("gaap" in plain_gaap_text and ("non gaap" in text or "adjusted" in text or "normalized" in text))
            or ("ifrs" in text and "non ifrs" in text and ("adjusted" in text or "normalized" in text))
        ):
            return None
        if "gaap" in text and "non gaap" not in text:
            if "basic" in text and "diluted" in text:
                return "US_GAAP_BASIC_AND_DILUTED_EPS"
            if "diluted" in text:
                return "US_GAAP_DILUTED_EPS"
            if "basic" in text:
                return "US_GAAP_BASIC_EPS"
            return None
        if "ifrs" in text:
            if "adjusted" in text and "diluted" in text:
                return "IFRS_ADJUSTED_DILUTED_EPS"
            if "adjusted" in text and "basic" in text:
                return "IFRS_ADJUSTED_BASIC_EPS"
            if "diluted" in text:
                return "IFRS_DILUTED_EPS"
            if "basic" in text:
                return "IFRS_BASIC_EPS"
            if "attributable" in text:
                return "IFRS_ATTRIBUTABLE_EPS"
            return None
        if "non gaap" in text or "adjusted" in text or "normalized" in text:
            if "diluted" in text:
                return "NON_GAAP_ADJUSTED_DILUTED_EPS" if ("adjusted" in text or "normalized" in text) else "NON_GAAP_DILUTED_EPS"
            if "basic" in text:
                return "NON_GAAP_ADJUSTED_BASIC_EPS" if ("adjusted" in text or "normalized" in text) else "NON_GAAP_BASIC_EPS"
            if "adjusted" in text or "normalized" in text:
                return "NON_GAAP_ADJUSTED_UNSPECIFIED_EPS"
        return None

    if metric == "revenue":
        if ("gaap" in text and "non gaap" in text) or ("ifrs" in text and "non ifrs" in text):
            return None
        if "gaap" in text and any(term in text for term in ("core revenue", "organic revenue", "adjusted revenue")):
            return None
        revenue_definitions = sum(term in text for term in ("operating revenue", "net sales", "total revenue"))
        if revenue_definitions > 1:
            return None
        if "gaap" in text:
            if "operating revenue" in text:
                return "US_GAAP_OPERATING_REVENUE"
            if "net sales" in text:
                return "US_GAAP_NET_SALES"
            if "total revenue" in text or "revenue" in text:
                return "US_GAAP_TOTAL_REVENUE"
            return None
        if "ifrs" in text:
            if "net sales" in text:
                return "IFRS_NET_SALES"
            if "total revenue" in text or "revenue" in text:
                return "IFRS_TOTAL_REVENUE"
            return None
    return None


def _split_legacy_currency(value: Any) -> tuple[str | None, str | None]:
    """Only split a legacy field when it explicitly distinguishes actual and estimate."""
    if not isinstance(value, str):
        return None, None
    match = re.fullmatch(
        r"\s*([A-Z]{3})\s+actual\s*;\s*([A-Z]{3})\s+estimate(?:\s*\([^)]*\))?\s*",
        value.strip(),
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).upper(), match.group(2).upper()
    # A single legacy currency is ambiguous and must not be copied to both sides.
    return None, None


def _currency_from_basis_label(label: Any) -> str | None:
    if not isinstance(label, str):
        return None
    match = re.search(
        r"\b(USD|EUR|GBP|CHF|CAD|AUD|JPY|CNY|INR|BRL|SGD|HKD|KRW|TWD|MXN|SEK|NOK|DKK|NZD|ZAR|ILS|SAR|AED|PLN|CZK|HUF|TRY|IDR|THB|MYR|PHP|CLP|COP|PEN)\s*(?:/share|per share|billion|billions|million|millions|bn|mm)\b",
        label,
        flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def _revenue_unit_from_basis_label(label: Any) -> str | None:
    if not isinstance(label, str):
        return None
    text = label.casefold()
    currency = _currency_from_basis_label(label)
    if not currency:
        return None
    if re.search(r"\b(billions?|bn)\b", text):
        return f"{currency}_BILLION"
    if re.search(r"\b(millions?|mm)\b", text):
        return f"{currency}_MILLION"
    return None


def _fill_if_missing(record: dict, key: str, value: Any) -> None:
    """Fill null/blank legacy slots from explicit evidence without overwriting populated values."""
    current = record.get(key)
    if current is None or (isinstance(current, str) and not current.strip()):
        record[key] = value

def migrate_legacy_record(record: dict, observed_at: str = "migration-preview") -> dict:
    """Create an in-memory v2 migration preview; never writes the source JSON."""
    migrated = dict(record)
    migrated["legacy_eps_comparison_status"] = record.get("eps_comparison_status")
    migrated["legacy_revenue_comparison_status"] = record.get("revenue_comparison_status")

    for metric in ("eps", "revenue"):
        # Only the dedicated actual-basis field is admissible. Legacy eps_basis is a narrative/comment field and may mix GAAP, adjusted and consensus descriptions.
        actual_label = record.get(f"{metric}_actual_basis")
        estimate_label = record.get(f"{metric}_estimate_basis")
        _fill_if_missing(migrated, f"{metric}_actual_basis_code", _legacy_basis_code(metric, actual_label))
        _fill_if_missing(migrated, f"{metric}_estimate_basis_code", _legacy_basis_code(metric, estimate_label))
        actual_currency, estimate_currency = _split_legacy_currency(
            record.get(f"{metric}_currency")
        )
        if actual_currency is None:
            actual_currency = _currency_from_basis_label(actual_label)
        if estimate_currency is None:
            estimate_currency = _currency_from_basis_label(estimate_label)
        _fill_if_missing(migrated, f"{metric}_actual_currency", actual_currency)
        _fill_if_missing(migrated, f"{metric}_estimate_currency", estimate_currency)
        # reporting_period describes the issuer's reported quarter only.
        # Never copy it to the consensus side: the provider's estimate period
        # must be captured independently or the comparison remains pending.
        actual_period = record.get(f"{metric}_actual_period")
        if not (isinstance(actual_period, str) and actual_period.strip()):
            actual_period = record.get("reporting_period")
        _fill_if_missing(migrated, f"{metric}_actual_period", actual_period)
        estimate_period = record.get(f"{metric}_estimate_period")
        _fill_if_missing(
            migrated,
            f"{metric}_estimate_period",
            estimate_period if isinstance(estimate_period, str) and estimate_period.strip() else None,
        )

    _fill_if_missing(migrated, "revenue_actual_unit", _revenue_unit_from_basis_label(record.get("revenue_actual_basis")))
    _fill_if_missing(migrated, "revenue_estimate_unit", _revenue_unit_from_basis_label(record.get("revenue_estimate_basis")))

    return apply_judgment(migrated, observed_at)


def apply_judgment(record: dict, observed_at: str) -> dict:
    """Write deterministic comparison fields to a record in the caller's data layer."""
    results = {}
    for metric in ("eps", "revenue"):
        result = evaluate_metric(record, metric)
        results[metric] = result
        record[f"{metric}_comparison_status"] = result["status"]
        record[f"{metric}_surprise"] = result["surprise"]
        record[f"{metric}_surprise_pct"] = result["surprise_pct"]
        record[f"{metric}_comparison_reason"] = result["reason"]
    record["judgment_engine_version"] = ENGINE_VERSION
    record["judgment_timestamp"] = observed_at
    record["earnings_comparison_summary"] = (
        f"EPS：{STATUS_LABELS[results['eps']['status']]}；"
        f"營收：{STATUS_LABELS[results['revenue']['status']]}"
    )
    return record


def render_status(record: dict, metric: str) -> str:
    """Read a persisted engine result. Never calculate or infer in the renderer."""
    if metric not in {"eps", "revenue"}:
        raise ValueError(f"unsupported earnings metric: {metric!r}")
    if record.get("judgment_engine_version") != ENGINE_VERSION:
        return "pending"
    status = record.get(f"{metric}_comparison_status")
    return status if status in VALID_STATUSES else "pending"


def render_summary(record: dict) -> str:
    """Render only a summary persisted by this engine version."""
    if record.get("judgment_engine_version") != ENGINE_VERSION:
        return "EPS／營收預期比較待統一口徑驗證；舊版自由文字判讀暫不作為 Beat／Miss 結論。"
    summary = record.get("earnings_comparison_summary")
    return summary if isinstance(summary, str) and summary.strip() else (
        "EPS／營收預期比較待核實。"
    )


def audit_record(record: dict) -> list[str]:
    """Recompute and audit every persisted judgment field without mutation."""
    issues = []
    version = record.get("judgment_engine_version")
    if version != ENGINE_VERSION:
        issues.append("legacy_or_missing_judgment_engine_version")

    results = {}
    for metric in ("eps", "revenue"):
        computed = evaluate_metric(record, metric)
        results[metric] = computed
        stored_status = record.get(f"{metric}_comparison_status")
        if stored_status in DIRECTIONAL_STATUSES and computed["status"] not in DIRECTIONAL_STATUSES:
            issues.append(f"{metric}_directional_status_not_supported_by_v2_evidence")
        if version == ENGINE_VERSION:
            if stored_status != computed["status"]:
                issues.append(f"{metric}_stored_status_differs_from_engine_result")
            if record.get(f"{metric}_comparison_reason") != computed["reason"]:
                issues.append(f"{metric}_stored_reason_differs_from_engine_result")
            if record.get(f"{metric}_surprise") != computed["surprise"]:
                issues.append(f"{metric}_stored_surprise_differs_from_engine_result")
            if record.get(f"{metric}_surprise_pct") != computed["surprise_pct"]:
                issues.append(f"{metric}_stored_surprise_pct_differs_from_engine_result")

    if version == ENGINE_VERSION:
        expected_summary = (
            f"EPS：{STATUS_LABELS[results['eps']['status']]}；"
            f"營收：{STATUS_LABELS[results['revenue']['status']]}"
        )
        if record.get("earnings_comparison_summary") != expected_summary:
            issues.append("stored_summary_differs_from_engine_result")
    return issues
