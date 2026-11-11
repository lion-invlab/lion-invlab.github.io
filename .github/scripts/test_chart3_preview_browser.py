#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "chart3-preview-visual-qa"
OUT.mkdir(parents=True, exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

os.chdir(ROOT)
server = ThreadingHTTPServer(("127.0.0.1", 8765), QuietHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
report = {"status": "FAIL", "checks": [], "console_errors": [], "page_errors": [], "failed_requests": []}

def check(name, ok, detail=None):
    report["checks"].append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, viewport in [("desktop", {"width": 1440, "height": 1000}), ("mobile", {"width": 390, "height": 844})]:
            page = browser.new_page(viewport=viewport, device_scale_factor=1)
            page.on("console", lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: report["page_errors"].append(str(err)))
            page.on("requestfailed", lambda req: report["failed_requests"].append({"url": req.url, "failure": req.failure}))
            response = page.goto("http://127.0.0.1:8765/research/tac-chart3/chart3-preview.html", wait_until="networkidle", timeout=60000)
            check(label + "_http_200", response is not None and response.status == 200, response.status if response else None)
            page.wait_for_function("document.querySelector('#charts') && !document.querySelector('#charts').hidden", timeout=60000)
            check(label + "_four_series_svg", page.locator("#vix-chart svg").count() == 1 and page.locator("#stress-chart svg").count() == 3)
            check(label + "_guide_visible", page.locator(".guide").is_visible())
            check(label + "_latest_values_visible", bool(page.locator("#vix-latest").inner_text().strip()) and bool(page.locator("#stress-latest").inner_text().strip()))
            check(label + "_no_empty_paths", page.locator(".chart svg path[d]").count() == 4)
            if label == "mobile":
                overflow = page.locator(".chart").evaluate_all("(els) => els.map(e => ({client:e.clientWidth,scroll:e.scrollWidth}))")
                check("mobile_chart_horizontal_scroll", all(x["scroll"] > x["client"] for x in overflow), overflow)
                check("mobile_svg_min_width", page.locator(".chart svg").evaluate_all("(els) => els.every(e => e.getBoundingClientRect().width >= 760)"))
            else:
                widths = page.locator(".chart").evaluate_all("(els) => els.map(e => ({client:e.clientWidth,scroll:e.scrollWidth}))")
                check("desktop_no_chart_overflow", all(x["scroll"] <= x["client"] + 2 for x in widths), widths)
            page.screenshot(path=str(OUT / f"chart3-{label}.png"), full_page=True)
            page.close()
        browser.close()
    check("no_console_errors", not report["console_errors"], report["console_errors"])
    check("no_page_errors", not report["page_errors"], report["page_errors"])
    check("no_failed_requests", not report["failed_requests"], report["failed_requests"])
    report["status"] = "PASS"
except Exception as exc:
    report["error"] = repr(exc)
finally:
    server.shutdown()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
if report["status"] != "PASS":
    sys.exit(1)
