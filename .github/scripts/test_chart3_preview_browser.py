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
    check(label + "_seventeen_event_legend_items", page.locator("#event-drawdown-key [data-event-entry]").count() == 17)
    check(label + "_eighteen_drawdown_bands", page.locator("#combined-chart svg rect[data-drawdown]").count() == 18)
    check(label + "_eighteen_drawdown_percentage_labels", page.locator("#combined-chart svg text[data-drawdown-label]").count() == 18)
    check(label + "_eighteen_drawdown_ledger_items", page.locator("#event-drawdown-key [data-drawdown-entry]").count() == 18)
    check(label + "_35_history_checkboxes_default_checked", page.locator("#event-drawdown-key input[type=checkbox]:checked").count() == 35)
    check(label + "_17_event_checkboxes", page.locator("#event-drawdown-key input[data-history-event]").count() == 17)
    check(label + "_18_drawdown_checkboxes", page.locator("#event-drawdown-key input[data-history-drawdown]").count() == 18)
    drawdown_ledger_text = page.locator("#event-drawdown-key").inner_text()
    legacy_note = page.locator("#pre-series-history-note")
    check(label + "_pre_series_1990_note_visible", legacy_note.is_visible())
    legacy_text = legacy_note.inner_text()
    check(label + "_pre_series_1990_note_has_dates_closes_and_method", all(value in legacy_text for value in ["1990-07-16", "1990-10-11", "-19.9%", "368.95", "295.46", "1993-12-31", "不補畫價格線"]))
    check(label + "_pre_series_1990_source_links", "sec.gov/Archives" in legacy_note.locator("a").nth(0).get_attribute("href") and "bmogamhub.com" in legacy_note.locator("a").nth(1).get_attribute("href"))
    legacy_marker = page.locator('#combined-chart svg rect[data-drawdown="dd-1990"]')
    check(label + "_pre_series_1990_boundary_marker", legacy_marker.get_attribute("data-drawdown-before-series") == "true" and legacy_marker.evaluate("(e)=>Math.abs(e.getBBox().width-2)<0.01"))
    legacy_checkbox = page.locator('#event-drawdown-key input[data-history-drawdown="dd-1990"]')
    legacy_checkbox.uncheck()
    check(label + "_pre_series_1990_note_hides_with_drawdown", legacy_note.evaluate("(e)=>e.hidden"))
    legacy_checkbox.check()
    check(label + "_pre_series_1990_note_restores_with_drawdown", legacy_note.is_visible())
    check(label + "_drawdown_labels_include_2011_and_2022", all(value in drawdown_ledger_text for value in ["-19.4%", "-25.4%", "-16.0%", "-12.4%", "-14.7%"]))
    check(label + "_event_dates_and_sources", all(value in page.locator("#event-drawdown-key").inner_text() for value in ["1990-07-16 → 1990-10-11", "1997-07-02 → 1998-12-31", "2002-11-27 → 2003-03-11", "2011-04-29 → 2011-10-03", "2025-02-19 → 2025-04-08"]) and page.locator("#event-drawdown-key a").count() >= 35)
    check(label + "_event_bands_inside_plot", page.locator("#combined-chart svg").evaluate("(svg)=>[...svg.querySelectorAll('rect[data-event]')].every(e=>{const b=e.getBBox(),top=Number(svg.dataset.plotTop),bottom=Number(svg.dataset.plotBottom);return b.y===top&&b.height===bottom-top&&b.width>=2})"))
    check(label + "_event_bands_behind_series", page.locator("#combined-chart svg").evaluate("(svg)=>{const a=[...svg.children].findIndex(e=>e.matches('rect[data-event]'));const b=[...svg.children].findIndex(e=>e.matches('path[data-series]'));return a>=0&&b>a}"))
    check(label + "_drawdown_bands_inside_plot", page.locator("#combined-chart svg").evaluate("(svg)=>{const top=Number(svg.dataset.plotTop),bottom=Number(svg.dataset.plotBottom),els=[...svg.querySelectorAll('rect[data-drawdown]')];return els.length===18&&els.every(e=>{const b=e.getBBox();return b.y===top&&b.height===bottom-top&&b.width>=2})}"))
    check(label + "_drawdown_labels_inside_plot", page.locator("#combined-chart svg").evaluate("(svg)=>{const l=Number(svg.dataset.plotLeft),r=Number(svg.dataset.plotRight),t=Number(svg.dataset.plotTop),b=Number(svg.dataset.plotBottom),els=[...svg.querySelectorAll('text[data-drawdown-label]')];return els.length===18&&els.every(e=>{const x=Number(e.getAttribute('x')),y=Number(e.getAttribute('y')),box=e.getBBox();return box.x>=l&&box.x+box.width<=r&&box.y>=t&&box.y+box.height<=b})}"))
    check(label + "_all_selected_by_default", page.locator("#series-filters input[data-series-toggle]:checked").count() == 5)
    check(label + "_right_price_axis", page.locator("#combined-chart svg text[data-axis='right']").count() == 6)
    check(label + "_right_axis_ticks_inside_svg", page.locator("#combined-chart svg").evaluate("(svg)=>{const r=svg.getBoundingClientRect(),ts=[...svg.querySelectorAll('text[data-axis=right]')].map(e=>e.getBoundingClientRect());return ts.every(t=>t.left>=r.left-1&&t.right<=r.right+1)}"))
    check(label + "_left_percentile_axis", any(term in page.locator("#combined-chart svg").evaluate("(e)=>e.textContent") for term in ["金融壓力指標","壓力指標百分位"]))
    check(label + "_legend_five_series", page.locator("#combined-legend .swatch").count() == 5)
    check(label + "_guide_visible", page.locator(".guide").is_visible())
    # Verify an individual series can be hidden and restored.
    vix = page.locator('#series-filters input[data-series-toggle="VIXCLS"]')
    vix.uncheck()
    check(label + "_single_series_hide", page.locator("#combined-chart svg path[data-series]").count() == 4)
    vix.check()
    check(label + "_single_series_restore", page.locator("#combined-chart svg path[data-series]").count() == 5)
    # Event and drawdown controls must operate independently and update chart overlays.
    ev = page.locator("#event-drawdown-key input[data-history-event=\"gfc\"]")
    ev.uncheck()
    check(label + "_single_event_hide_band", page.locator("#combined-chart svg rect[data-event=\"gfc\"]:visible").count() == 0)
    check(label + "_single_event_checkbox_unchecked", not ev.is_checked())
    dd = page.locator("#event-drawdown-key input[data-history-drawdown=\"dd-2007\"]")
    check(label + "_independent_drawdown_still_visible", page.locator("#combined-chart svg rect[data-drawdown=\"dd-2007\"]:visible").count() == 1)
    dd.uncheck()
    check(label + "_single_drawdown_hide_band", page.locator("#combined-chart svg rect[data-drawdown=\"dd-2007\"]:visible").count() == 0)
    check(label + "_single_drawdown_hide_label", page.locator("#combined-chart svg text[data-drawdown-label=\"dd-2007\"]:visible").count() == 0)
    ev.check()
    check(label + "_event_restore", page.locator("#combined-chart svg rect[data-event=\"gfc\"]:visible").count() == 1)
    dd.check()
    check(label + "_drawdown_restore", page.locator("#combined-chart svg rect[data-drawdown=\"dd-2007\"]:visible").count() == 1)
    page.locator("#clear-all-series").click()
    check(label + "_clear_all", page.locator("#combined-chart svg path[data-series]").count() == 0)
    check(label + "_clear_all_controls", page.locator("#series-filters input:checked").count() == 0)
    page.locator("#select-all-series").click()
    check(label + "_select_all_restore", page.locator("#combined-chart svg path[data-series]").count() == 5)
    check(label + "_select_all_controls", page.locator("#series-filters input:checked").count() == 5)
    page.locator("#clear-all-history").click()
    check(label + "_clear_all_history_checkboxes", page.locator("#event-drawdown-key input:checked").count() == 0)
    check(label + "_clear_all_event_bands", page.locator("#combined-chart svg rect[data-event]:visible").count() == 0)
    check(label + "_clear_all_drawdown_bands", page.locator("#combined-chart svg rect[data-drawdown]:visible").count() == 0)
    page.locator("#select-all-history").click()
    check(label + "_select_all_history_checkboxes", page.locator("#event-drawdown-key input:checked").count() == 35)
    check(label + "_select_all_event_bands", page.locator("#combined-chart svg rect[data-event]:visible").count() == 17)
    check(label + "_select_all_drawdown_bands", page.locator("#combined-chart svg rect[data-drawdown]:visible").count() == 18)
    # Verify the percentile warm-up and synchronized timeline controls.
    stl = page.locator('#combined-chart svg path[data-series="STLFSI4"]')
    first_valid = stl.get_attribute("data-first-valid-date") or ""
    check(label + "_full_520_week_window", stl.get_attribute("data-percentile-window") == "520" and first_valid >= "2000-01-01", first_valid)
    check(label + "_timeline_controls_present", page.locator("#timeline-zoom-in").count() == 1 and page.locator("#timeline-zoom-out").count() == 1 and page.locator("#timeline-reset").count() == 1)
    initial = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
    initial_span = page.evaluate("(v)=>Date.parse(v[1])-Date.parse(v[0])", initial)
    initial_axis = page.locator("#combined-chart svg path[data-series='SP500']").evaluate("(e)=>[Number(e.dataset.axisMin),Number(e.dataset.axisMax)]")
    page.locator("#timeline-zoom-in").click()
    page.wait_for_function("(v)=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart!==v[0]&&e.dataset.viewEnd!==v[1]}", arg=initial, timeout=3000)
    zoomed = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
    zoomed_span = page.evaluate("(v)=>Date.parse(v[1])-Date.parse(v[0])", zoomed)
    check(label + "_button_zoom_in_reduces_time_span", zoomed_span < initial_span)
    zoomed_axis = page.locator("#combined-chart svg path[data-series='SP500']").evaluate("(e)=>[Number(e.dataset.axisMin),Number(e.dataset.axisMax)]")
    render_ms = float(page.locator("#combined-chart").get_attribute("data-render-ms") or "9999")
    check(label + "_timeline_render_finishes_under_250ms", render_ms < 250, render_ms)
    right_ticks = page.locator("#combined-chart svg text[data-axis='right']").count()
    check(label + "_dynamic_right_axis_has_six_ticks", right_ticks == 6, right_ticks)
    check(label + "_dynamic_right_axis_tracks_zoom_range", zoomed_axis != initial_axis and zoomed_axis[1] > zoomed_axis[0], {"initial":initial_axis,"zoomed":zoomed_axis})
    price_meta = page.locator("#combined-chart svg path[data-series='SP500']").evaluate("(e)=>({min:Number(e.dataset.priceMin),max:Number(e.dataset.priceMax),axisMin:Number(e.dataset.axisMin),axisMax:Number(e.dataset.axisMax),transform:e.getAttribute('transform')})")
    check(label + "_visible_sp500_range_inside_dynamic_axis", price_meta["axisMin"] <= price_meta["min"] and price_meta["axisMax"] >= price_meta["max"], price_meta)
    check(label + "_sp500_visible_points_are_bounded", page.locator("#combined-chart svg path[data-series='SP500']").evaluate("(e)=>Number(e.dataset.visiblePoints)>1&&e.getAttribute('d').length>20"))
    check(label + "_sp500_path_uses_plot_clip", page.locator("#combined-chart svg").evaluate("(svg)=>{const p=svg.querySelector('path[data-series=SP500]'),c=svg.querySelector('clipPath#plot-clip');return !!p&&p.getAttribute('clip-path')==='url(#plot-clip)'&&c?.getAttribute('clipPathUnits')==='userSpaceOnUse'&&p.getAttribute('transform')===null}"))
    page.locator("#timeline-zoom-out").click()
    page.wait_for_timeout(40)
    page.locator("#timeline-reset").click()
    page.wait_for_function("()=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart==='1993-12-31'&&e.dataset.viewEnd==='2026-11-10'}", timeout=3000)
    reset = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
    check(label + "_timeline_reset_restores_full_range", reset == ["1993-12-31", "2026-11-10"], reset)
    svg_box = page.locator("#combined-chart svg").bounding_box()
    if svg_box and label == "desktop":
        cx = svg_box["x"] + svg_box["width"] * 0.55
        cy = svg_box["y"] + svg_box["height"] * 0.45
        page.mouse.move(cx, cy)
        page.mouse.wheel(0, -250)
        page.wait_for_function("(v)=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart!==v[0]&&e.dataset.viewEnd!==v[1]}", arg=reset, timeout=3000)
        wheel_zoom = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
        wheel_span = page.evaluate("(v)=>Date.parse(v[1])-Date.parse(v[0])", wheel_zoom)
        check(label + "_mouse_wheel_zoom", wheel_span < initial_span, wheel_zoom)
        page.locator("#timeline-reset").click()
        page.locator("#timeline-zoom-in").click()
        before_drag = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + 55, cy, steps=4)
        page.mouse.up()
        dragged = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
        check(label + "_mouse_drag_pans_timeline", dragged != before_drag, dragged)
        page.locator("#timeline-reset").click()
    elif svg_box:
        # Simulate two-finger pinch zoom and one-finger horizontal pan on mobile.
        pinch = page.evaluate("""() => {
          const el=document.querySelector('#combined-svg');
          const touch=(id,x,y)=>new Touch({identifier:id,target:el,clientX:x,clientY:y,screenX:x,screenY:y,pageX:x,pageY:y});
          const a=touch(1,120,180),b=touch(2,220,180);
          el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,cancelable:true,touches:[a,b],targetTouches:[a,b],changedTouches:[a,b]}));
          const c=touch(1,80,180),d=touch(2,260,180);
          el.dispatchEvent(new TouchEvent('touchmove',{bubbles:true,cancelable:true,touches:[c,d],targetTouches:[c,d],changedTouches:[c,d]}));
          el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,cancelable:true,touches:[],targetTouches:[],changedTouches:[c,d]}));
          return [document.querySelector('#combined-svg').dataset.viewStart,document.querySelector('#combined-svg').dataset.viewEnd];
        }""")
        page.wait_for_function("(v)=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart!==v[0]&&e.dataset.viewEnd!==v[1]}", arg=initial, timeout=3000)
        pinch = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
        pinch_span = page.evaluate("(v)=>Date.parse(v[1])-Date.parse(v[0])", pinch)
        check(label + "_two_finger_pinch_zoom", pinch_span < initial_span, pinch)
        page.locator("#timeline-reset").click()
        page.wait_for_function("()=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart==='1993-12-31'&&e.dataset.viewEnd==='2026-11-10'}", timeout=3000)
        page.locator("#timeline-zoom-in").click()
        page.wait_for_function("(v)=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart!==v[0]&&e.dataset.viewEnd!==v[1]}", arg=initial, timeout=3000)
        before_pan = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
        panned = page.evaluate("""() => {
          const el=document.querySelector('#combined-svg');
          const touch=(id,x,y)=>new Touch({identifier:id,target:el,clientX:x,clientY:y,screenX:x,screenY:y,pageX:x,pageY:y});
          const a=touch(1,120,180);
          el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,cancelable:true,touches:[a],targetTouches:[a],changedTouches:[a]}));
          const b=touch(1,180,180);
          el.dispatchEvent(new TouchEvent('touchmove',{bubbles:true,cancelable:true,touches:[b],targetTouches:[b],changedTouches:[b]}));
          el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,cancelable:true,touches:[],targetTouches:[],changedTouches:[b]}));
          return [document.querySelector('#combined-svg').dataset.viewStart,document.querySelector('#combined-svg').dataset.viewEnd];
        }""")
        page.wait_for_function("(v)=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart!==v[0]&&e.dataset.viewEnd!==v[1]}", arg=before_pan, timeout=3000)
        panned = page.locator("#combined-chart svg").evaluate("(e)=>[e.dataset.viewStart,e.dataset.viewEnd]")
        check(label + "_one_finger_drag_pans_timeline", panned != before_pan, panned)
        page.locator("#timeline-reset").click()
        page.wait_for_function("()=>{const e=document.querySelector('#combined-chart svg');return e&&e.dataset.viewStart==='1993-12-31'&&e.dataset.viewEnd==='2026-11-10'}", timeout=3000)

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
            check(label + "_no_chart_horizontal_overflow", chart_box["scroll"] <= chart_box["client"] + 2, chart_box)
            svg_layout = page.locator("#combined-chart svg").evaluate("(e)=>({width:e.getBoundingClientRect().width,container:e.parentElement.clientWidth,viewWidth:Number(e.viewBox.baseVal.width)})")
            check(label + "_responsive_svg_fits_container", abs(svg_layout["width"]-svg_layout["container"]) <= 2 and svg_layout["viewWidth"] <= 1100, svg_layout)
            axis_layout = page.locator("#combined-chart svg").evaluate("(e)=>{const w=e.viewBox.baseVal.width,ticks=[...e.querySelectorAll('text[data-axis=right]')].map(t=>t.getBBox());return {viewWidth:w,minLeft:Math.min(...ticks.map(t=>t.x)),maxRight:Math.max(...ticks.map(t=>t.x+t.width)),tickCount:ticks.length}}")
            check(label + "_right_price_axis_visible_without_horizontal_scroll", axis_layout["minLeft"] >= 0 and axis_layout["maxRight"] <= axis_layout["viewWidth"] and axis_layout["tickCount"] == 6, axis_layout)
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
