#!/usr/bin/env python3
"""Build TAC pivot levels from normalized, source-attributed OHLC input.

The market-data collector owns retrieval. This module owns validation and pivot
math. The HTML assembler only renders the resulting key_levels JSON contract.
"""
from __future__ import annotations
import argparse, json, re, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = ("dow", "sp500", "nasdaq", "sox", "russell2000")
EXPECTED = {
    "dow": "道瓊工業指數",
    "sp500": "S&P 500",
    "nasdaq": "Nasdaq Composite",
    "sox": "費城半導體指數（SOX）",
    "russell2000": "Russell 2000",
}
CENT = Decimal("0.01")

def dec(value, field):
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field}: not a decimal") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{field}: must be a positive finite number")
    return result

def fmt(value):
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):,.2f}"

def build(payload, report_date):
    if payload.get("report_date") != report_date:
        raise ValueError("report_date mismatch between OHLC input and report fixture")
    trading_date = payload.get("trading_date")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(trading_date or "")):
        raise ValueError("invalid trading_date")
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("items must be an array")
    by_key = {}
    for item in items:
        key = item.get("key")
        if key in by_key:
            raise ValueError(f"duplicate key: {key}")
        by_key[key] = item
    missing = [key for key in REQUIRED if key not in by_key]
    extra = [key for key in by_key if key not in REQUIRED]
    if missing or extra:
        raise ValueError(f"required keys mismatch; missing={missing}, extra={extra}")
    output = []
    for key in REQUIRED:
        item = by_key[key]
        if item.get("name") != EXPECTED[key]:
            raise ValueError(f"{key}: instrument name mismatch")
        if item.get("trading_date") != trading_date:
            raise ValueError(f"{key}: trading date mismatch")
        if item.get("quote_type") != "cash_index":
            raise ValueError(f"{key}: only cash-index OHLC is accepted; CFD/futures cannot substitute")
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            raise ValueError(f"{key}: missing symbol")
        source_name = str(item.get("source_name") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        parsed = urlparse(source_url)
        if not source_name or parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"{key}: missing valid HTTPS source attribution")
        h, l, c = (dec(item.get(field), f"{key}.{field}") for field in ("high","low","close"))
        if h < l or not (l <= c <= h):
            raise ValueError(f"{key}: invalid OHLC relationship")
        p = (h + l + c) / Decimal(3)
        s1 = Decimal(2) * p - h
        r1 = Decimal(2) * p - l
        output.append({
            "key": key, "name": EXPECTED[key], "symbol": symbol,
            "s1": fmt(s1), "p": fmt(p), "r1": fmt(r1),
            "ohlc": f"H {fmt(h)}｜L {fmt(l)}｜C {fmt(c)}",
            "trading_date": trading_date, "quote_type": "cash_index",
            "source_name": source_name, "url": source_url,
            "formula": payload.get("formula", "P=(H+L+C)/3; S1=2P-H; R1=2P-L")
        })
    return {
        "baseline_date": trading_date,
        "formula": "經典樞紐點：P=(H+L+C)/3；S1=2P−H；R1=2P−L。",
        "items": output
    }

def self_test():
    sample = {
        "report_date":"2026-11-09","trading_date":"2026-11-06",
        "items":[{
            "key":"dow","name":"道瓊工業指數","symbol":"^DJI","trading_date":"2026-11-06",
            "open":101,"high":110,"low":90,"close":100,"quote_type":"cash_index",
            "source_name":"test source","source_url":"https://example.com/ohlc"
        }]
    }
    # Fill the other four instruments with valid OHLC rows.
    for key,name,symbol in zip(REQUIRED[1:], list(EXPECTED.values())[1:], ["^GSPC","^IXIC","^SOX","^RUT"]):
        sample["items"].append({"key":key,"name":name,"symbol":symbol,"trading_date":"2026-11-06","open":101,"high":110,"low":90,"close":100,"quote_type":"cash_index","source_name":"test source","source_url":"https://example.com/ohlc"})
    result=build(sample,"2026-11-09")
    assert result["items"][0]["p"] == "100.00"
    assert result["items"][0]["s1"] == "90.00"
    assert result["items"][0]["r1"] == "110.00"
    bad=json.loads(json.dumps(sample)); bad["items"][0]["quote_type"]="cfd"
    try: build(bad,"2026-11-09")
    except ValueError: pass
    else: raise AssertionError("CFD must fail closed")
    bad=json.loads(json.dumps(sample)); bad["items"].pop()
    try: build(bad,"2026-11-09")
    except ValueError: pass
    else: raise AssertionError("missing index must fail closed")
    print("key_levels_builder self-test: PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ohlc",required=True)
    ap.add_argument("--data",required=True)
    ap.add_argument("--report-date",required=True)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test(); return
    raw=json.loads(Path(args.ohlc).read_text(encoding="utf-8"))
    report=json.loads(Path(args.data).read_text(encoding="utf-8"))
    generated=build(raw,args.report_date)
    if report.get("report_date") != args.report_date:
        raise SystemExit("report fixture date mismatch")
    report["key_levels"]=generated
    Path(args.data).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print(f"key_levels_builder: generated {len(generated['items'])} levels from {generated['baseline_date']}")

if __name__ == "__main__":
    main()
