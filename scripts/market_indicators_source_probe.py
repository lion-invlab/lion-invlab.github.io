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
                page.screenshot(path=str(screenshot_path), full_page=False, timeout=12000)
                item["screenshot"] = str(screenshot_path)
            except Exception as exc:
                item["screenshot_error"] = f"{type(exc).__name__}: {exc}"
            item["keyword_checks"] = {word: bool(re.search(re.escape(word), body, re.I)) for word in source["needles"]}
            item["ok"] = bool(response and response.status == 200 and len(body) > 100 and all(item["keyword_checks"].values()) and screenshot_path.exists())
            if not item["ok"]:
                result["validation_errors"].append(f"{source['label']}: page/keyword/screenshot validation failed")
            # Do not treat a displayed quote as validated until extraction and independent numeric cross-check exist.
            item["quote_extraction_status"] = item.get("candidate_quote_status", "not_applicable_official_page_capture_only")
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
            result["validation_errors"].append(f"{source['label']}: {item['error']}")
        result["sources"].append(item)
        page.close()
    browser.close()

result["finished_at"] = stamp()
result["status"] = "capture_passed_needs_numeric_validation" if not result["validation_errors"] else "failed"
(OUT / "market-indicators-source-probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
# Capture-only run succeeds if all source pages load; numeric values are explicitly not validated.
if result["status"] != "capture_passed_needs_numeric_validation":
    raise SystemExit(1)
