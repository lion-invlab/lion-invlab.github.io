#!/usr/bin/env python3
"""Reconstruct conservative point-in-time TAC Chart 3 snapshots from ALFRED events."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json
from datetime import date,datetime,timezone
from pathlib import Path

SERIES=("VIXCLS","NFCI","NFCICREDIT","STLFSI4")
META={
 "VIXCLS":{"label":"CBOE VIX","frequency":"daily","unit":"index points","methodology_note":"VIX methodology changed in 2003; structural break must be considered."},
 "NFCI":{"label":"Chicago Fed National Financial Conditions Index","frequency":"weekly","unit":"index points","methodology_note":"Positive values indicate tighter-than-average financial conditions."},
 "NFCICREDIT":{"label":"NFCI Credit Subindex","frequency":"weekly","unit":"index points","methodology_note":"A component of NFCI; not an independent standalone credit index."},
 "STLFSI4":{"label":"St. Louis Fed Financial Stress Index","frequency":"weekly","unit":"index points","methodology_note":"Positive values indicate above-average financial stress."}
}

def reconstruct_series(path:Path,series_id:str,as_of_date:str):
    cutoff=date.fromisoformat(as_of_date)
    latest_by_observation={}
    previous_key=None
    event_rows=0
    latest_vintage=None
    with gzip.open(path,"rt",encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            obs=row["observation_date"]
            vintage=row["vintage_date"]
            key=(obs,vintage)
            if previous_key is not None and key<=previous_key:
                raise RuntimeError(f"{series_id}: event rows are not strictly sorted/unique at {key}")
            previous_key=key
            event_rows+=1
            vdate=date.fromisoformat(vintage)
            odate=date.fromisoformat(obs)
            # Conservative point-in-time rule: do not use same-day vintage values,
            # because the observations endpoint does not supply release timestamps.
            if vdate>=cutoff or odate>cutoff:
                continue
            latest_by_observation[obs]=row
            if latest_vintage is None or vintage>latest_vintage:
                latest_vintage=vintage
    observations=[]
    missing=0
    for obs,row in sorted(latest_by_observation.items()):
        raw=row["value"]
        if raw=='.':
            value=None;status="source_missing_value";missing+=1
        elif raw in ("",None):
            raise RuntimeError(f"{series_id}: blank value was stored as a vintage event on {obs}")
        else:
            try:value=float(raw)
            except ValueError:raise RuntimeError(f"{series_id}: non-numeric value {raw!r} on {obs}")
            status="source_value"
        observations.append({"date":obs,"value":value,"value_raw":raw,"value_status":status,"last_known_vintage":row["vintage_date"]})
    return {
        "series_id":series_id,"label":META[series_id]["label"],"frequency":META[series_id]["frequency"],"unit":META[series_id]["unit"],
        "as_of_date":as_of_date,"latest_available_vintage_before_as_of":latest_vintage,
        "observation_span":{"first":observations[0]["date"] if observations else None,"last":observations[-1]["date"] if observations else None},
        "observation_count":len(observations),"valid_observations":sum(x["value"] is not None for x in observations),
        "missing_observations":missing,"event_rows_scanned":event_rows,
        "source_file":path.name,"source_file_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "release_timestamp_available":False,"methodology_note":META[series_id]["methodology_note"],
        "observations":observations
    }

def reconcile_current_snapshot(current_path:Path,observations:list[dict]):
    with gzip.open(current_path,"rt",encoding="utf-8-sig",newline="") as f:
        current={r["observation_date"]:r["value"] for r in csv.DictReader(f)}
    reconstructed={r["date"]:r["value_raw"] for r in observations}
    if current!=reconstructed:
        missing=sorted(set(current)-set(reconstructed))
        extra=sorted(set(reconstructed)-set(current))
        mismatch=sorted(d for d in set(current)&set(reconstructed) if current[d]!=reconstructed[d])
        raise RuntimeError(f"Point-in-time/current reconciliation failed: missing={len(missing)}, extra={len(extra)}, mismatches={len(mismatch)}; examples={missing[:2]} {extra[:2]} {mismatch[:2]}")
    return {"status":"PASS","current_rows":len(current),"reconstructed_rows":len(reconstructed),"mismatches":0}

def build_snapshot(data_dir:Path,as_of_date:str,output:Path|None=None):
    date.fromisoformat(as_of_date)
    manifest=json.loads((data_dir/"manifest.json").read_text(encoding="utf-8"))
    series=[]
    for sid in SERIES:
        state=json.loads((data_dir/"series"/sid/"state.json").read_text(encoding="utf-8"))
        event_path=data_dir/"series"/sid/"vintage_events.csv.gz"
        if hashlib.sha256(event_path.read_bytes()).hexdigest()!=state["events_sha256"]:
            raise RuntimeError(f"{sid}: vintage event SHA-256 does not match state checkpoint")
        result=reconstruct_series(event_path,sid,as_of_date)
        dates=json.loads((data_dir/"series"/sid/"vintage_dates.json").read_text(encoding="utf-8"))["vintage_dates"]
        result["vintage_history_coverage"]={"first":dates[0],"last":dates[-1],"count":len(dates)}
        result["history_available_for_as_of"]=bool(result["latest_available_vintage_before_as_of"])
        if date.fromisoformat(as_of_date)>date.fromisoformat(state["last_vintage_date"]):
            result["current_snapshot_reconciliation"]=reconcile_current_snapshot(data_dir/"series"/sid/"current.csv.gz",result["observations"])
        else:
            result["current_snapshot_reconciliation"]={"status":"NOT_APPLICABLE","reason":"as_of_date is not later than the latest current vintage"}
        series.append(result)
    obj={
        "schema_version":"1.0","dataset_id":"TAC_CHART3_POINT_IN_TIME_SNAPSHOT","as_of_date":as_of_date,
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method":{
            "reconstruction":"latest output_type=3 event per observation_date with vintage_date strictly earlier than as_of_date",
            "same_day_vintage_policy":"excluded because exact release timestamp is unavailable",
            "future_observation_policy":"observation_date later than as_of_date is excluded",
            "missing_values":"source '.' retained as null; no imputation",
            "forward_fill":False,"interpolation":False,"resampling":False,
            "release_date":"not supplied by observations endpoint; never inferred",
            "lookahead_bias_control":"strict prior-day vintage cutoff; no same-day vintage values"
        },
        "series":series,
        "limitations":[
            "Vintage history begins at different dates for each series; do not assume full-history point-in-time coverage.",
            "Vintage date is a date-level availability proxy, not an exact publication timestamp.",
            "NFCICREDIT is a component of NFCI and should not be double-counted as independent evidence.",
            "VIX methodology has a structural break around 2003."
        ],
        "baseline_manifest_chart_dataset_sha256":manifest.get("chart_dataset",{}).get("sha256")
    }
    raw=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    digest=hashlib.sha256(raw).hexdigest()
    if output:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(raw)
        output.with_suffix(output.suffix+".sha256").write_text(digest+"  "+output.name+"\n",encoding="utf-8")
    return {"status":"PASS","as_of_date":as_of_date,"sha256":digest,"bytes":len(raw),"series":[{"series_id":s["series_id"],"latest_vintage":s["latest_available_vintage_before_as_of"],"observations":s["observation_count"],"valid":s["valid_observations"],"missing":s["missing_observations"],"history_available":s["history_available_for_as_of"]} for s in series],"output":str(output) if output else None}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data-dir",default="data/tac-chart3")
    p.add_argument("--as-of-date",required=True,help="YYYY-MM-DD; same-day vintage is excluded conservatively")
    p.add_argument("--output",default=None)
    a=p.parse_args()
    result=build_snapshot(Path(a.data_dir),a.as_of_date,Path(a.output) if a.output else None)
    print(json.dumps(result,ensure_ascii=False,indent=2))
