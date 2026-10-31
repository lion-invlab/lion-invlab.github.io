#!/usr/bin/env python3
"""Fetch TAC auxiliary daily market fields from Investing.com HK with exact-date Yahoo fallback.

Covers 11 S&P sector ETFs, DXY and five FX pairs, WTI/Brent, gold/silver,
VIX and MOVE. CNN Fear & Greed remains a separate official-source collector.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from fetch_tac_global_indices import (
    fetch_yahoo_fallback,
    normalized_header,
    parse_date,
    parse_number,
)

ROOT = "https://hk.investing.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# group, key, page category, slug, expected identity, Yahoo fallback, unit, label
INSTRUMENTS = [
    ("sectors", "xlk", "etfs", "spdr-select-sector---technology", "XLK", "XLK", "USD/share", "資訊科技 XLK"),
    ("sectors", "xly", "etfs", "spdr-consumer-discr.-select-sector", "XLY", "XLY", "USD/share", "非必需消費 XLY"),
    ("sectors", "xlb", "etfs", "spdr-materials-select-sector-etf", "XLB", "XLB", "USD/share", "原材料 XLB"),
    ("sectors", "xlu", "etfs", "spdr-select-sector---utilities", "XLU", "XLU", "USD/share", "公用事業 XLU"),
    ("sectors", "xli", "etfs", "industrial-sector-spdr-trust", "XLI", "XLI", "USD/share", "工業 XLI"),
    ("sectors", "xlv", "etfs", "spdr---health-care", "XLV", "XLV", "USD/share", "醫療保健 XLV"),
    ("sectors", "xlf", "etfs", "financial-select-sector-spdr-fund", "XLF", "XLF", "USD/share", "金融 XLF"),
    ("sectors", "xlc", "etfs", "communication-services-select-spdr", "XLC", "XLC", "USD/share", "通訊服務 XLC"),
    ("sectors", "xlre", "etfs", "real-estate-select-sector-spdr", "XLRE", "XLRE", "USD/share", "房地產 XLRE"),
    ("sectors", "xlp", "etfs", "spdr---consumer-staples", "XLP", "XLP", "USD/share", "必需消費 XLP"),
    ("sectors", "xle", "etfs", "spdr-energy-select-sector-fund", "XLE", "XLE", "USD/share", "能源 XLE"),
    ("fx", "dxy", "indices", "usdollar", "DXY", "DX-Y.NYB", "index_point", "美元指數 DXY"),
    ("fx", "usd_twd", "currencies", "usd-twd", "USD/TWD", "TWD=X", "exchange_rate", "USD/TWD"),
    ("fx", "eur_usd", "currencies", "eur-usd", "EUR/USD", "EURUSD=X", "exchange_rate", "EUR/USD"),
    ("fx", "gbp_usd", "currencies", "gbp-usd", "GBP/USD", "GBPUSD=X", "exchange_rate", "GBP/USD"),
    ("fx", "aud_usd", "currencies", "aud-usd", "AUD/USD", "AUDUSD=X", "exchange_rate", "AUD/USD"),
    ("fx", "usd_jpy", "currencies", "usd-jpy", "USD/JPY", "JPY=X", "exchange_rate", "USD/JPY"),
    ("energy", "wti", "commodities", "crude-oil", "WTI", "CL=F", "USD/barrel", "WTI 原油期貨"),
    ("energy", "brent", "commodities", "brent-oil", "布倫特", "BZ=F", "USD/barrel", "Brent 原油期貨"),
    ("precious_metals", "gold_gc", "commodities", "gold", "黃金期貨", "GC=F", "USD/ounce", "黃金期貨 GC"),
    ("precious_metals", "silver_si", "commodities", "silver", "白銀期貨", "SI=F", "USD/ounce", "白銀期貨 SI"),
    ("risk_indicators", "vix", "indices", "volatility-s-p-500", "VIX", "^VIX", "index_point", "VIX"),
    ("risk_indicators", "move", "indices", "ice-bofaml-move", "MOVE", "^MOVE", "index_point", "MOVE"),
]

def parse_investing_history(html: str, expected: str, trading_date: date) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    heading_text = heading.get_text(" ", strip=True) if heading else ""
    if expected.upper() not in heading_text.upper():
        raise ValueError(f"instrument identity mismatch: expected {expected}, heading={heading_text!r}")

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [normalized_header(c.get_text(" ", strip=True))
                   for c in rows[0].find_all(["th", "td"])]
        date_i = next((i for i, h in enumerate(headers) if "日期" in h or h == "date"), None)
        close_i = next((i for i, h in enumerate(headers)
                        if "收市" in h or "收盤" in h or h in {"close", "price"}), None)
        change_i = next((i for i, h in enumerate(headers)
                         if "升跌" in h or "change" in h), None)
        if None in (date_i, close_i, change_i):
            continue
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if max(date_i, close_i, change_i) >= len(cells):
                continue
            try:
                row_date = parse_date(cells[date_i].get_text(" ", strip=True))
            except ValueError:
                continue
            if row_date != trading_date:
                continue
            close = parse_number(cells[close_i].get_text(" ", strip=True))
            change = parse_number(cells[change_i].get_text(" ", strip=True))
            if close is None or close <= 0 or change is None:
                raise ValueError("exact-date row has invalid close or percentage change")
            return {"close": close, "change_pct": change, "heading": heading_text}
    raise ValueError(f"exact trading-date row {trading_date.isoformat()} not found")

def pending_record(unit: str, reason: str) -> dict:
    return {
        "value": None, "unit": unit, "change": None, "change_unit": "percent",
        "status": "pending_verification", "source": None,
        "fallback_used": False, "fallback_reason": None,
        "notes": "待核實；未沿用舊值。原因：" + reason,
    }

def fetch_one(session: requests.Session, item: tuple, trading_date: date,
              observed_at: str) -> tuple[str, str, dict]:
    group, key, category, slug, identity, yahoo, unit, label = item
    url = f"{ROOT}/{category}/{slug}-historical-data"
    primary_error = ""
    try:
        response = session.get(url, timeout=(10, 30))
        response.raise_for_status()
        if len(response.text) < 5000:
            raise ValueError("response unexpectedly short")
        parsed = parse_investing_history(response.text, identity, trading_date)
        return group, key, {
            "value": parsed["close"], "unit": unit,
            "change": parsed["change_pct"], "change_unit": "percent",
            "status": "verified",
            "source": {
                "name": "Investing.com 香港站", "url": url,
                "observed_at": observed_at, "data_date": trading_date.isoformat(),
                "quote_type": "investing_com_hk_historical_close_pct_change",
                "instrument": f"{label} | {parsed['heading']}",
            },
            "fallback_used": False, "fallback_reason": None,
            "notes": "指定交易日歷史收市價及日升跌幅；不混用盤中報價。",
        }
    except Exception as exc:
        primary_error = str(exc)

    try:
        fallback = fetch_yahoo_fallback(
            session, key, yahoo, trading_date, observed_at, primary_error
        )
        fallback["unit"] = unit
        fallback["notes"] = (
            "Investing.com 香港站未成功取得指定日期，改用 Yahoo Finance 日線；"
            "僅接受完全相符交易日期及精確標的代號。"
        )
        return group, key, fallback
    except Exception as exc:
        return group, key, pending_record(unit, f"Investing.com: {primary_error}; Yahoo: {exc}")

def build_fragment(trading_date: date, report_date: date, records: dict,
                   observed_at: str) -> dict:
    expected = {(g, k) for g, k, *_ in INSTRUMENTS}
    if set(records) != expected:
        raise ValueError("auxiliary market field set mismatch")
    grouped = {g: {} for g in ("sectors", "fx", "energy", "precious_metals", "risk_indicators")}
    for (group, key), record in records.items():
        grouped[group][key] = record
    # CNN Fear & Greed is intentionally not inferred from a substitute indicator.
    grouped["risk_indicators"]["cnn_fear_greed"] = pending_record(
        "score_0_100", "CNN Business official Fear & Greed source collector not yet connected"
    )
    return {
        "fragment_schema_version": 1,
        "dataset": "tac_auxiliary_markets",
        "report_date": report_date.isoformat(),
        "trading_date": trading_date.isoformat(),
        "fetched_at": observed_at,
        **grouped,
    }

def self_test() -> None:
    html = """<html><h1>State Street Technology Select Sector SPDR ETF (XLK)</h1>
    <table><tr><th>Date</th><th>Price</th><th>Open</th><th>Change %</th></tr>
    <tr><td>Oct 30, 2026</td><td>179.51</td><td>182.11</td><td>-4.89%</td></tr></table></html>"""
    p = parse_investing_history(html, "XLK", date(2026, 10, 30))
    assert p["close"] == 179.51 and p["change_pct"] == -4.89
    try:
        parse_investing_history(html, "XLF", date(2026, 10, 30))
    except ValueError as exc:
        assert "identity mismatch" in str(exc)
    else:
        raise AssertionError("wrong instrument identity must be rejected")
    try:
        parse_investing_history(html, "XLK", date(2026, 10, 29))
    except ValueError as exc:
        assert "exact trading-date row" in str(exc)
    else:
        raise AssertionError("stale date must be rejected")
    assert len(INSTRUMENTS) == 23
    assert len({(x[0], x[1]) for x in INSTRUMENTS}) == 23
    print("PASS: auxiliary historical parser, exact-date and identity guards")
    print("PASS: 23 ETF/FX/commodity/risk instrument mappings")
    print("PASS: CNN Fear & Greed remains explicitly pending, not substituted")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trading-date")
    parser.add_argument("--report-date")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.trading_date, args.report_date, args.output)):
        parser.error("--trading-date, --report-date and --output are required")
    trading_date = date.fromisoformat(args.trading_date)
    report_date = date.fromisoformat(args.report_date)
    observed_at = datetime.now(timezone.utc).isoformat()
    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh-HK,zh;q=0.9,en;q=0.8",
    })
    retry = Retry(total=2, connect=2, read=2, backoff_factor=0.7,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset({"GET"}))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    records = {}
    # Sequential requests keep a modest pace and avoid bursty source traffic.
    for item in INSTRUMENTS:
        group, key, record = fetch_one(session, item, trading_date, observed_at)
        records[(group, key)] = record
        print(f"{group}.{key}: {record['status']} value={record['value']} change={record['change']}")
    fragment = build_fragment(trading_date, report_date, records, observed_at)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified = sum(1 for group in fragment.values() if isinstance(group, dict)
                   for value in group.values() if isinstance(value, dict)
                   and value.get("status") == "verified")
    pending = 24 - verified
    print(f"Auxiliary markets: {verified}/24 verified; {pending}/24 pending (CNN included)")
    print("Saved " + str(out))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
