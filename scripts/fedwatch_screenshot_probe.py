#!/usr/bin/env python3
"""Bounded-time CME FedWatch screenshot probe; test branch only."""
import json
import re
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
    "validation_errors": [],
}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-http2", "--disable-dev-shm-usage"])
    context = browser.new_context(
        viewport={"width": 1920, "height": 1400},
        device_scale_factor=1,
        locale="en-US",
        timezone_id="Asia/Taipei",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8"},
    )
    page = context.new_page()
    page.set_default_timeout(6000)
    page.on("requestfailed", lambda req: result.setdefault("request_failures", []).append({
        "url": req.url, "failure": req.failure
    }) if len(result.get("request_failures", [])) < 25 else None)
    try:
        response = None
        for candidate in URLS:
            try:
                response = page.goto(candidate, wait_until="commit", timeout=20000)
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
        page.wait_for_timeout(12000)
        result["title"] = page.title()
        result["final_url"] = page.url
        try:
            result["page_text_excerpt"] = page.locator("body").inner_text(timeout=6000)[:10000]
        except Exception as exc:
            result["page_text_excerpt"] = f"[body text unavailable: {type(exc).__name__}: {exc}]"
        try:
            page.screenshot(path=str(OUT / "fedwatch-parent.png"), full_page=False, timeout=8000)
            result["screenshots"].append("fedwatch-evidence/fedwatch-parent.png")
        except Exception as exc:
            result["parent_screenshot_error"] = f"{type(exc).__name__}: {exc}"
        for i, frame in enumerate(page.frames):
            # Only capture the embedded QuikStrike frame, not every third-party frame.
            if i == 0 or "quikstrike" not in frame.url.lower():
                continue
            try:
                body_text = frame.locator("body").inner_text(timeout=4000)
            except Exception as exc:
                body_text = f"[frame body unavailable: {type(exc).__name__}: {exc}]"
            item = {"index": i, "url": frame.url, "name": frame.name, "text_excerpt": body_text[:6000], "text_full": body_text}
            result["frames"].append(item)
            try:
                frame.locator("body").screenshot(path=str(OUT / f"fedwatch-frame-{i}.png"), timeout=8000)
                result["screenshots"].append(f"fedwatch-evidence/fedwatch-frame-{i}.png")
            except Exception as exc:
                item["screenshot_error"] = f"{type(exc).__name__}: {exc}"
        frame_texts = [f.get("text_excerpt", "") for f in result["frames"]]
        all_text = "\n".join([result.get("page_text_excerpt", "")] + frame_texts)
        result["has_quikstrike_frame"] = any("quikstrike" in f.get("url", "").lower() for f in result["frames"])
        result["has_probability_or_rate_table_hints"] = any(
            h in all_text.lower() for h in ["probability", "target rate", "no change", "meeting", "加息", "降息"]
        )

        # Parse only the embedded QuikStrike frame text; normalize invisible Unicode separators first.
        qtext_raw = "\n".join(
            f.get("text_full", f.get("text_excerpt", ""))
            for f in result["frames"]
            if "quikstrike" in f.get("url", "").lower()
        )
        qtext = re.sub(r"[\u200b\u200c\u200d\ufeff\u00a0]+", " ", qtext_raw)
        qtext = re.sub(r"[ \t]+", " ", qtext)
        qtext = re.sub(r"\n{2,}", "\n", qtext)

        meeting = (
            re.search(r"Target Rate Probabilities for\s+([0-9]{1,2}\s+[A-Z][a-z]{2}\s+[0-9]{1,4})\s+Fed Meeting", qtext, re.I)
            or re.search(r"MEETING INFORMATION.*?MEETING DATE.*?\n(.*?)(?:\t|\s{2,})[A-Z0-9]{3,}.*?\n", qtext, re.S | re.I)
        )
        prob_section = re.search(
            r"PROBABILITIES\s+EASE\s+NO CHANGE\s+HIKE\s+([0-9.]+)\s*%\s+([0-9.]+)\s*%\s+([0-9.]+)\s*%",
            qtext, re.I | re.S
        )
        current_rate = (
            re.search(r"(\d{3}-\d{1,3})\s*\(Current\)", qtext, re.I)
            or re.search(r"Current target rate is\s+(\d{3}-\d{1,3})", qtext, re.I)
        )
        data_stamp = re.search(r"Data as of\s+([^\n]+)", qtext, re.I)
        # Cross-check the summary probabilities against the detailed NOW target-rate table.
        now_row = re.search(
            r"(?m)^\s*(\d{3}-\d{3})\s*\(Current\)\s+([0-9]+(?:\.[0-9]+)?)%\s+([0-9]+(?:\.[0-9]+)?)%",
            qtext, re.I
        )
        table_start = qtext.find("TARGET RATE (BPS)")
        detailed_table_text = qtext[table_start:] if table_start >= 0 else ""
        next_row = re.search(
            r"(?m)^\\s*(\\d{3}-\\d{3})\\s+([0-9]+(?:\\.[0-9]+)?)%\\s+([0-9]+(?:\\.[0-9]+)?)%\\s+([0-9]+(?:\\.[0-9]+)?)%\\s+([0-9]+(?:\\.[0-9]+)?)%\\s*$",
            detailed_table_text, re.I
        )
        errors = result["validation_errors"]
        if not result["has_quikstrike_frame"]:
            errors.append("Missing embedded QuikStrike frame.")
        if not meeting:
            errors.append("Could not parse Fed meeting date from embedded QuikStrike text.")
        if not prob_section:
            errors.append("Could not parse EASE / NO CHANGE / HIKE probabilities from embedded QuikStrike text.")
        if not current_rate:
            errors.append("Could not parse current target rate range from embedded QuikStrike text.")
        if not data_stamp:
            errors.append("Could not parse source data timestamp from embedded QuikStrike text.")
        if not now_row:
            errors.append("Could not parse the detailed NOW/current target-rate table row.")
        if not next_row:
            errors.append("Could not parse the next target-rate probability table row.")
        if prob_section and now_row and next_row:
            try:
                summary_no_change = float(prob_section.group(2))
                summary_hike = float(prob_section.group(3))
                table_no_change = float(now_row.group(2))
                # The next rate row's first probability is the NOW probability of a hike.
                table_hike = float(next_row.group(2))
                if abs(summary_no_change - table_no_change) > 0.01:
                    errors.append("Summary no-change probability does not match the current-rate NOW table value.")
                if abs(summary_hike - table_hike) > 0.01:
                    errors.append("Summary hike probability does not match the next-rate NOW table value.")
                result["table_crosscheck"] = {
                    "current_rate": now_row.group(1),
                    "no_change_pct": table_no_change,
                    "next_rate": next_row.group(1),
                    "hike_pct": table_hike,
                    "passed": abs(summary_no_change - table_no_change) <= 0.01 and abs(summary_hike - table_hike) <= 0.01
                }
            except (ValueError, IndexError) as exc:
                errors.append(f"Could not validate summary against detailed target-rate table: {exc}")
        if prob_section:
            ease, unchanged, hike = [float(x) for x in prob_section.groups()]
            total = ease + unchanged + hike
            result["probabilities_pct"] = {"ease": ease, "no_change": unchanged, "hike": hike, "sum": round(total, 4)}
            if abs(total - 100.0) > 0.2:
                errors.append(f"Probability total is {total:.2f}%, outside 100% ± 0.2%.")
        if meeting:
            result["meeting_date"] = meeting.group(1)
        if current_rate:
            result["current_target_rate_bps"] = current_rate.group(1)
        if data_stamp:
            result["source_data_timestamp"] = data_stamp.group(1).strip()
        result["parser_text_length"] = len(qtext)
        result["parser_text_excerpt"] = qtext[:10000]
        result["validated_probabilities"] = not errors and bool(result.get("probabilities_pct"))
        result["interpretation"] = (
            "Machine checks passed; human review is still required before publishing."
            if result["validated_probabilities"]
            else "Do not publish values: screenshot/text validation failed; inspect evidence and logs."
        )
        result["status"] = "validated" if result["validated_probabilities"] and result["screenshots"] else "validation_failed"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        browser.close()
result["completed_at"] = stamp()
(OUT / "fedwatch-diagnostic.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "validated":
    raise SystemExit(1)
