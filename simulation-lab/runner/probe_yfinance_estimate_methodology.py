#!/usr/bin/env python3
"""Probe Yahoo EPS methodology and compare its default consensus with the TAC capture."""
from __future__ import annotations
import argparse, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf

def clean(v):
    if isinstance(v, dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)): return [clean(x) for x in v]
    if hasattr(v,"item"):
        try: return clean(v.item())
        except Exception: pass
    if isinstance(v,float) and not math.isfinite(v): return None
    return v

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--capture",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--tickers",default="BIDU,NVDA,WMT")
    a=p.parse_args()
    capture=json.loads(Path(a.capture).read_text(encoding="utf-8"))
    by_ticker={x["ticker"]:x for x in capture["entries"]}
    rows=[]
    for symbol in [x.strip().upper() for x in a.tickers.split(",") if x.strip()]:
        observed=datetime.now(timezone.utc).isoformat()
        row={"ticker":symbol,"observed_at":observed,"source_url":f"https://finance.yahoo.com/quote/{symbol}/analysis/"}
        try:
            t=yf.Ticker(symbol)
            eps=clean(t.get_earnings_estimate(as_dict=True))
            rev=clean(t.get_revenue_estimate(as_dict=True))
            qeps=eps.get("0q",{}) if isinstance(eps,dict) else {}
            qrev=rev.get("0q",{}) if isinstance(rev,dict) else {}
            captured=by_ticker.get(symbol,{})
            captured_eps=captured.get("eps",{}).get("estimate")
            captured_rev=captured.get("revenue",{}).get("estimate")
            eps_avg=qeps.get("avg")
            rev_avg=qrev.get("avg")
            eps_match=(eps_avg is not None and captured_eps is not None and abs(float(eps_avg)-float(captured_eps))<=max(1e-8,abs(float(captured_eps))*1e-8))
            rev_match=(rev_avg is not None and captured_rev is not None and abs(float(rev_avg)-float(captured_rev))<=max(1e-4,abs(float(captured_rev))*1e-8))
            row.update({"status":"ok","eps_0q":qeps,"revenue_0q":qrev,"eps_matches_captured_value":eps_match,"revenue_matches_captured_value":rev_match,"eps_methodology":qeps.get("methodology"),"raw_response":{"earnings_estimate":eps,"revenue_estimate":rev}})
            raw=json.dumps(row["raw_response"],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
            row["raw_response_sha256"]=hashlib.sha256(raw).hexdigest()
        except Exception as exc:
            row.update({"status":"error","error":f"{type(exc).__name__}: {exc}"})
        rows.append(row)
    result={"schema_version":"tac-yfinance-methodology-probe-v1","captured_at":datetime.now(timezone.utc).isoformat(),"branch_scope":"simulation/tac-process-lab-2026-11-06","source":"Yahoo Finance via yfinance; TAC observation only; no vendor data_as_of inferred","records":rows,"counts":{"requested":len(rows),"ok":sum(x["status"]=="ok" for x in rows),"eps_methodology_present":sum(bool(x.get("eps_methodology")) for x in rows),"eps_matches":sum(x.get("eps_matches_captured_value") is True for x in rows),"revenue_matches":sum(x.get("revenue_matches_captured_value") is True for x in rows)}}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["counts"],ensure_ascii=False))
if __name__=="__main__": main()
