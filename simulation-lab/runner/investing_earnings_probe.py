#!/usr/bin/env python3
"""Read-only Investing.com earnings-page probe for SIM-1.2.

Captures the public earnings table and tests whether its fields are sufficient
for a PIT consensus snapshot. It never writes calendar JSON or production data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from consensus_snapshot_store import build_consensus_snapshot

TAIPEI = ZoneInfo("Asia/Taipei")
UA = "Mozilla/5.0 (compatible; TAC-Earnings-PIT-Probe/1.0; +https://lion-invlab.github.io/)"
TARGETS = [
    {
        "ticker": "NVDA",
        "company": "NVIDIA",
        "url": "https://www.investing.com/equities/nvidia-corp-earnings",
        "event_date": "2026-11-17",
        "period_markers": ("10/2026", "2026/10", "2026-10"),
        "date_markers": ("Nov 17, 2026", "17/11/2026", "2026-11-17", "2026年11月17日"),
    },
    {
        "ticker": "WMT",
        "company": "Walmart",
        "url": "https://www.investing.com/equities/wal-mart-stores-earnings",
        "event_date": "2026-11-19",
        "period_markers": ("10/2026", "2026/10", "2026-10"),
        "date_markers": ("Nov 19, 2026", "19/11/2026", "2026-11-19", "2026年11月19日"),
    },
    {
        "ticker": "BIDU",
        "company": "Baidu ADR",
        "url": "https://www.investing.com/equities/baidu.com-earnings",
        "event_date": "2026-11-16",
        "period_markers": ("09/2026", "2026/09", "2026-09"),
        "date_markers": ("Nov 16, 2026", "16/11/2026", "2026-11-16", "2026年11月16日"),
    },
]


def _first_number(text: str):
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", text or "")
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def _currency_and_units(text: str):
    # The earnings-table note ("All numbers in ...") takes precedence over
    # the quote-header trading currency, which can differ for ADRs.
    all_numbers = re.search(r"(?:All numbers in|數字皆以)\s*(USD|CNY|HKD|EUR|GBP|JPY)", text, re.I)
    header = re.search(r"(?:Currency in|貨幣)\s*(USD|CNY|HKD|EUR|GBP|JPY)", text, re.I)
    currency = (all_numbers or header).group(1).upper() if (all_numbers or header) else None
    return currency


def _basis_code(text: str, metric: str):
    lowered = text.casefold()
    if metric == "EPS":
        if "gaap" in lowered and "diluted" in lowered and "basic" not in lowered:
            return "US_GAAP_DILUTED_EPS"
        if "gaap" in lowered and "basic" in lowered and "diluted" not in lowered:
            return "US_GAAP_BASIC_EPS"
        if ("adjusted" in lowered or "non-gaap" in lowered or "non gaap" in lowered):
            if "diluted" in lowered:
                return "NON_GAAP_ADJUSTED_DILUTED_EPS"
            return "NON_GAAP_ADJUSTED_UNSPECIFIED_EPS"
        return None
    if "gaap" in lowered and "net sales" in lowered:
        return "US_GAAP_NET_SALES"
    if "gaap" in lowered and "revenue" in lowered:
        return "US_GAAP_TOTAL_REVENUE"
    return None


def parse_earnings_row(html: bytes, target: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    wanted_dates = target["date_markers"]
    wanted_periods = target["period_markers"]
    match_row = None
    match_cells = []
    for row in soup.select("table tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"], recursive=False)]
        joined = " | ".join(cells)
        if len(cells) >= 6 and any(d.casefold() in joined.casefold() for d in wanted_dates):
            if any(p.casefold() in joined.casefold() for p in wanted_periods):
                match_row, match_cells = joined, cells
                break

    currency = _currency_and_units(page_text)
    result = {
        "ticker": target["ticker"],
        "company": target["company"],
        "url": target["url"],
        "page_title": soup.title.get_text(" ", strip=True) if soup.title else None,
        "row_found": match_row is not None,
        "row_text": match_row,
        "currency": currency,
        "period": next((p for p in wanted_periods if match_row and p.casefold() in match_row.casefold()), None),
        "period_end_date": None,
        "eps_estimate": _first_number(match_cells[3]) if len(match_cells) > 3 else None,
        "revenue_estimate_raw": match_cells[5] if len(match_cells) > 5 else None,
        "revenue_estimate": _first_number(match_cells[5]) if len(match_cells) > 5 else None,
        "revenue_unit": None,
        "eps_basis_code": _basis_code(match_row or "", "EPS"),
        "revenue_basis_code": _basis_code(match_row or "", "REVENUE"),
        "statistic": "mean" if re.search(r"\b(mean|average consensus)\b", match_row or "", re.I) else None,
        "analyst_count": None,
        # Do not mistake a generic "Last Updated" for the estimate's as-of time.
        "data_as_of": None,
        "published_at": None,
    }
    raw_rev = result["revenue_estimate_raw"] or ""
    if re.search(r"(?:B|billion|億)\s*$", raw_rev, re.I):
        result["revenue_unit"] = f"{currency}_BILLION" if currency else None
        if "億" in raw_rev and result["revenue_estimate"] is not None:
            result["revenue_estimate"] = result["revenue_estimate"] / 10
    elif re.search(r"(?:M|million)\s*$", raw_rev, re.I):
        result["revenue_unit"] = f"{currency}_MILLION" if currency else None
    elif re.search(r"(?:K|thousand)\s*$", raw_rev, re.I):
        result["revenue_unit"] = f"{currency}_THOUSAND" if currency else None

    # Only explicit estimate-specific metadata may populate data_as_of.
    asof = re.search(
        r"(?:consensus|estimate)\s+(?:data\s+)?as of\s*[:：]?\s*(\d{4}-\d{2}-\d{2})",
        page_text, re.I
    )
    if asof:
        result["data_as_of"] = asof.group(1)
    return result


def fetch_one(target: dict, archive_dir: Path) -> dict:
    path = target["url"].split("://", 1)[1].split("/", 1)[1]
    hosts = ("hk.investing.com", "www.investing.com", "ca.investing.com", "uk.investing.com")
    attempts = []
    chosen = None
    for host in hosts:
        url = f"https://{host}/{path}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-HK,zh;q=0.9,en-US,en;q=0.8",
                "Cache-Control": "no-cache",
            },
        )
        status, headers, raw, error = None, {}, b"", None
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                status = response.status
                headers = {k.lower(): v for k, v in response.headers.items()}
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            raw = exc.read()
            error = f"HTTPError: {exc}"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        observed_at = datetime.now(TAIPEI).isoformat(timespec="seconds")
        digest = hashlib.sha256(raw).hexdigest() if raw else None
        raw_ref = None
        if raw:
            folder = archive_dir / target["ticker"]
            folder.mkdir(parents=True, exist_ok=True)
            raw_path = folder / f"{host.replace('.', '-')}-{digest}.html"
            if raw_path.exists() and raw_path.read_bytes() != raw:
                raise RuntimeError(f"raw HTML hash collision: {raw_path}")
            if not raw_path.exists():
                raw_path.write_bytes(raw)
            raw_ref = str(raw_path)
        parsed = parse_earnings_row(raw, {**target, "url": url}) if raw else {"row_found": False}
        attempts.append({
            "host": host, "url": url, "http_status": status,
            "observed_at": observed_at, "raw_response_sha256": digest,
            "raw_response_ref": raw_ref, "row_found": parsed.get("row_found", False),
            "transport_error": error,
        })
        if parsed.get("row_found"):
            chosen = (parsed, status, headers, raw, digest, raw_ref, observed_at, error, url)
            break
        if raw and (chosen is None or (status == 200 and chosen[1] != 200)):
            chosen = (parsed, status, headers, raw, digest, raw_ref, observed_at, error, url)

    if chosen:
        parsed, status, headers, raw, digest, raw_ref, observed_at, error, url = chosen
        parsed["url"] = url
    else:
        parsed, status, headers, raw, digest, raw_ref, observed_at, error, url = (
            {"ticker": target["ticker"], "company": target["company"], "url": target["url"],
             "row_found": False, "row_text": None, "currency": None, "eps_estimate": None,
             "revenue_estimate": None, "revenue_estimate_raw": None, "revenue_unit": None,
             "period": None, "period_end_date": None, "eps_basis_code": None,
             "revenue_basis_code": None, "statistic": None, "analyst_count": None,
             "data_as_of": None, "published_at": None, "page_title": None},
            None, {}, b"", None, None, datetime.now(TAIPEI).isoformat(timespec="seconds"),
            "all Investing.com locale hosts failed", target["url"]
        )

    snapshots = {}
    if not parsed.get("row_found"):
        for metric in ("EPS", "REVENUE"):
            snapshots[metric] = {
                "snapshot_status": "pending_required_fields",
                "reason": "investing_page_unavailable_or_target_row_not_found",
                "source_row_available": False,
                "raw_response_sha256": None,
            }
    elif raw:
        for metric in ("EPS", "REVENUE"):
            attempt = {
                "source_level": 4, "provider": "Investing.com", "url": url,
                "observed_at": observed_at, "data_as_of": parsed.get("data_as_of"),
                "published_at": parsed.get("published_at"), "period": parsed.get("period"),
                "period_end_date": parsed.get("period_end_date"),
                "value": parsed.get("eps_estimate") if metric == "EPS" else parsed.get("revenue_estimate"),
                "currency": parsed.get("currency"),
                "unit": None if metric == "EPS" else parsed.get("revenue_unit"),
                "basis_code": parsed.get("eps_basis_code") if metric == "EPS" else parsed.get("revenue_basis_code"),
                "statistic": parsed.get("statistic"), "analyst_count": parsed.get("analyst_count"),
            }
            event = {"id": f"probe-{target['ticker']}-{target['event_date']}",
                     "ticker": target["ticker"], "event_date": target["event_date"]}
            snapshot = build_consensus_snapshot(event, metric, attempt, raw, raw_ref)
            snapshots[metric] = {
                "snapshot_status": snapshot["snapshot_status"], "reason": snapshot["reason"],
                "source_row_available": True,
                "missing_data_as_of": not bool(parsed.get("data_as_of")),
                "missing_basis_code": not bool(attempt.get("basis_code")),
                "missing_statistic": not bool(attempt.get("statistic")),
                "missing_period_end_date": not bool(attempt.get("period_end_date")),
                "raw_response_sha256": digest,
            }

    return {
        **parsed, "observed_at": observed_at, "http_status": status,
        "content_type": headers.get("content-type"), "raw_response_sha256": digest,
        "raw_response_ref": raw_ref, "transport_error": error, "host_attempts": attempts,
        "snapshots": snapshots, "calendar_write": False, "production_write": False,
    }


def self_test():
    sample = b"""
    <html><head><title>Example earnings</title></head><body>
    <div>Currency in USD</div><div>All numbers in USD</div>
    <table><tr><th>Release Date</th><th>Period End</th><th>EPS</th><th>Forecast</th><th>Revenue</th><th>Forecast</th></tr>
    <tr><td>Nov 17, 2026</td><td>10/2026</td><td>--</td><td>/2.47</td><td>--</td><td>/108.85B</td></tr></table>
    </body></html>
    """
    parsed = parse_earnings_row(sample, TARGETS[0])
    assert parsed["row_found"]
    assert parsed["eps_estimate"] == 2.47
    assert parsed["revenue_estimate"] == 108.85
    assert parsed["currency"] == "USD"
    assert parsed["data_as_of"] is None

    hk_sample = """
    <html><head><title>NVDA 收益</title></head><body>
    <div>貨幣 USD</div><div>數字皆以USD計</div>
    <table><tr><th>公佈日期</th><th>截止</th><th>EPS</th><th>/預測</th><th>營收</th><th>/預測</th></tr>
    <tr><td>2026年11月17日</td><td>2026-10</td><td>--</td><td>/2.47</td><td>--</td><td>/1,088.00億</td></tr></table>
    </body></html>
    """.encode("utf-8")
    hk_parsed = parse_earnings_row(hk_sample, TARGETS[0])
    assert hk_parsed["row_found"]
    assert hk_parsed["eps_estimate"] == 2.47
    assert hk_parsed["revenue_estimate"] == 108.8
    assert hk_parsed["revenue_unit"] == "USD_BILLION"
    assert hk_parsed["currency"] == "USD"
    print("PASS: Investing.com English/HK locale parser; 億 converted to billions; missing as-of stays null")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--archive-dir", required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    archive_dir = Path(args.archive_dir)
    results = []
    for target in TARGETS:
        results.append(fetch_one(target, archive_dir))
        time.sleep(1.0)
    report = {
        "probe": "investing_com_public_earnings_page",
        "captured_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "branch_scope": "simulation/tac-process-lab-2026-11-06",
        "source_priority": "level 4 fallback only; Yahoo Finance, LSEG and FactSet precede it",
        "targets": results,
        "verdict": "ROW_CAPTURED_BUT_PIT_FIELDS_INCOMPLETE" if any(x.get("row_found") for x in results) else "NO_TARGET_ROWS_CAPTURED",
        "limitations": [
            "This is a read-only page probe, not a production Collector.",
            "Generic page Last Updated is not treated as consensus data_as_of.",
            "Undisclosed EPS basis, statistic, analyst count, period end date, or as-of time remain null.",
            "A numeric forecast alone is not eligible for directional Beat/Miss.",
            "No calendar JSON, HTML, main branch, or schedule is modified."
        ]
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "targets": [{
            "ticker": x["ticker"], "http_status": x["http_status"],
            "row_found": x["row_found"], "eps_estimate": x["eps_estimate"],
            "revenue_estimate": x["revenue_estimate"], "currency": x["currency"],
            "data_as_of": x["data_as_of"], "snapshots": x["snapshots"],
            "transport_error": x["transport_error"]
        } for x in results],
        "output": str(out)
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
