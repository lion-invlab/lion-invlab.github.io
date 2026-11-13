#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys, threading
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

def validate_chart(page, label):
    page.wait_for_function("document.querySelector('#combined-stress-card') && !document.querySelector('#combined-stress-card').hidden", timeout=60000)
    check(label + "_one_combined_svg", page.locator("#combined-chart svg").count() == 1)
    check(label + "_five_series_default", page.locator("#combined-chart svg path[data-series]").count() == 5)
    check(label + "_five_filters", page.locator("#series-filters input[data-series-toggle]").count() == 5)
    check(label + "_seventeen_event_bands", page.locator("#combined-chart svg rect[data-event]").count() == 17)
    check(label + "_seventeen_event_legend_items", page.locator("#major-event-key .event-item").count() == 17)
    check(label + "_eighteen_drawdown_bands", page.locator("#combined-chart svg rect[data-drawdown]").count() == 18)
    check(label + "_eighteen_drawdown_percentage_labels", page.locator("#combined-chart svg text[data-drawdown-label]").count() == 18)
    check(label + "_eighteen_drawdown_ledger_items", page.locator("#drawdown-key .event-item").count() == 18)
    check(label + "_drawdown_labels_include_2011_and_2022", page.locator("#drawdown-key").inner_text().includes("-19.4%") and page.locator("#drawdown-key").inner_text().includes("-25.4%") and page.locator("#drawdown-key").inner_text().includes("-16.0%") and page.locator("#drawdown-key").inner_text().includes("-12.4%") and page.locator("#drawdown-key").inner_text().includes("-14.7%"))
    check(label + "_event_dates_and_sources", "1990-07-16 → 1990-10-11" in page.locator("#major-event-key").inner_text() and "1997-07-02 → 1998-12-31" in page.locator("#major-event-key").inner_text() and "2002-11-27 → 2003-03-11" in page.locator("#major-event-key").inner_text() and "2011-04-29 → 2011-10-03" in page.locator("#major-event-key").inner_text() and "2025-02-19 → 2025-04-08" in page.locator("#major-event-key").inner_text() and page.locator("#major-event-key a").count() == 17)
    check(label + "_event_bands_inside_plot", page.locator("#combined-chart svg rect[data-event]").evaluate_all("(els)=>els.every(e=>{const b=e.getBBox();return b.y===34 && b.height===352 && b.y+b.height<=386 && b.width>=2})"))
    check(label + "_event_bands_behind_series", page.locator("#combined-chart svg").evaluate("(svg)=>{const a=[...svg.children].findIndex(e=>e.matches('rect[data-event]'));const b=[...svg.children].findIndex(e=>e.matches('path[data-series]'));return a>=0&&b>a}"))
    check(label + "_drawdown_bands_inside_plot", page.locator("#combined-chart svg rect[data-drawdown]").evaluate_all("(els)=>els.length===18&&els.every(e=>{const b=e.getBBox();return b.y===34&&b.height===352&&b.width>=2})"))
    check(label + "_drawdown_labels_inside_plot", page.locator("#combined-chart svg text[data-drawdown-label]").evaluate_all("(els)=>els.length===18&&els.every(e=>{const b=e.getBBox();return b.x>=78&&b.x+b.width<=1018&&b.y>=34&&b.y+b.height<=386})"))
    check(label + "_all_selected_by_default", page.locator("#series-filters input[data-series-toggle]:checked").count() == 5)
    check(label + "_right_price_axis", page.locator("#combined-chart svg text[data-axis='right']").count() == 5)
    check(label + "_left_percentile_axis", "金融壓力指標" in page.locator("#combined-chart svg").evaluate("(e)=>e.textContent"))
    check(label + "_legend_five_series", page.locator("#combined-legend .swatch").count() == 5)
    check(label + "_guide_visible", page.locator(".guide").is_visible())
    # Verify an individual series can be hidden and restored.
    vix = page.locator('#series-filters input[data-series-toggle="VIXCLS"]')
    vix.uncheck()
    check(label + "_single_series_hide", page.locator("#combined-chart svg path[data-series]").count() == 4)
    vix.check()
    check(label + "_single_series_restore", page.locator("#combined-chart svg path[data-series]").count() == 5)
    page.locator("#clear-all-series").click()
    check(label + "_clear_all", page.locator("#combined-chart svg path[data-series]").count() == 0)
    check(label + "_clear_all_controls", page.locator("#series-filters input:checked").count() == 0)
    page.locator("#select-all-series").click()
    check(label + "_select_all_restore", page.locator("#combined-chart svg path[data-series]").count() == 5)
    check(label + "_select_all_controls", page.locator("#series-filters input:checked").count() == 5)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, viewport in [("desktop", {"width": 1440, "height": 1000}), ("mobile", {"width": 390, "height": 844}), ("mobile320", {"width": 320, "height": 740})]:
            page = browser.new_page(viewport=viewport, device_scale_factor=1)
            page.on("console", lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: report["page_errors"].append(str(err)))
            page.on("requestfailed", lambda req: report["failed_requests"].append({"url": req.url, "failure": req.failure}))
            response = page.goto("http://127.0.0.1:8765/research/tac-chart3/chart3-preview.html", wait_until="networkidle", timeout=60000)
            check(label + "_http_200", response is not None and response.status == 200, response.status if response else None)
            validate_chart(page, label)
            chart_box = page.locator("#combined-chart").evaluate("(e)=>({client:e.clientWidth,scroll:e.scrollWidth})")
            if label == "desktop":
                check(label + "_no_chart_overflow", chart_box["scroll"] <= chart_box["client"] + 2, chart_box)
            else:
                check(label + "_chart_horizontal_scroll", chart_box["scroll"] > chart_box["client"], chart_box)
                check(label + "_svg_min_width", page.locator("#combined-chart svg").evaluate("(e)=>e.getBoundingClientRect().width >= 760"))
                page_widths = page.evaluate("({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})")
                check(label + "_no_page_level_horizontal_overflow", page_widths["scroll"] <= page_widths["client"] + 2, page_widths)
            page.screenshot(path=str(OUT / f"chart3-{label}.png"), full_page=True)
            page.close()
        for label, viewport in [("standalone_desktop", {"width": 1440, "height": 1000}), ("standalone_mobile320", {"width": 320, "height": 740})]:
            page = browser.new_page(viewport=viewport, device_scale_factor=1)
            standalone_data_requests = []
            page.on("console", lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: report["page_errors"].append(str(err)))
            page.on("requestfailed", lambda req: report["failed_requests"].append({"url": req.url, "failure": req.failure}))
            page.on("request", lambda req: standalone_data_requests.append(req.url) if "chart3_market_stress.json" in req.url else None)
            response = page.goto("http://127.0.0.1:8765/artifacts/chart3-preview-visual-qa/chart3-preview-standalone.html", wait_until="networkidle", timeout=60000)
            check(label + "_http_200", response is not None and response.status == 200, response.status if response else None)
            validate_chart(page, label)
            check(label + "_no_external_json_fetch", not standalone_data_requests, standalone_data_requests)
            if label == "standalone_mobile320":
                page_widths = page.evaluate("({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})")
                check(label + "_no_page_level_horizontal_overflow", page_widths["scroll"] <= page_widths["client"] + 2, page_widths)
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
