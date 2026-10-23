#!/usr/bin/env python3
"""Isolated source-access probe for VIX, MOVE and SOX. Capture-only; not production data."""
import json
import re
import csv
import io
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

OUT = Path("market-indicators-evidence")
OUT.mkdir(exist_ok=True)
SOURCES = [
    {"key": "vix_google", "label": "VIX Google Finance", "url": "https://www.google.com/finance/quote/VIX:INDEXCBOE", "needles": ["VIX"]},
    {"key": "vix_cboe", "label": "VIX Cboe official", "url": "https://www.cboe.com/tradable_products/vix/", "needles": ["VIX"]},
    {"key": "move_google", "label": "MOVE Google Finance", "url": "https://www.google.com/finance/quote/MOVE:INDEXNYSEGIS", "needles": ["MOVE"]},
    {"key": "move_barchart_api", "label": "MOVE Barchart historical API reachability probe", "url": "https://www.barchart.com/proxies/core-api/v1/historical/get?symbol=%24MOVE&fields=tradeTime.format%28m%252Fd%252FY%29%252CopenPrice%252ChighPrice%252ClowPrice%252ClastPrice%252CpriceChange%252CpercentChange%252Cvolume%252CsymbolCode%252CsymbolType&type=eod&orderBy=tradeTime&orderDir=desc&limit=10&meta=field.shortName%252Cfield.type%252Cfield.description&raw=1", "needles": ["MOVE", "tradeTime"]},
    {"key": "sox_google", "label": "SOX Google Finance", "url": "https://www.google.com/finance/quote/SOX:INDEXNASDAQ", "needles": ["SOX", "Semiconductor"]},
    {"key": "sox_nasdaq", "label": "SOX Nasdaq official", "url": "https://indexes.nasdaq.com/Index/Overview/SOX", "needles": ["SOX", "Semiconductor"]},
]
def stamp():
    now = datetime.now(timezone.utc)
    return {"utc": now.isoformat(), "taipei": now.astimezone(ZoneInfo("Asia/Taipei")).isoformat()}

result = {
    "purpose": "source reachability and visual-evidence probe only; values are not yet approved for publication",
    "started_at": stamp(),
    "status": "running",
    "sources": [],
    "validation_errors": [],
    "nonblocking_warnings": [],
}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-dev-shm-usage"])
    context = browser.new_context(
        viewport={"width": 1600, "height": 1200},
        device_scale_factor=1,
        locale="en-US",
        timezone_id="Asia/Taipei",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
    )
    for source in SOURCES:
        item = {**source, "captured_at": stamp(), "ok": False}
        page = context.new_page()
        page.set_default_timeout(12000)
        try:
            response = page.goto(source["url"], wait_until="domcontentloaded", timeout=30000)
            item["http_status"] = response.status if response else None
            page.wait_for_timeout(6500)
            item["title"] = page.title()
            item["final_url"] = page.url
            # Yahoo's ticker symbol alone is not enough to establish instrument identity.
            # The current ^MOVE page title identifies a Northern Trust iBoxx 5-Year
            # Treasury instrument, not the ICE BofA MOVE Index. Exclude it from fallback
            # validation unless the page title explicitly identifies the target index.
            if source["key"] == "move_yahoo_history":
                title = item["title"].casefold()
                item["instrument_identity_valid"] = (
                    "merrill lynch option volatility estimate" in title
                    or "ice bofa move index" in title
                    or "ice bofaml move index" in title
                )
                if not item["instrument_identity_valid"]:
                    item["instrument_identity_warning"] = (
                        "Ticker ^MOVE page title does not identify the ICE BofA MOVE Index; "
                        "rows must not be treated as independent MOVE-index history."
                    )
            try:
                body = page.locator("body").inner_text(timeout=10000)
            except Exception as exc:
                body = ""
                item["body_error"] = f"{type(exc).__name__}: {exc}"
            item["body_text"] = body[:12000]
            item["body_text_length"] = len(body)
            # Extract numeric quote candidates from visible text labels. Diagnostic only;
            # date/close semantics and independent agreement must be checked before publication.
            item["candidate_quote"] = None
            item["candidate_quote_source"] = None
            item["candidate_quote_status"] = "not_found"
            lines = [line.strip() for line in body.splitlines() if line.strip()]
            # Explicitly separate quote date/time from capture time. Google Finance's
            # "Today" is not sufficient evidence of a prior-session close.
            item["candidate_quote_date"] = None
            item["candidate_quote_timestamp"] = None
            item["previous_close"] = item.get("previous_close")
            item["previous_close_source"] = item.get("previous_close_source")
            item["close_interpretation"] = "unclassified; do not publish as validated close"
            if source["key"] == "vix_cboe":
                asof = re.search(r"\(as of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\)", body, re.I)
                if asof:
                    try:
                        item["candidate_quote_date"] = datetime.strptime(asof.group(1), "%B %d, %Y").date().isoformat()
                    except ValueError:
                        pass
                data_asof = re.search(r"Data as of\s+([0-9:]+\s*[AP]M)\s+(\d{1,2}/\d{1,2}/\d{4})", body, re.I)
                if data_asof:
                    item["candidate_quote_timestamp"] = f"{data_asof.group(2)} {data_asof.group(1)}"
            elif source["key"] == "sox_nasdaq":
                asof = re.search(r"DATA AS OF\s+(\d{1,2}/\d{1,2}/\d{4})", body, re.I)
                if asof:
                    try:
                        item["candidate_quote_date"] = datetime.strptime(asof.group(1), "%m/%d/%Y").date().isoformat()
                    except ValueError:
                        pass
            elif source["key"] in ("vix_google", "move_google", "sox_google"):
                # Google Finance typically renders a quote timestamp like
                # "Oct 22, 4:17:30 PM UTC-4" in the visible page text.
                ts = re.search(r"\b([A-Za-z]{3}\s+\d{1,2},\s+\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M\s+UTC[+-]\d+)\b", body)
                if ts:
                    item["candidate_quote_timestamp"] = ts.group(1)
                    try:
                        parsed = datetime.strptime(ts.group(1).split(" UTC")[0], "%b %d, %I:%M:%S %p")
                    except ValueError:
                        try:
                            parsed = datetime.strptime(ts.group(1).split(" UTC")[0], "%b %d, %I:%M %p")
                        except ValueError:
                            parsed = None
                    if parsed:
                        item["candidate_quote_date"] = parsed.replace(year=2026).date().isoformat()
            prev_google = re.search(r"Prev\. close\s+([0-9,]+\.\d+)", body, re.I)
            if prev_google and source["key"] in ("vix_google", "move_google", "sox_google"):
                item["previous_close"] = float(prev_google.group(1).replace(",", ""))
                item["previous_close_source"] = "Google Finance explicitly labelled Prev. close; candidate only"
                item["previous_close_status"] = "candidate_only_previous_session_close"
            label_by_key = {
                "vix_google": ["VIX"],
                "move_google": ["Merrill Lynch Option Volatility Estimate", "MOVE"],
                "sox_google": ["PHLX Semiconductor Sector", "SOX"],
            }
            labels = label_by_key.get(source["key"], [])
            if source["key"] == "sox_nasdaq":
                # Nasdaq official page presents the quote immediately after its DATA AS OF line.
                match = re.search(r"DATA AS OF\s+\d{1,2}/\d{1,2}/\d{4}\s+([0-9,]+\.\d+)", body, re.I)
                if match:
                    item["candidate_quote"] = float(match.group(1).replace(",", ""))
                    item["candidate_quote_source"] = "Nasdaq official DATA AS OF quote"
                    item["candidate_quote_status"] = "candidate_only"
            elif source["key"] == "vix_cboe":
                # Cboe's official page exposes the VIX spot price and an explicit as-of date.
                # Capture both current spot and the explicitly labelled previous close;
                # never confuse an intraday spot quote with the prior session's close.
                match = re.search(r"\(as of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\)\s+\$([0-9]+\.\d+)", body, re.I | re.S)
                prev = re.search(r"VIX\s+PREV\. CLOSE\s+([0-9]+\.\d+)", body, re.I)
                if match:
                    item["candidate_quote"] = float(match.group(2))
                    item["candidate_quote_source"] = f"Cboe official VIX spot price; as of {match.group(1)}"
                    item["candidate_quote_status"] = "candidate_only_intraday"
                if prev:
                    item["previous_close"] = float(prev.group(1))
                    item["previous_close_source"] = "Cboe official VIX PREV. CLOSE field"
                    item["previous_close_status"] = "candidate_only_previous_session_close"
            elif labels:
                for idx, line in enumerate(lines):
                    if any(line.casefold() == label.casefold() for label in labels):
                        for candidate_line in lines[idx + 1:idx + 5]:
                            cleaned = candidate_line.replace(",", "").replace("$", "").strip()
                            if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", cleaned):
                                value = float(cleaned)
                                if source["key"] == "vix_google" and 0 <= value <= 150:
                                    item["candidate_quote"] = value
                                elif source["key"] == "move_google" and 0 <= value <= 300:
                                    item["candidate_quote"] = value
                                elif source["key"] == "sox_google" and 100 <= value <= 100000:
                                    item["candidate_quote"] = value
                                if item["candidate_quote"] is not None:
                                    item["candidate_quote_source"] = f"visible page text after label: {line}"
                                    item["candidate_quote_status"] = "candidate_only"
                                    break
                        if item["candidate_quote"] is not None:
                            break
            if item["candidate_quote"] is None and source["key"] in ("vix_google", "move_google", "sox_google", "sox_nasdaq"):
                item["candidate_quote_status"] = "label_quote_pattern_not_found"
            screenshot_path = OUT / f"{source['key']}.png"
            try:
                # Google Finance sometimes fails a first screenshot while fonts /
                # charts are still settling. Retry with animations disabled and a
                # longer timeout before marking visual evidence unavailable.
                page.screenshot(path=str(screenshot_path), full_page=False, timeout=30000, animations="disabled")
                item["screenshot"] = str(screenshot_path)
                item["screenshot_status"] = "captured"
            except Exception as first_exc:
                item["screenshot_first_error"] = f"{type(first_exc).__name__}: {first_exc}"
                try:
                    page.screenshot(path=str(screenshot_path), full_page=False, timeout=30000, animations="disabled", type="png")
                    item["screenshot"] = str(screenshot_path)
                    item["screenshot_status"] = "captured_on_retry"
                except Exception as retry_exc:
                    item["screenshot_error"] = f"{type(retry_exc).__name__}: {retry_exc}"
                    item["screenshot_status"] = "failed_after_retry"
            item["keyword_checks"] = {word: bool(re.search(re.escape(word), body, re.I)) for word in source["needles"]}
            item["ok"] = bool(response and response.status == 200 and len(body) > 100 and all(item["keyword_checks"].values()) and screenshot_path.exists())
            if not item["ok"]:
                message = f"{source['label']}: page/keyword/screenshot validation failed"
                # Barchart historical endpoint is optional; HTTP 403/access denial
                # should remain visible but must not fail the whole capture probe.
                if source["key"] == "move_barchart_api":
                    result["nonblocking_warnings"].append(message)
                    item["blocking_for_capture"] = False
                else:
                    result["validation_errors"].append(message)
                    item["blocking_for_capture"] = True
            else:
                item["blocking_for_capture"] = False
            # Classify semantics, not just successful numeric extraction.
            if source["key"] == "vix_cboe" and item.get("previous_close") is not None:
                item["close_interpretation"] = "previous_close field extracted; session date must be independently confirmed"
            elif source["key"] == "sox_nasdaq" and item.get("candidate_quote_date"):
                item["close_interpretation"] = "dated official index quote candidate; compare with independent source and verify change arithmetic"
                pc = re.search(r"Previous Close\s+([0-9,]+\.\d+)", body, re.I)
                if pc:
                    parsed_previous = float(pc.group(1).replace(",", ""))
                    if item.get("candidate_quote") is not None and abs(parsed_previous - float(item["candidate_quote"])) < 0.02:
                        # Some Nasdaq page variants incorrectly mirror the current
                        # quote into the Previous Close field. Flag rather than trust it.
                        item["previous_close"] = None
                        item["previous_close_source"] = "Nasdaq official Previous Close field rejected: identical to current quote"
                        item["previous_close_status"] = "rejected_suspected_page_variant_error"
                        item["previous_close_validation"] = "failed_same_as_current_quote"
                        item["previous_close_reported_value"] = parsed_previous
                        item["previous_close_validation_blocking"] = True
                        result["validation_errors"].append(
                            f"SOX Nasdaq official page reports Previous Close {parsed_previous:.2f}, "
                            f"identical to its current quote {item['candidate_quote']:.2f}; "
                            "official previous-close field is invalid for daily-change validation"
                        )
                    else:
                        item["previous_close"] = parsed_previous
                        item["previous_close_source"] = "Nasdaq official Previous Close field; candidate only"
                        item["previous_close_status"] = "candidate_only_previous_session_close"
                        item["previous_close_validation"] = "not_independently_verified"
                # Validate the official page's displayed point change against the
                # extracted current quote and prior close when both are plausible.
                change_match = re.search(r"DATA AS OF\s+\d{1,2}/\d{1,2}/\d{4}\s+[0-9,]+\.\d+\s+([+-][0-9,]+\.\d+)", body, re.I)
                if change_match and item.get("previous_close") is not None and item.get("candidate_quote") is not None:
                    displayed_change = float(change_match.group(1).replace(",", ""))
                    calculated_change = float(item["candidate_quote"]) - float(item["previous_close"])
                    arithmetic_match = abs(displayed_change - calculated_change) < 0.02
                    item["change_arithmetic_check"] = {
                        "displayed_change": displayed_change,
                        "calculated_change": round(calculated_change, 2),
                        "matches_within_0_02": arithmetic_match,
                        "status": "consistent" if arithmetic_match else "official_page_change_conflicts_with_quote_and_previous_close",
                        "production_blocking": not arithmetic_match
                    }
                    if not arithmetic_match:
                        result["validation_errors"].append(
                            f"SOX Nasdaq official page arithmetic mismatch: displayed change {displayed_change:.2f}, "
                            f"but quote {item['candidate_quote']:.2f} minus previous close {item['previous_close']:.2f} "
                            f"equals {calculated_change:.2f}"
                        )
            elif source["key"] in ("move_google", "sox_google") and item.get("candidate_quote_date"):
                item["close_interpretation"] = "timestamped quote candidate; timestamp and independent source must confirm regular-session close"
            elif source["key"] == "vix_google" and item.get("candidate_quote_timestamp"):
                item["close_interpretation"] = "timestamped VIX quote; do not assume it is prior-session close"
            # Do not treat a displayed quote as validated until extraction and independent numeric cross-check exist.
            item["quote_extraction_status"] = item.get("candidate_quote_status", "not_applicable_official_page_capture_only")
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            result["validation_errors"].append(f"{source['label']}: {item['error']}")
        result["sources"].append(item)
        page.close()
    browser.close()

# Dated-history references: regression fixture for the last US session (2026-10-22)
# as observed on 2026-10-23 Taiwan time. Keep history captures separate from live quote widgets.
HISTORY_SOURCES = [
    {"key": "vix_cboe_history", "label": "VIX Cboe official historical CSV", "url": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv", "date_patterns": [r"10/22/2026", r"10/21/2026"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
    {"key": "vix_yahoo_history", "label": "VIX Yahoo Finance historical closes", "url": "https://hk.finance.yahoo.com/quote/%5EVIX/history/", "date_patterns": [r"22 Oct 2026|Oct 22, 2026|2026年10月22日", r"21 Oct 2026|Oct 21, 2026|2026年10月21日"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
    {"key": "move_investing_history", "label": "MOVE Investing.com historical prices", "url": "https://uk.investing.com/indices/ice-bofaml-move-historical-data", "date_patterns": [r"22/10/2026|22 Oct 2026|Oct 22, 2026", r"21/10/2026|21 Oct 2026|Oct 21, 2026"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 0},
    {"key": "move_yahoo_history", "label": "MOVE Yahoo Finance historical closes", "url": "https://finance.yahoo.com/quote/%5EMOVE/history/", "date_patterns": [r"22 Oct 2026|Oct 22, 2026|2026年10月22日", r"21 Oct 2026|Oct 21, 2026|2026年10月21日"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
    {"key": "move_barchart_history", "label": "MOVE Barchart historical prices", "url": "https://www.barchart.com/stocks/quotes/%24MOVE/historical-download", "date_patterns": [r"Oct 22, 2026|10/22/2026|2026-10-22", r"Oct 21, 2026|10/21/2026|2026-10-21"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
    {"key": "move_eoddata_history", "label": "MOVE EODData end-of-day history", "url": "https://www.eoddata.com/stockquote/INDEX/MOVE.htm", "date_patterns": [r"22 Oct 26|Oct 22, 2026", r"21 Oct 26|Oct 21, 2026"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
    {"key": "sox_yahoo_history", "label": "SOX Yahoo Finance historical closes", "url": "https://hk.finance.yahoo.com/quote/%5ESOX/history/", "date_patterns": [r"22 Oct 2026|Oct 22, 2026|2026年10月22日", r"21 Oct 2026|Oct 21, 2026|2026年10月21日"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
]

# Cross-source comparison is deliberately limited to dated, comparable fields.
by_key = {x.get("key"): x for x in result["sources"]}
# Capture date-matched historical rows as an independent validation layer.
# Parsing is conservative: retain source row text and extracted numeric columns for audit.
result["historical_references"] = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
    context = browser.new_context(viewport={"width": 1600, "height": 1200}, locale="en-US", timezone_id="Asia/Taipei", extra_http_headers={"Accept-Language": "en-US,en;q=0.9"})
    for source in HISTORY_SOURCES:
        item = {**source, "captured_at": stamp(), "ok": False, "rows": []}
        page = context.new_page()
        page.set_default_timeout(12000)
        try:
            # Cboe serves this endpoint as a file download, not an HTML page.
            # Playwright page.goto() raises "Download is starting", so fetch and
            # parse the official CSV directly with the standard library.
            if source["key"] == "vix_cboe_history":
                request = urllib.request.Request(
                    source["url"],
                    headers={"User-Agent": "Mozilla/5.0 TAC-source-probe/1.0", "Accept": "text/csv,*/*"},
                )
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read().decode("utf-8-sig")
                    item["http_status"] = response.status
                    item["final_url"] = response.geturl()
                item["body_text"] = body[:16000]
                item["body_text_length"] = len(body)
                reader = csv.reader(io.StringIO(body))
                header = next(reader, [])
                item["csv_header"] = header
                parsed = {}
                for raw_row in reader:
                    if len(raw_row) < 5:
                        continue
                    try:
                        date_key = datetime.strptime(raw_row[0].strip(), "%m/%d/%Y").date().isoformat()
                        close = float(raw_row[4].replace(",", "").strip())
                    except (ValueError, IndexError):
                        continue
                    if date_key in source["target_dates"]:
                        parsed[date_key] = {
                            "date": date_key,
                            "row_text": ",".join(raw_row),
                            "close_candidate": close,
                            "close_display_text": raw_row[4].strip(),
                            "numeric_columns": [float(v.replace(",", "").strip()) for v in raw_row[1:5]],
                            "status": "candidate_extracted_not_yet_certified",
                        }
                item["rows"] = [parsed[d] for d in source["target_dates"] if d in parsed]
                item["ok"] = bool(item["http_status"] == 200 and all(d in parsed for d in source["target_dates"]))
                item["note"] = "Official Cboe CSV fetched directly; rows/close values are candidates pending cross-source validation."
                item["screenshot_status"] = "not_applicable_raw_csv_source"
                if not item["ok"]:
                    item["error"] = "Official Cboe CSV did not contain all requested dated rows."
                result["historical_references"].append(item)
                page.close()
                continue
            response = page.goto(source["url"], wait_until="domcontentloaded", timeout=30000)
            item["http_status"] = response.status if response else None
            page.wait_for_timeout(4500)
            item["title"] = page.title()
            item["final_url"] = page.url
            # Validate instrument identity in the historical-reference loop itself.
            # The Yahoo ^MOVE symbol can resolve to a different Treasury instrument.
            if source["key"] == "move_yahoo_history":
                title = item["title"].casefold()
                item["instrument_identity_valid"] = (
                    "merrill lynch option volatility estimate" in title
                    or "ice bofa move index" in title
                    or "ice bofaml move index" in title
                )
                if not item["instrument_identity_valid"]:
                    item["instrument_identity_warning"] = (
                        "Yahoo ^MOVE title does not identify the ICE BofA MOVE Index; "
                        "do not use these rows as independent MOVE-index history."
                    )
            body = page.locator("body").inner_text(timeout=10000)
            item["body_text"] = body[:16000]
            item["body_text_length"] = len(body)
            lines = [line.strip() for line in body.splitlines() if line.strip()]
            for target_date, date_pattern in zip(source["target_dates"], source["date_patterns"]):
                matching = next((line for line in lines if re.search(date_pattern, line, re.I)), None)
                row = {"date": target_date, "row_text": matching, "close_candidate": None, "close_display_text": None, "status": "row_not_found"}
                if matching:
                    row_payload = re.sub(date_pattern, "", matching, count=1, flags=re.I)
                    nums = re.findall(r"(?<![A-Za-z])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", row_payload)
                    # Yahoo rows start with the date followed by Open/High/Low/Close;
                    # Investing.com rows start with date then Price (close candidate).
                    if len(nums) > source["value_index"]:
                        try:
                            row["close_display_text"] = nums[source["value_index"]]
                            row["close_candidate"] = float(row["close_display_text"].replace(",", ""))
                            row["numeric_columns"] = [float(v.replace(",", "")) for v in nums]
                            row["status"] = "candidate_extracted_not_yet_certified"
                        except ValueError:
                            row["status"] = "numeric_parse_failed"
                item["rows"].append(row)
            shot = OUT / f"{source['key']}.png"
            try:
                page.screenshot(path=str(shot), full_page=False, timeout=30000, animations="disabled")
                item["screenshot"] = str(shot)
                item["screenshot_status"] = "captured"
            except Exception as exc:
                item["screenshot_status"] = "failed"
                item["screenshot_error"] = f"{type(exc).__name__}: {exc}"
            item["ok"] = bool(
                response and response.status == 200 and len(body) > 100
                and all(x["close_candidate"] is not None for x in item["rows"])
                and item.get("instrument_identity_valid", True)
            )
            item["note"] = "Historical row values are candidates; verify column semantics and source publication date before production use."
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        result["historical_references"].append(item)
        page.close()
    browser.close()

# Compare historical close candidates to live-page previous-close fields only when the
# historical row for the immediately preceding session was successfully extracted.
history_by_key = {x.get("key"): x for x in result["historical_references"]}
for live_key, hist_key in [("vix_google", "vix_cboe_history"), ("move_google", "move_investing_history"), ("sox_google", "sox_yahoo_history")]:
    live = by_key.get(live_key, {})
    hist = history_by_key.get(hist_key, {})
    fallback_hist_key = "move_yahoo_history" if live_key == "move_google" else None
    fallback_hist = history_by_key.get(fallback_hist_key, {}) if fallback_hist_key else {}
    # If the primary MOVE history endpoint is blocked, try Yahoo's index symbol
    # first, then EODData. Do not treat a successful page load as a verified close.
    if not hist.get("ok") and fallback_hist.get("ok"):
        hist_key, hist = fallback_hist_key, fallback_hist
    if live_key == "move_google" and not hist.get("ok"):
        eod_fallback = history_by_key.get("move_eoddata_history", {})
        if eod_fallback.get("ok"):
            hist_key, hist = "move_eoddata_history", eod_fallback
    # The correct historical row is determined from the live quote's own date,
    # not a fixed date shared by all instruments. A quote dated 2026-10-23
    # should compare its previous close with 2026-10-22; a quote dated
    # 2026-10-22 should compare with 2026-10-21.
    quote_date = live.get("candidate_quote_date")
    rows = hist.get("rows", [])
    row_dates = [row.get("date") for row in rows if row.get("date")]
    expected_date = None
    if quote_date and quote_date in row_dates:
        # Historical providers expose trading sessions in descending order.
        # Use the immediately following row as the prior trading session.
        idx = row_dates.index(quote_date)
        if idx + 1 < len(row_dates):
            expected_date = row_dates[idx + 1]
    if expected_date is None and quote_date:
        # If the quote date itself is absent from the historical table (e.g.
        # live page is intraday and history is not yet updated), use the latest
        # available history date strictly before the quote date.
        expected_date = next((d for d in row_dates if d < quote_date), None)
    prior = next((row for row in rows if row.get("date") == expected_date), None)
    hist_value = prior.get("close_candidate") if prior else None
    live_value = live.get("previous_close")
    exact_match = bool(hist_value is not None and live_value is not None and abs(float(hist_value) - float(live_value)) < 0.02)
    # Derive the historical source's displayed precision from its original row text.
    # A one-decimal backup (EODData) can only support a rounded comparison, not exact agreement.
    displayed_precision = None
    if prior and prior.get("close_display_text") is not None:
        token = prior["close_display_text"]
        displayed_precision = len(token.rsplit(".", 1)[1]) if "." in token else 0
    rounded_tolerance = (0.5 * (10 ** (-displayed_precision))) if displayed_precision is not None else None
    rounded_match = bool(not exact_match and hist_value is not None and live_value is not None and rounded_tolerance is not None and abs(float(hist_value) - float(live_value)) <= rounded_tolerance + 1e-9)
    if exact_match:
        comparison_result = "exact_match_within_0_02"
    elif rounded_match:
        comparison_result = "rounded_match_at_source_display_precision"
    elif not hist.get("ok"):
        comparison_result = "historical_source_unavailable"
    else:
        comparison_result = "not_verified_or_mismatch"
    result.setdefault("dated_history_checks", []).append({
        "live_source": live_key,
        "historical_source": hist_key,
        "quote_date": quote_date,
        "target_session_date": expected_date,
        "historical_close_candidate": hist_value,
        "live_previous_close_candidate": live_value,
        "historical_displayed_decimal_places": displayed_precision,
        "rounded_comparison_tolerance": rounded_tolerance,
        "matches_within_0_02": exact_match,
        "rounded_match_at_source_precision": rounded_match,
        "result": comparison_result,
        "note": "Exact matches and rounded matches are distinct. A rounded match is not exact agreement; mismatches block approval and do not establish which provider is stale."
    })

g = by_key.get("sox_google", {})
n = by_key.get("sox_nasdaq", {})
result["cross_source_checks"] = []
# Compare the official Cboe CSV and Yahoo's dated VIX history directly.
# This detects disagreement between historical baselines even when both pages parse.
cboe_hist = history_by_key.get("vix_cboe_history", {})
yahoo_hist = history_by_key.get("vix_yahoo_history", {})
cboe_rows = {row.get("date"): row for row in cboe_hist.get("rows", []) if row.get("date")}
yahoo_rows = {row.get("date"): row for row in yahoo_hist.get("rows", []) if row.get("date")}
for session_date in sorted(set(cboe_rows) & set(yahoo_rows), reverse=True):
    cboe_close = cboe_rows[session_date].get("close_candidate")
    yahoo_close = yahoo_rows[session_date].get("close_candidate")
    if cboe_close is None or yahoo_close is None:
        continue
    delta = abs(float(cboe_close) - float(yahoo_close))
    result["cross_source_checks"].append({
        "pair": ["vix_cboe_history.close", "vix_yahoo_history.close"],
        "session_date": session_date,
        "cboe_close": float(cboe_close),
        "yahoo_close": float(yahoo_close),
        "absolute_difference": round(delta, 6),
        "values_match_within_0_02": delta < 0.02,
        "result": "historical_sources_agree" if delta < 0.02 else "historical_close_mismatch",
        "production_blocking": bool(delta >= 0.02),
        "note": "Dated close-to-close comparison; mismatches block approval and require source/date/field investigation."
    })
if g.get("candidate_quote") is not None and n.get("candidate_quote") is not None:
    same_date = bool(g.get("candidate_quote_date") and g.get("candidate_quote_date") == n.get("candidate_quote_date"))
    same_value = abs(float(g["candidate_quote"]) - float(n["candidate_quote"])) < 0.02
    result["cross_source_checks"].append({
        "pair": ["sox_google", "sox_nasdaq"],
        "same_quote_date": same_date,
        "values_match_within_0_02": same_value,
        "result": "candidate_sources_agree" if same_date and same_value else "needs_manual_review",
        "note": "Agreement is a diagnostic only; it does not certify source accuracy or production readiness."
    })
# Validate VIX displayed daily point changes against each page's own quote and previous close.
# These arithmetic checks catch extraction/label errors but do not establish which source is correct.
for key, pattern in [
    ("vix_google", r"\(([+-][0-9,]+\.\d+)\)\s*Today"),
    ("vix_cboe", r"([0-9]+\.\d+)%\s*\(([+-][0-9,]+\.\d+)\)\s*CHANGE"),
]:
    item = by_key.get(key, {})
    if item.get("candidate_quote") is not None and item.get("previous_close") is not None:
        body = item.get("body_text", "")
        match = re.search(pattern, body, re.I)
        if match:
            displayed = float((match.group(2) if key == "vix_cboe" else match.group(1)).replace(",", ""))
            calculated = float(item["candidate_quote"]) - float(item["previous_close"])
            result["cross_source_checks"].append({
                "pair": [f"{key}.quote", f"{key}.previous_close"],
                "displayed_change": displayed,
                "calculated_change": round(calculated, 2),
                "change_matches_within_0_02": abs(displayed - calculated) < 0.02,
                "result": "arithmetic_consistent" if abs(displayed - calculated) < 0.02 else "change_arithmetic_mismatch",
                "note": "Same-page arithmetic is not an independent source validation; cross-source disagreements remain blocking."
            })
# Compare the VIX previous-close candidates. A disagreement is a useful
# warning because Google Finance may lag or expose a stale quote widget.
vg = by_key.get("vix_google", {})
vc = by_key.get("vix_cboe", {})
if vg.get("previous_close") is not None and vc.get("previous_close") is not None:
    delta = abs(float(vg["previous_close"]) - float(vc["previous_close"]))
    google_date = vg.get("candidate_quote_date")
    cboe_date = vc.get("candidate_quote_date")
    vix_hist = history_by_key.get("vix_cboe_history", {})
    vix_rows = vix_hist.get("rows", [])
    row_by_date = {row.get("date"): row for row in vix_rows if row.get("date")}
    # A one-session-lag diagnosis requires all three dates and values:
    # Cboe prev close == immediately prior session; Google prev close == the older session.
    prior_row = next((row for row in vix_rows if row.get("date") and google_date and row["date"] < google_date), None)
    older_row = None
    if prior_row:
        older_row = next((row for row in vix_rows if row.get("date") and row["date"] < prior_row["date"]), None)
    prior_value = prior_row.get("close_candidate") if prior_row else None
    older_value = older_row.get("close_candidate") if older_row else None
    cboe_matches_prior = bool(prior_value is not None and abs(float(vc["previous_close"]) - float(prior_value)) < 0.02)
    google_matches_older = bool(older_value is not None and abs(float(vg["previous_close"]) - float(older_value)) < 0.02)
    google_differs_prior = bool(prior_value is not None and abs(float(vg["previous_close"]) - float(prior_value)) >= 0.02)
    lag_supported = bool(google_date and cboe_date == google_date and cboe_matches_prior and google_matches_older and google_differs_prior)
    root_status = "google_previous_close_matches_two_sessions_back_one_session_stale_supported" if lag_supported else "not_proven"
    if delta >= 0.02:
        result["validation_errors"].append(
            "VIX Google Finance previous close conflicts with Cboe official previous close "
            f"({float(vg['previous_close']):.2f} vs {float(vc['previous_close']):.2f}); "
            f"historical dates indicate Google matches the older session ({root_status}). "
            "Do not use Google previous-close field for a production daily-change calculation."
        )
    result["cross_source_checks"].append({
        "pair": ["vix_google.previous_close", "vix_cboe.previous_close"],
        "google_quote_date": google_date,
        "cboe_quote_date": cboe_date,
        "google_previous_close": float(vg["previous_close"]),
        "cboe_previous_close": float(vc["previous_close"]),
        "values_match_within_0_02": delta < 0.02,
        "absolute_difference": round(delta, 4),
        "historical_immediately_prior_session_date": prior_row.get("date") if prior_row else None,
        "historical_immediately_prior_session_close": prior_value,
        "historical_two_sessions_back_date": older_row.get("date") if older_row else None,
        "historical_two_sessions_back_close": older_value,
        "cboe_previous_close_matches_prior_session": cboe_matches_prior,
        "google_previous_close_matches_two_sessions_back": google_matches_older,
        "google_previous_close_differs_from_prior_session": google_differs_prior,
        "result": "candidate_sources_agree" if delta < 0.02 else "previous_close_mismatch",
        "root_cause_status": root_status,
        "production_blocking": bool(delta >= 0.02),
        "next_validation": "A supported one-session lag diagnosis is still a source-quality finding, not production approval; keep this field blocked until a reliable current-session close source is selected.",
        "note": "Date-based diagnostic uses captured historical rows. It only supports a one-session-lag finding when the Cboe prior close matches the immediately prior session and Google's value matches the older session."
    })
# Validate SOX's displayed daily point change against its explicitly labelled previous close.
# This is same-page arithmetic only; it is not independent source verification.
# Compare Google's current VIX quote with Cboe's official current spot quote.
# This is a cross-source snapshot comparison, not a close-price adjudication.
if vg.get("candidate_quote") is not None and vc.get("candidate_quote") is not None:
    quote_delta = abs(float(vg["candidate_quote"]) - float(vc["candidate_quote"]))
    implied_change_vs_cboe_prev = float(vg["candidate_quote"]) - float(vc["previous_close"]) if vc.get("previous_close") is not None else None
    result["cross_source_checks"].append({
        "pair": ["vix_google.quote", "vix_cboe.quote"],
        "google_quote": float(vg["candidate_quote"]),
        "cboe_quote": float(vc["candidate_quote"]),
        "absolute_difference": round(quote_delta, 4),
        "values_match_within_0_05": quote_delta < 0.05,
        "google_quote_minus_cboe_previous_close": round(implied_change_vs_cboe_prev, 2) if implied_change_vs_cboe_prev is not None else None,
        "result": "current_quotes_close" if quote_delta < 0.05 else "current_quote_mismatch",
        "note": "Snapshot times may differ. This check flags discrepancies; it does not substitute Cboe's prior close into Google's quote calculation."
    })
sg = by_key.get("sox_google", {})
if sg.get("candidate_quote") is not None and sg.get("previous_close") is not None:
    body = sg.get("body_text", "")
    change = re.search(r"\(([+-][0-9,]+\.\d+)\)\s*Today", body, re.I)
    if change:
        displayed = float(change.group(1).replace(",", ""))
        calculated = float(sg["candidate_quote"]) - float(sg["previous_close"])
        result["cross_source_checks"].append({
            "pair": ["sox_google.quote", "sox_google.previous_close"],
            "displayed_change": displayed,
            "calculated_change": round(calculated, 2),
            "change_matches_within_0_02": abs(displayed - calculated) < 0.02,
            "result": "arithmetic_consistent" if abs(displayed - calculated) < 0.02 else "change_arithmetic_mismatch",
            "note": "Same-page arithmetic is not an independent source validation."
        })
mg = by_key.get("move_google", {})
if mg.get("candidate_quote") is not None and mg.get("previous_close") is not None:
    # The displayed daily change is useful arithmetic validation, not an independent source.
    body = mg.get("body_text", "")
    change = re.search(r"\(([+-][0-9,]+\.\d+)\)\s*Today", body, re.I)
    if change:
        displayed = float(change.group(1).replace(",", ""))
        calculated = float(mg["candidate_quote"]) - float(mg["previous_close"])
        result["cross_source_checks"].append({
            "pair": ["move_google.quote", "move_google.previous_close"],
            "displayed_change": displayed,
            "calculated_change": round(calculated, 2),
            "change_matches_within_0_02": abs(displayed - calculated) < 0.02,
            "result": "arithmetic_consistent" if abs(displayed - calculated) < 0.02 else "change_arithmetic_mismatch",
            "note": "Same-page arithmetic is not an independent source validation."
        })
result["interpretation_policy"] = {
    "capture_timestamp_is_not_quote_timestamp": True,
    "previous_close_must_not_be_confused_with_current_quote": True,
    "a_previous_close_mismatch_does_not_prove_which_source_is_stale": True,
    "dated_historical_close_validation_required": True,
    "production_approval": False,
    "reason": "Probe captures live fields plus date-matched historical reference rows; historical parsing and cross-source agreement remain candidates and production approval stays false."
}
result["finished_at"] = stamp()
result["status"] = "capture_passed_needs_numeric_validation" if not result["validation_errors"] else "failed"
(OUT / "market-indicators-source-probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
# Capture-only run succeeds if all source pages load; numeric values are explicitly not validated.
if result["status"] != "capture_passed_needs_numeric_validation":
    raise SystemExit(1)
