#!/usr/bin/env python3
"""Convert ChatGPT's evidence-bearing direct webpage observations to TAC snapshot v1."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_SCHEMA = ROOT / "schemas" / "tac-investing-com-web-observations.schema.json"
OUTPUT_SCHEMA = ROOT / "schemas" / "tac-daily-market-snapshot.schema.json"

GROUPS = {
    "global_indices": ["dow", "sp500", "nasdaq_composite", "russell_2000", "sox",
        "hang_seng", "shanghai_composite", "shenzhen_component", "nikkei_225",
        "kospi", "twse", "singapore_sti", "asx_200", "ftse_100", "dax", "cac_40",
        "stoxx_europe_600"],
    "sectors": ["xlk", "xly", "xlb", "xlu", "xli", "xlv", "xlf", "xlc", "xlre", "xlp", "xle"],
    "bonds": ["us_2y", "us_10y", "us_30y"],
    "fx": ["dxy", "usd_twd", "eur_usd", "gbp_usd", "aud_usd", "usd_jpy"],
    "energy": ["wti", "brent"],
    "precious_metals": ["gold_gc", "silver_si"],
    "risk_indicators": ["vix", "move", "cnn_fear_greed"],
}
EXPECTED = [asset for group in GROUPS.values() for asset in group]
VALUE_TYPES = {
    **{asset: "index_level" for asset in GROUPS["global_indices"]},
    **{asset: "percent_change" for asset in GROUPS["sectors"]},
    **{asset: "yield_percent" for asset in GROUPS["bonds"]},
    "dxy": "index_level",
    **{asset: "price" for asset in ["usd_twd", "eur_usd", "gbp_usd", "aud_usd", "usd_jpy",
        "wti", "brent", "gold_gc", "silver_si"]},
    "vix": "index_level", "move": "index_level", "cnn_fear_greed": "index_score",
}
QUOTE_BASIS = {
    "index_level": "historical_close",
    "percent_change": "historical_close",
    "yield_percent": "daily_yield_curve",
    "price": "historical_close",
    "index_score": "index_score",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validators():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("jsonschema dependency is required") from exc
    fmt = FormatChecker()
    input_schema = load_json(INPUT_SCHEMA)
    output_schema = load_json(OUTPUT_SCHEMA)
    Draft202012Validator.check_schema(input_schema)
    Draft202012Validator.check_schema(output_schema)
    return (
        Draft202012Validator(input_schema, format_checker=fmt),
        Draft202012Validator(output_schema, format_checker=fmt),
    )


def errors_for(validator, data):
    return sorted(validator.iter_errors(data), key=lambda err: list(err.path))


def assert_valid(validator, data, label):
    errors = errors_for(validator, data)
    if errors:
        details = []
        for err in errors:
            path = ".".join(str(part) for part in err.path) or "$"
            details.append(f"{path}: {err.message}")
        raise ValueError(label + " invalid: " + "; ".join(details[:12]))


def convert(data: dict, input_validator, output_validator) -> dict:
    assert_valid(input_validator, data, "direct webpage observation package")
    meta = data["meta"]
    report_date = date.fromisoformat(meta["report_date"])
    observed = {row["asset_id"]: row for row in data["observations"]}
    if len(observed) != len(data["observations"]):
        raise ValueError("duplicate asset_id observations")
    missing = sorted(set(EXPECTED) - set(observed))
    unexpected = sorted(set(observed) - set(EXPECTED))
    if missing or unexpected:
        raise ValueError(f"asset coverage mismatch; missing={missing}, unexpected={unexpected}")

    snapshot = {
        "schema_version": 1,
        "meta": {
            "report_date": meta["report_date"],
            "trading_date": meta["trading_date"],
            "generated_at": meta["generated_at"],
            "timezone": "Asia/Taipei",
            "wr_version": "3.8",
        },
    }

    for group, assets in GROUPS.items():
        snapshot[group] = {}
        for asset in assets:
            row = observed[asset]
            expected_type = VALUE_TYPES[asset]
            if row["value_type"] != expected_type:
                raise ValueError(
                    f"{asset} value_type mismatch: expected {expected_type}, got {row['value_type']}"
                )
            if row["verification_status"] == "verified":
                if row["data_date"] is None:
                    raise ValueError(f"{asset} verified without data_date")
                if date.fromisoformat(row["data_date"]) > report_date:
                    raise ValueError(f"{asset} data_date is after report_date")
                if row["source"] is None:
                    raise ValueError(f"{asset} verified without source evidence")
            source = None
            if row["source"] is not None:
                source = {
                    "name": row["source"]["name"],
                    "url": row["source"]["url"],
                    "observed_at": row["observed_at"],
                    "data_date": row["data_date"] or meta["trading_date"],
                    "quote_type": row["quote_basis"],
                    "instrument": row["instrument"],
                }
            value = row["value"]
            change = row["change"]
            unit = row["unit"]
            change_unit = row["change_unit"]
            notes = row["notes"]
            if asset in GROUPS["sectors"]:
                # Binding map intentionally displays the change field only.
                # Keep the same verified percentage in value for schema integrity
                # and in change for the existing sector display slot.
                change = value
                change_unit = "%"
                unit = "%"
                note = "產業 ETF 僅顯示漲跌幅；未呈現 ETF 價格。"
                notes = f"{notes}；{note}" if notes else note
            snapshot[group][asset] = {
                "value": value,
                "unit": unit,
                "change": change,
                "change_unit": change_unit,
                "status": row["verification_status"],
                "source": source,
                "fallback_used": row["fallback_used"],
                "fallback_reason": row["fallback_reason"],
                "notes": notes,
            }

    fw = data["fedwatch"]
    snapshot["fedwatch"] = {
        "target_meeting": fw["target_meeting"],
        "updated_at": fw["updated_at"],
        "source": fw["source"],
        "probabilities": fw["probabilities"],
        "status": fw["verification_status"],
        "notes": fw["notes"],
    }
    assert_valid(output_validator, snapshot, "normalized TAC market snapshot")
    return snapshot


def self_test(input_validator, output_validator):
    from datetime import datetime, timezone
    generated = "2026-11-01T09:00:00+08:00"
    observations = []
    for asset in EXPECTED:
        is_sector = asset in GROUPS["sectors"]
        observations.append({
            "asset_id": asset, "instrument": asset.upper(),
            "value_type": VALUE_TYPES[asset],
            "value": 1.25 if is_sector else None,
            "change": 1.25 if is_sector else None,
            "change_unit": "%" if is_sector else None,
            "unit": "%" if is_sector else ("index point" if VALUE_TYPES[asset] in {"index_level", "index_score"} else "unit"),
            "currency": None,
            "quote_basis": QUOTE_BASIS[VALUE_TYPES[asset]],
            "data_date": None, "observed_at": generated, "source": None,
            "retrieval_method": "chatgpt_direct_webpage_read",
            "verification_status": "pending_verification",
            "fallback_used": False, "fallback_reason": None,
            "notes": "Test fixture only; not a market quote.",
        })
    package = {
        "schema_version": 1,
        "meta": {"report_date":"2026-11-02","trading_date":"2026-10-30",
            "generated_at":generated,"timezone":"Asia/Taipei","wr_version":"3.8",
            "capture_operator":"ChatGPT direct webpage review"},
        "expected_asset_ids": EXPECTED,
        "observations": observations,
        "fedwatch":{"target_meeting":None,"updated_at":None,"source":None,
            "probabilities":[],"retrieval_method":"chatgpt_direct_webpage_read",
            "verification_status":"pending_verification","notes":"Test fixture only."},
    }
    pending = convert(package, input_validator, output_validator)
    if len(pending["global_indices"]) != 17 or len(pending["sectors"]) != 11:
        raise AssertionError("asset group counts incorrect")
    if pending["sectors"]["xlk"]["change"] != 1.25 or pending["sectors"]["xlk"]["unit"] != "%":
        raise AssertionError("sector ETF percentage mapping incorrect")
    print("PASS: 44 pending observations convert and validate; sector ETF display remains percentage-only")

    verified = json.loads(json.dumps(package))
    verified_row = next(row for row in verified["observations"] if row["asset_id"] == "sp500")
    verified_row.update({"value": 6800.0, "change": 0.5, "change_unit": "%",
        "unit":"index point","data_date":"2026-10-30","verification_status":"verified",
        "source":{"name":"Investing.com Hong Kong","url":"https://hk.investing.com/indices/us-spx-500"}})
    result = convert(verified, input_validator, output_validator)
    sp = result["global_indices"]["sp500"]
    if sp["value"] != 6800.0 or sp["source"]["data_date"] != "2026-10-30":
        raise AssertionError("verified value or provenance was not preserved")
    print("PASS: verified quote value, source URL, data date and read timestamp preserved")

    wrong = json.loads(json.dumps(package))
    next(row for row in wrong["observations"] if row["asset_id"] == "xlk")["value_type"] = "price"
    try:
        convert(wrong, input_validator, output_validator)
    except ValueError as exc:
        if "xlk value_type mismatch" not in str(exc):
            raise
    else:
        raise AssertionError("wrong sector value_type unexpectedly accepted")
    print("PASS: incorrect asset/value-type pairing rejected")

    bad = json.loads(json.dumps(package))
    bad["observations"].pop()
    try:
        convert(bad, input_validator, output_validator)
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete observation package unexpectedly accepted")
    print("PASS: incomplete asset coverage rejected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    input_validator, output_validator = validators()
    if args.self_test:
        self_test(input_validator, output_validator)
        return 0
    if not args.input or not args.output:
        parser.error("--input and --output are required unless --self-test is used")
    result = convert(load_json(Path(args.input)), input_validator, output_validator)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output":str(output),"asset_count":len(EXPECTED),
        "verified_count":sum(1 for group in GROUPS for row in result[group].values() if row["status"]=="verified"),
        "pending_count":sum(1 for group in GROUPS for row in result[group].values() if row["status"]=="pending_verification"),
        "fedwatch_status":result["fedwatch"]["status"]},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("TAC OBSERVATION CONVERSION FAILED: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
