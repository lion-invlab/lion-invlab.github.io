#!/usr/bin/env python3
"""Bridge verified SIM-1.4 S&P 500 fixture data to Chart 3; never fetches quotes."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
from append_tac_sp500_daily_increment import append_handoff

def build_payload(data: dict) -> dict:
    report_date, trading_date = data.get("report_date"), data.get("trading_date")
    item = (data.get("global_markets") or {}).get("標普500指數") or {}
    source = item.get("source") or {}
    if source.get("verification_status") != "VERIFIED":
        raise ValueError("S&P 500 source verification_status must be VERIFIED")
    if source.get("source_role") != "PRIMARY":
        raise ValueError("S&P 500 source_role must be PRIMARY")
    if source.get("instrument_type") != "cash_index":
        raise ValueError("S&P 500 instrument_type must be cash_index")
    if source.get("quote_type") != "cash_index_close":
        raise ValueError("S&P 500 quote_type must be cash_index_close")
    if source.get("data_date") != trading_date:
        raise ValueError("S&P 500 source data_date must match report trading_date")
    url = str(source.get("url", ""))
    if "investing.com" not in url.lower() or "historical-data" not in url:
        raise ValueError("S&P 500 primary source must be an Investing.com historical-data page")
    if not source.get("evidence_method") or "historical data table" not in source["evidence_method"].lower():
        raise ValueError("S&P 500 historical-table evidence method is required")
    observed_at = source.get("checked_at_tw")
    if not observed_at:
        raise ValueError("S&P 500 checked_at_tw is required for actual observation timestamp")
    close = float(str(source.get("close_value") or item.get("display") or "").replace(",", ""))
    display = float(str(item.get("display", "")).replace(",", ""))
    if round(close, 2) != round(display, 2):
        raise ValueError("S&P 500 display does not match verified Close value")
    if source.get("daily_change_percent") != item.get("change_display"):
        raise ValueError("S&P 500 displayed change does not match verified source row")
    return {"report_date": report_date, "trading_date": trading_date,
            "sp500": {"value": close, "status": "verified", "notes": source.get("note", ""),
                      "source": {"name": source.get("name"), "url": url,
                                 "observed_at": observed_at, "data_date": trading_date,
                                 "quote_type": source.get("quote_type"),
                                 "instrument": "S&P 500 cash index"}}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", default="simulation-lab/output/chart3-handoff/sp500_daily_increment.jsonl")
    args=ap.parse_args()
    data=json.loads(Path(args.data).read_text(encoding="utf-8"))
    payload=build_payload(data)
    result=append_handoff(payload, Path(args.output))
    print(json.dumps({"status":result["status"],"report_date":payload["report_date"],
        "observation_date":result["record"]["observation_date"],"close":result["record"]["close"],
        "source_name":result["record"]["source_name"],"source_url":result["record"]["source_url"],
        "observed_at":result["record"]["observed_at"],"ledger_sha256":result["ledger_sha256"],
        "output":args.output},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
