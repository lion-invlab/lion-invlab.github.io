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

def date_in_row(text, target):
    from datetime import datetime as dt
    d=dt.strptime(target,"%Y-%m-%d")
    forms=[target,d.strftime("%b %d, %Y"),d.strftime("%B %d, %Y"),
           d.strftime("%d/%m/%Y"),d.strftime("%m/%d/%Y"),
           d.strftime("%d %b %Y"),d.strftime("%b %d, %y")]
    return any(x.lower() in text.lower() for x in forms)

async def observe(browser,row,target,timeout,sem):
    out={"name":row["name"],"group":row["group"],"source_url":row["source_url"],
         "instrument_identity_status":"NOT_INDEPENDENTLY_VERIFIED",
         "target_date":target,"quote_type":row.get("quote_type"),
         "read_method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE"}
    started=datetime.now(timezone.utc).isoformat()
    async with sem:
        page=await browser.new_page()
        try:
            response=await page.goto(row["source_url"],wait_until="domcontentloaded",timeout=timeout)
            out["http_status"]=response.status if response else None
            out["page_title"]=await page.title()
            out["final_url"]=page.url
            # Do not wait 30 seconds for a table that may never render.
            try:
                await page.locator("table tbody tr").first.wait_for(state="visible",timeout=min(timeout,8000))
            except Exception:
                pass
            rows=await page.locator("table tbody tr").all_inner_texts()
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
            v=number_token(row.get("expected_value")); c=number_token(row.get("expected_change"))
            vm=bool(v and v in normalized); cm=bool(c and c in normalized)
            if vm and cm:
                vi=normalized.index(v)
                ci=normalized.index(c,vi+1) if v==c and vi+1<len(normalized) else normalized.index(c)
                if vi==ci: cm=False
            out.update({"observed_row_text":candidate,"observed_numeric_tokens":tokens,
                        "expected_display_value":row.get("expected_value"),
                        "expected_change_display":row.get("expected_change"),
                        "display_value_match":vm,"display_change_match":cm})
            # Generic tokens are not sufficient to certify identity or quote convention.
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

async def run(a,work,target):
    sem=asyncio.Semaphore(a.concurrency)
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            tasks=[observe(browser,row,target,a.timeout_ms,sem) for row in work]
            observations=await asyncio.gather(*tasks)
        finally:
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
    ap.add_argument("--concurrency",type=int,default=6)
    a=ap.parse_args()
    if not 1<=a.concurrency<=12: raise SystemExit("--concurrency must be between 1 and 12")
    data=json.loads(Path(a.fixture).read_text(encoding="utf-8")); target=data.get("trading_date")
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
    observations,counts=asyncio.run(run(a,work,target))
    result={"schema_version":"1.1","report_date":a.report_date,"trading_date":target,
            "method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE_BOUNDED_CONCURRENCY",
            "row_count":44,"concurrency":a.concurrency,"timeout_ms":a.timeout_ms,
            "status_counts":counts,"verified_count":0,"observations":observations,
            "warning":"This stage records rendered source observations only. Generic numeric matches do not verify instrument identity, quote convention, or field mapping; no row is promoted to VERIFIED."}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"status_counts":counts,"row_count":len(observations)},ensure_ascii=False))
if __name__=="__main__": main()
