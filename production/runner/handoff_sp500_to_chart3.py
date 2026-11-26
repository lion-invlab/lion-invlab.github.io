#!/usr/bin/env python3
"""Bridge verified Investing.com S&P 500 cash-index evidence to Chart 3; never fetch quotes."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/".github"/"scripts"))
from append_tac_sp500_daily_increment import append_handoff

def _number(value):
    text=str(value or "").strip().replace(",","").replace("%","").replace("+","").replace("−","-")
    match=re.search(r"-?\d+(?:\.\d+)?",text)
    if not match: raise ValueError(f"Not a numeric S&P 500 value: {value!r}")
    return float(match.group())

def build_payload(data:dict)->dict:
    report_date,trading_date=data.get("report_date"),data.get("trading_date")
    item=(data.get("global_markets") or {}).get("標普500指數") or {}
    source=item.get("source") or {}
    if source.get("verification_status")!="VERIFIED":
        raise ValueError("S&P 500 source verification_status must be VERIFIED")
    if source.get("source_role") not in ("PRIMARY","USER_PROVIDED_SCREENSHOT"):
        raise ValueError("S&P 500 source_role must be PRIMARY or USER_PROVIDED_SCREENSHOT")
    if source.get("instrument_type")!="cash_index":
        raise ValueError("S&P 500 instrument_type must be cash_index")
    if source.get("quote_type")!="cash_index_close":
        raise ValueError("S&P 500 quote_type must be cash_index_close")
    if source.get("data_date")!=trading_date:
        raise ValueError("S&P 500 source data_date must match report trading_date")
    url=str(source.get("url",""))
    if "investing.com" not in url.lower() or "historical-data" not in url:
        raise ValueError("S&P 500 evidence must retain its Investing.com historical-data URL")
    method=str(source.get("read_method") or source.get("evidence_method") or "")
    allowed=("USER_PROVIDED_SCREENSHOT","MIXED_SCREENSHOT_AND_HISTORICAL_PAGE",
             "PLAYWRIGHT_RENDERED_HISTORY_TABLE","CHATGPT_WEB_OPEN_HISTORICAL_PAGE")
    if not any(x in method for x in allowed):
        raise ValueError(f"S&P 500 evidence method is not an approved current-run observation: {method!r}")
    observed_at=source.get("checked_at_tw") or source.get("screenshot_observation_applied_at")
    if not observed_at:
        raise ValueError("S&P 500 actual observation timestamp is required")
    close=_number(source.get("close_value") if source.get("close_value") is not None else item.get("display"))
    display=_number(item.get("display"))
    if round(close,2)!=round(display,2):
        raise ValueError("S&P 500 display does not match verified Close value")
    source_change=source.get("daily_change_percent")
    display_change=_number(item.get("change_display"))
    if source_change is None or round(float(source_change),2)!=round(display_change,2):
        raise ValueError("S&P 500 displayed change does not match verified source row")
    note=str(source.get("note") or "")
    if source.get("source_role")=="USER_PROVIDED_SCREENSHOT":
        note=(note+"; evidence_type=USER_PROVIDED_SCREENSHOT").strip("; ")
    return {"report_date":report_date,"trading_date":trading_date,
            "sp500":{"value":close,"status":"verified","notes":note,
                     "source":{"name":source.get("name"),"url":url,"observed_at":observed_at,
                               "data_date":trading_date,"quote_type":source.get("quote_type"),
                               "instrument":"S&P 500 cash index"}}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True)
    ap.add_argument("--output",default="data/tac-chart3/sp500_daily_increment.jsonl")
    args=ap.parse_args()
    data=json.loads(Path(args.data).read_text(encoding="utf-8"))
    payload=build_payload(data)
    result=append_handoff(payload,Path(args.output))
    print(json.dumps({"status":result["status"],"report_date":payload["report_date"],
        "observation_date":result["record"]["observation_date"],"close":result["record"]["close"],
        "source_name":result["record"]["source_name"],"source_url":result["record"]["source_url"],
        "observed_at":result["record"]["observed_at"],"ledger_sha256":result["ledger_sha256"],
        "output":args.output},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
