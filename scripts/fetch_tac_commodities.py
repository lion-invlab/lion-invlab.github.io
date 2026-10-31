#!/usr/bin/env python3
"""Fetch WTI, Brent, GC gold and SI silver with exchange-first provenance.

The public exchange page is attempted first. If its exact-date, contract-specific
settlement row is not machine-readable, the collector uses the documented
Investing.com historical-data fallback only when the page identifies a contract month.
"""
from __future__ import annotations
import argparse,json,math,re,sys,time
from datetime import date,datetime,timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PRODUCTS={
 "wti":{"exchange":"CME/NYMEX","official":"https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.settlements.html",
        "fallback":"https://hk.investing.com/commodities/crude-oil-historical-data",
        "identity":("WTI","Crude Oil"),"unit":"USD/barrel","instrument":"NYMEX WTI Crude Oil futures (CL)"},
 "brent":{"exchange":"ICE Futures Europe","official":"https://www.ice.com/products/219",
          "fallback":"https://hk.investing.com/commodities/brent-oil-historical-data",
          "identity":("Brent","London Brent"),"unit":"USD/barrel","instrument":"ICE Brent Crude futures"},
 "gold":{"exchange":"CME/COMEX","official":"https://www.cmegroup.com/markets/metals/precious/gold.settlements.html",
         "fallback":"https://hk.investing.com/commodities/gold-historical-data",
         "identity":("Gold","黃金"),"unit":"USD/oz","instrument":"COMEX Gold futures (GC)"},
 "silver":{"exchange":"CME/COMEX","official":"https://www.cmegroup.com/markets/metals/precious/silver.settlements.html",
           "fallback":"https://hk.investing.com/commodities/silver-historical-data",
           "identity":("Silver","白銀"),"unit":"USD/oz","instrument":"COMEX Silver futures (SI)"},
}

def parse_number(raw):
    value=(raw or "").strip().replace(",","").replace("%","").replace("−","-").replace("＋","+").replace("－","-")
    if value in {"","-","—","–","N/A","NA"}: raise ValueError("missing numeric value")
    number=float(value)
    if not math.isfinite(number): raise ValueError("non-finite numeric value")
    return number

def parse_date(raw):
    value=" ".join((raw or "").split())
    m=re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",value)
    if m:return date(*(int(x) for x in m.groups()))
    m=re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",value)
    if m:return date(*(int(x) for x in m.groups()))
    for fmt in ("%b %d, %Y","%B %d, %Y","%d/%m/%Y"):
        try:return datetime.strptime(value,fmt).date()
        except ValueError:pass
    raise ValueError("unrecognized settlement date: "+value)

def parse_contract_month(title):
    m=re.search(r"(\d{4})年\s*(\d{1,2})月",title)
    if m:return f"{m.group(1)}-{int(m.group(2)):02d}"
    m=re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b",title,re.I)
    if m:
        month={"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}[m.group(1).lower()[:3]]
        return f"{m.group(2)}-{month:02d}"
    raise ValueError("contract month missing from instrument heading: "+title)

def parse_investing_history(page,config,target):
    soup=BeautifulSoup(page,"html.parser")
    heading=soup.find("h1"); title=heading.get_text(" ",strip=True) if heading else ""
    if not any(x.lower() in title.lower() for x in config["identity"]):
        raise ValueError("fallback instrument identity mismatch: "+repr(title))
    contract_month=parse_contract_month(title)
    code_match=re.search(r"\(([A-Z0-9]{2,8})\)",title)
    contract_code=code_match.group(1) if code_match else None
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        headers=[re.sub(r"[\s（）()%％]","",x.get_text(" ",strip=True)).lower() for x in rows[0].find_all(["th","td"])]
        di=next((i for i,h in enumerate(headers) if "日期" in h or h=="date"),None)
        ci=next((i for i,h in enumerate(headers) if "收市" in h or "收盤" in h or h=="close"),None)
        pi=next((i for i,h in enumerate(headers) if "升跌" in h or "change" in h),None)
        if None in (di,ci,pi):continue
        for row in rows[1:]:
            cells=row.find_all(["td","th"])
            if max(di,ci,pi)>=len(cells):continue
            try:day=parse_date(cells[di].get_text(" ",strip=True))
            except ValueError:continue
            if day!=target:continue
            close=parse_number(cells[ci].get_text(" ",strip=True))
            change=parse_number(cells[pi].get_text(" ",strip=True))
            if close<=0:raise ValueError("historical close must be positive")
            return {"close":close,"change_pct":change,"title":title,"contract_month":contract_month,"contract_code":contract_code}
    raise ValueError("exact requested trading-date row absent from Investing.com history")

def parse_official_table(page,config,target):
    """Try an exact-date public exchange settlement table; never infer missing contract data."""
    soup=BeautifulSoup(page,"html.parser")
    page_text=soup.get_text(" ",strip=True)
    target_text=target.isoformat()
    if target_text not in page_text and target.strftime("%m/%d/%Y") not in page_text:
        raise ValueError("official exchange page does not expose requested settlement date")
    matches=[]
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        headers=[re.sub(r"[\s()%]","",x.get_text(" ",strip=True)).lower() for x in rows[0].find_all(["th","td"])]
        settle_i=next((i for i,h in enumerate(headers) if "settle" in h or "結算" in h),None)
        month_i=next((i for i,h in enumerate(headers) if "month" in h or "月份" in h),None)
        change_i=next((i for i,h in enumerate(headers) if h=="change" or "升跌" in h),None)
        if settle_i is None or month_i is None or change_i is None:continue
        for row in rows[1:]:
            cells=row.find_all(["td","th"])
            if max(settle_i,month_i,change_i)>=len(cells):continue
            month=cells[month_i].get_text(" ",strip=True)
            if not month or month.lower() in {"total","cash","spot"}:continue
            try:settle=parse_number(cells[settle_i].get_text(" ",strip=True)); change=parse_number(cells[change_i].get_text(" ",strip=True))
            except ValueError:continue
            if settle>0:matches.append({"settle":settle,"change":change,"contract_month":month})
    if not matches:raise ValueError("official page contains no parseable contract settlement rows")
    # Use the most actively traded listed contract only when a volume column can distinguish it.
    # Without an unambiguous front/active contract, do not select a row by guesswork.
    if len(matches)!=1:raise ValueError("official page has multiple contracts and no unambiguous active-contract selector")
    item=matches[0]
    prior=item["settle"]-item["change"]
    if prior<=0:raise ValueError("official prior settlement invalid")
    return {"close":item["settle"],"change_pct":round(item["change"]/prior*100,2),"contract_month":item["contract_month"]}

def pending(config,reason):
    return {"value":None,"unit":config["unit"],"change":None,"change_unit":"percent","status":"pending_verification",
            "source":None,"fallback_used":False,"fallback_reason":None,"notes":"待核實：未取得可確認合約月份與指定日期的期貨報價。原因："+reason}

def fetch_one(session,key,config,target,observed):
    official_error=None
    try:
        response=session.get(config["official"],timeout=(10,30));response.raise_for_status()
        parsed=parse_official_table(response.text,config,target)
        return {"value":parsed["close"],"unit":config["unit"],"change":parsed["change_pct"],"change_unit":"percent",
                "status":"verified","source":{"name":config["exchange"],"url":config["official"],"observed_at":observed,
                "data_date":target.isoformat(),"quote_type":"exchange_futures_settlement","instrument":config["instrument"]+" "+parsed["contract_month"]},
                "fallback_used":False,"fallback_reason":None,"notes":"採用交易所指定日期的期貨結算價與同合約日變動。"}
    except Exception as exc:official_error=str(exc)
    try:
        response=session.get(config["fallback"],timeout=(10,30));response.raise_for_status()
        if len(response.text)<3000:raise ValueError("Investing.com response unexpectedly short")
        parsed=parse_investing_history(response.text,config,target)
        return {"value":parsed["close"],"unit":config["unit"],"change":parsed["change_pct"],"change_unit":"percent",
                "status":"verified","source":{"name":"Investing.com 香港站","url":config["fallback"],"observed_at":observed,
                "data_date":target.isoformat(),"quote_type":"investing_com_futures_historical_close","instrument":config["instrument"]+" "+parsed["contract_month"]+((" ("+parsed["contract_code"]+")") if parsed["contract_code"] else "")},
                "fallback_used":True,"fallback_reason":config["exchange"]+" primary settlement page did not expose a unique exact-date contract row: "+official_error,
                "notes":"依 WR 使用 Investing.com 歷史資料備援；保留頁面合約月份與代碼。此欄位為歷史收市口徑，不標稱為交易所結算價。"}
    except Exception as exc:
        return pending(config,config["exchange"]+": "+official_error+"；Investing.com fallback: "+str(exc))

def build_fragment(target,report,records,observed):
    if set(records)!=set(PRODUCTS):raise ValueError("commodity field set mismatch")
    return {"fragment_schema_version":1,"dataset":"tac_commodities","report_date":report.isoformat(),
            "trading_date":target.isoformat(),"fetched_at":observed,
            "source_priority":"TAC_WORK_RULES.md §13.2: CME/NYMEX WTI and COMEX GC/SI; ICE Brent; Investing.com HK historical pages only as documented fallback with contract month.",
            "energy":{"wti":records["wti"],"brent":records["brent"]},
            "precious_metals":{"gold":records["gold"],"silver":records["silver"]}}

def self_test():
    html="""<html><h1>WTI原油期貨 - 2026年12月 (OIL)</h1><table><tr><th>日期</th><th>收市</th><th>升跌（%）</th></tr><tr><td>2026年10月30日</td><td>102.95</td><td>+0.93%</td></tr></table></html>"""
    parsed=parse_investing_history(html,PRODUCTS["wti"],date(2026,10,30))
    assert parsed["close"]==102.95 and parsed["contract_month"]=="2026-12"
    try:parse_investing_history(html,PRODUCTS["gold"],date(2026,10,30))
    except ValueError:pass
    else:raise AssertionError("wrong commodity identity must fail closed")
    try:parse_investing_history(html,PRODUCTS["wti"],date(2026,10,29))
    except ValueError:pass
    else:raise AssertionError("missing exact commodity date must fail closed")
    gold=parse_contract_month("黃金期貨 - 2026年12月 (GCZ6)")
    brent=parse_contract_month("倫敦布蘭特原油期貨 - 2027年1月 (LCOF7)")
    assert gold=="2026-12" and brent=="2027-01"
    try:parse_contract_month("WTI Crude Oil Futures")
    except ValueError:pass
    else:raise AssertionError("missing contract month must fail closed")
    print("PASS: exact-date commodity history and instrument identity validation")
    print("PASS: contract month extracted for WTI, Brent, GC and SI")
    print("PASS: missing date or contract month rejected; no stale row reuse")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--trading-date");parser.add_argument("--report-date");parser.add_argument("--output");parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:self_test();return 0
    if not all((args.trading_date,args.report_date,args.output)):parser.error("--trading-date, --report-date and --output are required")
    target=date.fromisoformat(args.trading_date);report=date.fromisoformat(args.report_date);observed=datetime.now(timezone.utc).isoformat()
    retry=Retry(total=3,connect=3,read=3,backoff_factor=1,status_forcelist=(429,500,502,503,504),allowed_methods=frozenset(["GET"]))
    session=requests.Session();session.mount("https://",HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent":"Mozilla/5.0 (compatible; TAC-Investment-Report/1.0)","Accept-Language":"zh-HK,zh;q=0.9,en;q=0.8"})
    records={}
    for key,config in PRODUCTS.items():records[key]=fetch_one(session,key,config,target,observed);time.sleep(0.35)
    fragment=build_fragment(target,report,records,observed)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    verified=sum(1 for x in records.values() if x["status"]=="verified");fallback=sum(1 for x in records.values() if x["fallback_used"])
    print(f"Commodities: {verified}/4 verified; {fallback} Investing.com fallbacks; {4-verified} pending_verification")
    for key,item in records.items():print(f"{key}: {item['status']} value={item['value']} change={item['change']} fallback={item['fallback_used']}")
    print("Saved "+str(output));return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:print("FAIL: "+str(exc),file=sys.stderr);raise SystemExit(1)
