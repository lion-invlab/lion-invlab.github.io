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
    check(label + "_repo_dimension_data_loaded", "Repo 維度" in page.locator("#load-status").inner_text(), page.locator("#load-status").inner_text())
    check(label + "_repo_chart_rendered", page.locator("#repo-chart path.repo-series").count() == 5)
    check(label + "_repo_zoom_enabled", page.locator("#repo-chart .repo-zoom-hitarea").evaluate("(e)=>!!e && getComputedStyle(e).touchAction===\"none\""))
    page.locator("#repo-dimension-controls button[data-dimension='collateral']").click()
    check(label + "_repo_collateral_switch", page.locator("#repo-chart path.repo-series").count() == 3)
    page.locator("#repo-dimension-controls button[data-dimension='tenor']").click()
    check(label + "_repo_tenor_switch", page.locator("#repo-chart path.repo-series").count() == 3)
    page.locator("#repo-dimension-controls button[data-dimension='counterparty']").click()
    check(label + "_repo_counterparty_switch", page.locator("#repo-chart path.repo-series").count() == 5)

    # Regression: exercise actual wheel zoom in/out and drag, then verify every
    # series still has a finite SVG path and the date window remains bounded.
    repo_svg = page.locator("#repo-chart")
    def repo_snapshot():
        return repo_svg.locator("path.repo-series").evaluate_all(
            "(els)=>els.map(e=>({d:e.getAttribute('d'),box:(()=>{const b=e.getBBox();return {x:b.x,y:b.y,width:b.width,height:b.height}})()}))"
        )
    def repo_domain():
        return repo_svg.evaluate("(e)=>({start:e.dataset.domainStart,end:e.dataset.domainEnd,fullStart:e.dataset.fullDomainStart,fullEnd:e.dataset.fullDomainEnd})")
    before_wheel = repo_snapshot()
    repo_box = repo_svg.bounding_box()
    wheel_x = repo_box["x"] + repo_box["width"] * 0.52
    wheel_y = repo_box["y"] + repo_box["height"] * 0.48
    page.mouse.move(wheel_x, wheel_y)
    page.mouse.wheel(0, -160)
    page.wait_for_timeout(120)
    after_zoom_in = repo_snapshot()
    check(label + "_repo_wheel_zoom_changes_paths", any(a["d"] != b["d"] for a, b in zip(before_wheel, after_zoom_in)), [a["d"][:80] if a["d"] else "" for a in after_zoom_in])
    check(label + "_repo_paths_survive_zoom_in", len(after_zoom_in) == 5 and all(p["d"] and not any(v in p["d"] for v in ("NaN","Infinity","undefined")) and p["box"]["width"] > 0 for p in after_zoom_in), {"paths":after_zoom_in,"svg":repo_svg.evaluate("(e)=>({domain:e.dataset.domainStart+\"..\"+e.dataset.domainEnd,full:e.dataset.fullDomainStart+\"..\"+e.dataset.fullDomainEnd,points:e.dataset.repoPointCount,keys:e.dataset.repoKeyCount,y:e.dataset.repoYDomain,finite:e.dataset.repoFinitePoints,generated:e.dataset.repoGeneratedPathLengths,selection:e.dataset.repoPathSelectionCount,first:e.dataset.repoFirstPoint})"),"legend":page.locator("#repo-legend").inner_text()})
    domain = repo_domain()
    check(label + "_repo_zoom_domain_bounded", domain["start"] >= domain["fullStart"] and domain["end"] <= domain["fullEnd"] and domain["start"] < domain["end"], domain)
    page.mouse.wheel(0, 160)
    page.wait_for_timeout(120)
    after_zoom_out = repo_snapshot()
    check(label + "_repo_paths_survive_zoom_out", len(after_zoom_out) == 5 and all(p["d"] and not any(v in p["d"] for v in ("NaN","Infinity","undefined")) for p in after_zoom_out), after_zoom_out)
    # Zoom back in before dragging; a full-range domain cannot pan by design.
    page.mouse.wheel(0, -160)
    page.wait_for_timeout(120)
    before_drag = repo_snapshot()
    domain_before_drag = repo_domain()
    page.mouse.move(wheel_x, wheel_y)
    page.mouse.down()
    page.mouse.move(wheel_x - 55, wheel_y, steps=5)
    page.mouse.up()
    page.wait_for_timeout(120)
    after_drag = repo_snapshot()
    check(label + "_repo_drag_changes_paths", any(a["d"] != b["d"] for a, b in zip(before_drag, after_drag)), [a["d"][:80] if a["d"] else "" for a in after_drag])
    check(label + "_repo_paths_survive_drag", len(after_drag) == 5 and all(p["d"] and not any(v in p["d"] for v in ("NaN","Infinity","undefined")) for p in after_drag), after_drag)
    domain = repo_domain()
    check(label + "_repo_drag_domain_bounded", domain["start"] >= domain["fullStart"] and domain["end"] <= domain["fullEnd"] and domain["start"] < domain["end"], domain)
    check(label + "_repo_drag_changes_domain", domain["start"] != domain_before_drag["start"] or domain["end"] != domain_before_drag["end"], {"before":domain_before_drag,"after":domain})
    if label == "mobile":
        # Verify a real one-finger touch drag on the Repo hit area.
        page.locator("#repo-chart").scroll_into_view_if_needed()
        page.wait_for_timeout(150)
        mobile_box = page.locator("#repo-chart .repo-zoom-hitarea").bounding_box()
        tx = mobile_box["x"] + mobile_box["width"] * 0.58
        ty = mobile_box["y"] + mobile_box["height"] * 0.45
        cdp = page.context.new_cdp_session(page)
        cdp.send("Input.dispatchTouchEvent", {"type":"touchStart","touchPoints":[{"x":tx,"y":ty,"id":11,"radiusX":7,"radiusY":7,"force":1}]})
        cdp.send("Input.dispatchTouchEvent", {"type":"touchMove","touchPoints":[{"x":tx-45,"y":ty,"id":11,"radiusX":7,"radiusY":7,"force":1}]})
        cdp.send("Input.dispatchTouchEvent", {"type":"touchEnd","touchPoints":[]})
        page.wait_for_timeout(150)
        touch_domain = repo_domain()
        check(label + "_repo_touch_drag_changes_domain", touch_domain["start"] != domain["start"] or touch_domain["end"] != domain["end"], {"before":domain,"after":touch_domain})
        check(label + "_repo_touch_drag_bounded", touch_domain["start"] >= touch_domain["fullStart"] and touch_domain["end"] <= touch_domain["fullEnd"] and touch_domain["start"] < touch_domain["end"], touch_domain)
    page.locator("#repo-dimension-controls button[data-dimension='collateral']").click()
    reset_domain = repo_domain()
    check(label + "_repo_dimension_switch_resets_domain", reset_domain["start"] == reset_domain["fullStart"] and reset_domain["end"] == reset_domain["fullEnd"], reset_domain)
    page.locator("#repo-dimension-controls button[data-dimension='counterparty']").click()

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
        # Earlier mobile touch-drag checks scroll down to Repo/Holdings. Bring
        # the total chart back into the viewport before dispatching CDP pinch.
        page.locator("#total-chart").scroll_into_view_if_needed()
        page.wait_for_timeout(200)
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
        page.locator("#holding-chart").scroll_into_view_if_needed()
        page.wait_for_timeout(250)
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

    for chart_id in ("total-chart", "type-chart", "flow-chart", "holding-chart", "repo-chart"):
        box = page.locator("#" + chart_id).bounding_box()
        check(label + "_" + chart_id + "_fits_viewport", box is not None and box["width"] <= page.evaluate("window.innerWidth") + 1, box)
        if label == "mobile":
            check(label + "_" + chart_id + "_readable_height", box is not None and box["height"] >= 220, box)
            font_size = page.locator("#" + chart_id + " .axis text").first.evaluate("(e)=>parseFloat(getComputedStyle(e).fontSize)")
            check(label + "_" + chart_id + "_axis_font_size", font_size >= 15, font_size)
    bad_paths = page.locator("svg path[d]").evaluate_all("(els)=>els.filter(e=>/(NaN|Infinity|undefined)/.test(e.getAttribute(\"d\")||\"\")).map(e=>({svg:e.ownerSVGElement?.id,cls:e.getAttribute(\"class\"),d:(e.getAttribute(\"d\")||\"\").slice(0,180)}))")
    print(label + "_bad_svg_paths", bad_paths, flush=True)
    check(label + "_all_chart_paths_finite", len(bad_paths) == 0, bad_paths)
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
