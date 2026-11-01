#!/usr/bin/env python3
"""Capture the TAC market-data bundle for the review-only daily pipeline.

Primary sources: Investing.com HK historical pages for indices, sectors, FX,
commodities and VIX/MOVE; U.S. Treasury official feed for 2Y/10Y/30Y; CNN
Business official Fear & Greed snapshot; Investing.com Fed Rate Monitor.
FRED is used only for Treasury fields missing from the official Treasury feed.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BOND_KEYS = ("us_2y", "us_10y", "us_30y")

def pending_bond(key: str, report_date: str, trading_date: str, reason: str) -> dict:
    names = {"us_2y": "U.S. Treasury 2Y CMT", "us_10y": "U.S. Treasury 10Y CMT", "us_30y": "U.S. Treasury 30Y CMT"}
    return {
        "value": None, "unit": "%", "change": None, "change_unit": "percentage_point",
        "status": "pending_verification", "source": None, "fallback_used": False,
        "fallback_reason": None, "notes": f"{names[key]}: {reason}; 未以舊值替代。",
    }

def merge_treasury_fragments(primary: dict | None, fallback: dict | None,
                             report_date: str, trading_date: str,
                             fallback_error: str | None = None) -> dict:
    primary_bonds = primary.get("bonds", {}) if isinstance(primary, dict) else {}
    fallback_bonds = fallback.get("bonds", {}) if isinstance(fallback, dict) else {}
    merged = {}
    for key in BOND_KEYS:
        primary_record = primary_bonds.get(key)
        fallback_record = fallback_bonds.get(key)
        if isinstance(primary_record, dict) and primary_record.get("status") == "verified":
            merged[key] = dict(primary_record)
            merged[key]["fallback_used"] = False
            merged[key]["fallback_reason"] = None
            continue
        if isinstance(fallback_record, dict) and fallback_record.get("status") == "verified":
            record = dict(fallback_record)
            record["fallback_used"] = True
            record["fallback_reason"] = (
                "U.S. Treasury official feed missing or failed for this maturity/date; "
                "used FRED DGS series as documented fallback."
            )
            record["notes"] = (str(record.get("notes") or "") +
                              " | 備援僅填補官方 Treasury 缺漏欄位；未覆蓋已核實官方值。").strip()
            merged[key] = record
            continue
        if isinstance(primary_record, dict):
            merged[key] = dict(primary_record)
            if fallback_error:
                merged[key]["notes"] = (str(merged[key].get("notes") or "") +
                                        f" | FRED 備援亦未取得：{fallback_error}").strip()
            continue
        reason = "官方 Treasury 主來源與 FRED 備援均未產出此欄位"
        if fallback_error:
            reason += f"；FRED 備援錯誤：{fallback_error}"
        merged[key] = pending_bond(key, report_date, trading_date, reason)
    return {
        "fragment_schema_version": 1,
        "dataset": "us_treasury_daily_par_yield_curve_with_field_level_fallback",
        "report_date": report_date,
        "trading_date": trading_date,
        "bonds": merged,
    }

def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"capture output must be a JSON object: {path}")
    return value

def run_command(command: list[str], output: Path) -> dict:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {
        "command": command,
        "return_code": result.returncode,
        "stdout": result.stdout[-6000:],
        "stderr": result.stderr[-6000:],
        "output_exists": output.is_file(),
        "output": str(output.relative_to(ROOT)),
    }

def self_test() -> None:
    def rec(value, status="verified", fallback=False):
        return {"value": value, "unit": "%", "change": 0.01, "change_unit": "percentage_point",
                "status": status, "source": {"name": "test", "url": "https://example.com"},
                "fallback_used": fallback, "fallback_reason": None, "notes": "test"}
    primary = {"bonds": {
        "us_2y": rec(3.5), "us_10y": rec(None, "missing"), "us_30y": rec(None, "missing")
    }}
    fallback = {"bonds": {
        "us_2y": rec(9.9), "us_10y": rec(4.1), "us_30y": rec(None, "missing")
    }}
    result = merge_treasury_fragments(primary, fallback, "2026-11-02", "2026-10-30")
    assert result["bonds"]["us_2y"]["value"] == 3.5
    assert result["bonds"]["us_2y"]["fallback_used"] is False
    assert result["bonds"]["us_10y"]["value"] == 4.1
    assert result["bonds"]["us_10y"]["fallback_used"] is True
    assert result["bonds"]["us_30y"]["status"] == "missing"
    empty = merge_treasury_fragments(None, None, "2026-11-02", "2026-10-30", "network down")
    assert all(empty["bonds"][key]["status"] == "pending_verification" for key in BOND_KEYS)
    print("PASS: official Treasury verified values are never overwritten by FRED")
    print("PASS: FRED fills only missing maturities and records fallback provenance")
    print("PASS: unavailable primary and fallback remain pending without guessed values")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-date")
    ap.add_argument("--trading-date")
    ap.add_argument("--output-dir")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.report_date, args.trading_date, args.output_dir)):
        ap.error("--report-date, --trading-date and --output-dir are required")
    report_day = date.fromisoformat(args.report_date)
    trading_day = date.fromisoformat(args.trading_date)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty capture directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "global_indices": output_dir / "global-indices.json",
        "sectors": output_dir / "sectors.json",
        "treasury_primary": output_dir / "treasury-primary.json",
        "treasury_fallback": output_dir / "treasury-fred-fallback.json",
        "treasury": output_dir / "treasury.json",
        "secondary": output_dir / "secondary-market.json",
        "fedwatch": output_dir / "fedwatch-investing-com.json",
        "fedwatch_text": output_dir / "fedwatch-investing-com.txt",
    }
    reports = {}
    base = [sys.executable]
    common = ["--trading-date", trading_day.isoformat(), "--report-date", report_day.isoformat()]
    for name, script in (("global_indices", "fetch_tac_global_indices.py"),
                         ("sectors", "fetch_tac_sector_etfs.py"),
                         ("secondary", "fetch_tac_secondary_market.py")):
        output = outputs[name]
        reports[name] = run_command(base + [str(SCRIPTS / script)] + common + ["--output", str(output)], output)
        if not output.is_file():
            raise SystemExit(f"{name} capture produced no output; see capture report")

    primary_path = outputs["treasury_primary"]
    treasury_report = run_command(
        base + [str(SCRIPTS / "fetch_tac_treasury_yields.py")] + common + ["--output", str(primary_path)],
        primary_path
    )
    reports["treasury_primary"] = treasury_report
    primary_data = read_json(primary_path)
    need_fallback = primary_data is None or any(
        primary_data.get("bonds", {}).get(key, {}).get("status") != "verified" for key in BOND_KEYS
    )
    fallback_data = None
    fallback_error = None
    if need_fallback:
        fallback_path = outputs["treasury_fallback"]
        fallback_report = run_command(
            base + [str(SCRIPTS / "fetch_tac_treasury_fred_fallback.py")] + common + ["--output", str(fallback_path)],
            fallback_path
        )
        reports["treasury_fallback"] = fallback_report
        try:
            fallback_data = read_json(fallback_path)
            if fallback_data is None:
                fallback_error = fallback_report["stderr"] or "FRED fallback produced no output"
        except Exception as exc:
            fallback_error = str(exc)
    merged_treasury = merge_treasury_fragments(primary_data, fallback_data,
                                               report_day.isoformat(), trading_day.isoformat(),
                                               fallback_error)
    outputs["treasury"].write_text(json.dumps(merged_treasury, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fedwatch_command = [
        "node", str(SCRIPTS / "capture_tac_fedwatch_fallback.mjs"),
        "--output", str(outputs["fedwatch"]),
        "--text-output", str(outputs["fedwatch_text"]),
    ]
    reports["fedwatch"] = run_command(fedwatch_command, outputs["fedwatch"])
    if not outputs["fedwatch"].is_file():
        raise SystemExit("Fed Rate Monitor capture produced no JSON output")

    manifest = {
        "report_date": report_day.isoformat(),
        "trading_date": trading_day.isoformat(),
        "output_dir": str(output_dir.relative_to(ROOT)) if output_dir.is_relative_to(ROOT) else str(output_dir),
        "market_fragments": [str(outputs[key].relative_to(ROOT)) for key in ("global_indices", "sectors", "treasury", "secondary")],
        "fedwatch_capture": str(outputs["fedwatch"].relative_to(ROOT)),
        "collectors": reports,
        "treasury_fallback_used": [key for key in BOND_KEYS if merged_treasury["bonds"][key].get("fallback_used")],
    }
    (output_dir / "capture_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in ("global_indices", "sectors", "treasury", "secondary"):
        fragment = read_json(outputs[name])
        groups = [key for key in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators") if key in fragment]
        verified = sum(1 for group in groups for record in fragment[group].values() if record.get("status") == "verified")
        total = sum(len(fragment[group]) for group in groups)
        print(f"{name}: {verified}/{total} verified; {total-verified} pending")
    fedwatch = read_json(outputs["fedwatch"])
    print(f"FedWatch: {fedwatch.get('status')} (Investing.com primary capture; mapping is a separate fail-closed step)")
    print("Capture bundle saved: " + str(output_dir))
    print("Next: pass all four market fragments and --fedwatch-capture to run_tac_daily_pipeline.py.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
