#!/usr/bin/env python3
"""Chromium visual smoke test for TAC rendered mother-template fixtures."""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "artifacts/tac-visual-regression"
SCREENSHOTS = FIXTURES / "screenshots"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "tablet": {"width": 768, "height": 1024},
    "mobile-320": {"width": 320, "height": 900},
}
REPORT = FIXTURES / "browser-visual-report.json"

def main():
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for template in ("monday", "weekday"):
            path = FIXTURES / f"{template}.html"
            if not path.exists():
                raise SystemExit(f"missing rendered fixture: {path}")
            for label, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport, device_scale_factor=1)
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(path.as_uri(), wait_until="load")
                page.wait_for_timeout(150)
                metrics = page.evaluate("""() => ({
                    viewportWidth: window.innerWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    bodyWidth: document.body.scrollWidth,
                    documentHeight: document.documentElement.scrollHeight,
                    bodyHeight: document.body.scrollHeight,
                    title: document.title,
                    visibleMain: !!document.querySelector('main, #app, body > header'),
                    calendarGroups: document.querySelectorAll('.calendar-status-group').length,
                    indexRows: document.querySelectorAll('#global-markets .row').length
                })""")
                shot = SCREENSHOTS / f"{template}-{label}.png"
                page.screenshot(path=str(shot), full_page=True, animations="disabled")
                problems = []
                if metrics["documentWidth"] > viewport["width"] + 1:
                    problems.append(f"horizontal overflow: document={metrics['documentWidth']} viewport={viewport['width']}")
                if metrics["documentHeight"] < 400:
                    problems.append(f"unexpectedly short page: {metrics['documentHeight']}px")
                if metrics["indexRows"] < 10:
                    problems.append(f"global market rows missing: {metrics['indexRows']}")
                if page_errors:
                    problems.append("page errors: " + " | ".join(page_errors))
                result = {
                    "template": template, "viewport": label,
                    "viewport_size": viewport, "metrics": metrics,
                    "screenshot": str(shot.relative_to(ROOT)),
                    "status": "FAIL" if problems else "PASS",
                    "problems": problems,
                }
                results.append(result)
                if problems:
                    failures.append(result)
                print(f"{result['status']}: {template} / {label}: {metrics['documentWidth']}px wide x {metrics['documentHeight']}px high")
                for problem in problems:
                    print("  - " + problem)
                page.close()
        browser.close()
    REPORT.write_text(json.dumps({"results": results, "failure_count": len(failures)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved browser report: {REPORT.relative_to(ROOT)}")
    print(f"Saved {len(results)} screenshots under {SCREENSHOTS.relative_to(ROOT)}")
    if failures:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
