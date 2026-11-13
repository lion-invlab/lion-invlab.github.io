#!/usr/bin/env python3
"""Single-source TAC earnings comparison engine.

This module is the only component allowed to calculate EPS/revenue Beat/Miss.
HTML assembly must call render_status/render_summary only; it must never infer a
comparison from raw numbers or free-text basis descriptions.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
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
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_RESERVED_CODES = {"UNKNOWN", "UNVERIFIED", "NOT_DISCLOSED", "OTHER", "N_A", "NA"}


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def _valid_code(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(_CODE_RE.fullmatch(value))
        and value not in _RESERVED_CODES
    )


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
        and isinstance(observed_at, str)
        and bool(observed_at.strip())
    )


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

    actual_basis = record.get(f"{metric}_actual_basis_code")
    estimate_basis = record.get(f"{metric}_estimate_basis_code")
    if not _valid_code(actual_basis) or not _valid_code(estimate_basis):
        return _result("pending", "missing_verified_normalized_basis_code", actual, estimate)
    if actual_basis != estimate_basis:
        return _result("incomparable", "basis_code_mismatch", actual, estimate)

    actual_currency = record.get(f"{metric}_actual_currency")
    estimate_currency = record.get(f"{metric}_estimate_currency")
    if not _valid_currency(actual_currency) or not _valid_currency(estimate_currency):
        return _result("pending", "missing_or_invalid_separate_currency", actual, estimate)
    if actual_currency != estimate_currency:
        return _result("incomparable", "currency_mismatch", actual, estimate)

    actual_period = record.get(f"{metric}_actual_period")
    estimate_period = record.get(f"{metric}_estimate_period")
    if not isinstance(actual_period, str) or not actual_period.strip():
        return _result("pending", "missing_actual_reporting_period", actual, estimate)
    if not isinstance(estimate_period, str) or not estimate_period.strip():
        return _result("pending", "missing_consensus_reporting_period", actual, estimate)
    if actual_period.strip().casefold() != estimate_period.strip().casefold():
        return _result("incomparable", "reporting_period_mismatch", actual, estimate)

    if metric == "revenue":
        actual_unit = record.get("revenue_actual_unit")
        estimate_unit = record.get("revenue_estimate_unit")
        if not isinstance(actual_unit, str) or not actual_unit.strip():
            return _result("pending", "missing_actual_revenue_unit", actual, estimate)
        if not isinstance(estimate_unit, str) or not estimate_unit.strip():
            return _result("pending", "missing_consensus_revenue_unit", actual, estimate)
        if actual_unit.strip().casefold() != estimate_unit.strip().casefold():
            return _result("incomparable", "revenue_unit_mismatch", actual, estimate)

    actual_source = record.get("source")
    consensus_key = "consensus_source" if metric == "eps" else "revenue_consensus_source"
    consensus_source = record.get(consensus_key)
    if not _valid_source(actual_source):
        return _result("pending", "missing_actual_source_url_or_observed_at", actual, estimate)
    if not _valid_source(consensus_source):
        return _result("pending", "missing_consensus_source_url_or_observed_at", actual, estimate)

    if record.get(f"{metric}_consensus_conflict") is True:
        return _result("consensus_divergent", "verified_consensus_sources_diverge", actual, estimate)

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
    """Return data-quality issues without mutating the source record."""
    issues = []
    version = record.get("judgment_engine_version")
    if version != ENGINE_VERSION:
        issues.append("legacy_or_missing_judgment_engine_version")
    for metric in ("eps", "revenue"):
        stored = record.get(f"{metric}_comparison_status")
        computed = evaluate_metric(record, metric)["status"]
        if stored in DIRECTIONAL_STATUSES and computed not in DIRECTIONAL_STATUSES:
            issues.append(f"{metric}_directional_status_not_supported_by_v2_evidence")
        elif version == ENGINE_VERSION and stored != computed:
            issues.append(f"{metric}_stored_status_differs_from_engine_result")
    return issues
