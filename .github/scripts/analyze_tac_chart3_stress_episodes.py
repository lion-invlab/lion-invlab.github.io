#!/usr/bin/env python3
"""Read-only TAC Chart 3 stress-episode analysis from existing ALFRED output_type=3 chunks.
Latest-vintage results are retrospective, NOT contemporaneous PIT. Historical availability
uses vintage_date < observation_date. No fill, interpolation, resampling or imputation.
"""
import argparse,csv,glob,hashlib,json,re,statistics
from collections import defaultdict
from datetime import date,datetime,timezone
from pathlib import Path
S=("VIXCLS","NFCI","NFCICREDIT","STLFSI4")
E={"GFC_2007_2009":("2007-07-01","2009-06-30","2007-01-01","2007-06-30"),
"COVID_2020":("2020-02-01","2020-06-30","2019-08-01","2020-01-31"),
"RATE_2022":("2022-01-01","2022-12-31","2021-07-01","2021-12-31")}
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def num(x):
 try:return None if x in (None,"",".") else float(x)
 except:return None
def load(root):
 d={s:defaultdict(dict) for s in S};files={}
 for s in S:
  fs=glob.glob(str(root/f"{s}_vintage_changes_*.json"))
  if not fs:raise FileNotFoundError(s)
  for fn in fs:
   p=Path(fn);files[p.name]={"bytes":p.stat().st_size,"sha256":sha(p)}
   o=json.loads(p.read_text(encoding="utf-8"))
   if o.get("output_type")!=3:raise ValueError(f"{p.name}: output_type must be 3")
   for row in o.get("observations",[]):
    obs=row.get("date")
    if not obs:continue
    for k,v in row.items():
     m=re.fullmatch(re.escape(s)+r"_(\d{8})",k)
     if not m or v in (None,""):continue
     z=m.group(1);vd=f"{z[:4]}-{z[4:6]}-{z[6:]}"
     old=d[s][obs].get(vd)
     if old is not None and old!=v:raise ValueError(f"duplicate conflict {s} {obs} {vd}")
     d[s][obs][vd]=v
 return d,files
def rows(d,s,a,b,cutoff):
 out=[]
 for obs,vs in d[s].items():
  if a<=obs<=b:
   eligible=[(v,x) for v,x in vs.items() if v<cutoff]
   if eligible:
    v,x=max(eligible);x=num(x)
    if x is not None:out.append({"observation_date":obs,"vintage_date":v,"value":x})
 return sorted(out,key=lambda x:x["observation_date"])
def stats(r):
 if not r:return None
 v=[x["value"] for x in r];lo=min(r,key=lambda x:x["value"]);hi=max(r,key=lambda x:x["value"])
 return {"n":len(r),"start":r[0]["observation_date"],"end":r[-1]["observation_date"],"mean":statistics.mean(v),"median":statistics.median(v),"min":lo["value"],"min_date":lo["observation_date"],"max":hi["value"],"max_date":hi["observation_date"],"last":r[-1]["value"],"last_date":r[-1]["observation_date"]}
def pit_count(d,s,a,b):
 return sum(1 for obs,vs in d[s].items() if a<=obs<=b and any(v<obs for v in vs))
def revisions(d,s,a,b,cutoff):
 z=[]
 for obs,vs in d[s].items():
  q=sorted((v,num(x)) for v,x in vs.items() if v<cutoff and num(x) is not None)
  if a<=obs<=b and len(q)>1:z.append(abs(q[-1][1]-q[0][1]))
 return {"n":len(z),"mean_abs_revision":statistics.mean(z) if z else None,"max_abs_revision":max(z) if z else None}
def main():
 p=argparse.ArgumentParser();p.add_argument("--artifact-dir",type=Path,required=True);p.add_argument("--as-of",default="2026-11-12");p.add_argument("--output-json",type=Path,default=Path("tac_chart3_stress_episode_analysis.json"));p.add_argument("--output-csv",type=Path,default=Path("tac_chart3_stress_episode_summary.csv"));a=p.parse_args();date.fromisoformat(a.as_of)
 d,files=load(a.artifact_dir);out={"as_of":a.as_of,"executed_at_utc":datetime.now(timezone.utc).isoformat(),"retrospective_rule":f"latest vintage strictly before {a.as_of}; retrospective only, NOT historical real-time PIT","historical_pit_rule":"vintage_date < observation_date; same-day vintages excluded; no fill/interpolation/resampling/imputation","input_chunk_file_count":len(files),"input_chunk_files":files,"episodes":{},"limitations":["Latest vintage results may include later revisions and are not contemporaneous PIT.","No exact intraday release timestamps; same-day vintages are excluded from historical PIT.","Weekly and daily series have different frequencies.","NFCICREDIT is a component of NFCI, not independent confirmation.","VIX methodology changed in 2003.","No S&P 500 return series; no signal or return backtest.","Redistribution requires license review."]}
 csv=[]
 for ep,(st,en,bs,be) in E.items():
  out["episodes"][ep]={}
  for s in S:
   br=rows(d,s,bs,be,a.as_of);er=rows(d,s,st,en,a.as_of);b=stats(br);e=stats(er)
   out["episodes"][ep][s]={"retrospective_baseline":b,"retrospective_event":e,"historical_pit_availability":{"baseline_n":pit_count(d,s,bs,be),"event_n":pit_count(d,s,st,en)},"revision_sensitivity":revisions(d,s,st,en,a.as_of)}
   if b and e:e["mean_minus_baseline_mean"]=e["mean"]-b["mean"]
   csv.append([ep,s,b["mean"] if b else "",e["mean"] if e else "",e["max"] if e else "",e["max_date"] if e else "",e["n"] if e else 0,pit_count(d,s,bs,be),pit_count(d,s,st,en),"RETROSPECTIVE_NOT_REALTIME_PIT"])
 a.output_json.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 with a.output_csv.open("w",newline="",encoding="utf-8-sig") as f:
  w=csvmod.writer(f);w.writerow(["episode","series","baseline_mean","event_mean","event_peak","peak_date","event_n","baseline_historical_pit_n","event_historical_pit_n","status"]);w.writerows(csv)
 print(json.dumps({"as_of":a.as_of,"input_files":len(files),"episodes":{k:{s:v["historical_pit_availability"] for s,v in z.items()} for k,z in out["episodes"].items()}},ensure_ascii=False,indent=2))
import csv as csvmod
if __name__=="__main__":main()
