#!/usr/bin/env python3
"""Bounded-concurrency browser observations for TAC's 44 historical market pages.
Page-read success is deliberately separate from numeric/instrument verification.
"""
from __future__ import annotations
import argparse, asyncio, hashlib, json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.async_api import async_playwright
from stage2_screenshot_inputs import apply_page_completions_to_fixture, apply_screenshot_values_to_fixture, load_screenshot_bundle
from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture

def number_token(value):
    s=str(value or "").replace(",","").replace("\u2212","-").replace("+","").strip()
    m=re.search(r"-?\d+(?:\.\d+)?",s)
    return None if not m else f"{float(m.group()):.8f}".rstrip("0").rstrip(".")

def classify_http_response(status):
    """Distinguish transport/access failures from a successful page with no target row."""
    if status is None:
        return "TOOL_READ_FAILURE"
    if int(status) < 200 or int(status) >= 400:
        return "TOOL_READ_FAILURE"
    return "PAGE_READ_OK"


def classify_rendered_page(body_text, match_count):
    """Separate access challenges from a successfully read page lacking the requested date."""
    challenge_markers=("captcha", "access denied", "verify you are human",
                       "checking your browser", "just a moment")
    if any(marker in str(body_text or "").lower() for marker in challenge_markers):
        return "TOOL_READ_FAILURE"
    if not match_count:
        return "TARGET_DATE_NOT_FOUND"
    return "PAGE_READ_OK"

def target_date_markers(target):
    from datetime import datetime as dt
    d=dt.strptime(target,"%Y-%m-%d")
    return list(dict.fromkeys([
        target, d.strftime("%b %d, %Y"), d.strftime("%B %d, %Y"),
        d.strftime("%d/%m/%Y"), d.strftime("%m/%d/%Y"),
        d.strftime("%d %b %Y"), d.strftime("%Y/%m/%d"),
        f"{d.year}年{d.month}月{d.day}日",
    ]))


def date_in_row(text, target):
    from datetime import datetime as dt
    d=dt.strptime(target,"%Y-%m-%d")
    forms=[target,d.strftime("%b %d, %Y"),d.strftime("%B %d, %Y"),
           d.strftime("%d/%m/%Y"),d.strftime("%m/%d/%Y"),
           d.strftime("%d %b %Y"),d.strftime("%b %d, %y"),
           f"{d.year}年{d.month}月{d.day}日",
           f"{d.year}/{d.month}/{d.day}",
           f"{d.month}/{d.day}/{d.year}",
           f"{d.day}/{d.month}/{d.year}"]
    low=text.lower()
    return any(x.lower() in low for x in forms)

IDENTITY_ALIASES = {
    "道瓊工業指數": ["Dow Jones Industrial Average", "道瓊斯工業平均指數", "DJI"],
    "標普500指數": ["S&P 500", "SPX"],
    "那斯達克綜合指數": ["Nasdaq Composite", "Nasdaq綜合指數", "IXIC"],
    "羅素2000指數": ["Russell 2000", "RUT"],
    "費城半導體指數": ["Philadelphia Semiconductor", "費城半導體指數", "SOX"],
    "日經225": ["Nikkei 225", "N225"],
    "韓國 KOSPI": ["KOSPI", "KS11"],
    "台灣加權指數": ["Taiwan Weighted", "臺灣加權指數", "TWII"],
    "新加坡海峽時報指數 STI": ["FTSE Straits Times Singapore", "STI"],
    "澳洲 S&P/ASX 200": ["S&P/ASX200", "ASX 200", "AXJO"],
    "上海綜合指數": ["Shanghai Composite", "上證綜合指數", "SSEC"],
    "深證成指": ["SZSE Component", "深證成份指數", "SZI"],
    "香港恆生指數": ["Hang Seng", "HSI"],
    "英國 FTSE 100": ["FTSE 100", "FTSE"],
    "德國 DAX": ["DAX", "GDAXI"],
    "法國 CAC 40": ["CAC40", "CAC 40", "FCHI"],
    "STOXX Europe 600": ["STOXX 600", "STOXX"],
    "2年期美債殖利率": ["United States 2-Year Bond Yield"],
    "10年期美債殖利率": ["United States 10-Year Bond Yield"],
    "30年期美債殖利率": ["United States 30-Year Bond Yield"],
    "美元指數": ["US Dollar Index", "DXY"],
    "美元／新台幣": ["USD TWD", "USD/TWD"],
    "歐元／美元": ["EUR USD", "EUR/USD"],
    "英鎊／美元": ["GBP USD", "GBP/USD"],
    "澳幣／美元": ["AUD USD", "AUD/USD"],
    "美元／日圓": ["USD JPY", "USD/JPY"],
    "WTI原油期貨": ["WTI原油期貨", "WTI Crude Oil"],
    "Brent原油期貨": ["Brent Oil", "布倫特原油期貨"],
    "黃金期貨 GC": ["黃金期貨", "Gold Futures"],
    "白銀期貨 SI": ["白銀期貨", "Silver Futures"],
    "XLK": ["XLK", "Technology Select Sector SPDR Fund", "Technology Select Sector SPDR ETF"],
    "XLF": ["XLF", "Financial Select Sector SPDR Fund", "Financial Select Sector SPDR ETF"],
    "XLE": ["XLE", "Energy Select Sector SPDR Fund", "Energy Select Sector SPDR ETF"],
    "XLV": ["XLV", "Health Care Select Sector SPDR Fund", "Health Care Select Sector SPDR ETF"],
    "XLY": ["XLY", "Consumer Discretionary Select Sector SPDR Fund", "Consumer Discretionary Select Sector SPDR ETF"],
    "XLP": ["XLP", "Consumer Staples Select Sector SPDR Fund", "Consumer Staples Select Sector SPDR ETF"],
    "XLI": ["XLI", "Industrial Select Sector SPDR Fund", "Industrials Select Sector SPDR Fund", "Industrial Select Sector SPDR ETF"],
    "XLB": ["XLB", "Materials Select Sector SPDR Fund", "Materials Select Sector SPDR ETF"],
    "XLU": ["XLU", "Utilities Select Sector SPDR Fund", "Utilities Select Sector SPDR ETF"],
    "XLRE": ["XLRE", "Real Estate Select Sector SPDR Fund", "Real Estate Select Sector SPDR ETF"],
    "XLC": ["XLC", "Communication Services Select Sector SPDR Fund", "Communication Services Select Sector SPDR ETF"],
    "vix": ["CBOE Volatility Index", "VIX"],
    "move": ["ICE:MOVE", "ICE BofAML U.S. Bond Market Option Volatility Estimate Index", "ICE BofAML MOVE", "MOVE Index", "MOVE", "Merrill Lynch Option Volatility Estimate", "INDEXNYSEGIS: MOVE"],
    "fear_greed": ["CNN Fear & Greed Index", "US stocks · CNN"],
}

def cnn_score_matches_display(score, expected_display):
    """CNN exposes decimal precision while TAC's score card displays a rounded integer."""
    try:
        return number_token(str(int(float(score) + 0.5))) == number_token(expected_display)
    except (TypeError, ValueError, OverflowError):
        return False


def cnn_band_for_score(score):
    """Derive the prior-close sentiment band using CNN's published 0-100 thresholds."""
    value = float(score)
    if not 0 <= value <= 100:
        raise ValueError("CNN Fear & Greed score must be between 0 and 100")
    if value < 25:
        return "extreme fear"
    if value < 45:
        return "fear"
    if value < 55:
        return "neutral"
    if value < 75:
        return "greed"
    return "extreme greed"

def parse_cnn_history(payload, target):
    """Return CNN's own composite daily score/rating for the exact UTC date."""
    block = payload.get("fear_and_greed_historical") or {}
    points = block.get("data") or []
    matches = []
    recent = []
    for index, point in enumerate(points):
        stamp = point.get("x") or point.get("timestamp")
        if stamp is None:
            continue
        try:
            point_time = datetime.fromtimestamp(float(stamp) / 1000, timezone.utc)
            observed_date = point_time.date().isoformat()
        except (TypeError, ValueError, OverflowError):
            continue
        item = {
            "array_index": index,
            "date_utc": observed_date,
            "timestamp_utc": point_time.isoformat(),
            "score": point.get("y", point.get("score")),
            "rating": str(point.get("rating") or "").strip().lower(),
        }
        if observed_date == target:
            matches.append(item)
        if index >= max(0, len(points) - 8):
            recent.append(item)
    if not matches:
        return {"status": "TARGET_DATE_NOT_FOUND", "recent_points": recent}
    # Keep the latest timestamp if CNN exposes more than one point for a UTC date;
    # when timestamps tie, preserve the last point in the provider's array.
    selected = sorted(matches, key=lambda x: (x["timestamp_utc"], x["array_index"]))[-1]
    if selected["score"] is None or not selected["rating"]:
        return {"status": "OBSERVED_PENDING_FIELD_MAPPING", "date": target,
                "target_date_points": matches, "recent_points": recent}
    return {
        "status": "PAGE_READ_OK",
        "date": target,
        "timestamp_utc": selected["timestamp_utc"],
        "score": selected["score"],
        "rating": selected["rating"],
        "target_date_points": matches,
        "recent_points": recent,
    }

def split_cells(text):
    raw = str(text or "")
    if "\t" in raw:
        return [part.strip() for part in raw.split("\t")]
    return [part.strip() for part in re.split(r"\s*\|\s*", raw) if part.strip()]

def header_indexes(lines, cell_count=None):
    for line in lines:
        cells = split_cells(line)
        normalized = [re.sub(r"[^a-z0-9%\u4e00-\u9fff]", "", x.lower()) for x in cells]
        date_i = next((i for i,x in enumerate(normalized) if "date" in x or "日期" in x), None)
        if date_i is None:
            continue
        # Some pages expose an unrelated leading instrument header in the same
        # collection. Anchor the historical table at its Date column.
        cells = cells[date_i:]
        normalized = normalized[date_i:]
        value_i = next((i for i,x in enumerate(normalized) if any(k in x for k in ("price","close","收市","收盤","價格"))), None)
        change_i = next((i for i,x in enumerate(normalized) if ("change" in x and "%" in x) or "升跌" in x or "漲跌" in x or "變動%" in x), None)
        if value_i is not None and change_i is not None:
            if cell_count is None or max(value_i, change_i) < cell_count:
                return cells, 0, value_i, change_i
    return None, None, None, None

async def observe_once(context,row,target,timeout,sem,challenge_wait_ms=9000):
    out={"name":row["name"],"group":row["group"],"source_url":row["source_url"],
         "instrument_identity_status":"NOT_INDEPENDENTLY_VERIFIED",
         "target_date":target,"quote_type":row.get("quote_type"),
         "read_method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE","provenance":"CURRENT_RUN_BROWSER_OBSERVATION"}
    started=datetime.now(timezone.utc).isoformat()
    async with sem:
        page=await context.new_page()
        page.set_default_timeout(min(timeout,3000))
        page.set_default_navigation_timeout(timeout)
        try:
            if row["name"] == "fear_greed":
                # First open CNN Business dashboard; use its official graphdata endpoint
                # for the exact historical composite row if the page itself is not date-specific.
                official_page_status=None
                try:
                    official_response=await page.goto(row["source_url"],wait_until="domcontentloaded",timeout=min(timeout,8000))
                    official_page_status=official_response.status if official_response else None
                    out["official_page_title"]=await page.title()
                    official_body=await page.locator("body").inner_text()
                    out["official_page_last_updated"]=next((line.strip() for line in official_body.splitlines() if "last updated" in line.lower()),None)
                except Exception as official_exc:
                    out["official_page_error"]=f"{type(official_exc).__name__}: {official_exc}"
                out["official_page_http_status"]=official_page_status
                out["official_page_readable"]=official_page_status==200
                # Read CNN's own composite historical series, never its seven component rows.
                endpoint="https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
                api_response=await context.request.get(endpoint,timeout=timeout,headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Referer": "https://edition.cnn.com/markets/fear-and-greed",
                    "Accept": "application/json, text/plain, */*",
                })
                out.update({"data_endpoint_url":endpoint,"http_status":api_response.status,
                            "final_url":endpoint,"read_method":"CNN_OFFICIAL_PREVIOUS_CLOSE","provenance":"CURRENT_CNN_OFFICIAL_API_OBSERVATION"})
                if api_response.status != 200:
                    out.update({"status":"TOOL_READ_FAILURE","error":f"CNN_GRAPH_DATA_HTTP_{api_response.status}"})
                    return out
                out["source_page_fetched"]=True
                raw=await api_response.body()
                out["raw_response_sha256"]=hashlib.sha256(raw).hexdigest()
                payload=json.loads(raw.decode("utf-8"))
                parsed=parse_cnn_history(payload,target)
                headline=payload.get("fear_and_greed") or {}
                historical=payload.get("fear_and_greed_historical") or {}
                out["cnn_current_headline"]={
                    "score":headline.get("score"), "rating":headline.get("rating"),
                    "timestamp":headline.get("timestamp"),
                    "previous_close":headline.get("previous_close"),
                }
                out["cnn_historical_block_summary"]={
                    "score":historical.get("score"), "rating":historical.get("rating"),
                    "timestamp":historical.get("timestamp"),
                    "point_count":len(historical.get("data") or []),
                }
                out["cnn_target_date_points"]=parsed.get("target_date_points",[])
                out["cnn_recent_history_points"]=parsed.get("recent_points",[])
                out["page_title"]="CNN Business Fear & Greed historical data"
                previous_close=headline.get("previous_close")
                headline_timestamp=headline.get("timestamp")
                try:
                    headline_dt=datetime.fromisoformat(str(headline_timestamp).replace("Z","+00:00")).astimezone(timezone.utc)
                    headline_date=headline_dt.date().isoformat()
                except (TypeError, ValueError, OverflowError):
                    out.update({"status":"OBSERVED_PENDING_FIELD_MAPPING","error":"CNN_HEADLINE_TIMESTAMP_MISSING_OR_INVALID"})
                    return out
                if previous_close is None or headline_date <= target:
                    out.update({"status":"OBSERVED_PENDING_FIELD_MAPPING","error":"CNN_PREVIOUS_CLOSE_NOT_PROVEN_TO_PRECEDE_TARGET_SESSION"})
                    return out
                score=str(previous_close)
                rating=cnn_band_for_score(previous_close)
                expected_band=str(row.get("expected_change") or "").strip().lower()
                score_match=(row.get("expected_value") is None or cnn_score_matches_display(score,row.get("expected_value")))
                band_match=(not expected_band or rating==expected_band)
                out.update({
                    "instrument_identity":"CNN Fear & Greed Index",
                    "instrument_identity_status":"VERIFIED",
                    "observed_date":target,
                    "previous_close_target_date":target,
                    "source_timestamp_utc":headline_dt.isoformat(),
                    "observed_value":score,
                    "observed_change":rating,
                    "observed_value_field":"fear_and_greed.previous_close",
                    "observed_change_field":"derived_from_fear_and_greed.previous_close_using_cnn_bands",
                    "historical_series_diagnostic_status":"MATCH" if parsed.get("status")=="PAGE_READ_OK" and abs(float(parsed.get("score"))-float(previous_close))<0.0000001 else "DISAGREES_OR_UNAVAILABLE",
                    "historical_series_diagnostic_value":parsed.get("score"),
                    "historical_series_diagnostic_timestamp_utc":parsed.get("timestamp_utc"),
                    "expected_display_value":row.get("expected_value"),
                    "expected_change_display":row.get("expected_change"),
                    "display_value_match":score_match,
                    "display_change_match":band_match,
                    "field_mapping_status":"VERIFIED",
                    "status":"VERIFIED" if score_match and band_match else "OBSERVED_PENDING_FIELD_MAPPING",
                })
                return out
            request_url=row.get("request_url") or row["source_url"]
            out["attempt_url"]=request_url
            response=await page.goto(request_url,wait_until="domcontentloaded",timeout=timeout)
            # Investing.com hydrates historical rows after DOMContentLoaded; wait for the requested session date.
            markers=target_date_markers(target)
            try:
                await page.wait_for_function("(markers) => markers.some(m => (document.body?.innerText || '').includes(m))", arg=markers, timeout=min(timeout,7000))
            except Exception:
                await page.wait_for_timeout(1200)
            navigation_status=response.status if response else None
            out["navigation_http_status"]=navigation_status
            out["http_status"]=navigation_status
            out["page_title"]=await page.title()
            out["final_url"]=page.url
            challenge_resolved=False
            if navigation_status == 403:
                # Cloudflare may serve a temporary interstitial with HTTP 403 while
                # normal browser-side verification is still running. Wait for the
                # page itself to complete; never solve CAPTCHAs or bypass access controls.
                try:
                    await page.wait_for_function("""() => {
                      const body=(document.body?.innerText || '').toLowerCase();
                      const challenge=['just a moment','checking your browser','verify you are human','access denied'];
                      const stillBlocked=challenge.some(x=>body.includes(x));
                      const rows=document.querySelectorAll('table tr, [role=row]').length;
                      return !stillBlocked && rows > 1;
                    }""", timeout=challenge_wait_ms)
                    challenge_resolved=True
                    out["http_status"]=200
                    out["challenge_interstitial_resolved"]=True
                    out["page_title"]=await page.title()
                    out["final_url"]=page.url
                except Exception:
                    out["challenge_interstitial_resolved"]=False
            response_class=classify_http_response(out["http_status"])
            if response_class == "TOOL_READ_FAILURE":
                out["status"]="TOOL_READ_FAILURE"
                out["error"]="SOURCE_PAGE_HTTP_" + str(navigation_status if navigation_status is not None else "NO_RESPONSE") + "; NORMAL_BROWSER_CHALLENGE_DID_NOT_COMPLETE; NOT EVIDENCE_OF_SOURCE_NO_DATA"
                return out
            # Do not wait 30 seconds for a table that may never render.
            # Investing.com HK pages may use Chinese-localized dates; US pages use English.
            # Do not assume a semantic HTML table: inspect table rows, ARIA rows, then body text.
            rows=[]
            for selector in ("table tr", '[role="row"]'):
                try:
                    await page.locator(selector).first.wait_for(state="visible",timeout=min(timeout,1500))
                    found=await page.locator(selector).all_inner_texts()
                    rows.extend(x.strip() for x in found if x.strip())
                except Exception:
                    pass
            header_lines=[]
            for selector in ("table thead tr", "th", "[role=columnheader]"):
                try:
                    found=await page.locator(selector).all_inner_texts()
                    if found:
                        header_lines.append("\t".join(x.strip() for x in found if x.strip()))
                except Exception:
                    pass
            body_text=await page.locator("body").inner_text()
            body_lines=[x.strip() for x in body_text.splitlines() if x.strip()]
            matches=list(dict.fromkeys(x for x in rows+body_lines if date_in_row(x,target)))
            out["rendered_row_candidate_count"]=len(rows)
            out["body_text_line_count"]=len(body_lines)
            out["target_date_rows"]=matches[:5]
            page_status=classify_rendered_page(body_text,len(matches))
            if page_status != "TOOL_READ_FAILURE":
                out["source_page_fetched"]=True
            if page_status == "TOOL_READ_FAILURE":
                out["status"]="TOOL_READ_FAILURE"
                out["error"]="SOURCE_PAGE_CHALLENGE_OR_ACCESS_BLOCK; NOT EVIDENCE_OF_SOURCE_NO_DATA"
                return out
            if page_status == "TARGET_DATE_NOT_FOUND":
                out["status"]="TARGET_DATE_NOT_FOUND"
                out["error"]="TARGET_DATE_NOT_PRESENT_ON_SUCCESSFULLY_READ_PAGE"
                title_text=(out.get("page_title","")+" "+(await page.locator("h1").first.inner_text() if await page.locator("h1").count() else "")).lower()
                aliases=IDENTITY_ALIASES.get(row["name"],[row["name"]])
                matched_identity=next((alias for alias in aliases if alias.lower() in title_text),None)
                out["instrument_identity"]=matched_identity
                out["instrument_identity_status"]="VERIFIED" if matched_identity else "NOT_INDEPENDENTLY_VERIFIED"
                out["page_body_excerpt"]="\n".join(body_lines[:80])[:5000]
                try:
                    out["page_date_controls"]=await page.locator("input").evaluate_all("(els) => els.slice(0,20).map(e => ({type:e.type,placeholder:e.placeholder,value:e.value,ariaLabel:e.getAttribute('aria-label')}))")
                except Exception:
                    out["page_date_controls"]=[]
                return out
            candidate=matches[0]
            cells=split_cells(candidate)
            headers,date_i,value_i,change_i=header_indexes(header_lines+rows+body_lines, len(cells))
            title_text=(out.get("page_title","")+" "+(await page.locator("h1").first.inner_text() if await page.locator("h1").count() else "")).lower()
            aliases=IDENTITY_ALIASES.get(row["name"],[row["name"]])
            matched_identity=next((alias for alias in aliases if alias.lower() in title_text),None)
            identity_ok=matched_identity is not None
            field_ok=bool(headers and date_i is not None and value_i is not None and change_i is not None
                          and max(date_i,value_i,change_i)<len(cells)
                          and date_in_row(cells[date_i],target))
            observed_value=cells[value_i] if field_ok else None
            observed_change=cells[change_i] if field_ok else None
            vm=bool(field_ok and (row.get("expected_value") is None or number_token(observed_value)==number_token(row.get("expected_value"))))
            cm=bool(field_ok and (row.get("expected_change") is None or number_token(observed_change)==number_token(row.get("expected_change"))))
            out.update({
                "observed_row_text":candidate,
                "observed_date":target if field_ok else None,
                "observed_cells":cells,
                "observed_headers":headers,
                "expected_display_value":row.get("expected_value"),
                "expected_change_display":row.get("expected_change"),
                "observed_value":observed_value,
                "observed_change":observed_change,
                "observed_value_field":headers[value_i] if field_ok else None,
                "observed_change_field":headers[change_i] if field_ok else None,
                "display_value_match":vm,
                "display_change_match":cm,
                "instrument_identity":matched_identity,
                "instrument_identity_status":"VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "screenshot_instrument_identity_status":"VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
                "field_mapping_status":"VERIFIED" if field_ok else "PENDING_FIELD_HEADER_MAPPING",
            })
            out["preexisting_value_comparison"]="NOT_PERFORMED_BLANK_INPUT" if row.get("expected_value") is None else "COMPARED_TO_EXISTING_FIXTURE"
            if identity_ok and field_ok and vm and cm:
                out["status"]="VERIFIED"
                out["numeric_token_match_only"]=False
            else:
                out["status"]="OBSERVED_PENDING_FIELD_MAPPING"
                out["numeric_token_match_only"]=bool(vm and cm)
            return out
        except Exception as exc:
            out.update({"status":"TOOL_READ_FAILURE","error":f"{type(exc).__name__}: {exc}"})
            return out
        finally:
            out["started_at_utc"]=started
            finished=datetime.now(timezone.utc)
            out["finished_at_utc"]=finished.isoformat()
            out["finished_at_tw"]=finished.astimezone(timezone(timedelta(hours=8))).isoformat()
            await page.close()
            await asyncio.sleep(0.5)

async def observe(context,row,target,timeout,sem):
    """Read Investing.com first; MOVE alone may fall back to TradingView ICE:MOVE."""
    original_url=row["source_url"]
    is_move=row.get("group")=="risk" and row.get("name")=="move"
    backup_url="https://www.tradingview.com/symbols/ICE-MOVE/"
    if is_move and row.get("move_backup_only"):
        backup_row=dict(row); backup_row["request_url"]=backup_url
        result=await observe_once(context,backup_row,target,min(timeout,12000),sem,challenge_wait_ms=4000)
        result["source_url"]=original_url
        result["source_role"]="BACKUP_1"
        result["evidence_source_url"]=backup_url
        result["read_method"]="PLAYWRIGHT_RENDERED_TRADINGVIEW_SYMBOL_PAGE"
        if result.get("status")=="TARGET_DATE_NOT_FOUND":
            result.update({"status":"SOURCE_UPDATE_PENDING","read_status":"SOURCE_UPDATE_PENDING",
                           "observed_date":None,"observed_value":None,"observed_change":None,
                           "observed_value_field":None,"observed_change_field":None,
                           "error":"MOVE_TARGET_SESSION_NOT_YET_AVAILABLE_ON_TRADINGVIEW"})
        elif result.get("status")=="VERIFIED":
            result["read_status"]="PAGE_CONTENT_READ_SUCCESS"
            result["read_method"]="PLAYWRIGHT_RENDERED_TRADINGVIEW_SYMBOL_PAGE"
        else:
            result["read_status"]="TOOL_READ_FAILURE"
            result["read_method"]="PLAYWRIGHT_RENDERED_TRADINGVIEW_SYMBOL_PAGE"
        result["attempt_count"]=1
        result["attempt_history"]=[{"round":1,"source_role":"BACKUP_1","request_url":backup_url,
            "status":result.get("status"),"http_status":result.get("http_status"),
            "page_title":result.get("page_title"),"final_url":result.get("final_url"),
            "instrument_identity":result.get("instrument_identity"),"instrument_identity_status":result.get("instrument_identity_status"),
            "instrument_identity":result.get("instrument_identity"),"instrument_identity_status":result.get("instrument_identity_status"),
            "observed_row_text":result.get("observed_row_text"),"page_body_excerpt":result.get("page_body_excerpt"),
            "started_at_utc":result.get("started_at_utc"),"finished_at_utc":result.get("finished_at_utc"),
            "error":result.get("error")}]
        result["verification_round"]=1
        return result
    result=await observe_once(context,row,target,timeout,sem,challenge_wait_ms=6000)
    attempts=[{
        "round":1,"source_role":"PRIMARY","request_url":original_url,"status":result.get("status"),
        "http_status":result.get("http_status"),
        "navigation_http_status":result.get("navigation_http_status"),
        "page_title":result.get("page_title"),"final_url":result.get("final_url"),
        "observed_row_text":result.get("observed_row_text"),"page_body_excerpt":result.get("page_body_excerpt"),
        "error":result.get("error"),
        "started_at_utc":result.get("started_at_utc"),
        "finished_at_utc":result.get("finished_at_utc"),
    }]
    if is_move and result.get("status") in ("TARGET_DATE_NOT_FOUND","TOOL_READ_FAILURE"):
        backup_row=dict(row); backup_row["request_url"]=backup_url
        backup=await observe_once(context,backup_row,target,min(timeout,12000),sem,challenge_wait_ms=4000)
        attempts.append({
            "round":2,"source_role":"BACKUP_1","request_url":backup_url,"status":backup.get("status"),
            "http_status":backup.get("http_status"),
            "navigation_http_status":backup.get("navigation_http_status"),
            "page_title":backup.get("page_title"),"final_url":backup.get("final_url"),
            "instrument_identity":backup.get("instrument_identity"),"instrument_identity_status":backup.get("instrument_identity_status"),
            "observed_row_text":backup.get("observed_row_text"),"page_body_excerpt":backup.get("page_body_excerpt"),
            "error":backup.get("error"),
            "started_at_utc":backup.get("started_at_utc"),
            "finished_at_utc":backup.get("finished_at_utc"),
        })
        if backup.get("status")=="VERIFIED":
            result=backup
            result["source_role"]="BACKUP_1"
            result["evidence_source_url"]=backup_url
            result["primary_source_url"]=original_url
            result["read_status"]="PAGE_CONTENT_READ_SUCCESS"
            result["read_method"]="PLAYWRIGHT_RENDERED_TRADINGVIEW_SYMBOL_PAGE"
        elif result.get("status")=="TARGET_DATE_NOT_FOUND" or backup.get("status")=="TARGET_DATE_NOT_FOUND":
            primary_excerpt=result.get("page_body_excerpt","")
            backup_excerpt=backup.get("page_body_excerpt","")
            result.update({
                "status":"SOURCE_UPDATE_PENDING",
                "read_status":"SOURCE_UPDATE_PENDING",
                "source_role":"PRIMARY_AND_BACKUP_PENDING",
                "source_url":original_url,
                "evidence_source_url":backup_url if backup.get("source_page_fetched") else original_url,
                "source_page_fetched":bool(result.get("source_page_fetched") or backup.get("source_page_fetched")),
                "backup_page_title":backup.get("page_title"),
                "backup_final_url":backup.get("final_url"),
                "page_title":backup.get("page_title") if backup.get("source_page_fetched") else result.get("page_title"),
                "final_url":backup.get("final_url") if backup.get("source_page_fetched") else result.get("final_url"),
                "attempt_url":backup_url if backup.get("source_page_fetched") else original_url,
                "read_method":"PLAYWRIGHT_RENDERED_TRADINGVIEW_SYMBOL_PAGE" if backup.get("source_page_fetched") else "PLAYWRIGHT_RENDERED_HISTORY_TABLE",
                "instrument_identity":backup.get("instrument_identity") if backup.get("source_page_fetched") else result.get("instrument_identity"),
                "instrument_identity_status":backup.get("instrument_identity_status") if backup.get("source_page_fetched") else result.get("instrument_identity_status"),
                "http_status":backup.get("http_status") if backup.get("source_page_fetched") else result.get("http_status"),
                "observed_date":None,"observed_value":None,"observed_change":None,
                "observed_value_field":None,"observed_change_field":None,
                "page_body_excerpt":"\\n".join(x for x in (primary_excerpt,backup_excerpt) if x)[:5000],
                "primary_attempt_status":attempts[0]["status"],
                "backup_attempt_status":attempts[1]["status"],
                "error":"MOVE_TARGET_SESSION_NOT_YET_AVAILABLE_ON_READABLE_PRIMARY_OR_BACKUP_PAGE",
            })
        else:
            result=backup if result.get("status")=="TOOL_READ_FAILURE" else result
            result["source_role"]="PRIMARY_AND_BACKUP_READ_FAILURE"
            result["primary_attempt_status"]=attempts[0]["status"]
            result["backup_attempt_status"]=attempts[1]["status"]
            if result.get("status")=="TOOL_READ_FAILURE": result["read_status"]="TOOL_READ_FAILURE"
    result["source_url"]=original_url
    result["verification_round"]=next((x["round"] for x in attempts if x["status"]=="VERIFIED"),attempts[-1]["round"])
    result["attempt_count"]=len(attempts)
    result["attempt_history"]=attempts
    return result

def _screenshot_identity_matches(name, identity):
    text=str(identity or "").casefold()
    aliases=IDENTITY_ALIASES.get(name,[name])
    return any(str(alias).casefold() in text for alias in aliases)


def _apply_screenshot_fields(row, observation, screenshot):
    """Overlay screenshot-provided fields without replacing them with page values."""
    if not screenshot:
        return observation
    fields=screenshot["fields"]
    observation.setdefault("group",row["group"])
    observation.setdefault("name",row["name"])
    is_fg=row["group"]=="risk" and row["name"]=="fear_greed"
    screenshot_identity_ok=_screenshot_identity_matches(row["name"],screenshot.get("instrument_identity"))
    value_key="score" if is_fg else "close"
    change_key="band" if is_fg else "change"
    evidence={}
    for key,item in fields.items():
        evidence[key]={
            "source_type":"USER_PROVIDED_SCREENSHOT",
            "evidence_path":item["evidence_path"],
            "evidence_sha256":item["evidence_sha256"],
            "captured_at":item["captured_at"],
            "quote_timestamp":item.get("quote_timestamp"),
            "field_name":item["field_name"],
            "value":item["value"],
        }

    page_ok=(screenshot_identity_ok
             and observation.get("source_page_fetched") is True
             and observation.get("instrument_identity_status")=="VERIFIED"
             and observation.get("field_mapping_status")=="VERIFIED"
             and observation.get("observed_value") is not None
             and observation.get("observed_change") is not None)
    required_keys=(value_key,change_key)
    screenshot_only=all(key in fields for key in required_keys)
    if screenshot_only:
        identity=screenshot["instrument_identity"]
        identity_ok=_screenshot_identity_matches(row["name"],identity)
        value=fields[value_key]["value"]
        change=fields[change_key]["value"]
        vm=(row.get("expected_value") is None or number_token(value)==number_token(row.get("expected_value")))
        cm=(not row.get("expected_change") or str(change).strip().casefold()==str(row.get("expected_change") or "").strip().casefold()) if is_fg else (row.get("expected_change") is None or number_token(change)==number_token(row.get("expected_change")))
        observation.update({
            "status":"VERIFIED" if identity_ok and vm and cm else "OBSERVED_PENDING_FIELD_MAPPING",
            "source_url":row["source_url"],
            "target_date":row.get("target_date") or observation.get("target_date"),
            "observed_date":screenshot["data_date"],
            "instrument_identity":identity,
            "instrument_identity_status":"VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "screenshot_instrument_identity_status":"VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "field_mapping_status":"VERIFIED",
            "observed_value":value,
            "observed_change":change,
            "observed_value_field":fields[value_key]["field_name"],
            "observed_change_field":fields[change_key]["field_name"],
            "observed_value_key":value_key,
            "observed_change_key":change_key,
            "display_value_match":vm,
            "display_change_match":cm,
            "read_method":"USER_PROVIDED_SCREENSHOT",
            "provenance":"CURRENT_USER_PROVIDED_SCREENSHOT",
            "read_status":"USER_PROVIDED_SCREENSHOT_CONFIRMED",
            "source_page_fetched":False,
            "http_status":None,
            "field_evidence":evidence,
            "screenshot_evidence_path":screenshot["evidence_path"],
            "screenshot_evidence_sha256":screenshot["evidence_sha256"],
        })
        observation["finished_at_utc"]=screenshot["captured_at"]
        observation["finished_at_tw"]=screenshot["captured_at"]
        return observation

    # Partial screenshot: retain screenshot fields and use the historical page only
    # for required fields that were not supplied in the screenshot.
    if not page_ok:
        observation["field_evidence"]=evidence
        observation["screenshot_instrument_identity_status"]="VERIFIED" if screenshot_identity_ok else "NOT_INDEPENDENTLY_VERIFIED"
        observation["read_method"]="MIXED_SCREENSHOT_AND_HISTORICAL_PAGE"
        observation["provenance"]="CURRENT_RUN_MIXED_FIELD_OBSERVATION"
        observation["read_status"]="MIXED_FIELD_OBSERVATIONS_PENDING"
        observation["source_page_fetched"]=bool(observation.get("source_page_fetched"))
        return observation

    page_value=observation.get("observed_value")
    page_change=observation.get("observed_change")
    tradingview_move=(row["group"]=="risk" and row["name"]=="move" and
                      (observation.get("source_role")=="BACKUP_1" or
                       observation.get("evidence_source_url")=="https://www.tradingview.com/symbols/ICE-MOVE/"))
    page_source_type="TRADINGVIEW_HISTORICAL_PAGE" if tradingview_move else "INVESTING_HISTORICAL_PAGE"
    page_source_url=observation.get("data_endpoint_url") or observation.get("evidence_source_url") or observation.get("attempt_url") or row["source_url"]
    if value_key in fields:
        observation["observed_value"]=fields[value_key]["value"]
        observation["observed_value_field"]=fields[value_key]["field_name"]
        observation["observed_value_key"]=value_key
        observation["display_value_match"]=number_token(fields[value_key]["value"])==number_token(row.get("expected_value"))
        evidence[value_key]=evidence[value_key]
    else:
        observation["observed_value_key"]=value_key
        evidence[value_key]={
            "source_type":"CNN_OFFICIAL_API" if is_fg else page_source_type,"source_url":page_source_url,
            "field_name":observation.get("observed_value_field"),
            "value":page_value,"observed_at":observation.get("finished_at_tw"),
        }
    if change_key in fields:
        observation["observed_change"]=fields[change_key]["value"]
        observation["observed_change_field"]=fields[change_key]["field_name"]
        observation["observed_change_key"]=change_key
        observation["display_change_match"]=(
            str(fields[change_key]["value"]).strip().casefold()==str(row.get("expected_change") or "").strip().casefold()
            if is_fg else number_token(fields[change_key]["value"])==number_token(row.get("expected_change"))
        )
    else:
        observation["observed_change_key"]=change_key
        evidence[change_key]={
            "source_type":page_source_type,"source_url":page_source_url,
            "field_name":observation.get("observed_change_field"),
            "value":page_change,"observed_at":observation.get("finished_at_tw"),
        }
    observation["field_evidence"]=evidence
    observation["screenshot_instrument_identity_status"]="VERIFIED" if screenshot_identity_ok else "NOT_INDEPENDENTLY_VERIFIED"
    observation["read_method"]="MIXED_SCREENSHOT_AND_OFFICIAL_SOURCE" if is_fg else "MIXED_SCREENSHOT_AND_HISTORICAL_PAGE"
    observation["provenance"]="CURRENT_RUN_MIXED_FIELD_OBSERVATION"
    observation["read_status"]="MIXED_FIELD_OBSERVATIONS_CONFIRMED"
    observation["status"]=(
        "VERIFIED"
        if observation.get("instrument_identity_status")=="VERIFIED"
        and observation.get("screenshot_instrument_identity_status")=="VERIFIED"
        and observation.get("field_mapping_status")=="VERIFIED"
        and observation.get("display_value_match") is True
        and observation.get("display_change_match") is True
        else "OBSERVED_PENDING_FIELD_MAPPING"
    )
    return observation


def persist_fixture(path: Path, data: dict, *, no_fixture_write: bool = False) -> bool:
    """Persist the working Fixture only for production runs, never diagnostic runs."""
    if no_fixture_write:
        return False
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return True


def _ensure_field_evidence(row, observation):
    """Record field-level provenance for page-only rows as well as screenshot rows."""
    if observation.get("field_evidence"):
        return
    is_fg=row["group"]=="risk" and row["name"]=="fear_greed"
    value_key,change_key=("score","band") if is_fg else ("close","change")
    is_tradingview_move=(row["group"]=="risk" and row["name"]=="move" and
                        (observation.get("source_role")=="BACKUP_1" or
                         observation.get("evidence_source_url")=="https://www.tradingview.com/symbols/ICE-MOVE/"))
    source_type="CNN_OFFICIAL_API" if is_fg else ("TRADINGVIEW_HISTORICAL_PAGE" if is_tradingview_move else "INVESTING_HISTORICAL_PAGE")
    source_url=observation.get("data_endpoint_url") or observation.get("evidence_source_url") or observation.get("attempt_url") or row.get("source_url")
    observed_at=observation.get("finished_at_tw") or observation.get("finished_at_utc")
    evidence={}
    for key,field_name,value in (
        (value_key,observation.get("observed_value_field"),observation.get("observed_value")),
        (change_key,observation.get("observed_change_field"),observation.get("observed_change")),
    ):
        if value is not None:
            evidence[key]={
                "source_type":source_type,
                "source_url":source_url,
                "field_name":field_name,
                "value":value,
                "observed_at":observed_at,
            }
    observation["field_evidence"]=evidence
    observation["observed_value_key"]=value_key
    observation["observed_change_key"]=change_key


async def run(a,work,target,screenshot_inputs):
    sem=asyncio.Semaphore(a.concurrency)
    by_key={}
    for row in work:
        shot=screenshot_inputs.get((row["group"],row["name"]))
        row["screenshot_input"]=shot
        required=("score","band") if row["group"]=="risk" and row["name"]=="fear_greed" else ("close","change")
        if shot and all(key in shot["fields"] for key in required):
            empty={
                "name":row["name"],"group":row["group"],"source_url":row["source_url"],
                "target_date":target,"quote_type":row.get("quote_type"),
                "status":"PENDING","source_page_fetched":False,
            }
            by_key[(row["group"],row["name"])]=_apply_screenshot_fields(row,empty,shot)
    pending=[row for row in work if (row["group"],row["name"]) not in by_key]
    if pending:
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            context=await browser.new_context(locale="zh-HK",timezone_id="Asia/Taipei")
            try:
                tasks=[observe(context,row,target,a.timeout_ms,sem) for row in pending]
                page_observations=await asyncio.gather(*tasks)
            finally:
                await context.close()
                await browser.close()
        for row,item in zip(pending,page_observations):
            item=_apply_screenshot_fields(row,item,row.get("screenshot_input"))
            by_key[(row["group"],row["name"])]=item
    observations=[by_key[(row["group"],row["name"])] for row in work]
    for row,item in zip(work,observations):
        _ensure_field_evidence(row,item)
    for item in observations:
        canonical=json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
        item["observation_record_sha256"]=hashlib.sha256(canonical).hexdigest()
    counts={}
    for item in observations: counts[item["status"]]=counts.get(item["status"],0)+1
    return observations,counts

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fixture",required=True); ap.add_argument("--report-date",required=True)
    ap.add_argument("--output",required=True); ap.add_argument("--timeout-ms",type=int,default=15000)
    ap.add_argument("--concurrency",type=int,default=4)
    ap.add_argument("--screenshot-bundle", help="Date-matched SHA-locked screenshot sidecar JSON; defaults to production/input/market-screenshot-observations-REPORT_DATE.json")
    ap.add_argument("--no-fixture-write", action="store_true",
                    help="Emit observations without writing populated values back to the input fixture")
    ap.add_argument("--only", help="Optional exact group:name row selector, e.g. risk:fear_greed")
    ap.add_argument("--move-backup-only", action="store_true",
                    help="Read only the TradingView ICE:MOVE history backup; requires --only risk:move")
    a=ap.parse_args()
    if not 1<=a.concurrency<=12: raise SystemExit("--concurrency must be between 1 and 12")
    fixture_path=Path(a.fixture)
    data=json.loads(fixture_path.read_text(encoding="utf-8"))
    data=blank_fixture(data,apply_screenshots=False)
    target=data.get("trading_date")
    if data.get("report_date")!=a.report_date or not target: raise SystemExit("Fixture date mismatch")
    screenshot_bundle=Path(a.screenshot_bundle) if a.screenshot_bundle else Path(
        f"production/input/market-screenshot-observations-{a.report_date}.json"
    )
    screenshot_inputs=load_screenshot_bundle(screenshot_bundle,data,Path.cwd()) if screenshot_bundle.is_file() else {}
    if a.only:
        group_name, sep, item_name = a.only.partition(":")
        if not sep or not group_name or not item_name:
            raise SystemExit("--only must use group:name")
        screenshot_inputs={key:value for key,value in screenshot_inputs.items() if key==(group_name,item_name)}
    if screenshot_inputs:
        data=apply_screenshot_values_to_fixture(data,screenshot_inputs)
        persist_fixture(fixture_path, data, no_fixture_write=a.no_fixture_write)
    work=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for name,item in (data.get(group) or {}).items():
            src=item.get("source") or {}
            if group in ("energy", "metals"):
                expected_value, expected_change = src.get("history_close"), src.get("history_change")
            elif group == "risk" and src.get("score_value") is not None:
                expected_value, expected_change = src.get("score_value"), src.get("band")
            else:
                expected_value, expected_change = src.get("close_value"), src.get("daily_change_percent")
            work.append({"group":group,"name":name,"source_url":src.get("url"),
                         "expected_value":expected_value,"expected_change":expected_change,
                         "quote_type":src.get("quote_type"), "instrument_identity_expected":src.get("instrument_identity") or src.get("name") or name})
    for name,display_change in (data.get("sectors") or {}).items():
        src=(data.get("sector_sources") or {}).get(name) or {}
        # Sector cards display only daily % change, but the historical source row
        # must be checked against the ETF's actual close AND its daily % change.
        # Never compare the close field to the card's percentage display.
        work.append({"group":"sectors","name":name,"source_url":src.get("url"),
                     "expected_value":src.get("history_close"),
                     "expected_change":src.get("history_change"),
                     "quote_type":src.get("quote_type"),
                     "instrument_ticker":name, "instrument_identity_expected":name})
    if a.only:
        work = [row for row in work if row["group"] == group_name and row["name"] == item_name]
        if len(work) != 1:
            raise SystemExit(f"--only selector must match exactly one row, matched {len(work)}")
    elif len(work) != 44:
        raise SystemExit(f"Expected 44 source rows, got {len(work)}")
    if a.move_backup_only:
        if a.only != "risk:move":
            raise SystemExit("--move-backup-only requires --only risk:move")
        work[0]["move_backup_only"]=True
    if any(not x["source_url"] for x in work): raise SystemExit("One or more selected rows have no source URL")
    observations,counts=asyncio.run(run(a,work,target,screenshot_inputs))
    if screenshot_inputs:
        observations=apply_page_completions_to_fixture(data,observations,screenshot_inputs)
        persist_fixture(fixture_path, data, no_fixture_write=a.no_fixture_write)
        for item in observations:
            item.pop("observation_record_sha256",None)
            canonical=json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
            item["observation_record_sha256"]=hashlib.sha256(canonical).hexdigest()
        counts={}
        for item in observations:
            counts[item.get("status","UNKNOWN")]=counts.get(item.get("status","UNKNOWN"),0)+1
    screenshot_only_count=sum(1 for item in observations if item.get("read_method")=="USER_PROVIDED_SCREENSHOT")
    mixed_count=sum(1 for item in observations if item.get("read_method")=="MIXED_SCREENSHOT_AND_HISTORICAL_PAGE")
    page_count=sum(1 for item in observations if item.get("source_page_fetched") is True)
    result={"schema_version":"1.2","report_date":a.report_date,"trading_date":target,
            "method":"SCREENSHOT_FIRST_WITH_INVESTING_HISTORICAL_PAGE_FIELD_COMPLETION",
            "row_count":len(observations),"concurrency":a.concurrency,"timeout_ms":a.timeout_ms,
            "screenshot_bundle":str(screenshot_bundle) if screenshot_inputs else None,
            "screenshot_only_count":screenshot_only_count,"mixed_field_count":mixed_count,
            "historical_page_read_count":page_count,
            "status_counts":counts,"verified_count":sum(1 for item in observations if item.get("status")=="VERIFIED"),"observations":observations,
            "warning":"Screenshot fields are immutable, SHA-locked inputs and take precedence. Only missing required fields are completed from the Investing.com historical data table. Access failures are never treated as source no-data."}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    result["bundle_sha256"]=hashlib.sha256(out.read_bytes()).hexdigest()
    summary={"output":str(out),"status_counts":counts,"row_count":len(observations),
        "preexisting_market_values_used":False}
    if not a.no_fixture_write:
        populated=populate_fixture(data,result)
        persist_fixture(fixture_path, populated, no_fixture_write=a.no_fixture_write)
        summary.update({"fixture_output":str(fixture_path),
            "verified_count":populated["stage2_market_bootstrap"]["verified_count"],
            "pending_count":populated["stage2_market_bootstrap"]["pending_count"]})
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__": main()
