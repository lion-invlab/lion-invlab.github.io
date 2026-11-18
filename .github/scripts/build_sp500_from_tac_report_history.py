#!/usr/bin/env python3
"""Convert TAC's audited daily S&P 500 OHLC handoff JSONL into Chart 3 close history.

Each observation retains its own actual source; no provider is inferred or relabeled.
"""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, json, math, zlib
from pathlib import Path
from urllib.parse import urlparse

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def varint(value):
    if value < 0:
        raise ValueError("varint only accepts non-negative integers")
    out=bytearray()
    while value >= 128:
        out.append((value & 127) | 128); value >>= 7
    out.append(value)
    return out

def load_records(path: Path):
    raw=path.read_bytes()
    records={}
    for line_no,line in enumerate(raw.decode("utf-8-sig").splitlines(),1):
        if not line.strip():
            continue
        try:
            item=json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid JSONL at line {line_no}") from exc
        day=item.get("observation_date")
        try:
            dt.date.fromisoformat(day)
        except Exception as exc:
            raise ValueError(f"Invalid observation_date at line {line_no}") from exc
        if day in records:
            raise ValueError(f"Duplicate observation_date: {day}")
        claimed=item.get("record_sha256")
        body={k:v for k,v in item.items() if k!="record_sha256"}
        actual=hashlib.sha256(canonical(body)).hexdigest()
        if not claimed or claimed != actual:
            raise ValueError(f"record_sha256 mismatch for {day}")
        source_url=item.get("source_url","")
        parsed=urlparse(source_url)
        if parsed.scheme!="https" or not parsed.hostname:
            raise ValueError(f"Missing valid HTTPS source_url for {day}")
        note=str(item.get("source_note","")).lower()
        if not ("現金指數" in note or "cash index" in note):
            raise ValueError(f"Cash-index identity not explicitly confirmed for {day}")
        non_cfd=("非cfd" in note or "non-cfd" in note or "not cfd" in note or "非差價合約" in note)
        if (("cfd" in note or "差價合約" in note) and not non_cfd):
            raise ValueError(f"CFD observation rejected for {day}")
        close=float(item.get("close",0))
        if not math.isfinite(close) or close<=0:
            raise ValueError(f"Invalid close for {day}")
        if item.get("series_id")!="SP500" or item.get("instrument")!="S&P 500 cash price index":
            raise ValueError(f"Unexpected instrument identity for {day}")
        for field in ("source_name","retrieved_at","retrieval_method"):
            if not item.get(field):
                raise ValueError(f"Missing {field} for {day}")
        try:
            stamp=dt.datetime.fromisoformat(item["retrieved_at"].replace("Z","+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone missing")
        except Exception as exc:
            raise ValueError(f"Invalid retrieved_at for {day}") from exc
        records[day]=item
    if not records:
        raise ValueError("No S&P 500 observations in handoff JSONL")
    return raw, records

def convert(input_jsonl: Path, compact_path: Path, provenance_path: Path):
    raw,records=load_records(input_jsonl)
    rows=sorted((day,round(float(item["close"])*100)) for day,item in records.items())
    packed=bytearray()
    previous_day=dt.date.fromisoformat(rows[0][0]).toordinal()
    previous_close=0
    for day,cents in rows:
        ordinal=dt.date.fromisoformat(day).toordinal()
        if cents<=0:
            raise ValueError(f"Invalid close cents for {day}")
        delta=cents-previous_close
        packed.extend(varint(ordinal-previous_day))
        packed.extend(varint(2*delta if delta>=0 else -2*delta-1))
        previous_day,previous_close=ordinal,cents
    raw_hash=hashlib.sha256(raw).hexdigest()
    compact={
        "schema_version":"1.0.0","encoding":"zlib+base64",
        "start":rows[0][0],"end":rows[-1][0],"rows":len(rows),
        "payload":base64.b64encode(zlib.compress(bytes(packed))).decode("ascii"),
        "source_dataset_sha256":raw_hash
    }
    source_observations=[]
    for day,item in sorted(records.items()):
        source_observations.append({
            "date":day,"source_name":item["source_name"],"source_url":item["source_url"],
            "source_note":item.get("source_note",""),"retrieved_at":item["retrieved_at"],
            "retrieval_method":item["retrieval_method"],"record_sha256":item["record_sha256"]
        })
    provenance={
        "schema_version":"2.0","source":"TAC daily report D4; source varies by observation",
        "method":"tac_daily_report_verified_ohlc_jsonl","source_sha256":raw_hash,
        "source_filename":input_jsonl.name,"rows":len(rows),
        "source_observation_date":rows[-1][0],"observations":source_observations
    }
    compact_path.parent.mkdir(parents=True,exist_ok=True)
    provenance_path.parent.mkdir(parents=True,exist_ok=True)
    compact_path.write_text(json.dumps(compact,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    provenance_path.write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"rows":len(rows),"start":rows[0][0],"end":rows[-1][0],"source_sha256":raw_hash,
            "distinct_sources":sorted({x["source_name"] for x in source_observations})}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-jsonl",type=Path,required=True)
    p.add_argument("--compact",type=Path,required=True)
    p.add_argument("--provenance",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(convert(a.input_jsonl,a.compact,a.provenance),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
