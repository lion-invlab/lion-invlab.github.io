#!/usr/bin/env python3
from __future__ import annotations
import json, os, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "us-mmf-chart-visual-qa"
OUT.mkdir(parents=True, exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

os.chdir(ROOT)
server = ThreadingHTTPServer(("127.0.0.1", 8766), QuietHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
report = {"status": "FAIL", "checks": [], "console_errors": [], "page_errors": [], "failed_requests": []}

def check(name, ok, detail=None):
    report["checks"].append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")

def validate(page, label):
    # Desktop: wheel/drag; mobile: verify real two-finger pinch via CDP.
    page.goto("http://127.0.0.1:8766/research/us-mmf-chart/chart-preview.html", wait_until="networkidle", timeout=90000)
    page.wait_for_function("document.querySelector('#load-status')?.textContent.includes('資料載入完成')", timeout=90000)
    check(label + "_data_loaded", "資料載入完成" in page.locator("#load-status").inner_text(), page.locator("#load-status").inner_text())
    check(label + "_total_210_quarters", page.locator("#load-status").inner_text().find("總規模 210 季") >= 0)
    check(label + "_category_63_quarters", page.locator("#load-status").inner_text().find("基金類型 63 季") >= 0)
    check(label + "_transaction_304_observations", page.locator("#load-status").inner_text().find("交易資料 304 筆") >= 0)
    check(label + "_efa_188_months", page.locator("#load-status").inner_text().find("EFA 持倉 188 月") >= 0)
    check(label + "_latest_total_kpi", page.locator("#kpi-total").inner_text() == "$8.44T")
    check(label + "_latest_quarter", "2026 Q2" in page.locator("#kpi-quarter").inner_text())
    check(label + "_government_kpi", page.locator("#kpi-gov").inner_text() == "$6.89T")
    check(label + "_prime_kpi", page.locator("#kpi-prime").inner_text() == "$1.39T")
    check(label + "_tax_exempt_kpi", page.locator("#kpi-tax").inner_text() == "$0.15T")
    check(label + "_total_line_rendered", page.locator("#total-chart path.line-total").count() == 1)
    check(label + "_fund_type_areas_rendered", page.locator("#type-chart path.area").count() == 3)
    check(label + "_transaction_line_rendered", page.locator("#flow-chart path.line-flow").count() == 1)
    check(label + "_transaction_zero_baseline", page.locator("#flow-chart line.zero-line").count() == 1)
    check(label + "_transaction_zoom_enabled", page.locator("#flow-chart").evaluate("(e)=>!!e.__zoom && getComputedStyle(e).touchAction===\"none\""))
    check(label + "_holding_stack_rendered", page.locator("#holding-chart path.area-holding").count() == 6)
    check(label + "_holding_zoom_enabled", page.locator("#holding-chart").evaluate("(e)=>!!e.__zoom && getComputedStyle(e).touchAction===\"none\""))
    check(label + "_holding_total_188_months", page.locator("#holding-legend .legend-item").count() == 6)
    page.locator("#holding-type-controls button[data-type=\"Government\"]").click()
    check(label + "_holding_government_switch", page.locator("#holding-chart path.area-holding").count() == 5)
    page.locator("#holding-type-controls button[data-type=\"Prime\"]").click()
    check(label + "_holding_prime_switch", page.locator("#holding-chart path.area-holding").count() == 6)
    page.locator("#holding-type-controls button[data-type=\"Tax-exempt\"]").click()
    check(label + "_holding_tax_exempt_switch", page.locator("#holding-chart path.area-holding").count() == 3)
    page.locator("#holding-type-controls button[data-type=\"Total\"]").click()
    check(label + "_total_zoom_enabled", page.locator("#total-chart").evaluate("(e)=>!!e.__zoom && getComputedStyle(e).touchAction==='none'"))
    check(label + "_type_zoom_enabled", page.locator("#type-chart").evaluate("(e)=>!!e.__zoom && getComputedStyle(e).touchAction==='none'"))

    page.locator("#total-controls button[data-years='10']").click()
    page.wait_for_timeout(450)
    k = page.locator("#total-chart").evaluate("(e)=>e.__zoom.k")
    check(label + "_total_10y_zoom", k > 1.5, k)
    page.locator("#total-controls button[data-years='all']").click()
    page.wait_for_timeout(450)
    k_reset = page.locator("#total-chart").evaluate("(e)=>e.__zoom.k")
    check(label + "_total_zoom_reset", abs(k_reset-1) < 0.001, k_reset)

    page.locator("#type-controls button[data-years='5']").click()
    page.wait_for_timeout(450)
    k2 = page.locator("#type-chart").evaluate("(e)=>e.__zoom.k")
    check(label + "_type_5y_zoom", k2 > 1.5, k2)
    page.locator("#type-controls button[data-years='all']").click()
    page.wait_for_timeout(450)

    if label == "mobile":
        box = page.locator("#total-chart").bounding_box()
        cx = box["x"] + box["width"] * 0.55
        cy = box["y"] + box["height"] * 0.48
        cdp = page.context.new_cdp_session(page)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [
            {"x": cx - 28, "y": cy, "id": 1, "radiusX": 8, "radiusY": 8, "force": 1},
            {"x": cx + 28, "y": cy, "id": 2, "radiusX": 8, "radiusY": 8, "force": 1},
        ]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
            {"x": cx - 58, "y": cy, "id": 1, "radiusX": 8, "radiusY": 8, "force": 1},
            {"x": cx + 58, "y": cy, "id": 2, "radiusX": 8, "radiusY": 8, "force": 1},
        ]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(300)
        pinch_k = page.locator("#total-chart").evaluate("(e)=>e.__zoom.k")
        check(label + "_two_finger_pinch_zoom", pinch_k > 1.05, pinch_k)
        page.locator("#total-controls button[data-years='all']").click()
        page.wait_for_timeout(450)
        hbox = page.locator("#holding-chart").bounding_box()
        hcx = hbox["x"] + hbox["width"] * 0.55
        hcy = hbox["y"] + hbox["height"] * 0.48
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [
            {"x": hcx - 28, "y": hcy, "id": 3, "radiusX": 8, "radiusY": 8, "force": 1},
            {"x": hcx + 28, "y": hcy, "id": 4, "radiusX": 8, "radiusY": 8, "force": 1},
        ]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
            {"x": hcx - 58, "y": hcy, "id": 3, "radiusX": 8, "radiusY": 8, "force": 1},
            {"x": hcx + 58, "y": hcy, "id": 4, "radiusX": 8, "radiusY": 8, "force": 1},
        ]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(300)
        holding_pinch_k = page.locator("#holding-chart").evaluate("(e)=>e.__zoom.k")
        check(label + "_holding_two_finger_pinch_zoom", holding_pinch_k > 1.05, holding_pinch_k)
        page.locator("#holding-type-controls button[data-type='Total']").click()
        page.wait_for_timeout(300)

    for chart_id in ("total-chart", "type-chart", "flow-chart", "holding-chart"):
        box = page.locator("#" + chart_id).bounding_box()
        check(label + "_" + chart_id + "_fits_viewport", box is not None and box["width"] <= page.evaluate("window.innerWidth") + 1, box)
        if label == "mobile":
            check(label + "_" + chart_id + "_readable_height", box is not None and box["height"] >= 220, box)
            font_size = page.locator("#" + chart_id + " .axis text").first.evaluate("(e)=>parseFloat(getComputedStyle(e).fontSize)")
            check(label + "_" + chart_id + "_axis_font_size", font_size >= 15, font_size)
    check(label + "_no_horizontal_page_overflow", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
    page.screenshot(path=str(OUT / (label + ".png")), full_page=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    desktop = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    desktop.on("console", lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None)
    desktop.on("pageerror", lambda err: report["page_errors"].append(str(err)))
    desktop.on("requestfailed", lambda req: report["failed_requests"].append({"url": req.url, "error": req.failure}))
    validate(desktop, "desktop")

    mobile_context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
    mobile = mobile_context.new_page()
    mobile.on("console", lambda msg: report["console_errors"].append(msg.text) if msg.type == "error" else None)
    mobile.on("pageerror", lambda err: report["page_errors"].append(str(err)))
    mobile.on("requestfailed", lambda req: report["failed_requests"].append({"url": req.url, "error": req.failure}))
    validate(mobile, "mobile")
    mobile_context.close()
    browser.close()

check("no_page_errors", len(report["page_errors"]) == 0, report["page_errors"])
check("no_console_errors", len(report["console_errors"]) == 0, report["console_errors"])
report["status"] = "PASS"
(OUT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
server.shutdown()
