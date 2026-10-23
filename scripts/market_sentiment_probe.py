#!/usr/bin/env python3
"""Isolated TAC market-sentiment data probe. Does not update homepage, JSON, or schedules."""
import json, re, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
started = datetime.now(timezone.utc).isoformat()
report = {
    "purpose": "isolated market sentiment source test only",
    "started_at_utc": started,
    "captured_at_utc": None,
    "captured_at_taipei": None,
    "sources": {},
    "notes": [
        "Yahoo chart results are a fallback probe, not a replacement for the preferred official source.",
        "CNN Fear & Greed endpoint is undocumented and may change or block automated requests.",
        "CME FedWatch intraday API requires an entitled API ID/OAuth token; public page extraction is diagnostic only.",
        "No report HTML, production JSON, homepage, or existing schedule is modified."
    ]
}

def fetch(url, headers=None, timeout=20):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html, */*", **(headers or {})})
    with urlopen(req, timeout=timeout) as r:
        body = r.read()
        return r.status, r.headers.get("content-type", ""), body

def probe_yahoo(symbol, label):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?range=5d&interval=1d"
    item = {"source": "Yahoo Finance chart API (fallback probe)", "url": url}
    try:
        status, ctype, body = fetch(url, {"Accept": "application/json"})
        data = json.loads(body.decode("utf-8"))
        result = (data.get("chart", {}).get("result") or [None])[0]
        if not result:
            raise ValueError(str(data.get("chart", {}).get("error") or "empty chart result"))
        meta = result.get("meta", {})
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        points = []
        for ts, close in zip(timestamps, closes):
            if close is not None:
                points.append({"timestamp_utc": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                               "date_utc": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                               "close": close})
        if not points:
            raise ValueError("No non-null daily close points returned")
        item.update({"status": "ok", "http_status": status, "symbol": meta.get("symbol", symbol),
                     "currency": meta.get("currency"), "exchange_timezone": meta.get("exchangeTimezoneName"),
                     "latest_daily_close": points[-1], "history": points})
    except Exception as e:
        item.update({"status": "failed", "error": f"{type(e).__name__}: {e}"})
    return item

def probe_cnn():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    item = {"source": "CNN Fear & Greed (undocumented endpoint)", "url": url}
    try:
        status, ctype, body = fetch(url, {"Accept":"application/json", "Origin":"https://www.cnn.com",
            "Referer":"https://www.cnn.com/markets/fear-and-greed"})
        payload = json.loads(body.decode("utf-8"))
        headline = payload.get("fear_and_greed") or payload.get("fearAndGreed") or payload.get("current") or payload
        score = headline.get("score") if isinstance(headline, dict) else None
        rating = headline.get("rating") if isinstance(headline, dict) else None
        timestamp = headline.get("timestamp") if isinstance(headline, dict) else None
        if score is None:
            # Some graphdata responses only expose history; use the last point only if its shape is explicit.
            series = payload.get("fear_and_greed_historical") or payload.get("history") or []
            if isinstance(series, list) and series:
                last = series[-1]
                if isinstance(last, dict):
                    score = last.get("y", last.get("score", last.get("value")))
                    timestamp = last.get("x", last.get("date", last.get("timestamp")))
        if not isinstance(score, (int, float)) or not 0 <= float(score) <= 100:
            raise ValueError("Response received but no validated 0-100 score was found; schema may differ")
        item.update({"status":"ok", "http_status":status, "score":round(float(score),2),
                     "rating":rating, "source_timestamp":timestamp, "payload_keys":list(payload.keys())[:30]})
    except Exception as e:
        item.update({"status":"failed", "error":f"{type(e).__name__}: {e}"})
    return item

def probe_cme_page():
    url = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"
    item = {"source":"CME FedWatch official public page (diagnostic, not authenticated API)", "url":url,
            "official_api_note":"CME intraday REST API requires API ID entitlement and OAuth bearer token."}
    try:
        status, ctype, body = fetch(url, {"Accept":"text/html,application/xhtml+xml"})
        html = body.decode("utf-8", errors="replace")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I|re.S)
        # Detect data hints without claiming the percentages are validated.
        date_strings = sorted(set(re.findall(r"20\\d{2}-\\d{2}-\\d{2}", html)))
        pct_strings = re.findall(r"(?<![\\w.])\\d{1,3}(?:\\.\\d{1,3})?\\s*%", html)
        api_hints = sorted(set(re.findall(r"https?[^\\\"' ]{0,250}(?:fedwatch|quikstrike|forecast|probab)[^\\\"' ]{0,250}", html, re.I)))[:20]
        item.update({"status":"diagnostic_only", "http_status":status, "content_type":ctype,
                     "title":re.sub(r"\\s+"," ",title_match.group(1)).strip() if title_match else None,
                     "html_bytes":len(body), "date_string_samples":date_strings[-20:],
                     "percentage_string_samples":pct_strings[:30], "api_url_hints":api_hints,
                     "validated_meeting_probabilities":False,
                     "reason":"Public HTML retrieval does not prove the displayed meeting probability tree was loaded or current."})
    except Exception as e:
        item.update({"status":"failed", "error":f"{type(e).__name__}: {e}"})
    return item



def probe_vix_cboe():
    url = "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
    item = {"source":"Cboe official VIX historical CSV", "url":url}
    try:
        status, ctype, body = fetch(url, {"Accept":"text/csv"})
        rows = [x.strip().split(",") for x in body.decode("utf-8-sig").splitlines() if x.strip()]
        valid = []
        for r in rows[1:]:
            if len(r) >= 5:
                date_text = r[0].strip()
                try:
                    # Cboe historical CSV commonly uses MM/DD/YYYY.
                    dt = datetime.strptime(date_text, "%m/%d/%Y").date()
                    close = float(r[4])
                    valid.append({"date":dt.isoformat(),"close":close})
                except (ValueError, TypeError):
                    continue
        if not valid: raise ValueError("No valid dated Cboe VIX daily close rows parsed")
        item.update({"status":"ok","http_status":status,"latest_daily_close":valid[-1],
                     "history":valid[-5:],"quote_type":"official daily close"})
    except Exception as e:
        item.update({"status":"failed","error":f"{type(e).__name__}: {e}"})
    return item

def probe_vix_fred():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"
    item = {"source":"FRED VIXCLS daily close (CBOE-sourced fallback)", "url":url}
    try:
        status, ctype, body = fetch(url, {"Accept":"text/csv"})
        rows = [x.strip().split(",") for x in body.decode("utf-8-sig").splitlines() if x.strip()]
        valid = [{"date":r[0], "close":float(r[1])} for r in rows[1:] if len(r)>1 and re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}",r[0]) and r[1] not in (".","")]
        if not valid: raise ValueError("No dated VIX close rows")
        item.update({"status":"ok","http_status":status,"latest_daily_close":valid[-1],
                     "history":valid[-5:],"quote_type":"daily close","note":"FRED can lag the latest trading session; validate session date before report use."})
    except Exception as e:
        item.update({"status":"failed","error":f"{type(e).__name__}: {e}"})
    return item


def probe_tradingview_move():
    url = "https://scanner.tradingview.com/america/scan"
    item = {"source":"TradingView scanner (TVC:MOVE)", "url":"https://tw.tradingview.com/symbols/TVC-MOVE/"}
    payload = json.dumps({
        "symbols":{"tickers":["TVC:MOVE"],"query":{"types":[]}},
        "columns":["close","change","name","description","update_mode","currency","pricescale","type","typespecs"]
    }).encode("utf-8")
    try:
        req = Request(url, data=payload, headers={"User-Agent":UA,"Content-Type":"application/json",
                    "Accept":"application/json","Origin":"https://www.tradingview.com",
                    "Referer":"https://www.tradingview.com/"}, method="POST")
        with urlopen(req, timeout=20) as r:
            body = r.read()
            status = r.status
        raw_text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(raw_text)
        except Exception:
            raise ValueError(f"Non-JSON response HTTP {status}: {raw_text[:500]}")
        rows = data.get("data") or []
        row = next((x for x in rows if x.get("s") == "TVC:MOVE"), rows[0] if rows else None)
        if not row or not isinstance(row.get("d"), list) or row["d"][0] is None:
            raise ValueError(f"No close row for TVC:MOVE; response={raw_text[:1000]}")
        vals = row["d"]
        item.update({"status":"ok","http_status":status,"symbol":row.get("s"),
                     "value":vals[0],"change_percent":vals[1],
                     "name":vals[2],"description":vals[3],"update_mode":vals[4],
                     "currency":vals[5],"price_scale":vals[6],"instrument_type":vals[7],
                     "captured_at_utc":datetime.now(timezone.utc).isoformat(),
                     "quote_type":"TradingView scanner snapshot; session date and official close not independently confirmed",
                     "usable_as_official_daily_close":False})
    except Exception as e:
        item.update({"status":"failed","error":f"{type(e).__name__}: {e}"})
    return item

def probe_move_web():
    urls = [
        "https://www.google.com/finance/quote/MOVE:INDEXNYSEGIS",
        "https://www.investing.com/indices/ice-bofaml-move-historical-data",
        "https://au.investing.com/indices/ice-bofaml-move-historical-data",
    "https://ca.investing.com/indices/ice-bofaml-move-historical-data",
        "https://www.eoddata.com/stockquote/INDEX/MOVE.htm"
    ]
    errors = []
    for url in urls:
        item = {"source":"MOVE public historical page fallback", "url":url}
        try:
            headers = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language":"en-US,en;q=0.9", "Referer":"https://www.investing.com/", "Origin":"https://www.investing.com", "Sec-Fetch-Dest":"document", "Sec-Fetch-Mode":"navigate", "Sec-Fetch-Site":"same-origin"}
            status, ctype, body = fetch(url, headers)
            html = body.decode("utf-8", errors="replace")
            if "google.com/finance" in url:
                candidates = re.findall(r'data-last-price="([0-9]+(?:\.[0-9]+)?)"', html)
                if not candidates:
                    candidates = re.findall(r'<div[^>]*class="[^"]*(?:YMlKec[^"]*fxKbKc|fxKbKc[^"]*YMlKec)[^"]*"[^>]*>\s*([0-9]+(?:\.[0-9]+)?)\s*</div>', html)
                if not candidates:
                    candidates = re.findall(r'<meta[^>]*itemprop="price"[^>]*content="([0-9]+(?:\.[0-9]+)?)"', html, re.I)
                if not candidates:
                    candidates = re.findall(r'"(?:lastPrice|price|close)"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?', html, re.I)
                if candidates:
                    item.update({"status":"ok","http_status":status,"latest_snapshot":{"value":float(candidates[0]),
                                 "captured_at_utc":datetime.now(timezone.utc).isoformat()},
                                 "quote_type":"page snapshot; session date not confirmed",
                                 "validation_note":"Do not label as previous close unless page exposes and validates the session date."})
                    return item
            # Investing.com historical table rows: Date | Price | Open | High | Low | Vol. | Change %.
            if "investing.com/indices/ice-bofaml-move-historical-data" in url:
                inv_rows = []
                for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.I|re.S):
                    cells = [re.sub(r"\\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip()
                             for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.I|re.S)]
                    if len(cells) < 2:
                        continue
                    date_text = cells[0].strip()
                    dt = None
                    for fmt in ("%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
                        try:
                            dt = datetime.strptime(date_text, fmt).date()
                            break
                        except ValueError:
                            pass
                    if dt is None:
                        continue
                    price_text = re.sub(r"[^0-9.\\-]", "", cells[1])
                    try:
                        price = float(price_text)
                    except ValueError:
                        continue
                    if 20 <= price <= 250:
                        inv_rows.append({"date": dt.isoformat(), "close": price})
                if inv_rows:
                    item.update({"status":"ok","http_status":status,"latest_daily_close":inv_rows[0],
                                 "history":inv_rows[:5],"quote_type":"daily close from structured Investing.com historical table",
                                 "validation_note":"Verify the latest session date against an independent source before publishing.",
                                 "attempts_before_success":errors[:]})
                    return item
            # EODData uses structured table rows: Date | Open | High | Low | Close | Volume.
            if "eoddata.com" in url:
                eod_rows = []
                for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.I|re.S):
                    cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip()
                             for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.I|re.S)]
                    if not cells:
                        continue
                    date_match = re.search(r"(\d{1,2}\s+(?:Oct|Sep|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug)\s+\d{2})", cells[0], re.I)
                    if date_match and len(cells) >= 5:
                        numeric_cells = [re.sub(r"[^0-9.\-]", "", x) for x in cells[1:]]
                        try:
                            prices = [float(x) for x in numeric_cells if x and re.fullmatch(r"-?\d+(?:\.\d+)?", x)]
                        except ValueError:
                            continue
                        if len(prices) >= 4:
                            eod_rows.append({"date_text":date_match.group(1),"close":prices[3]})
                if eod_rows:
                    item.update({"status":"ok","http_status":status,"latest_daily_close":eod_rows[0],
                                 "history":eod_rows[:5],"quote_type":"daily close from structured EODData table",
                                 "validation_note":"Confirm parsed row and session date against a second independent source before publishing.",
                                 "attempts_before_success":errors[:]})
                    return item
            plain = re.sub(r"<[^>]+>", " ", html)
            plain = re.sub(r"\s+", " ", plain)
            # Match a dated row and the first numeric field following the date; keep raw evidence for review.
            matches = []
            for m in re.finditer(r"(Oct|Sep|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug)\s+\d{1,2},?\s+20\d{2}", plain):
                tail = plain[m.end():m.end()+100]
                nums = re.findall(r"(?<![\w])\d{2,3}\.\d{2}(?![\w])", tail)
                if nums:
                    matches.append({"date_text":m.group(0),"close":float(nums[0])})
            if not matches:
                # EODData can render a compact table; use ISO-like or abbreviated day rows.
                for m in re.finditer(r"(\d{1,2}\s+(?:Oct|Sep|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug)\s+\d{2})", plain):
                    nums = re.findall(r"(?<![\w])\d{2,3}\.\d{2}(?![\w])", plain[m.end():m.end()+100])
                    if nums: matches.append({"date_text":m.group(0),"close":float(nums[0])})
            if not matches:
                raise ValueError("Page returned but no dated MOVE daily close rows could be parsed")
            item.update({"status":"ok","http_status":status,"latest_daily_close":matches[0],
                         "history":matches[:5],"quote_type":"daily close candidate",
                         "validation_note":"Confirm parsed row and session date against a second independent source before publishing."})
            return item
        except Exception as e:
            errors.append({"url":url,"error":f"{type(e).__name__}: {e}",
                           "response_preview":re.sub(r"\s+"," ",body.decode("utf-8",errors="replace"))[:500] if "body" in locals() else None})
    return {"source":"MOVE public historical page fallback","status":"failed","attempts":errors}


report["sources"]["VIX"] = probe_vix_cboe()
if report["sources"]["VIX"].get("status") != "ok":
    report["sources"]["VIX"]["fallback"] = probe_yahoo("%5EVIX", "VIX")
    if report["sources"]["VIX"]["fallback"].get("status") != "ok":
        report["sources"]["VIX"]["fallback_2"] = probe_vix_fred()
    vix_fb = report["sources"]["VIX"].get("fallback", {})
    if vix_fb.get("status") != "ok":
        vix_fb = report["sources"]["VIX"].get("fallback_2", {})
    if vix_fb.get("status") == "ok":
        report["sources"]["VIX"]["fallback_used"] = True
        report["sources"]["VIX"]["status"] = "ok_via_fallback"
        report["sources"]["VIX"]["latest_daily_close"] = vix_fb["latest_daily_close"]
        report["sources"]["VIX"]["effective_source"] = vix_fb["source"]
report["sources"]["MOVE"] = probe_tradingview_move()
if report["sources"]["MOVE"].get("status") != "ok":
    report["sources"]["MOVE"]["fallback"] = probe_move_web()
    if report["sources"]["MOVE"]["fallback"].get("status") == "ok":
        report["sources"]["MOVE"]["status"] = "ok_via_fallback"
        report["sources"]["MOVE"]["effective_source"] = report["sources"]["MOVE"]["fallback"]["source"]
if report["sources"]["MOVE"].get("status") != "ok":
    report["sources"]["MOVE"]["fallback"] = probe_move_web()
    if report["sources"]["MOVE"]["fallback"].get("status") == "ok":
        report["sources"]["MOVE"]["fallback_used"] = True
        report["sources"]["MOVE"]["status"] = "ok_via_fallback"
        report["sources"]["MOVE"]["latest_daily_close"] = report["sources"]["MOVE"]["fallback"].get("latest_daily_close") or report["sources"]["MOVE"]["fallback"].get("latest_snapshot")
        report["sources"]["MOVE"]["effective_source"] = report["sources"]["MOVE"]["fallback"]["source"]
report["sources"]["CNN_FEAR_GREED"] = probe_cnn()
report["sources"]["CME_FEDWATCH"] = probe_cme_page()
now = datetime.now(timezone.utc)
from zoneinfo import ZoneInfo
report["captured_at_utc"] = now.isoformat()
report["captured_at_taipei"] = now.astimezone(ZoneInfo("Asia/Taipei")).isoformat()
report["summary"] = {k: v.get("status") for k,v in report["sources"].items()}
report["automatically_usable_count"] = sum(1 for k,v in report["sources"].items()
    if v.get("status") in ("ok", "ok_via_fallback") and k != "CME_FEDWATCH")
print(json.dumps(report, ensure_ascii=False, indent=2))
with open("market-sentiment-probe.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
