#!/usr/bin/env python3
"""TAC market-data collection for review branch. Fail closed; never relabel stale data."""
import json, re, sys
from datetime import datetime, timezone, date
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

OUT = Path("data/tac_market_snapshot.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; TACMarketCollector/1.0)"}
SESSION = requests.Session()
SESSION.headers.update(UA)
NOW = datetime.now(timezone.utc)
TAIPEI = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
INDEXES = {
    "道瓊工業指數": "^DJI", "S&P 500": "^GSPC",
    "Nasdaq Composite": "^IXIC", "費城半導體指數（SOX）": "^SOX",
    "Russell 2000": "^RUT",
}
def yahoo_chart(symbol, range_="10d", interval="1d"):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + requests.utils.quote(symbol, safe="")
    r = SESSION.get(url, params={"range": range_, "interval": interval}, timeout=(8, 20))
    r.raise_for_status()
    payload = r.json()["chart"]
    if payload.get("error") or not payload.get("result"):
        raise RuntimeError(str(payload.get("error") or "Yahoo chart empty"))
    item = payload["result"][0]
    q = item["indicators"]["quote"][0]
    rows = []
    for i, ts in enumerate(item.get("timestamp") or []):
        d = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        vals = {k: (q.get(k.lower()) or [None] * len(item["timestamp"]))[i] for k in ("Open","High","Low","Close")}
        rows.append({"date": d, **vals})
    return rows
def valid_close_rows(symbol):
    rows = yahoo_chart(symbol)
    valid = [r for r in rows if r.get("Close") is not None]
    if not valid: raise RuntimeError("no close values")
    return valid
def collect_indicator(label, symbols):
    errors=[]
    for symbol in symbols:
        try:
            rows=valid_close_rows(symbol)
            row=rows[-1]
            return {"value": row["Close"], "date": row["date"], "symbol": symbol,
                    "source": "Yahoo Finance chart API", "status": "ok"}
        except Exception as e: errors.append(f"{symbol}: {type(e).__name__}: {e}")
    return {"value": None, "date": None, "source": "Yahoo Finance chart API", "status": "missing", "error": " | ".join(errors)}
def collect_cnn():
    urls = [
      "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/",
      "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    ]
    errors=[]
    for url in urls:
        try:
            r=SESSION.get(url, timeout=(8,20)); r.raise_for_status(); j=r.json()
            fg=j.get("fear_and_greed") or {}
            score=fg.get("score")
            if score is None: raise ValueError("fear_and_greed.score missing")
            stamp=fg.get("timestamp") or fg.get("previous_close")
            return {"value": float(score), "date": str(stamp) if stamp else None,
                    "source": url, "status":"ok", "rating":fg.get("rating")}
        except Exception as e: errors.append(f"{url}: {type(e).__name__}: {e}")
    return {"value":None,"date":None,"source":"CNN Business Fear & Greed endpoint","status":"missing","error":" | ".join(errors)}
def collect_fedwatch():
    # Keep a dated source snapshot even if the site changes its markup. Only mark
    # parsed probabilities valid when explicit named outcomes and percentages exist.
    url="https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"
    try:
        r=SESSION.get(url, timeout=(8,25)); r.raise_for_status()
        html=r.text
        Path("data").mkdir(exist_ok=True)
        Path("data/fedwatch_snapshot.html").write_text(html, encoding="utf-8")
        text=re.sub(r"<[^>]+>", " ", html)
        text=re.sub(r"\\s+", " ", text)
        # No fabricated probability: a parser pass requires a recognizable outcome and percent.
        matches=re.findall(r"(?:Target Rate|No Change|Maintain|25 bps|25 Basis Points)[^%]{0,100}(\\d{1,3}(?:\\.\\d+)?)\\s*%", text, re.I)
        return {"value": matches if matches else None, "date": NOW.isoformat(timespec="seconds"),
                "source":url,"status":"snapshot_saved_parse_pending" if not matches else "parsed_candidate",
                "note":"Saved raw HTML snapshot; verify parsed outcomes against rendered FedWatch table."}
    except Exception as e:
        return {"value":None,"date":None,"source":url,"status":"missing","error":f"{type(e).__name__}: {e}"}
def main():
    result={"schema_version":1,"fetched_at_utc":NOW.isoformat(timespec="seconds"),
            "fetched_at_taipei":TAIPEI,"branch":"tac-test-2026-10-23","indicators":{},"key_levels":{},
            "overall_status":"incomplete"}
    # Indicators: VIX, MOVE, CNN Fear & Greed, CME FedWatch, SOX close.
    result["indicators"]["VIX"]=collect_indicator("VIX",["^VIX"])
    result["indicators"]["MOVE"]=collect_indicator("MOVE",["^MOVE","MOVE"])
    result["indicators"]["CNN Fear & Greed"]=collect_cnn()
    result["indicators"]["CME FedWatch"]=collect_fedwatch()
    result["indicators"]["SOX"]=collect_indicator("SOX",["^SOX"])
    errors=[]
    for name,ticker in INDEXES.items():
        try:
            rows=valid_close_rows(ticker)
            row=rows[-1]
            vals={k:row.get(k) for k in ("Open","High","Low","Close")}
            if any(v is None for v in vals.values()): raise ValueError(f"OHLC missing: {vals}")
            vals={k:float(v) for k,v in vals.items()}
            if vals["High"] < vals["Low"] or not vals["Low"] <= vals["Close"] <= vals["High"]:
                raise ValueError(f"OHLC logic failed: {vals}")
            p=(vals["High"]+vals["Low"]+vals["Close"])/3
            result["key_levels"][name]={"ticker":ticker,"date":row["date"],"source":"Yahoo Finance chart API",
              **vals,"S1":round(2*p-vals["High"],4),"P":round(p,4),"R1":round(2*p-vals["Low"],4),"status":"ok"}
        except Exception as e:
            result["key_levels"][name]={"ticker":ticker,"date":None,"source":"Yahoo Finance chart API",
              "status":"missing","error":f"{type(e).__name__}: {e}"}
            errors.append(f"{name}: {e}")
    # Do not present previous-session closes as the current session: latest date is recorded explicitly.
    indicator_ok=all(v.get("status")=="ok" for k,v in result["indicators"].items() if k!="CME FedWatch")
    keys_ok=all(v.get("status")=="ok" for v in result["key_levels"].values())
    fed_ok=result["indicators"]["CME FedWatch"].get("status")=="parsed_candidate"
    result["overall_status"]="complete_candidate" if indicator_ok and keys_ok and fed_ok else "incomplete"
    result["validation"]={"all_five_indexes_ohlc_ok":keys_ok,"indicators_ok":indicator_ok,
      "fedwatch_probabilities_parsed":fed_ok,"errors":errors}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"fetched_at_taipei":TAIPEI,"overall_status":result["overall_status"],
      "indicators":{k:{"status":v.get("status"),"date":v.get("date"),"value":v.get("value")} for k,v in result["indicators"].items()},
      "key_levels":{k:{"status":v.get("status"),"date":v.get("date"),"close":v.get("Close"),"S1":v.get("S1"),"P":v.get("P"),"R1":v.get("R1")} for k,v in result["key_levels"].items()}},ensure_ascii=False,indent=2))
    if not keys_ok or not indicator_ok or not fed_ok: sys.exit(1)
if __name__=="__main__": main()
