#!/usr/bin/env python3
"""Fetch VIX, MOVE and CNN Fear & Greed with exact source/date validation."""
from __future__ import annotations
import argparse, json, math, re, sys, time
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fetch_tac_fx import parse_date, parse_number, parse_yahoo_chart

INVESTING = {
    "vix": {
        "url":"https://hk.investing.com/indices/volatility-s-p-500-historical-data",
        "identity":("VIX","CBOE Volatility Index"),
        "instrument":"CBOE Volatility Index (VIX)","unit":"index_point","fallback":"^VIX",
    },
    "move": {
        "url":"https://hk.investing.com/indices/ice-bofaml-move-historical-data",
        "identity":("MOVE","ICE BofA MOVE Index","ICE BofAML MOVE Index"),
        "instrument":"ICE BofA MOVE Index","unit":"index_point","fallback":None,
    },
}
CNN_URL="https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_PAGE="https://www.cnn.com/markets/fear-and-greed"

def parse_investing_history(page: str, identity: tuple[str,...], target: date) -> dict:
    soup=BeautifulSoup(page,"html.parser")
    heading=soup.find("h1"); title=heading.get_text(" ",strip=True) if heading else ""
    if not any(x.lower() in title.lower() for x in identity):
        raise ValueError("instrument identity mismatch: "+repr(title))
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows: continue
        headers=[re.sub(r"[\s（）()%％]","",c.get_text(" ",strip=True)).lower() for c in rows[0].find_all(["th","td"])]
        di=next((i for i,h in enumerate(headers) if "日期" in h or h=="date"),None)
        ci=next((i for i,h in enumerate(headers) if "收市" in h or "收盤" in h or h=="close"),None)
        pi=next((i for i,h in enumerate(headers) if "升跌" in h or "change" in h),None)
        if None in (di,ci,pi): continue
        for row in rows[1:]:
            cells=row.find_all(["td","th"])
            if max(di,ci,pi)>=len(cells): continue
            try: day=parse_date(cells[di].get_text(" ",strip=True))
            except ValueError: continue
            if day!=target: continue
            close=parse_number(cells[ci].get_text(" ",strip=True))
            change=parse_number(cells[pi].get_text(" ",strip=True))
            if close<=0: raise ValueError("historical close must be positive")
            return {"close":close,"change_pct":change,"heading":title}
    raise ValueError("exact trading-date row not found: "+target.isoformat())

def parse_cnn_timestamp(value) -> datetime:
    if isinstance(value,(int,float)):
        seconds=float(value)/1000 if value>10_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds,timezone.utc)
    if isinstance(value,str):
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        if parsed.tzinfo is None: raise ValueError("CNN timestamp missing timezone")
        return parsed.astimezone(timezone.utc)
    raise ValueError("CNN timestamp missing or invalid")

def extract_cnn_snapshot(payload: dict) -> dict:
    candidates=[]
    def walk(value):
        if isinstance(value,dict):
            if "score" in value and any(k in value for k in ("timestamp","updated_at","date")):
                candidates.append(value)
            for child in value.values(): walk(child)
        elif isinstance(value,list):
            for child in value: walk(child)
    walk(payload)
    if not candidates: raise ValueError("CNN official response contains no timestamped score")
    # Prefer the top-level current fear_and_greed object when present.
    preferred=payload.get("fear_and_greed") or payload.get("fearAndGreed")
    item=preferred if isinstance(preferred,dict) and "score" in preferred else candidates[0]
    score=float(item["score"])
    if not math.isfinite(score) or not 0<=score<=100: raise ValueError("CNN score outside 0-100")
    timestamp=item.get("timestamp",item.get("updated_at",item.get("date")))
    updated=parse_cnn_timestamp(timestamp)
    rating=str(item.get("rating") or item.get("description") or "").strip()
    return {"score":score,"updated_at":updated,"rating":rating}

def pending(config:dict,reason:str)->dict:
    return {"value":None,"unit":config["unit"],"change":None,"change_unit":"percent",
            "status":"pending_verification","source":None,"fallback_used":False,
            "fallback_reason":None,"notes":"待核實：未取得指定交易日資料。原因："+reason}

def fetch_market_indicator(session,key,config,target,observed):
    primary_error=None
    try:
        response=session.get(config["url"],timeout=(10,30)); response.raise_for_status()
        if len(response.text)<3000: raise ValueError("Investing.com response unexpectedly short")
        parsed=parse_investing_history(response.text,config["identity"],target)
        return {"value":parsed["close"],"unit":config["unit"],"change":parsed["change_pct"],"change_unit":"percent",
                "status":"verified","source":{"name":"Investing.com 香港站","url":config["url"],
                "observed_at":observed,"data_date":target.isoformat(),
                "quote_type":"investing_com_hk_historical_close_pct_change","instrument":config["instrument"]},
                "fallback_used":False,"fallback_reason":None,"notes":"採用指定交易日期的歷史收市值與日漲跌幅。"}
    except Exception as exc: primary_error=str(exc)
    ticker=config.get("fallback")
    if ticker:
        try:
            from datetime import timedelta, time as dtime
            from fetch_tac_fx import parse_yahoo_chart
            start=datetime.combine(target-timedelta(days=7),dtime.min,tzinfo=timezone.utc)
            end=datetime.combine(target+timedelta(days=2),dtime.min,tzinfo=timezone.utc)
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={int(start.timestamp())}&period2={int(end.timestamp())}&interval=1d"
            response=session.get(url,timeout=(10,30)); response.raise_for_status()
            parsed=parse_yahoo_chart(response.json(),ticker,target)
            return {"value":parsed["close"],"unit":config["unit"],"change":parsed["change_pct"],"change_unit":"percent",
                    "status":"verified","source":{"name":"Yahoo Finance","url":f"https://finance.yahoo.com/quote/{ticker}/history/",
                    "observed_at":observed,"data_date":target.isoformat(),"quote_type":"yahoo_chart_daily_close_pct_change",
                    "instrument":config["instrument"]},"fallback_used":True,
                    "fallback_reason":"Investing.com 優先來源失敗："+primary_error,
                    "notes":"備援採用同一交易日歷史收盤列；漲跌幅依當日與前一有效交易日收盤計算。"}
        except Exception as exc:
            return pending(config,"Investing.com: "+primary_error+"；Yahoo: "+str(exc))
    return pending(config,"Investing.com: "+primary_error+"；未找到可確認標的身分的 MOVE 備援，不以 ETF／其他債券指數代替。")

def fetch_cnn(session,target,observed):
    config={"unit":"score"}
    try:
        response=session.get(CNN_URL,timeout=(10,30),headers={"Origin":"https://www.cnn.com","Referer":CNN_PAGE})
        response.raise_for_status()
        parsed=extract_cnn_snapshot(response.json())
        data_day=parsed["updated_at"].astimezone(ZoneInfo("America/New_York")).date()
        if data_day!=target:
            raise ValueError(f"CNN score date mismatch: expected {target}, got {data_day}")
        return {"value":parsed["score"],"unit":"score","change":None,"change_unit":None,"status":"verified",
                "source":{"name":"CNN Business official graphdata endpoint","url":CNN_URL,
                          "observed_at":parsed["updated_at"].isoformat(),"data_date":data_day.isoformat(),
                          "quote_type":"cnn_official_fear_and_greed_score","instrument":"CNN Fear & Greed Index"},
                "fallback_used":False,"fallback_reason":None,
                "notes":"CNN 評級："+(parsed["rating"] or "未提供")+"；採用官方端點實際更新時間，不沿用舊快照。"}
    except Exception as exc:
        return {"value":None,"unit":"score","change":None,"change_unit":None,"status":"pending_verification",
                "source":None,"fallback_used":False,"fallback_reason":None,
                "notes":"CNN 官方頁／資料端點未能取得指定交易日且含時間戳記的分數；原因："+str(exc)}

def build_fragment(target,report,records,observed):
    if set(records)!={"vix","move","cnn_fear_greed"}: raise ValueError("risk indicator field set mismatch")
    return {"fragment_schema_version":1,"dataset":"tac_risk_indicators","report_date":report.isoformat(),
            "trading_date":target.isoformat(),"fetched_at":observed,
            "source_priority":"TAC_WORK_RULES.md §13.2/§21.3: Investing.com HK for VIX/MOVE; CNN official graphdata for Fear & Greed; Yahoo ^VIX fallback only; no ambiguous MOVE substitution.",
            "risk_indicators":records}

def self_test():
    sample="""<html><h1>CBOE Volatility Index (VIX)</h1><table><tr><th>Date</th><th>Close</th><th>Change %</th></tr><tr><td>Oct 30, 2026</td><td>18.20</td><td>-1.25%</td></tr></table></html>"""
    parsed=parse_investing_history(sample,("VIX","CBOE Volatility Index"),date(2026,10,30))
    assert parsed["close"]==18.2 and parsed["change_pct"]==-1.25
    try: parse_investing_history(sample,("MOVE",),date(2026,10,30))
    except ValueError: pass
    else: raise AssertionError("wrong indicator identity must fail closed")
    try: parse_investing_history(sample,("VIX",),date(2026,10,29))
    except ValueError: pass
    else: raise AssertionError("missing exact indicator date must fail closed")
    cnn=extract_cnn_snapshot({"fear_and_greed":{"score":34.5,"rating":"fear","timestamp":"2026-10-30T20:00:00Z"}})
    assert cnn["score"]==34.5 and cnn["rating"]=="fear"
    try: extract_cnn_snapshot({"fear_and_greed":{"score":110,"timestamp":"2026-10-30T20:00:00Z"}})
    except ValueError: pass
    else: raise AssertionError("out-of-range CNN score must fail closed")
    assert INVESTING["move"]["fallback"] is None
    print("PASS: exact-date VIX/MOVE history and instrument identity validation")
    print("PASS: CNN official score, timestamp and 0-100 range validation")
    print("PASS: no unverified MOVE fallback substitution")

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
    for key,config in INVESTING.items():
        records[key]=fetch_market_indicator(session,key,config,target,observed); time.sleep(0.3)
    records["cnn_fear_greed"]=fetch_cnn(session,target,observed)
    fragment=build_fragment(target,report,records,observed)
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    verified=sum(1 for x in records.values() if x["status"]=="verified")
    fallback=sum(1 for x in records.values() if x["fallback_used"])
    print(f"Risk indicators: {verified}/3 verified; {fallback} fallbacks; {3-verified} pending_verification")
    for key,item in records.items(): print(f"{key}: {item['status']} value={item['value']} change={item['change']} fallback={item['fallback_used']}")
    print("Saved "+str(output)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc: print("FAIL: "+str(exc),file=sys.stderr); raise SystemExit(1)
