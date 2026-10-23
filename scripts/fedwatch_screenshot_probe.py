#!/usr/bin/env python3
"""Capture CME FedWatch public page in an isolated GitHub Actions test."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

OUT = Path("fedwatch-evidence")
OUT.mkdir(exist_ok=True)
URL = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"
result = {
    "source": "CME FedWatch official public page",
    "url": URL,
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "captured_at_taipei": datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Taipei")).isoformat(),
    "status": "starting",
    "screenshots": [],
    "frames": [],
    "validated_probabilities": False,
}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
    try:
        response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        result["http_status"] = response.status if response else None
        result["initial_title"] = page.title()
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(12000)
        # Dismiss common consent overlays only when an obvious button is present.
        for pattern in ["Accept All", "Accept all", "I Agree", "Agree", "Accept"]:
            try:
                button = page.get_by_role("button", name=pattern, exact=True).first
                if button.is_visible(timeout=500):
                    button.click(timeout=1000)
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                pass
        result["title"] = page.title()
        result["final_url"] = page.url
        result["page_text_excerpt"] = page.locator("body").inner_text(timeout=10000)[:12000]
        result["frames"] = []
        for i, frame in enumerate(page.frames):
            try:
                body_text = frame.locator("body").inner_text(timeout=3000)[:5000]
            except Exception as exc:
                body_text = f"[frame body unavailable: {type(exc).__name__}]"
            frame_info = {"index": i, "url": frame.url, "name": frame.name, "text_excerpt": body_text}
            result["frames"].append(frame_info)
            if i > 0:
                try:
                    frame.locator("body").screenshot(path=str(OUT / f"fedwatch-frame-{i}.png"), timeout=10000)
                    result["screenshots"].append(f"fedwatch-evidence/fedwatch-frame-{i}.png")
                except Exception as exc:
                    frame_info["screenshot_error"] = f"{type(exc).__name__}: {exc}"
        page.screenshot(path=str(OUT / "fedwatch-viewport.png"), full_page=False)
        result["screenshots"].append("fedwatch-evidence/fedwatch-viewport.png")
        try:
            page.screenshot(path=str(OUT / "fedwatch-full-page.png"), full_page=True, timeout=20000)
            result["screenshots"].append("fedwatch-evidence/fedwatch-full-page.png")
        except Exception as exc:
            result["full_page_screenshot_error"] = f"{type(exc).__name__}: {exc}"
        visible_text = " ".join([result.get("page_text_excerpt", "")] + [f.get("text_excerpt", "") for f in result["frames"]])
        result["has_probability_or_rate_table_hints"] = any(x in visible_text.lower() for x in ["probability", "target rate", "no change", "meeting"])
        result["validated_probabilities"] = False
        result["interpretation"] = "Screenshots and diagnostic text only. Human review is required; this test does not certify any probability values."
        result["status"] = "captured" if result["screenshots"] else "capture_failed"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        browser.close()

result["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
result["completed_at_taipei"] = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Taipei")).isoformat()
(OUT / "fedwatch-diagnostic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "captured":
    raise SystemExit(1)
