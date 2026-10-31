#!/usr/bin/env python3
"""Fetch the six fixed TAC FX indicators with exact-date source validation.

Investing.com is primary. Yahoo Finance is a dated fallback for the five currency
pairs only; DXY never falls back to DX futures because that is a different instrument.
"""
from __future__ import annotations
import argparse, json, math, re, sys, time
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

FX = {
    "dxy": {
        "url": "https://www.investing.com/indices/usdollar-historical-data",
        "identity": ("US Dollar Index", "US Dollar Currency Index"),
        "unit": "index_point", "instrument": "DXY spot/CFD index",
        "fallback": None,
    },
    "usd_twd": {
        "url": "https://hk.investing.com/currencies/usd-twd-historical-data",
        "identity": ("USD/TWD", "US Dollar Taiwan Dollar"),
        "unit": "USD/TWD", "instrument": "USD/TWD",
        "fallback": "TWD=X",
    },
    "eur_usd": {
        "url": "https://hk.investing.com/currencies/eur-usd-historical-data",
        "identity": ("EUR/USD", "Euro US Dollar"),
        "unit": "EUR/USD", "instrument": "EUR/USD",
        "fallback": "EURUSD=X",
    },
    "gbp_usd": {
        "url": "https://hk.investing.com/currencies/gbp-usd-historical-data",
        "identity": ("GBP/USD", "British Pound US Dollar"),
        "unit": "GBP/USD", "instrument": "GBP/USD",
        "fallback": "GBPUSD=X",
    },
    "aud_usd": {
        "url": "https://hk.investing.com/currencies/aud-usd-historical-data",
        "identity": ("AUD/USD", "Australian Dollar US Dollar"),
        "unit": "AUD/USD", "instrument": "AUD/USD",
        "fallback": "AUDUSD=X",
    },
    "usd_jpy": {
        "url": "https://hk.investing.com/currencies/usd-jpy-historical-data",
        "identity": ("USD/JPY", "US Dollar Japanese Yen"),
        "unit": "USD/JPY", "instrument": "USD/JPY",
        "fallback": "JPY=X",
    },
}

def parse_number(raw: str) -> float:
    value=(raw or "").strip().replace(",","").replace("%","")
    value=value.replace("−","-").replace("＋","+").replace("－","-")
    if value in {"","-","—","–","N/A","NA"}: raise ValueError("missing numeric cell")
    number=float(value)
    if not math.isfinite(number): raise ValueError("non-finite numeric cell")
    return number

def parse_date(raw: str) -> date:
    value=" ".join((raw or "").split())
    m=re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",value)
    if m: return date(*(int(x) for x in m.groups()))
    m=re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",value)
    if m: return date(*(int(x) for x in m.groups()))
    for fmt in ("%d/%m/%Y","%b %d, %Y","%B %d, %Y"):
        try: return datetime.strptime(value,fmt).date()
        except ValueError: pass
    raise ValueError("unrecognized historical date: "+value)

def parse_investing_history(page: str, identity: tuple[str,...], target: date) -> dict:
    soup=BeautifulSoup(page,"html.parser")
    heading=soup.find("h1")
    title=heading.get_text(" ",strip=True) if heading else ""
    if not any(token.lower() in title.lower() for token in identity):
        raise ValueError("instrument identity mismatch: "+repr(title))
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows: continue
        headers=[re.sub(r"[\s（）()%％]","",c.get_text(" ",strip=True)).lower() for c in rows[0].find_all(["th","td"])]
        date_i=next((i for i,h in enumerate(headers) if "日期" in h or h=="date"),None)
        close_i=next((i for i,h in enumerate(headers) if "收市" in h or "收盤" in h or h=="close"),None)
        change_i=next((i for i,h in enumerate(headers) if "升跌" in h or "change" in h),None)
        if None in (date_i,close_i,change_i): continue
        for row in rows[1:]:
            cells=row.find_all(["td","th"])
            if max(date_i,close_i,change_i)>=len(cells): continue
            try: row_day=parse_date(cells[date_i].get_text(" ",strip=True))
            except ValueError: continue
            if row_day!=target: continue
            close=parse_number(cells[close_i].get_text(" ",strip=True))
            change=parse_number(cells[change_i].get_text(" ",strip=True))
            if close<=0: raise ValueError("historical close must be positive")
            return {"close":close,"change_pct":change,"heading":title}
    raise ValueError("exact trading-date row not found: "+target.isoformat())

def parse_yahoo_chart(payload: dict, ticker: str, target: date) -> dict:
    chart=payload.get("chart",{})
    if chart.get("error"): raise ValueError("Yahoo chart error: "+str(chart["error"]))
    results=chart.get("result") or []
    if len(results)!=1: raise ValueError("Yahoo chart result missing or ambiguous")
    result=results[0]; meta=result.get("meta") or {}
    if meta.get("symbol","").upper()!=ticker.upper():
        raise ValueError("Yahoo ticker identity mismatch")
    tz=ZoneInfo(meta.get("exchangeTimezoneName") or "UTC")
    timestamps=result.get("timestamp") or []
    quote=((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes=quote.get("close") or []
    points=[]
    for ts,close in zip(timestamps,closes):
        if close is None: continue
        day=datetime.fromtimestamp(ts,tz).date()
        points.append((day,float(close)))
    exact=[(i,v) for i,(day,v) in enumerate(points) if day==target]
    if len(exact)!=1: raise ValueError("Yahoo exact-date daily close missing or duplicated")
    index,close=exact[0]
    prior=[v for day,v in points[:index] if v>0]
    if not prior: raise ValueError("Yahoo previous close unavailable for percentage change")
    previous=prior[-1]
    if close<=0: raise ValueError("Yahoo close must be positive")
    return {"close":close,"change_pct":round((close/previous-1)*100,2)}

def pending(config: dict, reason: str) -> dict:
    return {"value":None,"unit":config["unit"],"change":None,"change_unit":"percent",
            "status":"pending_verification","source":None,"fallback_used":False,
            "fallback_reason":None,"notes":"待核實：未取得指定日期且可確認標的的報價。原因："+reason}

def fetch_one(session: requests.Session, key: str, config: dict, target: date, report: date, observed: str) -> dict:
    primary_error=None
    try:
        response=session.get(config["url"],timeout=(10,30)); response.raise_for_status()
        if len(response.text)<3000: raise ValueError("Investing.com response unexpectedly short")
        parsed=parse_investing_history(response.text,config["identity"],target)
        return {"value":parsed["close"],"unit":config["unit"],"change":parsed["change_pct"],
                "change_unit":"percent","status":"verified",
                "source":{"name":"Investing.com 香港站" if "hk.investing.com" in config["url"] else "Investing.com",
                          "url":config["url"],"observed_at":observed,"data_date":target.isoformat(),
                          "quote_type":"investing_com_historical_close_pct_change","instrument":config["instrument"]},
                "fallback_used":False,"fallback_reason":None,
                "notes":"採用完全符合指定交易日期的歷史收市價及日漲跌幅。"}
    except Exception as exc:
        primary_error=str(exc)
    ticker=config.get("fallback")
    if ticker:
        try:
            start=datetime.combine(target-timedelta(days=7),dtime.min,tzinfo=timezone.utc)
            end=datetime.combine(target+timedelta(days=2),dtime.min,tzinfo=timezone.utc)
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={int(start.timestamp())}&period2={int(end.timestamp())}&interval=1d"
            response=session.get(url,timeout=(10,30)); response.raise_for_status()
            parsed=parse_yahoo_chart(response.json(),ticker,target)
            return {"value":parsed["close"],"unit":config["unit"],"change":parsed["change_pct"],
                    "change_unit":"percent","status":"verified",
                    "source":{"name":"Yahoo Finance","url":f"https://finance.yahoo.com/quote/{ticker}/history/",
                              "observed_at":observed,"data_date":target.isoformat(),
                              "quote_type":"yahoo_chart_daily_close_pct_change","instrument":config["instrument"]},
                    "fallback_used":True,"fallback_reason":"Investing.com primary source unavailable or failed exact-date validation: "+primary_error,
                    "notes":"備援採用 Yahoo Finance 同一交易日收盤列；漲跌幅依當日收盤與前一有效交易日收盤計算。"}
        except Exception as fallback_exc:
            return pending(config,"Investing.com: "+primary_error+"；Yahoo Finance: "+str(fallback_exc))
    return pending(config,"Investing.com: "+primary_error+"；DXY 不以 DX 期貨替代現貨／CFD 指數。")

def build_fragment(target: date, report: date, records: dict, observed: str) -> dict:
    if set(records)!=set(FX): raise ValueError("FX field set mismatch")
    return {"fragment_schema_version":1,"dataset":"tac_fx","report_date":report.isoformat(),
            "trading_date":target.isoformat(),"fetched_at":observed,
            "source_priority":"TAC_WORK_RULES.md §13.2/§21.4: Investing.com primary; Yahoo dated fallback for FX pairs only; no DX futures substitution for DXY.",
            "fx":records}

def self_test():
    html="""<html><h1>美元兌新台幣 (USD/TWD)</h1><table><tr><th>日期</th><th>收市</th><th>升跌（%）</th></tr><tr><td>2026年10月30日</td><td>31.2500</td><td>+0.12%</td></tr></table></html>"""
    parsed=parse_investing_history(html,("USD/TWD","US Dollar Taiwan Dollar"),date(2026,10,30))
    assert parsed["close"]==31.25 and parsed["change_pct"]==0.12
    try: parse_investing_history(html,("EUR/USD",),date(2026,10,30))
    except ValueError: pass
    else: raise AssertionError("wrong FX instrument must fail closed")
    try: parse_investing_history(html,("USD/TWD",),date(2026,10,29))
    except ValueError: pass
    else: raise AssertionError("missing exact FX date must fail closed")
    payload={"chart":{"result":[{"meta":{"symbol":"EURUSD=X","exchangeTimezoneName":"America/New_York"},"timestamp":[1793312400,1793398800],"indicators":{"quote":[{"close":[1.16,1.17]}]}}],"error":None}}
    # Use the timestamps' actual exchange-local dates to avoid hard-coded UTC assumptions.
    tz=ZoneInfo("America/New_York")
    target=datetime.fromtimestamp(1793398800,tz).date()
    yahoo=parse_yahoo_chart(payload,"EURUSD=X",target)
    assert yahoo["close"]==1.17 and yahoo["change_pct"]>0
    assert FX["dxy"]["fallback"] is None
    assert len(FX)==6 and len({x["url"] for x in FX.values()})==6
    print("PASS: six fixed FX mappings and unique primary URLs")
    print("PASS: Investing.com exact-date history, identity and close/change parsing")
    print("PASS: Yahoo fallback computes same-date percentage change from previous close")
    print("PASS: DXY never substitutes DX futures")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--trading-date"); parser.add_argument("--report-date")
    parser.add_argument("--output"); parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test: self_test(); return 0
    if not all((args.trading_date,args.report_date,args.output)):
        parser.error("--trading-date, --report-date and --output are required")
    target=date.fromisoformat(args.trading_date); report=date.fromisoformat(args.report_date)
    observed=datetime.now(timezone.utc).isoformat()
    retry=Retry(total=3,connect=3,read=3,backoff_factor=1,status_forcelist=(429,500,502,503,504),allowed_methods=frozenset(["GET"]))
    session=requests.Session(); session.mount("https://",HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent":"Mozilla/5.0 (compatible; TAC-Investment-Report/1.0)","Accept-Language":"zh-HK,zh;q=0.9,en;q=0.8"})
    records={}
    for key,config in FX.items():
        records[key]=fetch_one(session,key,config,target,report,observed); time.sleep(0.35)
    fragment=build_fragment(target,report,records,observed)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    verified=sum(1 for x in records.values() if x["status"]=="verified")
    fallback=sum(1 for x in records.values() if x["fallback_used"])
    print(f"FX: {verified}/6 verified; {fallback} Yahoo fallbacks; {6-verified} pending_verification")
    for key,item in records.items(): print(f"{key}: {item['status']} value={item['value']} change={item['change']} fallback={item['fallback_used']}")
    print("Saved "+str(output)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc: print("FAIL: "+str(exc),file=sys.stderr); raise SystemExit(1)
