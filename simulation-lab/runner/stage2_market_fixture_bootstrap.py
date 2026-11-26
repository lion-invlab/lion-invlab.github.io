#!/usr/bin/env python3
"""Create a zero-market-value Stage 2 input and populate it only from this run's observations.

The base report contributes non-market content and the approved 44-instrument source
catalogue. All prior market prices, changes and observation evidence are removed before
the browser capture. The apply step writes only values returned by the current run.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

COUNTS = {"global_markets":17,"bonds":3,"fx":6,"energy":2,"metals":2,"risk":3,"sectors":11}
VALUE_KEYS = {
    "close_value","daily_change_percent","history_close","history_change","score_value",
    "source_score_value","cnn_target_date_score","backup_source_score_value","band",
    "change_display","raw_response_sha256","checked_at_tw","checked_at","read_at_taipei",
    "verified_at_tw","checked_at_taipei","evidence_method","web_reader_ref","web_line_start",
    "web_line_end","read_method","read_status","observed_value","observed_change",
    "source_page_fetched","page_title","trading_date","display_value_matches_saved_observation",
    "backup_web_reader_ref","backup_web_line_start","backup_web_line_end","provenance",
    "history_page_completion_at","history_page_completion_fields","screenshot_fields_applied",
    "history_close","history_change","screenshot_evidence","screenshot_evidence_path",
    "screenshot_evidence_sha256","screenshot_observation_applied_at",
}

def _decimal(value):
    text=str(value).strip().replace(",","").replace("$","").replace("%","").replace("+","").replace("−","-")
    try: return Decimal(text)
    except (InvalidOperation, ValueError): raise ValueError(f"Not a numeric market value: {value!r}")

def _format_spec(value):
    s=str(value or "")
    numeric=re.sub(r"[^0-9.]", "", s)
    decimals=len(numeric.split(".",1)[1]) if "." in numeric else 0
    return {"decimals":decimals,"commas":"," in s,"prefix":"$" if s.startswith("$") else "",
            "suffix":"%" if s.endswith("%") else "", "plus":s.startswith("+")}

def _fmt(value, spec, force_sign=False):
    d=_decimal(value)
    q=Decimal(1).scaleb(-int(spec.get("decimals",2)))
    s=f"{d.quantize(q,rounding=ROUND_HALF_UP):,.{int(spec.get('decimals',2))}f}" if spec.get("commas") else f"{d.quantize(q,rounding=ROUND_HALF_UP):.{int(spec.get('decimals',2))}f}"
    if not spec.get("commas"): s=s.replace(",","")
    if d>0 and (force_sign or spec.get("plus")): s="+"+s
    return str(spec.get("prefix",""))+s+str(spec.get("suffix",""))

def _rows(data):
    result=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for name,item in (data.get(group) or {}).items():
            result.append((group,name,item,item.get("source") or {}))
    for name,display in (data.get("sectors") or {}).items():
        result.append(("sectors",name,{"display":display},(data.get("sector_sources") or {}).get(name) or {}))
    return result

def _assert_universe(data):
    counts={}
    for group,name,_,source in _rows(data):
        counts[group]=counts.get(group,0)+1
        for key in ("name","url","data_date","quote_type","note"):
            if not source.get(key): raise ValueError(f"{group}/{name}: source.{key} missing")
        if source["data_date"] != data.get("trading_date"):
            raise ValueError(f"{group}/{name}: source date does not match trading_date")
        if not str(source["url"]).startswith("https://"):
            raise ValueError(f"{group}/{name}: source URL must be HTTPS")
    if counts != COUNTS:
        raise ValueError(f"44-row universe mismatch: {counts!r}")
    return counts

def blank_fixture(source):
    data=copy.deepcopy(source)
    _assert_universe(data)
    for group,name,item,src in _rows(data):
        if group=="sectors":
            src["_stage2_format"]={"close":_format_spec(src.get("history_close") or src.get("close_value")),
                                   "change":_format_spec(src.get("change_display") or item.get("display"))}
            data["sectors"][name]="待擷取"
        else:
            src["_stage2_format"]={"close":_format_spec(item.get("display")),
                                   "change":_format_spec(item.get("change_display"))}
            item["display"]="待擷取"
            item["change_display"]="待擷取"
        for key in VALUE_KEYS:
            src.pop(key,None)
        src["verification_status"]="PENDING"
        src["source_page_fetched"]=False
    screenshot_rows=0; screenshot_fields=0
    sidecar=Path(f"simulation-lab/input/market-screenshot-observations-{data['report_date']}.json")
    if sidecar.is_file():
        from stage2_screenshot_inputs import load_screenshot_bundle, apply_screenshot_values_to_fixture
        inputs=load_screenshot_bundle(sidecar,data,Path.cwd())
        apply_screenshot_values_to_fixture(data,inputs)
        screenshot_rows=len(inputs)
        screenshot_fields=sum(len(row.get("fields") or {}) for row in inputs.values())
    data["stage2_market_bootstrap"]={"status":"BLANK_INPUT_WITH_SCREENSHOTS" if screenshot_rows else "BLANK_INPUT",
        "preexisting_market_values_used":False,"screenshot_row_count":screenshot_rows,
        "screenshot_field_count":screenshot_fields,"row_count":44,
        "report_date":data["report_date"],"trading_date":data["trading_date"]}
    return data

def _get_observation_map(payload, data):
    if payload.get("report_date") != data.get("report_date") or payload.get("trading_date") != data.get("trading_date"):
        raise ValueError("Observation report/trading date does not match blank market input")
    observations=payload.get("observations") or []
    mapping={(x.get("group"),x.get("name")):x for x in observations}
    if len(mapping)!=44 or len(observations)!=44:
        raise ValueError(f"Expected 44 unique observations, got {len(mapping)}")
    expected={(g,n) for g,n,_,_ in _rows(data)}
    if set(mapping)!=expected:
        missing=sorted(expected-set(mapping)); extra=sorted(set(mapping)-expected)
        raise ValueError(f"Observation universe mismatch; missing={missing}; extra={extra}")
    return mapping

def populate_fixture(data, payload):
    out=copy.deepcopy(data)
    observations=_get_observation_map(payload,out)
    verified=0; pending=[]
    for group,name,item,src in _rows(out):
        obs=observations[(group,name)]
        if obs.get("source_url") != src.get("url"):
            raise ValueError(f"{group}/{name}: observation source URL mismatch")
        if obs.get("target_date") != out["trading_date"]:
            raise ValueError(f"{group}/{name}: observation target date mismatch")
        is_fg=group=="risk" and name=="fear_greed"
        screenshot=obs.get("read_method")=="USER_PROVIDED_SCREENSHOT"
        valid=(obs.get("status")=="VERIFIED" and obs.get("observed_date")==out["trading_date"]
               and obs.get("instrument_identity_status")=="VERIFIED"
               and obs.get("field_mapping_status")=="VERIFIED"
               and obs.get("observed_value") is not None and obs.get("observed_change") is not None
               and (screenshot or obs.get("source_page_fetched") is True))
        if not valid:
            if obs.get("read_status")=="MARKET_CLOSED" or obs.get("status")=="MARKET_CLOSED":
                if group=="sectors":
                    out["sectors"][name]="休市"
                    src["change_display"]="休市"
                else:
                    item["display"]="休市"; item["change_display"]="休市"
                src["verification_status"]="CLOSED"
                src["read_status"]="MARKET_CLOSED"
                src["source_page_fetched"]=bool(obs.get("source_page_fetched"))
                continue
            if group=="sectors": out["sectors"][name]="待核實"
            else:
                item["display"]="待核實"; item["change_display"]="待核實"
            src["verification_status"]="PENDING"
            src["read_status"]=obs.get("read_status") or obs.get("status") or "PENDING"
            src["source_page_fetched"]=bool(obs.get("source_page_fetched"))
            pending.append(f"{group}/{name}")
            continue
        fmt=src["_stage2_format"]; close_spec=fmt["close"]; change_spec=fmt["change"]
        raw_close=obs["observed_value"]; raw_change=obs["observed_change"]
        close_num=_decimal(raw_close); src["close_value"]=float(close_num)
        src["daily_change_percent"]=float(_decimal(raw_change)) if not is_fg else None
        src["history_close"]=float(close_num) if group not in ("energy","metals") else _fmt(raw_close,close_spec)
        if group=="sectors":
            change_text=_fmt(raw_change,change_spec,force_sign=True)
            src["history_change"]=float(_decimal(raw_change))
            src["change_display"]=change_text
            out["sectors"][name]=change_text
        elif is_fg:
            score=int(close_num)
            band=str(raw_change)
            src["score_value"]=score; src["source_score_value"]=score
            src["cnn_target_date_score"]=score; src["band"]=band
            src["history_close"]=score; src["history_change"]=None
            item["display"]=str(score); item["change_display"]=band
        else:
            item["display"]=_fmt(raw_close,close_spec)
            if group=="bonds":
                pct=_decimal(raw_change)
                previous=close_num/(Decimal(1)+pct/Decimal(100))
                bp=(close_num-previous)*Decimal(100)
                bp_spec={"decimals":1,"commas":False,"plus":True,"prefix":"","suffix":""}
                item["change_display"]=_fmt(bp,bp_spec)+" bp"
                src["history_change"]=float(pct)
            else:
                change_text=_fmt(raw_change,change_spec,force_sign=True)
                item["change_display"]=change_text
                src["history_change"]=change_text if group in ("energy","metals") else float(_decimal(raw_change))
        src["verification_status"]="VERIFIED"
        src["data_date"]=out["trading_date"]
        src["checked_at_tw"]=obs.get("finished_at_tw") or obs.get("captured_at_taipei")
        src["read_method"]=obs.get("read_method")
        src["read_status"]=obs.get("read_status") or "CURRENT_RUN_OBSERVATION_CONFIRMED"
        src["observed_value"]=raw_close; src["observed_change"]=raw_change
        src["instrument_identity"]=obs.get("instrument_identity")
        src["source_page_fetched"]=bool(obs.get("source_page_fetched"))
        src["browser_observation_record_sha256"]=obs.get("observation_record_sha256")
        src.pop("_stage2_format",None)
        verified+=1
    out["stage2_market_bootstrap"]={"status":"POPULATED" if not pending else "PARTIAL",
        "preexisting_market_values_used":False,"row_count":44,"verified_count":verified,
        "pending_count":len(pending),"pending_rows":pending,"report_date":out["report_date"],
        "trading_date":out["trading_date"],"observation_bundle_sha256":payload.get("bundle_sha256")}
    return out

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    b=sub.add_parser("blank"); b.add_argument("--data",required=True); b.add_argument("--output",required=True)
    a=sub.add_parser("apply"); a.add_argument("--data",required=True); a.add_argument("--observations",required=True); a.add_argument("--output",required=True)
    args=p.parse_args()
    source=json.loads(Path(args.data).read_text(encoding="utf-8"))
    if args.mode=="blank": result=blank_fixture(source)
    else:
        payload=json.loads(Path(args.observations).read_text(encoding="utf-8"))
        result=populate_fixture(source,payload)
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary=result.get("stage2_market_bootstrap",{})
    print(json.dumps({"output":str(path),"status":summary.get("status"),"verified_count":summary.get("verified_count",0),"pending_count":summary.get("pending_count",0),"preexisting_market_values_used":summary.get("preexisting_market_values_used")},ensure_ascii=False))

if __name__=="__main__": main()
