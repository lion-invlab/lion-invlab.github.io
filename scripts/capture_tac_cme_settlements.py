#!/usr/bin/env python3
"""Parse official CME Group Daily Bulletin settlement rows.

Only FINAL bulletins for the exact requested trade date are accepted. Preliminary,
stale, ambiguous, or missing rows raise ValueError so the caller can apply the WR
fallback policy without silently treating preliminary values as final.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from typing import Any

CME_SECTION_URLS = {
    "wti": "https://www.cmegroup.com/daily_bulletin/current/Section61_Energy_Futures_Products.pdf",
    "gold_gc": "https://www.cmegroup.com/daily_bulletin/current/Section62_Metals_Futures_Products.pdf",
    "silver_si": "https://www.cmegroup.com/daily_bulletin/current/Section62_Metals_Futures_Products.pdf",
}
CME_PRODUCT_CODES = {"wti": "CL", "gold_gc": "GC", "silver_si": "SI"}
CME_INSTRUMENTS = {
    "wti": "NYMEX Light Sweet Crude Oil (WTI)",
    "gold_gc": "COMEX Gold Futures (GC)",
    "silver_si": "COMEX Silver Futures (SI)",
}


def parse_cme_daily_bulletin_text(text: str, trading_date: date, product_code: str) -> dict[str, Any]:
    header = re.search(
        r"BULLETIN\s*#\s*\d+@\s*([A-Za-z]{3},\s*[A-Za-z]{3}\s+\d{1,2},\s+\d{4})",
        text,
    )
    if not header:
        raise ValueError("CME bulletin date header missing")
    bulletin_date = datetime.strptime(" ".join(header.group(1).split()), "%a, %b %d, %Y").date()
    if bulletin_date != trading_date:
        raise ValueError(
            f"CME bulletin date mismatch: expected {trading_date.isoformat()}, got {bulletin_date.isoformat()}"
        )

    first_page_header = text[:5000].upper()
    if "PRELIMINARY" in first_page_header:
        raise ValueError("CME Daily Bulletin is preliminary, not final")
    if "FINAL" not in first_page_header:
        raise ValueError("CME Daily Bulletin final status could not be verified")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start = next(
        (i for i, line in enumerate(lines) if re.match(rf"^{re.escape(product_code)}\s+FUT\s", line)),
        None,
    )
    if start is None:
        raise ValueError(f"CME bulletin product section missing: {product_code} FUT")

    contracts = []
    for line in lines[start + 1:]:
        if line.startswith(f"TOTAL {product_code} FUT"):
            break
        tokens = line.split()
        if len(tokens) < 10 or not re.fullmatch(r"[A-Z]{3}\d{2}", tokens[0]):
            continue
        try:
            settlement = float(tokens[4])
            if tokens[5] == "UNCH":
                point_change = 0.0
            elif tokens[5] in {"+", "-"}:
                magnitude = float(tokens[6])
                point_change = magnitude if tokens[5] == "+" else -magnitude
            else:
                continue
            volume = int(tokens[9].replace(",", ""))
        except (ValueError, IndexError):
            continue
        if settlement <= 0 or volume < 0:
            continue
        previous_settlement = settlement - point_change
        if previous_settlement <= 0:
            continue
        contracts.append({
            "contract": tokens[0],
            "settlement": settlement,
            "point_change": point_change,
            "change_pct": point_change / previous_settlement * 100,
            "volume": volume,
        })

    if not contracts:
        raise ValueError(f"CME bulletin has no valid {product_code} settlement rows")
    # Use the highest-volume listed contract and preserve its month explicitly.
    active = max(contracts, key=lambda row: row["volume"])
    return {
        **active,
        "data_date": bulletin_date.isoformat(),
        "bulletin_status": "final",
        "instrument": f"{CME_INSTRUMENTS_BY_CODE[product_code]} {active['contract']} (highest-volume contract)",
    }


CME_INSTRUMENTS_BY_CODE = {
    "CL": CME_INSTRUMENTS["wti"],
    "GC": CME_INSTRUMENTS["gold_gc"],
    "SI": CME_INSTRUMENTS["silver_si"],
}


def extract_cme_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("pypdf is required to parse official CME settlement bulletins") from exc
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_cme_daily_bulletin_pdf(pdf_bytes: bytes, trading_date: date, product_code: str) -> dict[str, Any]:
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("CME settlement response is not a PDF")
    return parse_cme_daily_bulletin_text(extract_cme_pdf_text(pdf_bytes), trading_date, product_code)


def self_test() -> None:
    sample = """2026 DAILY INFORMATION BULLETIN
PG61 BULLETIN # 210@ Fri, Oct 30, 2026 PG61
FINAL
CL FUT NYMEX CRUDE OIL (PHYSICAL)
DEC26 102.80 104.99 /102.43 104.12 + 2.12 268076 4309 258986 - 2792
JAN27 100.78 103.01 /100.47 102.21 + 2.07 114973 760 184974 + 860
TOTAL CL FUT 699445 12314 1913751 + 13793
"""
    parsed = parse_cme_daily_bulletin_text(sample, date(2026, 10, 30), "CL")
    assert parsed["contract"] == "DEC26"
    assert parsed["settlement"] == 104.12
    assert round(parsed["change_pct"], 4) == round(2.12 / 102.00 * 100, 4)
    assert parsed["data_date"] == "2026-10-30"

    for invalid_text, expected_error in (
        (sample.replace("FINAL", "PRELIMINARY"), "preliminary"),
        (sample.replace("Oct 30, 2026", "Oct 29, 2026"), "date mismatch"),
        (sample.replace("CL FUT", "RB FUT"), "section missing"),
    ):
        try:
            parse_cme_daily_bulletin_text(invalid_text, date(2026, 10, 30), "CL")
        except ValueError as exc:
            assert expected_error in str(exc)
        else:
            raise AssertionError(f"expected CME parser to reject: {expected_error}")
    print("PASS: CME official bulletin exact-date, final-status, contract and settlement parsing")
