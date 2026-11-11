#!/usr/bin/env python3
"""Bootstrap the TAC Chart 3 durable baseline from a completed GitHub Actions run."""
from __future__ import annotations
import argparse, csv, gzip, hashlib, io, json, os, re, shutil, tempfile, urllib.request, zipfile
from pathlib import Path
from datetime import datetime, timezone

SERIES = {
    "VIXCLS": {"start": "1990-01-01", "periods": ["1990_1999", "2000_2009", "2010_2019", "2020_2026"]},
    "NFCI": {"start": "1971-01-01", "periods": ["1971_1980", "1981_1990", "1991_2000", "2001_2010", "2011_2020", "2021_2026"]},
    "NFCICREDIT": {"start": "1971-01-01", "periods": ["1971_1980", "1981_1990", "1991_2000", "2001_2010", "2011_2020", "2021_2026"]},
    "STLFSI4": {"start": "1993-12-01", "periods": ["1993_2002", "2003_2012", "2013_2022", "2023_2026"]},
}
EVENT_FIELDS = ["series_id","observation_date","vintage_date","value","value_status","release_date","release_date_status","source_method","source_chunk","artifact_created_at","license_status"]
CURRENT_FIELDS = ["series_id","observation_date","value","realtime_start","realtime_end","retrieved_at","source_method","license_status","quality_flags"]
INITIAL_FIELDS = ["series_id","observation_date","value","realtime_start","realtime_end","release_date","release_date_status","retrieved_at","source_method","license_status"]

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def write_json(p,obj):
    raw=json.dumps(obj,ensure_ascii=False,indent=2).encode("utf-8")
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    return sha_bytes(raw),len(raw)

def write_gzip_csv(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("wb") as raw:
        with gzip.GzipFile(filename="",mode="wb",fileobj=raw,compresslevel=6,mtime=0) as gz:
            with io.TextIOWrapper(gz,encoding="utf-8-sig",newline="") as text:
                w=csv.DictWriter(text,fieldnames=fields);w.writeheader();w.writerows(rows)
    return sha_file(p),p.stat().st_size

def api_json(url,token):
    req=urllib.request.Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"TAC-Chart3-Bootstrap"})
    with urllib.request.urlopen(req,timeout=180) as r:return json.loads(r.read().decode("utf-8"))

def download_run_artifacts(run_id,repo,token,raw_root):
    meta=api_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100",token)
    raw_root.mkdir(parents=True,exist_ok=True);found={}
    for sid in SERIES:
        candidates=[a for a in meta.get("artifacts",[]) if a.get("name","").startswith(f"tac-chart3-{sid}-{run_id}-") and not a.get("expired")]
        if len(candidates)!=1:raise RuntimeError(f"Expected exactly one unexpired artifact for {sid}; found {len(candidates)}")
        a=candidates[0];url=f"https://api.github.com/repos/{repo}/actions/artifacts/{a['id']}/zip"
        req=urllib.request.Request(url,headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","User-Agent":"TAC-Chart3-Bootstrap"})
        with urllib.request.urlopen(req,timeout=300) as r:data=r.read()
        digest=sha_bytes(data);expected=(a.get("digest") or "").removeprefix("sha256:")
        if expected and digest!=expected:raise RuntimeError(f"Artifact digest mismatch for {sid}: {digest} != {expected}")
        zpath=raw_root/f"{sid}.zip";zpath.write_bytes(data);target=raw_root/sid;target.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                dest=(target/info.filename).resolve()
                if target.resolve() not in dest.parents and dest!=target.resolve():raise RuntimeError("Unsafe artifact path")
            z.extractall(target)
        found[sid]={"artifact_id":a["id"],"artifact_name":a["name"],"artifact_sha256":digest,"artifact_bytes":len(data),"raw_dir":str(target),"run_id":run_id}
    return found

def load_json(p):return json.loads(p.read_text(encoding="utf-8"))
def span(values):
    vals=sorted(values);return {"first":vals[0] if vals else None,"last":vals[-1] if vals else None}

def build_series(sid,raw,stage,retrieved,artifact):
    sd=stage/"series"/sid;sd.mkdir(parents=True,exist_ok=True)
    current=load_json(raw/f"{sid}_current_output_type1.json")["observations"]
    initial=load_json(raw/f"{sid}_initial_release_output_type4.json")["observations"]
    vintage_dates=load_json(raw/f"{sid}_vintage_dates.json")["vintage_dates"]
    if not current or not vintage_dates:raise RuntimeError(f"{sid}: current or vintage dates empty")
    expected_cols={f"{sid}_{d.replace('-','')}":d for d in vintage_dates}
    chunks=sorted(raw.glob(f"{sid}_vintage_changes_*.json"))
    if not chunks:raise RuntimeError(f"{sid}: no vintage chunks")
    events={};seen_cols=set();empty_chunks=0;count_mismatch=[];raw_rows=0;reported_count=0
    for fp in chunks:
        payload=load_json(fp);observations=payload.get("observations") or []
        raw_rows+=len(observations);reported_count+=int(payload.get("count") or 0)
        if not observations:empty_chunks+=1
        if int(payload.get("count") or 0)!=len(observations):count_mismatch.append(fp.name)
        for row in observations:
            d=row.get("date")
            if not d:continue
            for col,val in row.items():
                if col not in expected_cols:continue
                seen_cols.add(col)
                # A dot is a real source missing-value event; only empty/null means no event.
                if val in ("",None):continue
                key=(d,expected_cols[col])
                if key in events and events[key]["value"]!=val:raise RuntimeError(f"{sid}: conflicting duplicate event {key}")
                events[key]={"series_id":sid,"observation_date":d,"vintage_date":expected_cols[col],"value":val,"value_status":"source_missing_value" if val=="." else "source_value","release_date":"","release_date_status":"exact_release_date_not_supplied_by_observations_endpoint","source_method":"FRED API series/observations output_type=3 (new_and_revised_only)","source_chunk":fp.name,"artifact_created_at":retrieved,"license_status":"review_required_before_redistribution"}
    missing_cols=sorted(set(expected_cols)-seen_cols)
    if missing_cols:raise RuntimeError(f"{sid}: {len(missing_cols)} vintage columns absent")
    batches=max(int(re.search(r"_v(\d+)_",p.name).group(1)) for p in chunks)
    periods=SERIES[sid]["periods"];expected_grid={(b,p) for b in range(1,batches+1) for p in periods};actual_grid=set()
    for p in chunks:
        m=re.search(r"_v(\d+)_obs_(\d{4}_\d{4})_",p.name)
        if m:actual_grid.add((int(m.group(1)),m.group(2)))
    missing_grid=sorted(expected_grid-actual_grid)
    if missing_grid:raise RuntimeError(f"{sid}: missing chunk grid cells {missing_grid[:5]}")
    event_rows=sorted(events.values(),key=lambda x:(x["observation_date"],x["vintage_date"]))
    latest={}
    for e in event_rows:latest[e["observation_date"]]=(e["vintage_date"],e["value"])
    current_map={r["date"]:r["value"] for r in current}
    mismatches=[(d,v,latest[d][1]) for d,v in current_map.items() if d in latest and latest[d][1]!=v]
    no_history=[d for d in current_map if d not in latest]
    if mismatches or no_history:raise RuntimeError(f"{sid}: current reconciliation failed; mismatches={mismatches[:3]}, no_history={no_history[:3]}")
    earliest={}
    for e in event_rows:
        d=e["observation_date"]
        if d not in earliest or e["vintage_date"]<earliest[d][0]:earliest[d]=(e["vintage_date"],e["value"])
    init_mismatches=[];init_without=[]
    for row in initial:
        d=row["date"]
        if d not in earliest:init_without.append(d);continue
        if earliest[d][1]!=row["value"]:init_mismatches.append((d,row["value"],earliest[d][1]))
    if init_mismatches or init_without:raise RuntimeError(f"{sid}: initial-release reconciliation failed; mismatches={init_mismatches[:3]}, no_event={init_without[:3]}")
    event_sha,event_bytes=write_gzip_csv(sd/"vintage_events.csv.gz",EVENT_FIELDS,event_rows)
    current_rows=[]
    for r in current:
        flags=["source_missing_value"] if r.get("value")=="." else []
        current_rows.append({"series_id":sid,"observation_date":r["date"],"value":r["value"],"realtime_start":r.get("realtime_start",""),"realtime_end":r.get("realtime_end",""),"retrieved_at":retrieved,"source_method":"FRED API output_type=1 current snapshot","license_status":"review_required_before_redistribution","quality_flags":";".join(flags)})
    current_sha,current_bytes=write_gzip_csv(sd/"current.csv.gz",CURRENT_FIELDS,current_rows)
    initial_rows=[{"series_id":sid,"observation_date":r["date"],"value":r["value"],"realtime_start":r.get("realtime_start",""),"realtime_end":r.get("realtime_end",""),"release_date":"","release_date_status":"exact_release_date_not_supplied; realtime vintage window retained","retrieved_at":retrieved,"source_method":"FRED API output_type=4 initial release","license_status":"review_required_before_redistribution"} for r in initial]
    initial_sha,initial_bytes=write_gzip_csv(sd/"initial_release.csv.gz",INITIAL_FIELDS,initial_rows)
    date_obj={"series_id":sid,"vintage_dates":vintage_dates,"count":len(vintage_dates),"source_endpoint":"FRED series/vintagedates"}
    dates_sha,_=write_json(sd/"vintage_dates.json",date_obj)
    state={"series_id":sid,"last_vintage_date":vintage_dates[-1],"vintage_date_count":len(vintage_dates),"vintage_dates_sha256":dates_sha,"event_count":len(event_rows),"events_sha256":event_sha,"current_rows":len(current_rows),"current_sha256":current_sha,"initial_release_rows":len(initial_rows),"initial_release_sha256":initial_sha,"last_success_at":retrieved,"source_run_id":artifact.get("run_id"),"artifact_sha256":artifact["artifact_sha256"]}
    write_json(sd/"state.json",state)
    return {"series_id":sid,"artifact_id":artifact["artifact_id"],"artifact_sha256":artifact["artifact_sha256"],"current_rows":len(current),"current_span":span(current_map),"initial_release_rows":len(initial),"initial_release_span":span(r["date"] for r in initial),"vintage_dates":len(vintage_dates),"vintage_span":span(vintage_dates),"chunk_files":len(chunks),"chunk_grid_expected":len(expected_grid),"chunk_grid_present":len(actual_grid),"empty_chunks":empty_chunks,"count_mismatch_chunks":len(count_mismatch),"reported_count_sum":reported_count,"raw_observation_rows":raw_rows,"vintage_columns_seen":len(seen_cols),"missing_vintage_columns":len(missing_cols),"event_rows":len(event_rows),"source_missing_value_events":sum(1 for e in event_rows if e["value"]=="."),"duplicate_event_keys":0,"current_snapshot_mismatches":len(mismatches),"initial_release_mismatches":len(init_mismatches),"event_sha256":event_sha,"current_sha256":current_sha,"initial_release_sha256":initial_sha}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--run-id",type=int,default=43026998120);ap.add_argument("--repo",default=os.environ.get("GITHUB_REPOSITORY","lion-invlab/lion-invlab.github.io"));ap.add_argument("--output",default="data/tac-chart3");args=ap.parse_args()
    token=os.environ.get("GH_TOKEN","").strip()
    if not token:raise SystemExit("GH_TOKEN is required to download the source run artifacts.")
    retrieved=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory(prefix="tac-chart3-bootstrap-") as td:
        tmp=Path(td);artifacts=download_run_artifacts(args.run_id,args.repo,token,tmp/"raw");stage=tmp/"stage";summaries=[];raw_manifest=[]
        for sid in SERIES:
            raw=Path(artifacts[sid]["raw_dir"])
            for p in sorted(raw.iterdir()):
                if p.is_file():raw_manifest.append({"series_id":sid,"file":p.name,"bytes":p.stat().st_size,"sha256":sha_file(p)})
            summaries.append(build_series(sid,raw,stage,retrieved,artifacts[sid]))
        report={"project":"TAC Chart 3","run_id":args.run_id,"branch":"simulation/tac-process-lab-2026-11-06","retrieved_at":retrieved,"status":"PASS_WITH_DOCUMENTED_COVERAGE_LIMITATIONS","series":summaries,"raw_file_count":len(raw_manifest),"raw_file_bytes":sum(x["bytes"] for x in raw_manifest),"raw_files":raw_manifest,"artifacts":{sid:{k:v for k,v in a.items() if k not in ("raw_dir",)} for sid,a in artifacts.items()},"method":{"current":"FRED output_type=1","initial_release":"FRED output_type=4","vintage_events":"FRED output_type=3 new/revised observations only","vintage_index":"FRED series/vintagedates","dot":"preserved as explicit source_missing_value event","blank_cells":"empty/null only; no event","release_date":"exact per-observation date not supplied; left blank","imputation":False,"interpolation":False,"forward_fill":False,"license_status":"review_required_before_redistribution"}}
        write_json(stage/"manifest.json",report)
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);backup=output.with_name(output.name+".previous")
        if backup.exists():shutil.rmtree(backup)
        if output.exists():os.replace(output,backup)
        try:os.replace(stage,output)
        except Exception:
            if backup.exists() and not output.exists():os.replace(backup,output)
            raise
        if backup.exists():shutil.rmtree(backup)
        print(json.dumps({"status":report["status"],"output":str(output),"series":summaries,"raw_file_count":len(raw_manifest)},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
