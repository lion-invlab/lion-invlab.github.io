#!/usr/bin/env python3
"""Convert schema-validated TAC market snapshots into renderer display strings.

No quote is invented: pending/missing/closed records become explicit labels.
Verified FedWatch probabilities require a separately mapped renderer payload;
the normalized schema's rate-range array is never guessed into outcome labels.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any

GROUP_DECIMALS = {
    "global_indices": 2, "sectors": 2, "bonds": 2,
    "energy": 2, "precious_metals": 2,
}
FX_DECIMALS = {
    "dxy": 2, "usd_twd": 4, "eur_usd": 5,
    "gbp_usd": 5, "aud_usd": 5, "usd_jpy": 3,
}
RENDER_GROUPS = (
    "global_indices", "sectors", "bonds", "fx", "energy", "precious_metals",
)

def number_text(value: Any, decimals: int, thousands: bool = True) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("verified market value must be numeric")
    return format(value, f",.{decimals}f" if thousands else f".{decimals}f")

def change_text(value: Any, unit: Any, decimals: int = 2) -> str:
    if value is None:
        return "待核實"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("verified market change must be numeric")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("verified market change is missing its change_unit")
    normalized = unit.strip().casefold().replace(" ", "_")
    suffixes = {
        "percent": "%", "percentage": "%", "pct": "%", "%": "%",
        "basis_points": " bp", "basis_point": " bp", "bps": " bp", "bp": " bp",
        "index_points": " 點", "index_point": " 點", "points": " 點", "point": " 點",
    }
    if normalized not in suffixes:
        raise ValueError(f"unsupported change_unit {unit!r}; refusing to guess display suffix")
    if value == 0:
        return f"{number_text(value, decimals, False)}{suffixes[normalized]}"
    sign = "+" if value > 0 else "−"
    return f"{sign}{number_text(abs(value), decimals, False)}{suffixes[normalized]}"

def display_value(group: str, key: str, record: dict[str, Any]) -> str:
    status = record.get("status")
    if status == "market_closed":
        return "休市"
    if status != "verified":
        return "待核實"
    value = record.get("value")
    decimals = FX_DECIMALS.get(key, 2) if group == "fx" else (
        1 if group == "risk_indicators" and key == "cnn_fear_greed" else GROUP_DECIMALS.get(group, 2)
    )
    rendered = number_text(value, decimals)
    unit = str(record.get("unit", "")).casefold()
    if group == "bonds" and ("percent" in unit or "%" in unit):
        rendered += "%"
    return rendered

def display_change(record: dict[str, Any], decimals: int = 2) -> str:
    status = record.get("status")
    if status == "market_closed":
        return "休市"
    if status != "verified":
        return "待核實"
    return change_text(record.get("change"), record.get("change_unit"), decimals)

def pending_fedwatch(notes: str | None) -> dict[str, Any]:
    audit = notes.strip() if isinstance(notes, str) and notes.strip() else "FedWatch 資料待核實；不顯示推測機率。"
    return {
        "status": "pending_verification",
        "probabilities": {
            "hold": {"probability": 0.0, "rate_range": "待核實"},
            "hike_one": {"probability": 0.0, "rate_range": "待核實"},
        },
        "target_meeting": "待核實",
        "updated_at": "待核實",
        "target_rate_range": "待核實",
        "audit_text": audit,
        "aria_label": "FedWatch 機率待核實",
    }

def adapt_market_snapshot(snapshot: dict[str, Any],
                          renderer_fedwatch: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError("market snapshot must be an object")
    result = deepcopy(snapshot)
    for group in RENDER_GROUPS:
        records = result.get(group)
        if not isinstance(records, dict):
            raise ValueError(f"market snapshot missing group {group}")
        for key, record in records.items():
            if not isinstance(record, dict):
                raise ValueError(f"{group}.{key}: record must be an object")
            record["value"] = display_value(group, key, record)
            record["change"] = display_change(record)
    risk = result.get("risk_indicators")
    if not isinstance(risk, dict):
        raise ValueError("market snapshot missing risk_indicators")
    for key, record in risk.items():
        if not isinstance(record, dict):
            raise ValueError(f"risk_indicators.{key}: record must be an object")
        record["value"] = display_value("risk_indicators", key, record)
        record["change"] = display_change(record)
    fedwatch = snapshot.get("fedwatch")
    if not isinstance(fedwatch, dict):
        raise ValueError("market snapshot missing fedwatch")
    status = fedwatch.get("status")
    if status in {"pending_verification", "missing"}:
        if renderer_fedwatch is not None:
            raise ValueError("renderer FedWatch override supplied while normalized FedWatch is not verified")
        result["fedwatch"] = pending_fedwatch(fedwatch.get("notes"))
    elif status == "verified":
        if renderer_fedwatch is None:
            raise ValueError("verified FedWatch requires an explicit outcome-mapped renderer payload; rate-range order is not inferred")
        result["fedwatch"] = deepcopy(renderer_fedwatch)
    else:
        raise ValueError(f"unsupported normalized FedWatch status: {status!r}")
    return result
