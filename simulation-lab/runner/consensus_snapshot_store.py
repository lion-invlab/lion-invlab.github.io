#!/usr/bin/env python3
"""Append-only PIT consensus snapshot helpers for the isolated TAC schema-v2 prototype."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PROVIDER_BY_LEVEL = {
    1: "LSEG I/B/E/S",
    2: "FactSet Estimates",
    3: "Investing.com",
}
LEVEL_BY_PROVIDER = {v: k for k, v in PROVIDER_BY_LEVEL.items()}
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _raw_bytes(raw_response: str | bytes | dict | list) -> bytes:
    if isinstance(raw_response, bytes):
        return raw_response
    if isinstance(raw_response, str):
        return raw_response.encode("utf-8")
    return json.dumps(raw_response, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def archive_raw_response(raw_response: str | bytes | dict | list, archive_root: str | Path, relative_prefix: str) -> tuple[str, str]:
    """Write a raw response once under its content hash; never overwrite a different payload."""
    payload = _raw_bytes(raw_response)
    digest = hashlib.sha256(payload).hexdigest()
    root = Path(archive_root)
    rel = Path(relative_prefix) / f"{digest}.json"
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != payload:
            raise ValueError(f"immutable raw-response collision: {rel.as_posix()}")
    else:
        with target.open("xb") as handle:
            handle.write(payload)
    return rel.as_posix(), digest


def _parse_temporal(value: Any, field: str):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO date or datetime")
    raw = value.strip().replace("Z", "+00:00")
    if re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", raw):
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(f"{field} must be ISO-8601 date or timezone-aware datetime") from exc
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} datetime must include an explicit timezone")
        return parsed
    except ValueError as exc:
        if "must include an explicit timezone" in str(exc):
            raise
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601 date or timezone-aware datetime") from exc


def _cutoff_status(data_as_of: str | None, event_date: str) -> tuple[str, str]:
    if not data_as_of:
        return "pending_cutoff_time", "missing_data_as_of"
    asof = _parse_temporal(data_as_of, "data_as_of")
    event = _parse_temporal(event_date, "event_date")
    if isinstance(asof, datetime) and isinstance(event, datetime):
        if asof.astimezone(timezone.utc) < event.astimezone(timezone.utc):
            return "pre_release_eligible", "data_as_of_before_event"
        return "not_pre_release", "data_as_of_at_or_after_event"
    asof_date = asof.date() if isinstance(asof, datetime) else asof
    event_day = event.date() if isinstance(event, datetime) else event
    if asof_date < event_day:
        return "pre_release_eligible", "data_as_of_date_before_event_date"
    if asof_date > event_day:
        return "not_pre_release", "data_as_of_date_after_event_date"
    return "pending_cutoff_time", "same_day_date_only_cannot_prove_pre_release"


def build_consensus_snapshot(
    event: dict,
    metric: str,
    attempt: dict,
    raw_response: str | bytes | dict | list,
    raw_response_ref: str | None,
) -> dict:
    metric = metric.upper()
    if metric not in {"EPS", "REVENUE"}:
        raise ValueError("metric must be EPS or REVENUE")
    event_id = event.get("id")
    event_date = event.get("event_date")
    ticker = event.get("ticker")
    if not all(isinstance(x, str) and x.strip() for x in (event_id, event_date, ticker)):
        raise ValueError("event id, ticker, and event_date are required")

    level = attempt.get("source_level")
    provider = attempt.get("provider")
    if isinstance(level, bool) or not isinstance(level, int) or level not in PROVIDER_BY_LEVEL or PROVIDER_BY_LEVEL[level] != provider:
        raise ValueError("provider must match the fixed SIM-1.2 source level")
    observed_at = attempt.get("observed_at")
    _parse_temporal(observed_at, "observed_at")
    data_as_of = attempt.get("data_as_of")
    if data_as_of:
        _parse_temporal(data_as_of, "data_as_of")

    raw = _raw_bytes(raw_response)
    raw_sha = hashlib.sha256(raw).hexdigest()
    if not SHA256_RE.fullmatch(raw_sha):
        raise ValueError("raw response SHA-256 calculation failed")

    status, reason = _cutoff_status(data_as_of, event_date)
    value = attempt.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        value = None
    currency = attempt.get("currency")
    if not isinstance(currency, str) or not CURRENCY_RE.fullmatch(currency):
        currency = None
    period = attempt.get("period")
    period = period.strip() if isinstance(period, str) and period.strip() else None
    period_end_date = attempt.get("period_end_date")
    period_end_date = period_end_date.strip() if isinstance(period_end_date, str) and period_end_date.strip() else None
    statistic = attempt.get("statistic")
    statistic = statistic.strip() if isinstance(statistic, str) and statistic.strip() else None
    basis_code = attempt.get("basis_code")
    basis_code = basis_code.strip() if isinstance(basis_code, str) and basis_code.strip() else None
    unit = attempt.get("unit")
    unit = unit.strip() if isinstance(unit, str) and unit.strip() else None
    analyst_count = attempt.get("analyst_count")
    if isinstance(analyst_count, bool) or not isinstance(analyst_count, int) or analyst_count < 0:
        analyst_count = None
    source_url = attempt.get("url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        source_url = None

    missing = []
    for key, val in (("source_url", source_url), ("period", period), ("period_end_date", period_end_date),
                     ("value", value), ("currency", currency), ("statistic", statistic), ("basis_code", basis_code)):
        if val is None:
            missing.append(key)
    if metric == "REVENUE" and unit is None:
        missing.append("unit")
    if not isinstance(raw_response_ref, str) or not raw_response_ref.strip():
        missing.append("raw_response_ref")
    if status == "pre_release_eligible" and missing:
        status, reason = "pending_required_fields", "missing:" + ",".join(missing)

    identity = {
        "event_id": event_id, "metric": metric, "provider": provider,
        "data_as_of": data_as_of, "period": period, "period_end_date": period_end_date,
        "statistic": statistic, "value": value, "currency": currency, "unit": unit,
        "basis_code": basis_code, "raw_response_sha256": raw_sha,
    }
    snapshot_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "snapshot_id": snapshot_id,
        "event_id": event_id,
        "ticker": ticker,
        "metric": metric,
        "source_level": level,
        "provider": provider,
        "source_url": source_url,
        "observed_at": observed_at,
        "data_as_of": data_as_of,
        "provider_recalculated_at": attempt.get("provider_recalculated_at"),
        "event_date": event_date,
        "period": period,
        "period_end_date": period_end_date,
        "value": value,
        "statistic": statistic,
        "currency": currency,
        "unit": unit,
        "basis_code": basis_code,
        "analyst_count": analyst_count,
        "raw_response_ref": raw_response_ref,
        "raw_response_sha256": raw_sha,
        "snapshot_status": status,
        "reason": reason,
    }


def append_consensus_snapshot(event: dict, snapshot: dict) -> bool:
    """Append without replacing history. Returns False for an identical snapshot."""
    metric = snapshot.get("metric")
    if metric not in {"EPS", "REVENUE"}:
        raise ValueError("snapshot metric must be EPS or REVENUE")
    if snapshot.get("event_id") != event.get("id"):
        raise ValueError("snapshot event_id does not match target event")
    snapshot_id = snapshot.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not SHA256_RE.fullmatch(snapshot_id):
        raise ValueError("snapshot_id must be a SHA-256 hex digest")
    key = "eps_consensus_snapshots" if metric == "EPS" else "revenue_consensus_snapshots"
    history = event.setdefault(key, [])
    if not isinstance(history, list):
        raise ValueError(f"{key} must be an array")
    if any(isinstance(x, dict) and x.get("snapshot_id") == snapshot_id for x in history):
        return False
    history.append(dict(snapshot))
    return True
