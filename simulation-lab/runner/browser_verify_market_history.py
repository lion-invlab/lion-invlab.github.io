#!/usr/bin/env python3
"""Browser-based observation of the 44 configured historical market pages.
Run on a date-matched fixture; unresolved rows remain pending, never auto-promoted.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

def number_token(value):
    s=str(value or "").replace(",","").replace("\u2212","-").replace("+","").strip()
    m=re.search(r"-?\d+(?:\.\d+)?",s)
    return None if not m else f"{float(m.group()):.8f}".rstrip("0").rstrip(".")

def date_in_row(text, target):
    d=datetime.strptime(target,"%Y-%m-%d")
    forms=[target,d.strftime("%b %d, %Y"),d.strftime("%B %d, %Y"),
           d.strftime("%d/%m/%Y"),d.strftime("%m/%d/%Y"),
           d.strftime("%d %b %Y"),d.strftime("%b %d, %y")]
    return any(x.lower() in text.lower() for x in forms)

def observe(browser,row,target,timeout):
    page=browser.new_page()
    page.set_default_timeout(timeout)
    out={"name":row["name"],"group":row["group"],"source_url":row["source_url"],
         "instrument_identity":row["name"],"target_date":target,
         "quote_type":row.get("quote_type"),"read_method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE"}
    try:
        response=page.goto(row["source_url"],wait_until="domcontentloaded",timeout=timeout)
        out["http_status"]=response.status if response else None
        try: page.locator("table tbody tr").first.wait_for(state="visible",timeout=timeout)
        except Exception: pass
        out["page_title"]=page.title()
        out["final_url"]=page.url
        rows=page.locator("table tbody tr").all_inner_texts()
        matches=[x.strip() for x in rows if date_in_row(x,target)]
        out["rendered_table_row_count"]=len(rows)
        out["target_date_rows"]=matches[:3]
        if not matches:
            out["status"]="SOURCE_NO_DATA" if rows else "TOOL_READ_FAILURE"
            out["error"]="TARGET_DATE_ROW_NOT_FOUND" if rows else "NO_RENDERED_HISTORY_ROWS"
            return out
        candidate=matches[0]
        tokens=re.findall(r"[+\-\u2212]?\d[\d,]*(?:\.\d+)?\s*(?:%|bp)?",candidate,re.I)
        normalized=[number_token(x) for x in tokens]
        expected_value=row["expected_value"]
        expected_change=row["expected_change"]
        v=number_token(expected_value); c=number_token(expected_change)
        vm=bool(v and v in normalized); cm=bool(c and c in normalized)
        out.update({"observed_row_text":candidate,"observed_numeric_tokens":tokens,
                    "expected_display_value":expected_value,"expected_change_display":expected_change,
                    "display_value_match":vm,"display_change_match":cm})
        # A duplicate numeric token cannot satisfy both independent fields.
        if vm and cm:
            vi=normalized.index(v); ci=normalized.index(c,vi+1) if v==c and vi+1<len(normalized) else normalized.index(c)
            if vi==ci: cm=False
        out["display_change_match"]=cm
        out["status"]="VERIFIED" if vm and cm else "OBSERVED_PENDING_FIELD_MAPPING"
        return out
    except Exception as exc:
        out.update({"status":"TOOL_READ_FAILURE","error":f"{type(exc).__name__}: {exc}"})
        return out
    finally:
        page.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fixture",required=True); ap.add_argument("--report-date",required=True)
    ap.add_argument("--output",required=True); ap.add_argument("--timeout-ms",type=int,default=30000)
    a=ap.parse_args(); data=json.loads(Path(a.fixture).read_text(encoding="utf-8"))
    target=data.get("trading_date")
    if data.get("report_date")!=a.report_date or not target: raise SystemExit("Fixture date mismatch")
    work=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for name,item in (data.get(group) or {}).items():
            src=item.get("source") or {}
            work.append({"group":group,"name":name,"source_url":src.get("url"),
                         "expected_value":item.get("display"),"expected_change":item.get("change_display"),
                         "quote_type":src.get("quote_type")})
    for name,display in (data.get("sectors") or {}).items():
        src=(data.get("sector_sources") or {}).get(name) or {}
        work.append({"group":"sectors","name":name,"source_url":src.get("url"),
                     "expected_value":display,"expected_change":src.get("change_display") or display,
                     "quote_type":src.get("quote_type")})
    if len(work)!=44 or any(not x["source_url"] for x in work): raise SystemExit(f"Expected 44 source rows, got {len(work)}")
    observations=[]; counts={}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            for i,row in enumerate(work,1):
                item=observe(browser,row,target,a.timeout_ms)
                item["checked_at_utc"]=datetime.now(timezone.utc).isoformat()
                canonical=json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
                item["observation_record_sha256"]=hashlib.sha256(canonical).hexdigest()
                observations.append(item); counts[item["status"]]=counts.get(item["status"],0)+1
                print(json.dumps({"index":i,"name":row["name"],"status":item["status"]},ensure_ascii=False))
        finally: browser.close()
    result={"schema_version":"1.0","report_date":a.report_date,"trading_date":target,
            "method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE","row_count":44,
            "status_counts":counts,"verified_count":counts.get("VERIFIED",0),
            "observations":observations,
            "warning":"Only the target-date rendered row is used; unresolved field mapping is not promoted to VERIFIED."}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"status_counts":counts},ensure_ascii=False))
if __name__=="__main__": main()
