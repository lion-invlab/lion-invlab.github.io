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
from decimal import Decimal, InvalidOperation


ALLOWED_FIELDS = {"close", "change", "open", "high", "low", "score", "band"}
FIELD_NAMES = {
    "close": {"close", "price", "收盤", "收盤價", "收市", "價格"},
    "change": {"change %", "change", "漲跌（%）", "升跌（%）", "變動%", "漲跌幅", "升跌率 %", "升跌率%"},
    "open": {"open", "開市", "開盤"},
    "high": {"high", "最高", "高"},
    "low": {"low", "最低", "低"},
    "score": {"score", "fear & greed", "恐懼貪婪指數", "指數分數", "current score", "current_score"},
    "band": {"band", "rating", "情緒區間", "評級", "current band", "current_band"},
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



def _display_like(original, raw_value, percent=False):
    raw = str(raw_value).strip()
    old = str(original or "").strip()
    if "," in old and "," not in raw:
        numeric = raw.replace("$", "").replace("%", "")
        try:
            places = len(numeric.split(".", 1)[1]) if "." in numeric else 0
            raw = f"{Decimal(numeric):,.{places}f}"
        except (InvalidOperation, ValueError):
            pass
    if percent and "%" not in raw:
        raw += "%"
    if old.startswith("$") and not raw.startswith("$"):
        raw = "$" + raw
    elif old.endswith("%") and "%" not in raw:
        raw += "%"
    return raw


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
                source["close_value"] = value
                source["history_close"] = value
            else:
                source["close_value"] = value
                source["history_close"] = (
                    _display_like(item.get("display") if item else None, fields["close"]["value"])
                    if group in ("energy", "metals") else value
                )
                if item is not None:
                    item["display"] = _display_like(item.get("display"), fields["close"]["value"])
        if "change" in fields:
            value = _plain_number(fields["change"]["value"])
            if group == "sectors":
                source["daily_change_percent"] = value
                source["history_change"] = value
                source["change_display"] = _display_like(source.get("change_display"), fields["change"]["value"], percent=True)
                fixture["sectors"][name] = source["change_display"]
            else:
                source["daily_change_percent"] = value
                raw = str(fields["change"]["value"]).strip()
                if item is not None:
                    item["change_display"] = _display_like(item.get("change_display"), raw, percent=True)
                source["history_change"] = (
                    item["change_display"] if group in ("energy", "metals") and item is not None
                    else raw if group in ("energy", "metals") else value
                )
        if "score" in fields:
            value = _plain_number(fields["score"]["value"])
            source["score_value"] = value
            source["source_score_value"] = value
            source["cnn_target_date_score"] = value
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
        source["screenshot_evidence"] = {
            field: {
                "evidence_path": evidence["evidence_path"],
                "evidence_sha256": evidence["evidence_sha256"],
                "captured_at": evidence["captured_at"],
                "quote_timestamp": evidence.get("quote_timestamp"),
            }
            for field, evidence in fields.items()
        }
        first_evidence = next(iter(fields.values()))
        source["screenshot_evidence_path"] = first_evidence["evidence_path"]
        source["screenshot_evidence_sha256"] = first_evidence["evidence_sha256"]
        source["screenshot_fields_applied"] = sorted(fields)
    return fixture



def apply_page_completions_to_fixture(fixture: dict, observations: list[dict],
                                      screenshot_inputs: dict) -> list[dict]:
    """Fill only screenshot-missing required fields from the current-run source read."""
    by_key = {(row.get("group"), row.get("name")): row for row in observations}
    for key, screenshot in screenshot_inputs.items():
        observation = by_key.get(key)
        if not observation:
            continue
        if not (
            observation.get("source_page_fetched") is True
            and observation.get("field_mapping_status") == "VERIFIED"
            and observation.get("instrument_identity_status") == "VERIFIED"
            and observation.get("screenshot_instrument_identity_status") == "VERIFIED"
            and observation.get("observed_value") is not None
            and observation.get("observed_change") is not None
        ):
            group, name = key
            if group == "global_markets":
                pending_item = (fixture.get(group) or {}).get(name) or {}
                pending_source = pending_item.get("source") or {}
                if "cfd" in str(pending_source.get("quote_type") or "").lower():
                    required = ("close", "change")
                    if not all(field in screenshot["fields"] for field in required):
                        pending_item["display"] = "待核實"
                        pending_item["change_display"] = "待核實"
                        pending_source["verification_status"] = "PENDING"
            continue

        group, name = key
        is_fg = group == "risk" and name == "fear_greed"
        value_key, change_key = ("score", "band") if is_fg else ("close", "change")
        fields = screenshot["fields"]
        if group == "sectors":
            item = None
            source = (fixture.get("sector_sources") or {}).get(name)
        else:
            item = (fixture.get(group) or {}).get(name)
            source = (item or {}).get("source")
        if not source:
            raise ValueError(f"Screenshot completion lost Fixture source row: {group}/{name}")

        if value_key not in fields:
            raw = observation["observed_value"]
            value = _plain_number(raw)
            if is_fg:
                source["score_value"] = value
                source["source_score_value"] = value
                source["cnn_target_date_score"] = value
                source["backup_source_score_value"] = value
                if item is not None:
                    item["display"] = _display_like(item.get("display"), raw)
            elif group == "sectors":
                source["close_value"] = value
                source["history_close"] = value
            else:
                source["close_value"] = value
                source["history_close"] = (
                    _display_like(item.get("display"), raw)
                    if group in ("energy", "metals") and item is not None else value
                )
                if item is not None:
                    item["display"] = _display_like(item.get("display"), raw)

        if change_key not in fields:
            raw = observation["observed_change"]
            if is_fg:
                band = str(raw).strip()
                source["band"] = band
                if item is not None:
                    item["change_display"] = band
            else:
                value = _plain_number(raw)
                if group == "sectors":
                    source["daily_change_percent"] = value
                    source["history_change"] = value
                    source["change_display"] = _display_like(source.get("change_display"), raw, percent=True)
                    fixture["sectors"][name] = source["change_display"]
                else:
                    source["daily_change_percent"] = value
                    if item is not None:
                        item["change_display"] = _display_like(item.get("change_display"), raw, percent=True)
                    source["history_change"] = (
                        item["change_display"] if group in ("energy", "metals") and item is not None
                        else value
                    )

        source["history_page_completion_at"] = observation.get("finished_at_tw") or observation.get("finished_at_utc")
        source["history_page_completion_fields"] = [field for field in (value_key, change_key) if field not in fields]
        observation["observed_date"] = fixture.get("trading_date")
        observation["display_value_match"] = True
        observation["display_change_match"] = True
        observation["status"] = "VERIFIED"
        observation["read_status"] = "MIXED_FIELD_OBSERVATIONS_CONFIRMED"
    return observations


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
        approved_urls={source.get("url"),*(source.get("approved_primary_urls") or []),*(source.get("approved_backup_urls") or [])}
        if row.get("source_url") not in approved_urls:
            raise ValueError(f"{key}: screenshot source_url is not in the approved source list")
        if not str(row.get("instrument_identity") or "").strip():
            raise ValueError(f"{key}: screenshot instrument_identity is required")

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
            evidence_path = Path(str(item.get("evidence_path") or row.get("evidence_path") or ""))
            if not evidence_path.is_absolute():
                evidence_path = root / evidence_path
            try:
                resolved = evidence_path.resolve(strict=True)
                resolved.relative_to(root.resolve())
            except (OSError, ValueError):
                raise ValueError(f"{key}/{field}: screenshot evidence file missing or outside repository root")
            expected_sha = str(item.get("evidence_sha256") or row.get("evidence_sha256") or "").lower()
            if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
                raise ValueError(f"{key}/{field}: screenshot evidence_sha256 is malformed")
            actual_sha = _sha256(resolved)
            if actual_sha != expected_sha:
                raise ValueError(f"{key}/{field}: screenshot evidence SHA-256 mismatch")
            captured_at = str(item.get("captured_at") or row.get("captured_at") or "").strip()
            if not captured_at:
                raise ValueError(f"{key}/{field}: screenshot captured_at is required")
            normalized_fields[field] = {
                "value": item["value"],
                "field_name": field_name,
                "source_type": "USER_PROVIDED_SCREENSHOT",
                "evidence_path": str(resolved.relative_to(root.resolve())),
                "evidence_sha256": actual_sha,
                "captured_at": captured_at,
                "quote_timestamp": item.get("quote_timestamp", row.get("quote_timestamp")),
                "instrument_identity": row["instrument_identity"],
                "data_date": row["data_date"],
            }
        first_field = next(iter(normalized_fields.values()))
        result[key] = {
            "group": group,
            "name": name,
            "source_url": row["source_url"],
            "data_date": row["data_date"],
            "instrument_identity": row["instrument_identity"],
            "fields": normalized_fields,
            "evidence_path": first_field["evidence_path"],
            "evidence_sha256": first_field["evidence_sha256"],
            "captured_at": str(row.get("captured_at") or first_field["captured_at"]),
            "quote_timestamp": row.get("quote_timestamp", first_field.get("quote_timestamp")),
        }
    return result
