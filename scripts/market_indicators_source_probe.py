#!/usr/bin/env python3
"""Isolated source-access probe for VIX, MOVE and SOX. Capture-only; not production data."""
import json
import re
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
                result["validation_errors"].append(f"{source['label']}: page/keyword/screenshot validation failed")
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
                    item["change_arithmetic_check"] = {
                        "displayed_change": displayed_change,
                        "calculated_change": round(calculated_change, 2),
                        "matches_within_0_02": abs(displayed_change - calculated_change) < 0.02
                    }
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
    {"key": "vix_yahoo_history", "label": "VIX Yahoo Finance historical closes", "url": "https://hk.finance.yahoo.com/quote/%5EVIX/history/", "date_patterns": [r"22 Oct 2026|Oct 22, 2026|2026年10月22日", r"21 Oct 2026|Oct 21, 2026|2026年10月21日"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 3},
    {"key": "move_investing_history", "label": "MOVE Investing.com historical prices", "url": "https://www.investing.com/indices/ice-bofaml-move-historical-data", "date_patterns": [r"22/10/2026|Oct 22, 2026", r"21/10/2026|Oct 21, 2026"], "target_dates": ["2026-10-22", "2026-10-21"], "value_index": 0},
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
            response = page.goto(source["url"], wait_until="domcontentloaded", timeout=30000)
            item["http_status"] = response.status if response else None
            page.wait_for_timeout(4500)
            item["title"] = page.title()
            item["final_url"] = page.url
            body = page.locator("body").inner_text(timeout=10000)
            item["body_text"] = body[:16000]
            item["body_text_length"] = len(body)
            lines = [line.strip() for line in body.splitlines() if line.strip()]
            for target_date, date_pattern in zip(source["target_dates"], source["date_patterns"]):
                matching = next((line for line in lines if re.search(date_pattern, line, re.I)), None)
                row = {"date": target_date, "row_text": matching, "close_candidate": None, "status": "row_not_found"}
                if matching:
                    row_payload = re.sub(date_pattern, "", matching, count=1, flags=re.I)
                    nums = re.findall(r"(?<![A-Za-z])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", row_payload)
                    # Yahoo rows start with the date followed by Open/High/Low/Close;
                    # Investing.com rows start with date then Price (close candidate).
                    if len(nums) > source["value_index"]:
                        try:
                            row["close_candidate"] = float(nums[source["value_index"]].replace(",", ""))
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
            item["ok"] = bool(response and response.status == 200 and len(body) > 100 and all(x["close_candidate"] is not None for x in item["rows"]))
            item["note"] = "Historical row values are candidates; verify column semantics and source publication date before production use."
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        result["historical_references"].append(item)
        page.close()
    browser.close()

# Compare historical close candidates to live-page previous-close fields only when the
# historical row for the immediately preceding session was successfully extracted.
history_by_key = {x.get("key"): x for x in result["historical_references"]}
for live_key, hist_key in [("vix_google", "vix_yahoo_history"), ("move_google", "move_investing_history"), ("sox_google", "sox_yahoo_history")]:
    live = by_key.get(live_key, {}) if "by_key" in globals() else {}
    hist = history_by_key.get(hist_key, {})
    prior = next((row for row in hist.get("rows", []) if row.get("date") == "2026-10-22"), None)
    result.setdefault("dated_history_checks", []).append({
        "live_source": live_key,
        "historical_source": hist_key,
        "target_session_date": "2026-10-22",
        "historical_close_candidate": prior.get("close_candidate") if prior else None,
        "live_previous_close_candidate": live.get("previous_close"),
        "matches_within_0_02": (prior is not None and prior.get("close_candidate") is not None and live.get("previous_close") is not None and abs(float(prior["close_candidate"]) - float(live["previous_close"])) < 0.02),
        "result": "comparable_candidates_match" if (prior is not None and prior.get("close_candidate") is not None and live.get("previous_close") is not None and abs(float(prior["close_candidate"]) - float(live["previous_close"])) < 0.02) else "not_verified_or_mismatch",
        "note": "Date-matched historical row is captured for audit; a mismatch remains blocking and does not automatically establish which provider is stale."
    })

g = by_key.get("sox_google", {})
n = by_key.get("sox_nasdaq", {})
result["cross_source_checks"] = []
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
    # Both fields are explicitly labelled previous close, but only Cboe's
    # capture also carries an as-of date. A mismatch is a blocking alert;
    # it cannot by itself prove Google is stale because snapshot/session
    # semantics and market holidays must be checked against historical data.
    google_date = vg.get("candidate_quote_date")
    cboe_date = vc.get("candidate_quote_date")
    result["cross_source_checks"].append({
        "pair": ["vix_google.previous_close", "vix_cboe.previous_close"],
        "google_quote_date": google_date,
        "cboe_quote_date": cboe_date,
        "google_previous_close": float(vg["previous_close"]),
        "cboe_previous_close": float(vc["previous_close"]),
        "values_match_within_0_02": delta < 0.02,
        "absolute_difference": round(delta, 4),
        "result": "candidate_sources_agree" if delta < 0.02 else "previous_close_mismatch",
        "root_cause_status": "not_proven",
        "next_validation": "Check each value against dated official historical closes for the immediately preceding trading session; do not infer staleness from mismatch alone.",
        "note": "Mismatch blocks automatic close approval. The probe does not fetch historical close series and must not label a source stale without date-matched evidence."
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
