#!/usr/bin/env python3
"""Build a SHA-bound Stage 2-only receipt from the blank-input 44-row market run."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_GROUPS={"global_markets":17,"sectors":11,"bonds":3,"fx":6,"energy":2,"metals":2,"risk":3}
OFFICIAL_CALENDAR_HOSTS={"nyse.com","nasdaq.com","jpx.co.jp","cao.go.jp","global.krx.co.kr",
    "twse.com.tw","sgx.com","asx.com.au","sse.com.cn","szse.cn","hkex.com.hk",
    "londonstockexchange.com","deutsche-boerse.com","euronext.com","stoxx.com","sifma.org",
    "cmegroup.com","theice.com","cboe.com","ice.com"}

def official_calendar_url(value):
    try:
        parsed=urlparse(str(value or ""))
        host=(parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme=="https" and any(host==d or host.endswith("."+d) for d in OFFICIAL_CALENDAR_HOSTS)
    except ValueError:
        return False

def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical_sha(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def num(value):
    if value is None: return None
    text=str(value).replace(",","").replace("$","").replace("%","").replace("+","").replace("−","-").strip()
    try: return Decimal(text)
    except (InvalidOperation,ValueError): return None

def rows_for_fixture(data):
    rows=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for name,item in (data.get(group) or {}).items():
            rows.append((group,name,item,item.get("source") or {}))
    for name,value in (data.get("sectors") or {}).items():
        rows.append(("sectors",name,{"display":value},(data.get("sector_sources") or {}).get(name) or {}))
    return rows

def validate_inputs(data,audit,manifest,observations,report_date):
    if data.get("report_date")!=report_date: raise ValueError("fixture report_date mismatch")
    trading_date=data.get("trading_date")
    if audit.get("status")!="PASS" or audit.get("verification_scope")!="METADATA_AND_DATE_ONLY":
        raise ValueError("metadata/date audit is not PASS or has an unexpected scope")
    if audit.get("report_date")!=report_date or audit.get("trading_date")!=trading_date or audit.get("indicator_count")!=44:
        raise ValueError("metadata/date audit report/trading date or 44-row count mismatch")
    if audit.get("group_counts")!=EXPECTED_GROUPS: raise ValueError("metadata/date audit group counts mismatch")
    if audit.get("source_pages_fetched") is not False or audit.get("displayed_values_independently_reconciled") is not False:
        raise ValueError("metadata/date audit falsely claims source-value verification")
    if data.get("stage2_market_bootstrap",{}).get("preexisting_market_values_used") is not False:
        raise ValueError("Stage 2 input was not proven to start without preexisting market values")
    if observations.get("report_date")!=report_date or observations.get("trading_date")!=trading_date:
        raise ValueError("observation bundle report/trading date mismatch")
    obs_rows=observations.get("observations") or []
    obs_map={(r.get("group"),r.get("name")):r for r in obs_rows}
    if len(obs_rows)!=44 or len(obs_map)!=44: raise ValueError("observation bundle must contain 44 unique rows")
    for row in obs_rows:
        digest=row.get("observation_record_sha256")
        if digest!=canonical_sha({k:v for k,v in row.items() if k!="observation_record_sha256"}):
            raise ValueError(f"observation canonical SHA mismatch: {row.get('group')}/{row.get('name')}")
        from datetime import date
        try: target_day=date.fromisoformat(str(row.get("target_date")))
        except ValueError as exc: raise ValueError(f"observation target date malformed: {row.get('name')}") from exc
        if target_day>date.fromisoformat(report_date): raise ValueError(f"observation target date is after report date: {row.get('name')}")
    manifest_rows=manifest.get("rows") or []
    manifest_map={(r.get("group"),r.get("name")):r for r in manifest_rows}
    if len(manifest_rows)!=44 or len(manifest_map)!=44: raise ValueError("manifest must contain 44 unique rows")
    expected={(g,n) for g,n,_,_ in rows_for_fixture(data)}
    if set(obs_map)!=expected or set(manifest_map)!=expected: raise ValueError("fixture, observations and manifest identities differ")
    if manifest.get("report_date")!=report_date or manifest.get("trading_date")!=trading_date:
        raise ValueError("manifest report/trading date mismatch")
    if manifest.get("row_count")!=44: raise ValueError("manifest row_count is not 44")
    verified=manifest.get("verified_count"); pending=manifest.get("pending_count"); closed=manifest.get("closed_count",0)
    if any(not isinstance(x,int) or x<0 for x in (verified,pending,closed)) or verified+pending+closed!=44:
        raise ValueError("manifest verified/pending/closed counts do not reconcile to 44")
    market_status_counts={}
    for row in manifest_rows:
        state=row.get("market_data_status")
        if state is None:
            state=("VERIFIED" if row.get("verification_status")=="VERIFIED" else
                   "BACKUP_VERIFIED" if row.get("verification_status")=="BACKUP_VERIFIED" else
                   "CLOSED" if row.get("verification_status")=="CLOSED" else "PENDING")
        market_status_counts[state]=market_status_counts.get(state,0)+1
    if sum(market_status_counts.values())!=44:
        raise ValueError("manifest market data status counts do not reconcile to 44")
    declared_market_counts=manifest.get("market_status_counts")
    if declared_market_counts is not None and declared_market_counts!=market_status_counts:
        raise ValueError("manifest market_data_status counts disagree with its rows")
    if manifest.get("status") not in ("PASS","PARTIAL","PENDING"): raise ValueError("manifest status is invalid")
    if manifest.get("prior_observation_reused_count")!=0: raise ValueError("manifest reused a prior observation")
    if manifest.get("observation_record_hash_missing_count")!=0: raise ValueError("manifest contains missing observation record hashes")
    if manifest.get("displayed_values_reconciled") is not (pending==0 and verified+closed==44):
        raise ValueError("manifest reconciliation summary disagrees with row counts")
    if manifest.get("status")=="PASS" and pending!=0: raise ValueError("manifest PASS cannot contain pending rows")
    fixture_map={(g,n):(item,src) for g,n,item,src in rows_for_fixture(data)}
    row_receipts=[]; pending_rows=[]
    for key,obs in obs_map.items():
        mr=manifest_map[key]; group,name=key; item,src=fixture_map[key]
        row_data_date=src.get("data_date")
        if obs.get("target_date")!=row_data_date: raise ValueError(f"{group}/{name}: observation target date differs from fixture data_date")
        if obs.get("source_url")!=src.get("url") or mr.get("source_url")!=src.get("url"):
            raise ValueError(f"{group}/{name}: source URL differs across fixture/observation/manifest")
        if mr.get("data_date")!=row_data_date: raise ValueError(f"{group}/{name}: manifest data date mismatch")
        record=mr.get("browser_observation_record")
        status=mr.get("verification_status")
        if record is not None:
            if mr.get("observation_record_sha256")!=canonical_sha(record):
                raise ValueError(f"{group}/{name}: manifest record SHA mismatch")
            record_date=record.get("data_date") or record.get("target_date")
            if record.get("source_url")!=obs.get("source_url") or record_date!=row_data_date:
                raise ValueError(f"{group}/{name}: manifest record does not bind to observation")
            if num(record.get("observed_value"))!=num(obs.get("observed_value")):
                raise ValueError(f"{group}/{name}: manifest observed value differs from observation bundle")
            if num(record.get("observed_change"))!=num(obs.get("observed_change")) and str(record.get("observed_change"))!=str(obs.get("observed_change")):
                raise ValueError(f"{group}/{name}: manifest observed change differs from observation bundle")
        elif status in ("VERIFIED","BACKUP_VERIFIED") or mr.get("observation_record_sha256") is not None:
            raise ValueError(f"{group}/{name}: verified manifest row is missing its observation record")
        if obs.get("status")=="VERIFIED":
            if status not in ("VERIFIED","BACKUP_VERIFIED"): raise ValueError(f"{group}/{name}: verified observation not verified in manifest")
            if src.get("verification_status") not in ("VERIFIED","BACKUP_VERIFIED"):
                raise ValueError(f"{group}/{name}: fixture source status does not match manifest")
            actual=src.get("score_value") if group=="risk" and name=="fear_greed" else src.get("close_value")
            if num(actual)!=num(obs.get("observed_value")): raise ValueError(f"{group}/{name}: fixture value differs from current observation")
        elif obs.get("read_status")=="MARKET_CLOSED":
            if status!="CLOSED" or src.get("verification_status")!="CLOSED":
                raise ValueError(f"{group}/{name}: closure state mismatch")
            closure=record or {}
            if (mr.get("evidence_status")!="MARKET_CLOSED_OFFICIAL_HOLIDAY_EVIDENCE"
                    or closure.get("read_status")!="MARKET_CLOSED"
                    or closure.get("source_url")!=obs.get("source_url")
                    or closure.get("target_date")!=row_data_date
                    or closure.get("source_page_fetched") is not True
                    or closure.get("prior_observation_reused") is not False
                    or closure.get("provenance")!="CURRENT_CHATGPT_WEB_OPEN_OBSERVATION"
                    or closure.get("read_method")!="CHATGPT_WEB_OPEN_HISTORICAL_PAGE"
                    or not official_calendar_url(closure.get("closure_evidence_url"))
                    or not closure.get("closure_evidence_reader_ref")
                    or not isinstance(closure.get("closure_evidence_line_start"),int)
                    or not isinstance(closure.get("closure_evidence_line_end"),int)
                    or closure.get("closure_evidence_line_end")<closure.get("closure_evidence_line_start")):
                raise ValueError(f"{group}/{name}: official closure evidence record incomplete")
            if (obs.get("source_page_fetched") is not True
                    or obs.get("target_date")!=row_data_date
                    or obs.get("prior_observation_reused") is not False):
                raise ValueError(f"{group}/{name}: closure observation does not bind current target date")
        else:
            if status in ("VERIFIED","BACKUP_VERIFIED"): raise ValueError(f"{group}/{name}: pending observation promoted to verified")
            evidence=obs.get("field_evidence") or {}
            screenshot_fields={k for k,v in evidence.items() if (v or {}).get("source_type")=="USER_PROVIDED_SCREENSHOT"}
            if not screenshot_fields:
                if src.get("close_value") is not None or src.get("score_value") is not None:
                    raise ValueError(f"{group}/{name}: pending row retained an old numeric value")
                display=data["sectors"][name] if group=="sectors" else item.get("display")
                if display!="待核實": raise ValueError(f"{group}/{name}: pending row does not display 待核實")
            pending_rows.append({"group":group,"name":name,"status":status,"read_status":obs.get("read_status")})
        row_receipts.append({
            "group":group,"name":name,"status":status,
            "market_data_status":mr.get("market_data_status") or ("VERIFIED" if status=="VERIFIED" else "BACKUP_VERIFIED" if status=="BACKUP_VERIFIED" else "CLOSED" if status=="CLOSED" else "PENDING"),
            "source_url":src.get("url"),"data_date":row_data_date,
            "observation_row_sha256":obs.get("observation_record_sha256"),
            "manifest_record_sha256":mr.get("observation_record_sha256"),
            "read_method":obs.get("read_method"),
            "source_page_fetched":obs.get("source_page_fetched") is True,
            "closure_evidence":({
                "url":(mr.get("browser_observation_record") or {}).get("closure_evidence_url"),
                "reader_ref":(mr.get("browser_observation_record") or {}).get("closure_evidence_reader_ref"),
                "line_start":(mr.get("browser_observation_record") or {}).get("closure_evidence_line_start"),
                "line_end":(mr.get("browser_observation_record") or {}).get("closure_evidence_line_end"),
            } if status=="CLOSED" else None),
        })
    if len(row_receipts)!=44: raise ValueError("receipt row register is incomplete")
    return {"verified_count":verified,"pending_count":pending,"closed_count":closed,
            "market_status_counts":market_status_counts,
            "row_receipts":row_receipts,"pending_rows":pending_rows}

def build_receipt(args):
    data=json.loads(Path(args.data).read_text(encoding="utf-8"))
    audit=json.loads(Path(args.audit).read_text(encoding="utf-8"))
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    observations=json.loads(Path(args.observations).read_text(encoding="utf-8"))
    counts=validate_inputs(data,audit,manifest,observations,args.report_date)
    paths={"fixture":args.data,"audit":args.audit,"manifest":args.manifest,"observations":args.observations}
    hashes={key:sha_file(path) for key,path in paths.items()}
    run_id=str(args.run_id or os.environ.get("GITHUB_RUN_ID") or "LOCAL")
    commit=str(args.commit_sha or os.environ.get("GITHUB_SHA") or "UNKNOWN")
    branch=str(args.branch or os.environ.get("GITHUB_REF_NAME") or "main")
    batch_seed="|".join([args.report_date,data["trading_date"],run_id,commit,*[hashes[k] for k in ("fixture","audit","manifest","observations")]])
    batch_id=hashlib.sha256(batch_seed.encode()).hexdigest()[:24]
    status="PARTIAL" if counts["pending_count"] else "PASS"
    return {
        "schema_version":"1.0","receipt_type":"TAC_STAGE2_MARKET_SNAPSHOT",
        "status":status,"freeze_point":"STAGE2_MARKET_SNAPSHOT_LOCKED",
        "downstream_market_access":"READ_ONLY","preexisting_market_values_used":False,
        "repository":"lion-invlab/lion-invlab.github.io","branch":branch,
        "commit_sha":commit,"workflow_run_id":run_id,"batch_id":batch_id,
        "report_date":args.report_date,"trading_date":data["trading_date"],
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "row_count":44,**{k:v for k,v in counts.items() if k!="row_receipts"},
        "manifest_status":manifest.get("status"),
        "source_pages_fetched":manifest.get("source_pages_fetched"),
        "displayed_values_reconciled":manifest.get("displayed_values_reconciled"),
        "displayed_values_independently_reconciled":manifest.get("displayed_values_independently_reconciled"),
        "screenshot_row_count":manifest.get("screenshot_row_count",0),
        "screenshot_field_count":manifest.get("screenshot_field_count",0),
        "mixed_field_row_count":manifest.get("mixed_field_row_count",0),
        "historical_page_only_row_count":manifest.get("historical_page_only_row_count",0),
        "input_files":{key:{"path":paths[key],"sha256":hashes[key]} for key in paths},
        "pending_rows":counts["pending_rows"],"rows":counts["row_receipts"],
        "warning":"PARTIAL means pending rows remain explicitly unresolved. This receipt freezes only the Stage 2 market snapshot; it is not a Stage 3-4 prebuild receipt or REVIEW_READY approval."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report-date",required=True); p.add_argument("--data",required=True)
    p.add_argument("--audit",required=True); p.add_argument("--manifest",required=True)
    p.add_argument("--observations",required=True); p.add_argument("--output",required=True)
    p.add_argument("--run-id"); p.add_argument("--commit-sha"); p.add_argument("--branch")
    a=p.parse_args(); receipt=build_receipt(a)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"status":receipt["status"],"batch_id":receipt["batch_id"],
        "row_count":receipt["row_count"],"verified_count":receipt["verified_count"],
        "pending_count":receipt["pending_count"],"closed_count":receipt["closed_count"],
        "sha256":sha_file(out)},ensure_ascii=False))

if __name__=="__main__": main()
