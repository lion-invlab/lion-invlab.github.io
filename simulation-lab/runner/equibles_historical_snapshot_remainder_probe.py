#!/usr/bin/env python3
"""Fetch remaining Equibles historical snapshots (offset >= 10), read-only."""
from __future__ import annotations
import hashlib,json,os,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
BASE="https://api.equibles.com/v1/stocks/{ticker}/analyst-estimates"
TARGETS={
 "NVDA":{"event_date":"2026-11-17","period_markers":["2026-10-31"]},
 "WMT":{"event_date":"2026-11-19","period_markers":["2026-10-31"]},
 "BIDU":{"event_date":"2026-11-16","period_markers":["2026-09-30"]},
}
MAX_REQUESTS=60
class Client:
 def __init__(self):
  self.key=os.environ.get("EQUIBLES_API_KEY","").strip()
  if not self.key: raise RuntimeError("EQUIBLES_API_KEY missing")
  self.n=0; self.rawdir=Path("simulation-lab/output/equibles-raw"); self.rawdir.mkdir(parents=True,exist_ok=True)
 def get(self,ticker,params):
  if self.n>=MAX_REQUESTS: raise RuntimeError("60-request safety limit reached")
  self.n+=1
  url=BASE.format(ticker=ticker)+"?"+urllib.parse.urlencode(params)
  req=urllib.request.Request(url,headers={"Authorization":"Bearer "+self.key,"Accept":"application/json","User-Agent":"TAC-Earnings-PIT-Remainder-Probe/1.0"})
  try:
   with urllib.request.urlopen(req,timeout=35) as r: raw,status=r.read(),r.status
  except urllib.error.HTTPError as e: raw,status=e.read(),e.code
  try: payload=json.loads(raw.decode("utf-8")) if raw else {}
  except Exception: payload={"_parse_error":True,"excerpt":raw[:300].decode("utf-8","replace")}
  sha=hashlib.sha256(raw).hexdigest(); path=self.rawdir/f"{ticker}-rem-{self.n:03d}-{sha}.json"; path.write_bytes(raw)
  return payload,status,sha,str(path)
def metric(payload,name,markers):
 rows=[x for x in payload.get("data",[]) if isinstance(x,dict) and str(x.get("metric","")).casefold()==name.casefold() and any(m in str(x.get("period","")) for m in markers)]
 avg=next((x for x in rows if str(x.get("statistic","")).casefold() in ("average","mean")),None)
 cnt=next((x for x in rows if "analyst" in str(x.get("statistic","")).casefold() and "count" in str(x.get("statistic","")).casefold()),None)
 return {"row_count":len(rows),"average":avg.get("value") if avg else None,"unit":avg.get("unit") if avg else None,"basis":avg.get("basis") if avg else None,"analyst_count":cnt.get("value") if cnt else None,"publication_labels":sorted({str(x.get("publicationLabel")) for x in rows if x.get("publicationLabel")}),"basis_values":sorted({str(x.get("basis")) for x in rows if x.get("basis") is not None})}
def main():
 c=Client(); out=[]
 for ticker,cfg in TARGETS.items():
  pages=[]; allsnaps=[]
  for offset in (10,20,30,40,50,60,70,80,90):
   page,status,sha,path=c.get(ticker,{"limit":"100","snapshotOffset":str(offset)})
   pages.append({"offset":offset,"status":status,"meta":page.get("snapshotsMeta"),"raw_sha256":sha})
   snaps=page.get("snapshots",[]) if isinstance(page.get("snapshots"),list) else []
   allsnaps.extend(snaps)
   meta=page.get("snapshotsMeta") or {}
   if status!=200 or not meta.get("hasMore"): break
   time.sleep(.2)
  hist=[]
  for snap in allsnaps:
   sid=snap.get("id")
   if not sid: continue
   p,status,sha,path=c.get(ticker,{"limit":"100","snapshotId":sid})
   hist.append({"snapshot_id":sid,"http_status":status,"captured_at":p.get("capturedAt") or snap.get("capturedAt"),"verified_at":p.get("verifiedAt"),"publication_label":p.get("publicationLabel",snap.get("publicationLabel")),"provider":p.get("provider"),"eps":metric(p,"EPS",cfg["period_markers"]),"revenue":metric(p,"Revenue",cfg["period_markers"]),"raw_response_ref":path,"raw_response_sha256":sha})
   time.sleep(.2)
  out.append({"ticker":ticker,"event_date":cfg["event_date"],"remaining_pages":pages,"remaining_snapshots_fetched":len(hist),"history":hist})
 report={"probe":"equibles_historical_snapshot_remainder","captured_at":datetime.now(timezone.utc).isoformat(),"branch_scope":"simulation/tac-process-lab-2026-11-06","requests_used":c.n,"targets":out}
 path=Path("simulation-lab/output/equibles-historical-pit-remainder.json");path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"probe":report["probe"],"requests_used":c.n,"output":str(path),"targets":[{"ticker":x["ticker"],"remaining_snapshots_fetched":x["remaining_snapshots_fetched"],"basis_eps":sum(bool(h["eps"]["basis_values"]) for h in x["history"]),"basis_revenue":sum(bool(h["revenue"]["basis_values"]) for h in x["history"]),"pub_labels":sum(bool(h["publication_label"]) for h in x["history"])} for x in out]},ensure_ascii=False,indent=2))
 return 0
if __name__=="__main__": raise SystemExit(main())
