#!/usr/bin/env python3
"""Bounded-concurrency browser observations for TAC's 44 historical market pages.
Page-read success is deliberately separate from numeric/instrument verification.
"""
from __future__ import annotations
import argparse, asyncio, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

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
    "vix": ["CBOE Volatility Index", "VIX"],
    "move": ["ICE BofAML MOVE", "MOVE Index"],
    "fear_greed": ["CNN Fear & Greed Index", "US stocks · CNN"],
}

def cnn_score_matches_display(score, expected_display):
    """CNN exposes decimal precision while TAC's score card displays a rounded integer."""
    try:
        return number_token(str(int(float(score) + 0.5))) == number_token(expected_display)
    except (TypeError, ValueError, OverflowError):
        return False

def parse_cnn_history(payload, target):
    """Return CNN's own composite daily score/rating for the exact UTC date."""
    block = payload.get("fear_and_greed_historical") or {}
    points = block.get("data") or []
    for point in points:
        stamp = point.get("x") or point.get("timestamp")
        if stamp is None:
            continue
        try:
            observed_date = datetime.fromtimestamp(float(stamp) / 1000, timezone.utc).date().isoformat()
        except (TypeError, ValueError, OverflowError):
            continue
        if observed_date == target:
            score = point.get("y", point.get("score"))
            rating = point.get("rating")
            if score is None or not rating:
                return {"status": "OBSERVED_PENDING_FIELD_MAPPING", "date": observed_date}
            return {"status": "PAGE_READ_OK", "date": observed_date,
                    "timestamp_utc": datetime.fromtimestamp(float(stamp) / 1000, timezone.utc).isoformat(),
                    "score": score, "rating": str(rating).strip().lower()}
    return {"status": "TARGET_DATE_NOT_FOUND"}

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
         "read_method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE"}
    started=datetime.now(timezone.utc).isoformat()
    async with sem:
        page=await context.new_page()
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
                            "final_url":endpoint,"read_method":"CNN_OFFICIAL_HISTORICAL_JSON"})
                if api_response.status != 200:
                    out.update({"status":"TOOL_READ_FAILURE","error":f"CNN_GRAPH_DATA_HTTP_{api_response.status}"})
                    return out
                raw=await api_response.body()
                out["raw_response_sha256"]=hashlib.sha256(raw).hexdigest()
                payload=json.loads(raw.decode("utf-8"))
                parsed=parse_cnn_history(payload,target)
                out["page_title"]="CNN Business Fear & Greed historical data"
                if parsed["status"] == "TARGET_DATE_NOT_FOUND":
                    out.update({"status":"TARGET_DATE_NOT_FOUND","error":"CNN_HISTORICAL_SERIES_HAS_NO_TARGET_DATE"})
                    return out
                if parsed["status"] != "PAGE_READ_OK":
                    out.update({"status":"OBSERVED_PENDING_FIELD_MAPPING","error":"CNN_HISTORICAL_RECORD_MISSING_SCORE_OR_RATING"})
                    return out
                score=str(parsed["score"])
                rating=parsed["rating"]
                expected_band=str(row.get("expected_change") or "").strip().lower()
                score_match=cnn_score_matches_display(score,row.get("expected_value"))
                band_match=rating==expected_band
                out.update({
                    "instrument_identity":"CNN Fear & Greed Index",
                    "instrument_identity_status":"VERIFIED",
                    "observed_date":parsed["date"],
                    "source_timestamp_utc":parsed.get("timestamp_utc"),
                    "observed_value":score,
                    "observed_change":rating,
                    "observed_value_field":"fear_and_greed_historical.data[].y",
                    "observed_change_field":"fear_and_greed_historical.data[].rating",
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
                    await page.locator(selector).first.wait_for(state="visible",timeout=min(timeout,5000))
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
            if page_status == "TOOL_READ_FAILURE":
                out["status"]="TOOL_READ_FAILURE"
                out["error"]="SOURCE_PAGE_CHALLENGE_OR_ACCESS_BLOCK; NOT EVIDENCE_OF_SOURCE_NO_DATA"
                return out
            if page_status == "TARGET_DATE_NOT_FOUND":
                out["status"]="TARGET_DATE_NOT_FOUND"
                out["error"]="TARGET_DATE_NOT_PRESENT_ON_SUCCESSFULLY_READ_PAGE"
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
            vm=bool(field_ok and number_token(observed_value)==number_token(row.get("expected_value")))
            cm=bool(field_ok and number_token(observed_change)==number_token(row.get("expected_change")))
            out.update({
                "observed_row_text":candidate,
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
                "field_mapping_status":"VERIFIED" if field_ok else "PENDING_FIELD_HEADER_MAPPING",
            })
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
            out["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
            await page.close()
            await asyncio.sleep(0.5)

async def observe(context,row,target,timeout,sem):
    """SIM-1.4 Stage 2: first read, refresh unresolved rows, then date-query same source system."""
    if row["name"] == "fear_greed":
        return await observe_once(context,row,target,timeout,sem)
    attempts=[]
    original_url=row["source_url"]
    date_query_url=original_url + ("&" if "?" in original_url else "?") + f"end_date={target}&st_date={target}"
    plans=[
        (1, original_url, 9000, 0),
        (2, original_url, 2500, 3),
        (3, date_query_url, 2500, 3),
    ]
    final=None
    for attempt_no,request_url,challenge_wait_ms,delay in plans:
        if delay:
            await asyncio.sleep(delay)
        attempt_row=dict(row)
        attempt_row["request_url"]=request_url
        attempt_timeout=timeout if attempt_no==1 else min(timeout,8000)
        result=await observe_once(context,attempt_row,target,attempt_timeout,sem,challenge_wait_ms)
        attempts.append({
            "round":attempt_no,
            "request_url":request_url,
            "status":result.get("status"),
            "http_status":result.get("http_status"),
            "navigation_http_status":result.get("navigation_http_status"),
            "error":result.get("error"),
            "started_at_utc":result.get("started_at_utc"),
            "finished_at_utc":result.get("finished_at_utc"),
        })
        final=result
        if result.get("status")=="VERIFIED":
            break
    final["source_url"]=original_url
    final["verification_round"]=next((x["round"] for x in attempts if x["status"]=="VERIFIED"),attempts[-1]["round"])
    final["attempt_count"]=len(attempts)
    final["attempt_history"]=attempts
    return final

async def run(a,work,target):
    sem=asyncio.Semaphore(a.concurrency)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        context=await browser.new_context(
            locale="zh-HK",
            timezone_id="Asia/Taipei",
        )
        try:
            tasks=[observe(context,row,target,a.timeout_ms,sem) for row in work]
            observations=await asyncio.gather(*tasks)
        finally:
            await context.close()
            await browser.close()
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
    ap.add_argument("--concurrency",type=int,default=2)
    a=ap.parse_args()
    if not 1<=a.concurrency<=12: raise SystemExit("--concurrency must be between 1 and 12")
    data=json.loads(Path(a.fixture).read_text(encoding="utf-8")); target=data.get("trading_date")
    if data.get("report_date")!=a.report_date or not target: raise SystemExit("Fixture date mismatch")
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
    if len(work)!=44 or any(not x["source_url"] for x in work): raise SystemExit(f"Expected 44 source rows, got {len(work)}")
    observations,counts=asyncio.run(run(a,work,target))
    result={"schema_version":"1.1","report_date":a.report_date,"trading_date":target,
            "method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE_BOUNDED_CONCURRENCY",
            "row_count":44,"concurrency":a.concurrency,"timeout_ms":a.timeout_ms,
            "status_counts":counts,"verified_count":sum(1 for item in observations if item.get("status")=="VERIFIED"),"observations":observations,
            "warning":"Rows are VERIFIED only when the target date, instrument identity, mapped Price/Close and Change % fields, and both numeric values match. HTTP access failures are never treated as missing source data."}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"status_counts":counts,"row_count":len(observations)},ensure_ascii=False))
if __name__=="__main__": main()
