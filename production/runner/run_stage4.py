#!/usr/bin/env python3
"""Stage 4: validate current-run editorial research and merge it without changing market data."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator, FormatChecker

from stage_wr_preflight import stage_wr_preflight, require_stage_wr_receipt
from run_state import transition_state, validate_state

ROOT=Path(__file__).resolve().parents[2]
TZ=ZoneInfo("Asia/Taipei")
LAYERS=("political","policy_industry","macro","markets","strategy")
DOMAINS=("us_policy","us_china","geopolitics","trade_sanctions","major_economies","energy_resources")

def sha_bytes(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def sha(path:Path)->str:return sha_bytes(path.read_bytes())

def read_json(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def parse_tw(value:str)->datetime:
    raw=str(value).strip()
    try:
        dt=datetime.fromisoformat(raw.replace("Z","+00:00"))
    except ValueError:
        try:
            dt=datetime.strptime(raw,"%Y-%m-%d %H:%M")
        except ValueError:
            dt=datetime.strptime(raw,"%Y/%m/%d %H:%M")
    if dt.tzinfo is None:dt=dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)

def market_snapshot_digest(data:dict)->str:
    groups={k:data.get(k) for k in ("global_markets","sectors","sector_sources","bonds","fx","energy","metals","risk","fedwatch")}
    return sha_bytes(json.dumps(groups,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode())

def validate_research_bundle_binding(content:dict,context:dict,receipt:dict,bundle_path:Path)->dict:
    if receipt.get("status")!="PASS" or receipt.get("run_id")!=context.get("run_id") or receipt.get("report_date")!=context.get("report_date"):
        raise ValueError("Stage 4 research bundle receipt is not bound to this Run")
    if receipt.get("market_snapshot_sha256")!=content.get("market_snapshot_sha256"):
        raise ValueError("Stage 4 research bundle market snapshot SHA differs from editorial content")
    if content.get("research_bundle_sha256")!=receipt.get("bundle_sha256"):
        raise ValueError("Stage 4 editorial content research_bundle_sha256 differs from capture receipt")
    if not bundle_path.is_file() or sha(bundle_path)!=receipt.get("bundle_sha256"):
        raise ValueError("Stage 4 research bundle bytes do not match its receipt SHA-256")
    bundle=json.loads(bundle_path.read_text(encoding="utf-8"))
    if (bundle.get("run_id")!=context.get("run_id")
            or bundle.get("report_date")!=context.get("report_date")
            or bundle.get("trading_date")!=context.get("trading_date")
            or receipt.get("trading_date")!=context.get("trading_date")
            or bundle.get("market_snapshot_sha256")!=content.get("market_snapshot_sha256")):
        raise ValueError("Stage 4 research bundle contents are not bound to the exact Run, dates and market snapshot")
    return {"path":str(bundle_path.relative_to(ROOT)),"sha256":receipt["bundle_sha256"]}

def validate_stage4_wr_handoff(capture:dict, editorial:dict, wr_preflight:dict)->dict:
    """Ensure the Stage 4 instruction text is present; no WR hash attestation is required."""
    instructions=capture.get("stage4_work_instructions") or {}
    full_text=instructions.get("full_text")
    if (capture.get("status")!="AWAITING_EDITORIAL_INPUT"
            or instructions.get("path")!="production/stages/STAGE_4_NEWS_ANALYSIS.md"
            or not isinstance(full_text,str) or not full_text.strip()):
        raise ValueError("Stage 4 handoff is missing the complete Stage 4 instructions")
    return {"status":"LOADED","stage4_wr_path":instructions["path"],"full_text_available":True}

def normalize_news_publication_times(content:dict)->list[dict]:
    """Recompute Taiwan publication timestamps from preserved source time and IANA timezone."""
    changes=[]
    for section in ("focus_news","headlines"):
        for index,item in enumerate(content.get(section,[])):
            raw=str(item.get("published_at_source") or "").strip()
            zone=str(item.get("source_timezone") or "").strip()
            if not raw or not zone:
                continue
            tz=ZoneInfo(zone)
            parsed=None
            candidates=[raw]
            parts=raw.rsplit(" ",1)
            if len(parts)==2:
                candidates.append(parts[0])
            for candidate in candidates:
                for fmt in ("%Y-%m-%d %H:%M","%Y-%m-%d %I:%M %p","%b %d %Y %I:%M %p"):
                    try:
                        parsed=datetime.strptime(candidate,fmt)
                        break
                    except ValueError:
                        pass
                if parsed is not None:
                    break
            if parsed is None:
                raise ValueError(f"{section}[{index}] source publication timestamp cannot be parsed: {raw!r}")
            expected=parsed.replace(tzinfo=tz).astimezone(TZ).strftime("%Y-%m-%d %H:%M")
            supplied=str(item.get("published_at_tw") or "").strip()
            if supplied!=expected:
                changes.append({"section":section,"index":index,"source":raw,"timezone":zone,
                                "previous_taipei":supplied,"normalized_taipei":expected})
                item["published_at_tw"]=expected
    return changes

def validate_content(content:dict,context:dict,data:dict,bundle:dict|None=None)->dict:
    current_snapshot_sha=market_snapshot_digest(data)
    schema=json.loads((ROOT/"production/input/report-content.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors=sorted(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(content),key=lambda e:list(e.path))
    if errors:
        raise ValueError("Stage 4 JSON Schema errors: "+"; ".join(f"{'/'.join(map(str,e.path))}: {e.message}" for e in errors[:20]))
    report_date=date.fromisoformat(context["report_date"])
    if content.get("run_id")!=context["run_id"]:
        raise ValueError("Stage 4 content Run ID differs from the Stage 1 Run")
    if content["report_date"]!=context["report_date"] or content["trading_date"]!=context["trading_date"]:
        raise ValueError("Stage 4 content report_date/trading_date differs from Stage 1 Run context")
    if content.get("market_snapshot_sha256")!=current_snapshot_sha:
        raise ValueError("Stage 4 content was not bound to this exact frozen Stage 2 market snapshot")
    cutoff=parse_tw(content["news_cutoff_taipei"])
    production_date=report_date-timedelta(days=2) if report_date.weekday()==0 else report_date
    if report_date.weekday()==0:
        # Monday report is produced Saturday; cutoff must be the exact Stage 4 capture cutoff.
        if cutoff.date()!=production_date:
            raise ValueError("Monday-dated report news_cutoff_taipei must be on its Saturday production date")
        if bundle is not None:
            expected_bundle_cutoff=parse_tw(bundle["news_window"]["target_cutoff_taipei"])
            if cutoff!=expected_bundle_cutoff:
                raise ValueError("Monday-dated report news_cutoff_taipei must exactly match the Saturday Stage 4 bundle cutoff")
    else:
        expected_date=datetime.combine(production_date,time(5,25),TZ)
        if cutoff.date()!=production_date or cutoff>expected_date+timedelta(minutes=30):
            raise ValueError("news_cutoff_taipei must be on production date and no later than 05:55 Taiwan time")
    window_start_date=report_date-timedelta(days=3 if report_date.weekday()==0 else 1)
    window_start=datetime.combine(window_start_date,time(12,0),TZ)
    news_counts={}
    all_urls=set()
    for key,expected in (("focus_news",5),("headlines",10)):
        seen=set()
        for idx,item in enumerate(content[key]):
            url=item["url"]
            if url in seen or url in all_urls:raise ValueError(f"Duplicate URL across report news sections: {url}")
            seen.add(url);all_urls.add(url)
            published=parse_tw(item["published_at_tw"])
            if not window_start<=published<=cutoff:
                raise ValueError(f"{key}[{idx}] published_at_tw is outside the report window: {item['published_at_tw']}")
        news_counts[key]=expected
    if len(content["political_scan"]["domains_checked"])!=6 or tuple(content["political_scan"]["domains_checked"])!=DOMAINS:
        raise ValueError("Political scan must check the six required domains in canonical order")
    if not content["political_scan"]["findings"] and not str(content["political_scan"].get("no_material_change_note") or "").strip():
        raise ValueError("Empty political scan requires no_material_change_note")
    for idx,finding in enumerate(content["political_scan"]["findings"]):
        source_url=str(finding.get("source_url") or "")
        if finding.get("domain") not in DOMAINS or not finding.get("transmission") or not source_url.startswith("https://"):
            raise ValueError(f"Political scan finding {idx} requires a recognized domain, HTTPS source and transmission")
        if not finding.get("published_at") or not finding.get("checked_at"):
            raise ValueError(f"Political scan finding {idx} requires publication and check timestamps")
    for layer in LAYERS:
        for idx,evidence in enumerate(content["market_analysis"][layer]["sources"]):
            if not evidence.get("label") or not evidence.get("status") or not evidence.get("url"):
                raise ValueError(f"market_analysis.{layer}.sources[{idx}] requires label, URL and status")
            if not evidence.get("url","").startswith("https://"):
                raise ValueError(f"market_analysis.{layer}.sources[{idx}] requires HTTPS source URL")
            if not evidence.get("published_at") and not evidence.get("checked_at"):
                raise ValueError(f"market_analysis.{layer}.sources[{idx}] requires published_at or checked_at")
    if report_date.weekday()!=0 and len(content["core_observation"].get("points",[]))!=4:
        raise ValueError("Weekday core_observation requires exactly four follow-up points")
    if report_date.weekday()==0 and not content["core_observation"].get("details"):
        raise ValueError("Monday core_observation requires a disclosure details paragraph")
    fg=(data.get("risk") or {}).get("fear_greed") or {}
    fg_source=fg.get("source") or {}
    fg_status=str(fg_source.get("verification_status") or "").upper()
    fg_display=str(fg.get("display") or "")
    market_text=" ".join(content["market_analysis"]["markets"]["paragraphs"])
    if fg_status=="VERIFIED":
        score=fg_source.get("source_score_value")
        if score is None:raise ValueError("Verified CNN current dashboard requires source_score_value")
        canonical=str(int(float(score)+0.5))
        if canonical!=fg_display or f"Fear & Greed {fg_display}" not in content["sentiment"]:
            raise ValueError("Sentiment must reflect the verified current CNN Fear & Greed score")
        if f"Fear & Greed {fg_display}" not in market_text:
            raise ValueError("Markets analysis must reflect the verified current CNN Fear & Greed score")
    elif fg_status=="BACKUP_VERIFIED":
        score=fg_source.get("backup_source_score_value")
        provider="FGScore" if "fgscore.com" in str(fg_source.get("url","")) else "Financial Context"
        if score is None or str(int(float(score)+0.5))!=fg_display:
            raise ValueError("Verified Fear & Greed backup score does not match display")
        if provider not in content["sentiment"] or "備援" not in content["sentiment"] or fg_display not in content["sentiment"]:
            raise ValueError("Sentiment must disclose Fear & Greed provider backup and score")
        if provider not in market_text or "備援" not in market_text or fg_display not in market_text:
            raise ValueError("Markets analysis must disclose Fear & Greed provider backup and score")
    elif fg_status in ("PENDING","TOOL_READ_FAILURE","SOURCE_NO_DATA","DATE_MISMATCH"):
        if fg_display!="待核實" or "Fear & Greed" not in content["sentiment"] or "待核實" not in content["sentiment"] or "不沿用" not in content["sentiment"]:
            raise ValueError("Unresolved Fear & Greed must be disclosed as 待核實 and must reject stale carry-forward")
        if "Fear & Greed" not in market_text or not any(x in market_text for x in ("待核實","未能核實")):
            raise ValueError("Markets analysis must disclose unresolved Fear & Greed")
    else:
        raise ValueError(f"Unsupported Fear & Greed verification status: {fg_status!r}")
    level_items=content["key_levels"]["items"]
    if len(level_items) not in (0,5):raise ValueError("key_levels.items must be empty or contain exactly five cash-index items")
    if len(level_items)==5:
        required=("name","url","s2","s1","p","r1","r2","trading_date","quote_type")
        for idx,item in enumerate(level_items):
            missing=[k for k in required if not item.get(k)]
            if missing:raise ValueError(f"key_levels.items[{idx}] missing fields: {missing}")
            if item["trading_date"]!=context["trading_date"] or item["quote_type"]!="cash_index":
                raise ValueError(f"key_levels.items[{idx}] must use same-day cash-index OHLC")
    for layer in LAYERS:
        for row in content["market_analysis"][layer].get("supporting_market_rows",[]):
            group,name=row["group"],row["name"]
            if group=="sectors":
                item=(data.get("sector_sources") or {}).get(name)
                source=item or {}
            else:
                item=(data.get(group) or {}).get(name)
                source=(item or {}).get("source") or {} if isinstance(item,dict) else {}
            if item is None:raise ValueError(f"Unknown supporting market row: {group}/{name}")
            status=source.get("verification_status")
            if status not in ("VERIFIED","BACKUP_VERIFIED"):
                raise ValueError(f"Analysis layer {layer} cites non-verified market row {group}/{name}: {status}")
    return {"window_start":window_start,"cutoff":cutoff,"news_counts":news_counts}

def read_json(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--content")
    args=ap.parse_args()
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs_root=ROOT/"production/runs"
    if runs_root.is_symlink() or runs_root.resolve()!=runs_root.absolute() or run_dir.is_symlink():
        raise SystemExit("Stage 4 run directory must be a direct non-symlink child of production/runs")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs_root.resolve():
        raise SystemExit("Stage 4 run directory must be a direct non-symlink child of production/runs")
    context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
    wr_preflight=stage_wr_preflight("STAGE_4",context)
    state_path=run_dir/"run-state.json"
    state=read_json(state_path)
    validate_state(state,expected_run_id=context["run_id"])
    if state["stages"]["STAGE_3"]["status"]!="PASS" or state["stages"]["STAGE_4"]["status"]!="SUBMITTED":
        raise SystemExit("Stage 4 requires Stage 3 PASS and Stage 4 SUBMITTED in the authoritative Run state")
    fixture_path=run_dir/"report-data.json"
    stage2_receipt=json.loads((run_dir/"stage2-market-snapshot-receipt.json").read_text(encoding="utf-8"))
    stage3_receipt_path=run_dir/"stage3-calendar-receipt.json"
    stage3_receipt=json.loads(stage3_receipt_path.read_text(encoding="utf-8"))
    require_stage_wr_receipt(stage2_receipt,"STAGE_2",context)
    require_stage_wr_receipt(stage3_receipt,"STAGE_3",context)
    if stage2_receipt.get("run_id")!=context.get("run_id") or stage2_receipt.get("status") not in ("PASS","PARTIAL"):
        raise ValueError("Stage 2 receipt Run ID/status does not match this Run")
    if stage2_receipt.get("workflow_run_id")!=context.get("workflow_run_id"):
        raise ValueError("Stage 2 receipt workflow_run_id does not match the Stage 1 Run context")
    if stage3_receipt.get("run_id")!=context.get("run_id") or stage3_receipt.get("status")!="PASS":
        raise ValueError("Stage 3 receipt run identity/status mismatch")
    content_path=Path(args.content) if args.content else run_dir/"stage4-editorial-content.json"
    if not content_path.is_absolute():content_path=ROOT/content_path
    content_path=content_path.resolve()
    if content_path.parent!=run_dir or content_path.name!="stage4-editorial-content.json" or content_path.is_symlink():
        raise SystemExit("Stage 4 content must be the exact Run-scoped stage4-editorial-content.json file")
    if not content_path.is_file():
        raise SystemExit("Missing Run-scoped Stage 4 editorial content; date-global fallback is prohibited")
    content_sha256=sha(content_path)
    if state["stages"]["STAGE_4"].get("output_sha256")!=content_sha256:
        raise SystemExit("Stage 4 submitted state SHA does not match the exact Run-scoped editorial content")
    editorial=json.loads(content_path.read_text(encoding="utf-8"))
    timestamp_repairs=normalize_news_publication_times(editorial)
    stage3_receipt_sha256=sha(stage3_receipt_path)
    capture_path=run_dir/"capture-stage-receipt.json"
    if not capture_path.is_file():
        raise SystemExit("Stage 4 full-WR capture handoff is missing; refusing to start editorial merge.")
    try:
        editorial_wr_attestation=validate_stage4_wr_handoff(read_json(capture_path),editorial,wr_preflight)
    except ValueError as exc:
        raise SystemExit(str(exc))
    data=json.loads(fixture_path.read_text(encoding="utf-8"))
    bundle_receipt_path=run_dir/"stage4-research-bundle-receipt.json"
    bundle_path=run_dir/"stage4-research-bundle.json"
    if not bundle_receipt_path.is_file():
        raise ValueError("Stage 4 research bundle receipt is missing")
    bundle=read_json(bundle_path)
    bundle_binding=validate_research_bundle_binding(editorial,context,read_json(bundle_receipt_path),bundle_path)
    before=market_snapshot_digest(data)
    window=validate_content(editorial,context,data,bundle)
    data.update({
      "summary_title":editorial["summary_title"],
      "summary_points":editorial["summary_points"],
      "summary":"\n\n".join(f"{x['label']}｜{x['text']}" for x in editorial["summary_points"]),
      "focus_news":editorial["focus_news"],"headlines":editorial["headlines"],
      "sentiment":editorial["sentiment"],"market_sentiment":editorial.get("market_sentiment",editorial["sentiment"]),
      "market_analysis":editorial["market_analysis"],"political_scan":editorial["political_scan"],
      "core_observation":editorial["core_observation"],"observation":editorial["observation"],
      "key_levels":editorial["key_levels"],"market_comments":editorial["market_comments"],
      "news_cutoff_taipei":editorial["news_cutoff_taipei"],
      "news_window_taipei":editorial.get("news_window_taipei",f"{window['window_start'].strftime('%Y-%m-%d %H:%M')}–{window['cutoff'].strftime('%Y-%m-%d %H:%M')}"),
      "warning_note":editorial.get("warning_note",""),"quality_note":editorial.get("quality_note","")
    })
    if "earnings_health" in editorial:
        data["earnings_health"]=editorial["earnings_health"]
    if "pending_items" in editorial:data["pending_items"]=editorial["pending_items"]
    after=market_snapshot_digest(data)
    if before!=after:raise SystemExit("Stage 4 modified the frozen Stage 2 market snapshot")
    fixture_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    analysis={
      "schema_version":"1.0","run_id":context["run_id"],"report_date":context["report_date"],
      "run_id":context["run_id"],"market_snapshot_sha256":before,"research_bundle_sha256":bundle_binding["sha256"],
      "summary_points":editorial["summary_points"],"focus_news":editorial["focus_news"],
      "headlines":editorial["headlines"],"market_analysis":editorial["market_analysis"],
      "political_scan":editorial["political_scan"],"core_observation":editorial["core_observation"],
      "observation":editorial["observation"],"key_levels":editorial["key_levels"],
      "market_comments":editorial["market_comments"],"earnings_health":data.get("earnings_health"),"news_window_start_taipei":window["window_start"].isoformat(),
      "news_cutoff_taipei":window["cutoff"].isoformat()
    }
    analysis_path=run_dir/"analysis-data.json"
    analysis_path.write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={
      "schema_version":"1.0","stage":"STAGE_4_NEWS_ANALYSIS","status":"PASS",
      "run_id":context["run_id"],"report_date":context["report_date"],"trading_date":context["trading_date"],
      "news_counts":window["news_counts"],"publication_timestamp_normalizations":timestamp_repairs,"summary_points":len(editorial["summary_points"]),
      "analysis_layers":list(LAYERS),"political_domains":list(DOMAINS),
      "market_snapshot_sha256_before":before,"market_snapshot_sha256_after":after,
      "stage3_receipt_sha256":stage3_receipt_sha256,
      "editorial_run_binding":{"run_id":context["run_id"],"market_snapshot_sha256":before,"research_bundle_sha256":bundle_binding["sha256"]},
      "market_snapshot_unchanged":True,
      "editorial_input":{"path":str(content_path.relative_to(ROOT)),"sha256":sha(content_path)},
      "wr_preflight":wr_preflight,"state_version_before":state["state_version"],
      "editorial_worker_wr_attestation":editorial_wr_attestation,
      "research_bundle":bundle_binding,
      "outputs":{"analysis-data.json":sha(analysis_path),"report-data.json":sha(fixture_path)}
    }
    receipt_path=run_dir/"stage4-analysis-receipt.json"
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state=read_json(state_path)
    state=transition_state(state,stage="STAGE_4",expected_version=state["state_version"],expected_status="SUBMITTED",new_status="PASS",
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),input_sha256=content_sha256,
        output_sha256=sha(receipt_path),receipt_path=str(receipt_path.relative_to(ROOT)))
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
