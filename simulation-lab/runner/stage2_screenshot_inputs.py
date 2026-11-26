#!/usr/bin/env python3
"""Load date- and SHA-bound manual screenshot observations for Stage 2.

The sidecar records human-readable values transcribed from the screenshot. The
image itself remains the evidence; this module never performs OCR or invents
values. Screenshot values are immutable inputs and take precedence field by field.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ALLOWED_FIELDS = {"close", "change", "open", "high", "low", "score", "band"}
FIELD_NAMES = {
    "close": {"close", "price", "收盤", "收盤價", "收市", "價格"},
    "change": {"change %", "change", "漲跌（%）", "升跌（%）", "變動%", "漲跌幅"},
    "open": {"open", "開市", "開盤"},
    "high": {"high", "最高"},
    "low": {"low", "最低"},
    "score": {"score", "fear & greed", "恐懼貪婪指數", "指數分數"},
    "band": {"band", "rating", "情緒區間", "評級"},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



def _plain_number(value):
    text = str(value).strip().replace(",", "").replace("%", "").replace("+", "")
    try:
        return str(float(text)) if "." in text else str(int(text))
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"Screenshot numeric field is not parseable: {value!r}")


def apply_screenshot_values_to_fixture(fixture: dict, screenshot_inputs: dict) -> dict:
    """Apply screenshot values to the in-memory Fixture before expected-value construction."""
    for (group, name), row in screenshot_inputs.items():
        if group == "sectors":
            item = None
            source = (fixture.get("sector_sources") or {}).get(name)
        else:
            item = ((fixture.get(group) or {}).get(name))
            source = (item or {}).get("source")
        if not source:
            raise ValueError(f"Screenshot row has no fixture source: {group}/{name}")
        fields = row["fields"]
        if "close" in fields:
            value = _plain_number(fields["close"]["value"])
            if group == "sectors":
                source["history_close"] = value
            else:
                source["close_value"] = value
                source["history_close"] = value
                if item is not None:
                    item["display"] = str(fields["close"]["value"]).strip()
        if "change" in fields:
            value = _plain_number(fields["change"]["value"])
            if group == "sectors":
                source["history_change"] = value
                source["change_display"] = str(fields["change"]["value"]).strip()
                fixture["sectors"][name] = source["change_display"]
            else:
                source["daily_change_percent"] = value
                source["history_change"] = value
                if item is not None:
                    raw = str(fields["change"]["value"]).strip()
                    item["change_display"] = raw if "%" in raw else f"{raw}%"
        if "score" in fields:
            value = _plain_number(fields["score"]["value"])
            source["score_value"] = value
            source["source_score_value"] = value
            source["backup_source_score_value"] = value
            if item is not None:
                item["display"] = str(fields["score"]["value"]).strip()
        if "band" in fields:
            band = str(fields["band"]["value"]).strip()
            source["band"] = band
            if item is not None:
                item["change_display"] = band
        for field in ("open", "high", "low"):
            if field in fields:
                source[field] = _plain_number(fields[field]["value"])
        source["screenshot_observation_applied_at"] = row["captured_at"]
    return fixture


def load_screenshot_bundle(bundle_path: str | Path, fixture: dict,
                           repo_root: str | Path | None = None) -> dict:
    """Return {(group, name): row} after strict date/source/path/SHA validation."""
    path = Path(bundle_path)
    if not path.is_file():
        return {}
    root = Path(repo_root) if repo_root else Path.cwd()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("report_date") != fixture.get("report_date"):
        raise ValueError("Screenshot bundle report_date does not match fixture")
    if payload.get("trading_date") != fixture.get("trading_date"):
        raise ValueError("Screenshot bundle trading_date does not match fixture")

    result = {}
    for row in payload.get("observations") or []:
        group, name = row.get("group"), row.get("name")
        key = (group, name)
        if not group or not name or key in result:
            raise ValueError(f"Duplicate or incomplete screenshot observation key: {key}")
        source = ((fixture.get(group) or {}).get(name) or {}).get("source")
        if group == "sectors":
            source = (fixture.get("sector_sources") or {}).get(name)
        if not source:
            raise ValueError(f"Screenshot observation does not map to fixture row: {key}")
        if row.get("data_date") != fixture.get("trading_date"):
            raise ValueError(f"{key}: screenshot data_date does not match trading_date")
        if row.get("source_url") != source.get("url"):
            raise ValueError(f"{key}: screenshot source_url does not match fixture source contract")
        if not str(row.get("instrument_identity") or "").strip():
            raise ValueError(f"{key}: screenshot instrument_identity is required")

        evidence_path = Path(str(row.get("evidence_path") or ""))
        if not evidence_path.is_absolute():
            evidence_path = root / evidence_path
        try:
            resolved = evidence_path.resolve(strict=True)
            resolved.relative_to(root.resolve())
        except (OSError, ValueError):
            raise ValueError(f"{key}: screenshot evidence file missing or outside repository root")
        expected_sha = str(row.get("evidence_sha256") or "").lower()
        if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
            raise ValueError(f"{key}: screenshot evidence_sha256 is malformed")
        actual_sha = _sha256(resolved)
        if actual_sha != expected_sha:
            raise ValueError(f"{key}: screenshot evidence SHA-256 mismatch")
        captured_at = str(row.get("captured_at") or "").strip()
        if not captured_at:
            raise ValueError(f"{key}: screenshot captured_at is required")

        fields = row.get("fields") or {}
        if not fields or set(fields) - ALLOWED_FIELDS:
            raise ValueError(f"{key}: screenshot fields must use {sorted(ALLOWED_FIELDS)}")
        normalized_fields = {}
        for field, item in fields.items():
            if not isinstance(item, dict) or item.get("value") is None:
                raise ValueError(f"{key}/{field}: screenshot field value is missing")
            field_name = str(item.get("field_name") or "").strip()
            if field_name.casefold() not in {x.casefold() for x in FIELD_NAMES[field]}:
                raise ValueError(f"{key}/{field}: unsupported source field label {field_name!r}")
            normalized_fields[field] = {
                "value": item["value"],
                "field_name": field_name,
                "source_type": "USER_PROVIDED_SCREENSHOT",
                "evidence_path": str(resolved.relative_to(root.resolve())),
                "evidence_sha256": actual_sha,
                "captured_at": captured_at,
                "instrument_identity": row["instrument_identity"],
                "data_date": row["data_date"],
            }
        result[key] = {
            "group": group,
            "name": name,
            "source_url": row["source_url"],
            "data_date": row["data_date"],
            "instrument_identity": row["instrument_identity"],
            "fields": normalized_fields,
            "evidence_path": str(resolved.relative_to(root.resolve())),
            "evidence_sha256": actual_sha,
            "captured_at": captured_at,
        }
    return result
