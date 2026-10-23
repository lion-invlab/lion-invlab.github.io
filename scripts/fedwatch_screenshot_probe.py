#!/usr/bin/env python3
"""Capture CME FedWatch official page and embedded tool in isolated GitHub Actions test."""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

OUT = Path("fedwatch-evidence")
OUT.mkdir(exist_ok=True)
URLS = [
    "https://www.cmegroup.cn/fed-watch/",
    "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
]
def stamp():
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "taipei": datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Taipei")).isoformat(),
    }

result = {
    "source": "CME Group FedWatch official page",
    "candidate_urls": URLS,
    "started_at": stamp(),
    "status": "starting",
    "screenshots": [],
    "frames": [],
    "navigation_attempts": [],
    "validated_probabilities": False,
}
with sync_playwright() as p:
    # Headed mode under Xvfb is used because the embedded QuikStrike tool may not render headlessly.
    browser = p.chromium.launch(headless=False, args=["--disable-http2", "--disable-dev-shm-usage"])
    context = browser.new_context(
        viewport={"width": 1920, "height": 1400},
        device_scale_factor=1,
        locale="en-US",
        timezone_id="Asia/Taipei",
        ignore_https_errors=False,
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8"},
    )
    page = context.new_page()
    page.set_default_timeout(12000)
    page.on("requestfailed", lambda req: result.setdefault("request_failures", []).append({
        "url": req.url, "failure": req.failure
    }) if len(result.get("request_failures", [])) < 40 else None)
    try:
        response = None
        for candidate in URLS:
            try:
                # Wait only for the response commit, not all third-party page assets.
                response = page.goto(candidate, wait_until="commit", timeout=60000)
                result["navigation_attempts"].append({
                    "url": candidate, "http_status": response.status if response else None,
                    "title": page.title(), "landed_url": page.url
                })
                result["active_url"] = page.url
                break
            except Exception as exc:
                result["navigation_attempts"].append({"url": candidate, "error": f"{type(exc).__name__}: {exc}"})
        if not result.get("active_url"):
            raise RuntimeError("All CME page navigation attempts failed")
        result["http_status"] = response.status if response else None
        page.wait_for_timeout(25000)
        result["title"] = page.title()
        result["final_url"] = page.url
        try:
            result["page_text_excerpt"] = page.locator("body").inner_text(timeout=12000)[:14000]
        except Exception as exc:
            result["page_text_excerpt"] = f"[body text unavailable: {type(exc).__name__}: {exc}]"

        # Capture the full parent page and each embedded frame separately.
        try:
            page.screenshot(path=str(OUT / "fedwatch-parent.png"), full_page=True, timeout=25000)
            result["screenshots"].append("fedwatch-evidence/fedwatch-parent.png")
        except Exception as exc:
            result["parent_screenshot_error"] = f"{type(exc).__name__}: {exc}"
            try:
                page.screenshot(path=str(OUT / "fedwatch-viewport.png"), timeout=15000)
                result["screenshots"].append("fedwatch-evidence/fedwatch-viewport.png")
            except Exception as exc2:
                result["viewport_screenshot_error"] = f"{type(exc2).__name__}: {exc2}"

        for i, frame in enumerate(page.frames):
            try:
                body_text = frame.locator("body").inner_text(timeout=5000)[:8000]
            except Exception as exc:
                body_text = f"[frame body unavailable: {type(exc).__name__}: {exc}]"
            item = {"index": i, "url": frame.url, "name": frame.name, "text_excerpt": body_text}
            result["frames"].append(item)
            if i > 0:
                try:
                    frame.locator("body").screenshot(path=str(OUT / f"fedwatch-frame-{i}.png"), timeout=15000)
                    result["screenshots"].append(f"fedwatch-evidence/fedwatch-frame-{i}.png")
                except Exception as exc:
                    item["screenshot_error"] = f"{type(exc).__name__}: {exc}"

        all_text = " ".join([result.get("page_text_excerpt", "")] + [f.get("text_excerpt", "") for f in result["frames"]])
        hints = ["probability", "target rate", "no change", "meeting", "target rate probabilities", "加息", "降息"]
        result["has_probability_or_rate_table_hints"] = any(h in all_text.lower() for h in hints)
        result["has_quikstrike_frame"] = any("quikstrike" in f.get("url", "").lower() for f in result["frames"])
        result["validated_probabilities"] = False
        result["interpretation"] = "Capture only. Human verification of meeting date, rate bands and probabilities is still required."
        result["status"] = "captured" if result["screenshots"] else "capture_failed"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        browser.close()

result["completed_at"] = stamp()
(OUT / "fedwatch-diagnostic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "captured":
    raise SystemExit(1)
