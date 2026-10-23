#!/usr/bin/env python3
"""CNN Fear & Greed official-page screenshot and data probe; isolated test branch only."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

OUT = Path("cnn-fg-evidence")
OUT.mkdir(exist_ok=True)
URL = "https://www.cnn.com/markets/fear-and-greed"
DATA_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

def stamp():
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "taipei": datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Taipei")).isoformat(),
    }

result = {
    "source": "CNN Business Fear & Greed official page",
    "page_url": URL,
    "data_endpoint": DATA_URL,
    "started_at": stamp(),
    "status": "starting",
    "validated": False,
    "validation_errors": [],
    "screenshots": [],
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
    page = context.new_page()
    page.set_default_timeout(10000)
    page.on("requestfailed", lambda req: result.setdefault("request_failures", []).append(
        {"url": req.url, "failure": req.failure}
    ) if len(result.get("request_failures", [])) < 20 else None)
    try:
        response = page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        result["http_status"] = response.status if response else None
        page.wait_for_timeout(7000)
        result["title"] = page.title()
        result["final_url"] = page.url
        try:
            result["page_text_excerpt"] = page.locator("body").inner_text(timeout=8000)[:9000]
        except Exception as exc:
            result["page_text_excerpt_error"] = f"{type(exc).__name__}: {exc}"
        try:
            page.screenshot(path=str(OUT / "cnn-fear-greed-official-page.png"), full_page=False, timeout=15000)
            result["screenshots"].append("cnn-fg-evidence/cnn-fear-greed-official-page.png")
        except Exception as exc:
            result["validation_errors"].append(f"Official CNN page screenshot failed: {type(exc).__name__}: {exc}")

        # CNN's page renders this JSON endpoint. Request it with browser-like headers and retain raw evidence.
        api = context.request.get(DATA_URL, headers={
            "Referer": URL,
            "Origin": "https://www.cnn.com",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }, timeout=20000)
        result["data_http_status"] = api.status
        if api.status != 200:
            result["validation_errors"].append(f"CNN data endpoint returned HTTP {api.status}.")
        else:
            payload = api.json()
            (OUT / "cnn-fear-greed-raw.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result["raw_json_saved"] = "cnn-fg-evidence/cnn-fear-greed-raw.json"

            fg = payload.get("fear_and_greed") if isinstance(payload, dict) else None
            if not isinstance(fg, dict):
                result["validation_errors"].append("Expected fear_and_greed object is missing from CNN JSON response.")
            else:
                # CNN schema has changed over time; only accept explicit score and rating fields.
                score = fg.get("score", fg.get("value"))
                rating = fg.get("rating", fg.get("rating_class"))
                timestamp = fg.get("timestamp", fg.get("date", fg.get("updated_at")))
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = None
                if score is None or not (0 <= score <= 100):
                    result["validation_errors"].append("CNN Fear & Greed score missing or outside 0–100.")
                if not isinstance(rating, str) or not rating.strip():
                    result["validation_errors"].append("CNN Fear & Greed rating label missing.")
                if timestamp is None or str(timestamp).strip() == "":
                    result["validation_errors"].append("CNN source timestamp/date missing.")
                result["score"] = score
                result["rating"] = rating.strip() if isinstance(rating, str) else None
                result["source_timestamp_raw"] = timestamp
                result["score_source_key"] = "fear_and_greed.score" if "score" in fg else "fear_and_greed.value"
                result["payload_top_level_keys"] = list(payload.keys())[:40] if isinstance(payload, dict) else []
                if score is not None and isinstance(rating, str) and rating.strip() and timestamp is not None:
                    result["validated"] = True

        result["finished_at"] = stamp()
        result["status"] = "validated" if result["validated"] and not result["validation_errors"] else "failed"
    except Exception as exc:
        result["status"] = "failed"
        result["validation_errors"].append(f"{type(exc).__name__}: {exc}")
        result["finished_at"] = stamp()
    finally:
        browser.close()

(OUT / "cnn-fear-greed-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "validated":
    raise SystemExit(1)

# Repeatability note: this isolated probe is intentionally fail-closed on missing fields.
