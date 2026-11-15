#!/usr/bin/env python3
from __future__ import annotations
import json, os, threading, sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "chart2-browser-qa"
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
    page.wait_for_function("""() => document.querySelector('#long-chart path.series')
      && document.querySelector('#pe-chart path.series')
      && document.querySelector('#ep-chart path.series')
      && document.querySelector('#k-cape')?.textContent !== '—'""", timeout=30000)
    check(label+"_cape_value", page.locator("#k-cape").inner_text() == "40.71", page.locator("#k-cape").inner_text())
    check(label+"_cape_earnings_yield", page.locator("#k-ey").inner_text() == "2.46%", page.locator("#k-ey").inner_text())
    check(label+"_tips_real_yield", page.locator("#k-real").inner_text() == "2.78%", page.locator("#k-real").inner_text())
    check(label+"_spread", page.locator("#k-spread").inner_text() == "-0.33", page.locator("#k-spread").inner_text())
    svg = page.locator("#long-chart")
    check(label+"_long_term_chart_286_months", svg.get_attribute("data-points") == "286")
    check(label+"_long_term_history_start", svg.get_attribute("data-first-date") == "2003-01")
    check(label+"_long_term_history_end", svg.get_attribute("data-last-date") == "2026-10")
    check(label+"_two_yield_series", svg.locator("path.series").count() == 2)
    if label == "desktop":
        box = svg.bounding_box()
        before = svg.get_attribute("data-points")
        page.mouse.move(box["x"] + box["width"] * 0.55, box["y"] + box["height"] * 0.5)
        page.mouse.wheel(0, -240)
        page.wait_for_function("(n)=>Number(document.querySelector('#long-chart').dataset.points)<Number(n)", arg=before, timeout=3000)
        zoomed = svg.get_attribute("data-points")
        check(label+"_mouse_wheel_zoom_in", int(zoomed) < int(before), {"before":before,"after":zoomed})
        page.locator('[data-range="10"]').click()
        before_last = svg.get_attribute("data-last-date")
        box = svg.bounding_box()
        page.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.68, box["y"] + box["height"] * 0.5, steps=5)
        page.mouse.up()
        page.wait_for_function("(d)=>document.querySelector('#long-chart').dataset.lastDate<d", arg=before_last, timeout=3000)
        after_last = svg.get_attribute("data-last-date")
        check(label+"_mouse_drag_pan_earlier", after_last < before_last, {"before":before_last,"after":after_last})
        page.locator('[data-range="max"]').click()
    page.locator('[data-view="spread"]').click()
    check(label+"_spread_view_single_series", svg.locator("path.series").count() == 1)
    check(label+"_spread_view_zero_baseline", svg.locator("line.zero").count() == 1)
    page.locator('[data-view="cape-history"]').click()
    check(label+"_cape_full_history_1750_months", svg.get_attribute("data-points") == "1750")
    check(label+"_cape_full_history_starts_1881", svg.get_attribute("data-first-date") == "1881-01")
    check(label+"_cape_full_history_ends_2026_10", svg.get_attribute("data-last-date") == "2026-10")
    page.locator('[data-range="10"]').click()
    check(label+"_cape_ten_year_filter", svg.get_attribute("data-first-date") >= "2016-10", svg.get_attribute("data-first-date"))
    page.locator('[data-range="max"]').click()
    page.locator('[data-mode="forward"]').click()
    check(label+"_forward_pe_latest", page.locator("#f-pe").inner_text() == "20.85", page.locator("#f-pe").inner_text())
    check(label+"_forward_earnings_yield", page.locator("#f-ey").inner_text() == "4.80", page.locator("#f-ey").inner_text())
    check(label+"_equity_premium_latest", page.locator("#f-ep").inner_text() == "+2.80", page.locator("#f-ep").inner_text())
    check(label+"_fed_current_data_cutoff", "2026-04" in page.locator("#forward-asof").inner_text())
    check(label+"_fed_nov_2026_limit_disclosed", "沒有可解析的數值表" in page.locator("#forward-status").inner_text())
    page.locator("#fed-vintage").select_option("2025-11")
    check(label+"_fed_historical_vintage_switch", page.locator("#f-pe").inner_text() == "22.69", page.locator("#f-pe").inner_text())
    check(label+"_fed_historical_ep_vintage", page.locator("#f-ep").inner_text() == "+2.62", page.locator("#f-ep").inner_text())
    check(label+"_forward_pe_path", page.locator("#pe-chart path.series").count() == 1)
    check(label+"_forward_ep_path", page.locator("#ep-chart path.series").count() == 1)
    check(label+"_forward_series_ranges", page.locator("#pe-chart").get_attribute("data-first-date") == "1989-01" and page.locator("#ep-chart").get_attribute("data-first-date") == "1991-10")
    check(label+"_source_notes_visible", page.locator("#provenance").is_visible())
    check(label+"_spec_link", page.locator('a[href="./CHART2_SPEC.md"]').count() == 1)
    widths = page.evaluate("({client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})")
    check(label+"_no_page_horizontal_overflow", widths["scroll"] <= widths["client"] + 2, widths)
    for selector in ["#long-chart", "#pe-chart", "#ep-chart"]:
        dims = page.locator(selector).evaluate("(e)=>({w:e.getBoundingClientRect().width,parent:e.parentElement.getBoundingClientRect().width})")
        check(label+selector.replace("#","_")+"_svg_fits", abs(dims["w"]-dims["parent"]) <= 2, dims)

try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for label,viewport in [("desktop",{"width":1440,"height":1000}),("mobile390",{"width":390,"height":844}),("mobile320",{"width":320,"height":740})]:
            page=browser.new_page(viewport=viewport,device_scale_factor=1)
            page.on("console",lambda msg: report["console_errors"].append(msg.text) if msg.type=="error" else None)
            page.on("pageerror",lambda err: report["page_errors"].append(str(err)))
            page.on("requestfailed",lambda req: report["failed_requests"].append({"url":req.url,"failure":req.failure}))
            response=page.goto("http://127.0.0.1:8766/research/tac-chart2/chart2-preview.html",wait_until="networkidle",timeout=60000)
            check(label+"_http_200",response is not None and response.status==200,response.status if response else None)
            page.wait_for_function("""() => document.querySelector('#long-chart path.series') && document.querySelector('#k-cape')?.textContent !== '—'""", timeout=30000)
            page.screenshot(path=str(OUT/f"chart2-{label}-initial.png"),full_page=True)
            validate(page,label)
            page.screenshot(path=str(OUT/f"chart2-{label}-tested.png"),full_page=True)
            page.close()
        browser.close()
    check("no_console_errors",not report["console_errors"],report["console_errors"])
    check("no_page_errors",not report["page_errors"],report["page_errors"])
    check("no_failed_requests",not report["failed_requests"],report["failed_requests"])
    report["status"]="PASS"
except Exception as exc:
    report["error"]=repr(exc)
finally:
    server.shutdown()
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if report["status"]!="PASS":
    sys.exit(1)
