#!/usr/bin/env python3
"""Map Investing.com Fed Rate Monitor captures to TAC's two approved outcomes.

Mapping is accepted only when the selected next meeting has exactly two
outcomes: the current target range (hold) and exactly +25bp (one hike).
Any cut, extra outcome, missing current range or stale capture remains pending.
"""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Any

def parse_rate_range(value: Any) -> tuple[float, float]:
    if not isinstance(value, str):
        raise ValueError("rate range must be a string")
    match = re.fullmatch(r"\s*(\d+\.\d{2,3})\s*-\s*(\d+\.\d{2,3})\s*%?\s*", value)
    if not match:
        raise ValueError(f"invalid target rate range: {value!r}")
    lower, upper = float(match.group(1)), float(match.group(2))
    if upper <= lower:
        raise ValueError(f"invalid target rate range order: {value!r}")
    return lower, upper

def adapt_capture(capture: dict[str, Any], report_date: str) -> tuple[dict | None, dict | None, str | None]:
    if not isinstance(capture, dict):
        return None, None, "Fed Rate Monitor capture is not an object"
    if capture.get("provider") != "Investing.com Fed Rate Monitor" or capture.get("role") != "primary":
        return None, None, "capture is not from the WR-designated primary Fed Rate Monitor"
    if capture.get("status") != "captured_for_review":
        return None, None, capture.get("error") or "Investing.com Fed Rate Monitor capture is pending"
    validation = capture.get("validation")
    if not isinstance(validation, dict) or not all(validation.get(k) for k in (
        "is_monitor", "has_meeting_probabilities"
    )):
        return None, None, "Fed Rate Monitor capture failed source validation"
    try:
        report_day = date.fromisoformat(report_date)
        observed_at = datetime.fromisoformat(capture["observed_at"].replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            raise ValueError("page observation timestamp must include timezone")
        source_updated_raw = capture.get("source_updated_at_iso")
        source_updated = None
        if source_updated_raw:
            source_updated = datetime.fromisoformat(source_updated_raw.replace("Z", "+00:00"))
            if source_updated.tzinfo is None:
                raise ValueError("source update timestamp must include timezone")
        current_range = parse_rate_range(capture["current_target_range"])
    except Exception as exc:
        return None, None, str(exc)

    candidates = []
    for meeting in capture.get("meetings", []):
        try:
            meeting_day = datetime.strptime(meeting["meeting_date"], "%b %d, %Y").date()
        except Exception:
            continue
        if meeting_day >= report_day:
            candidates.append((meeting_day, meeting))
    if not candidates:
        return None, None, "no upcoming FOMC meeting distribution found"
    meeting_day, meeting = min(candidates, key=lambda item: item[0])
    rows = meeting.get("probabilities")
    if not isinstance(rows, list) or len(rows) != 2:
        return None, None, "next FOMC meeting does not have exactly two outcomes"
    by_range = {}
    for row in rows:
        if not isinstance(row, dict):
            return None, None, "invalid probability row"
        try:
            rate = parse_rate_range(row.get("target_rate"))
        except Exception as exc:
            return None, None, str(exc)
        probability = row.get("probability")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0 <= probability <= 100:
            return None, None, "FedWatch probability is outside 0-100"
        if rate in by_range:
            return None, None, "duplicate target rate range"
        by_range[rate] = float(probability)
    if abs(sum(by_range.values()) - 100.0) > 0.2:
        return None, None, "FedWatch probabilities do not sum to 100"

    hold_rate = current_range
    hike_rate = (round(current_range[0] + 0.25, 3), round(current_range[1] + 0.25, 3))
    normalized_rates = {(round(k[0], 3), round(k[1], 3)): v for k, v in by_range.items()}
    if set(normalized_rates) != {hold_rate, hike_rate}:
        return None, None, "outcomes are not exactly current target range plus one 25bp hike; refusing to infer hold/hike labels"
    hold_probability = normalized_rates[hold_rate]
    hike_probability = normalized_rates[hike_rate]
    current_label = f"{current_range[0]:.2f}-{current_range[1]:.2f}%"
    hike_label = f"{hike_rate[0]:.2f}-{hike_rate[1]:.2f}%"
    source_url = capture.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        return None, None, "Fed Rate Monitor source URL is missing or not HTTPS"
    provider = "Investing.com Fed Rate Monitor"
    updated_at = observed_at.isoformat()
    source_update_note = (
        f"provider Updated label={source_updated.isoformat()}"
        if source_updated is not None else "provider Updated label unavailable"
    )
    normalized = {
        "target_meeting": meeting_day.isoformat(),
        "updated_at": updated_at,
        "source": {"name": provider, "url": source_url},
        "probabilities": [
            {"rate_range": current_label, "probability": hold_probability},
            {"rate_range": hike_label, "probability": hike_probability},
        ],
        "status": "verified",
        "notes": (
            f"Investing.com Fed Rate Monitor primary capture; meeting={meeting_day.isoformat()}; "
            f"current target range={current_label}; observed_at={updated_at}; {source_update_note}; "
            "two outcomes explicitly mapped to current range (hold) and current range +25bp (one hike)."
        ),
    }
    renderer = {
        "probabilities": {
            "hold": {"probability": hold_probability, "rate_range": current_label},
            "hike_one": {"probability": hike_probability, "rate_range": hike_label},
        },
        "target_meeting": meeting_day.isoformat(),
        "updated_at": updated_at,
        "target_rate_range": current_label,
        "audit_text": normalized["notes"],
        "aria_label": (
            f"FedWatch {meeting_day.isoformat()}: hold {hold_probability:.1f} percent; "
            f"one 25 basis point hike {hike_probability:.1f} percent"
        ),
    }
    return normalized, renderer, None
