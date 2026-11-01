#!/usr/bin/env python3
"""TAC weekly calendar database prototype (stdlib only)."""
import argparse, json, re, sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "calendar" / "weeks"
VALID_STATUS = {"upcoming", "released", "cancelled", "postponed", "pending_verification"}

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def parse_dt(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include UTC offset")
        return parsed
    except Exception as exc:
        raise ValueError(f"invalid offset-aware event_date {value!r}: {exc}")

def validate_week(data):
    errors=[]
    if data.get("schema_version") != 1: errors.append("schema_version must be 1")
    if data.get("timezone") != "Asia/Taipei": errors.append("timezone must be Asia/Taipei")
    week_id=str(data.get("week_id",""))
    match=re.fullmatch(r"(\d{4})-W(\d{2})",week_id)
    if not match:
        errors.append("invalid ISO week_id")
        expected_start=None
    else:
        try:
            expected_start=date.fromisocalendar(int(match.group(1)),int(match.group(2)),1)
        except ValueError:
            errors.append("invalid ISO week number")
            expected_start=None
    try:
        start=date.fromisoformat(data["week_start"]); end=date.fromisoformat(data["week_end"])
        if end < start: errors.append("week_end precedes week_start")
        if expected_start and start != expected_start: errors.append("week_start does not match ISO week_id")
        if expected_start and end != expected_start + timedelta(days=4):
            errors.append("week_end must be Friday of the declared ISO week")
    except Exception: 
        errors.append("week_start/week_end must be ISO dates")
        start=end=None
    events=data.get("events",{})
    archive=data.get("status") in {"archive_candidate","archived"}
    for kind in ("economic","earnings"):
        records=events.get(kind,[])
        ids=set()
        for i,item in enumerate(records):
            prefix=f"{kind}[{i}]"
            eid=item.get("id")
            if not eid: errors.append(prefix+": missing id")
            elif eid in ids: errors.append(prefix+": duplicate id "+eid)
            else: ids.add(eid)
            try:
                dt=parse_dt(item["event_date"])
                if start and end and not (start <= dt.date() <= end):
                    errors.append(prefix+": event outside declared week")
            except Exception as exc: errors.append(prefix+": "+str(exc))
            stars=item.get("importance_stars")
            if not isinstance(stars,int) or stars not in (4,5):
                errors.append(prefix+": importance_stars must be TAC 4 or 5")
            elif archive and stars != 5:
                errors.append(prefix+": archived prior-week records must be TAC 5-star only")
            if archive and item.get("status") != "released":
                errors.append(prefix+": archived prior-week records must be released")
            if item.get("status") not in VALID_STATUS: errors.append(prefix+": invalid status")
            source=item.get("source")
            if not isinstance(source,dict) or not source.get("url"): errors.append(prefix+": source.url required")
    for kind in ("economic","earnings"):
        if data.get("coverage",{}).get(kind,{}).get("status") not in {"complete","incomplete","not_applicable"}:
            errors.append(f"coverage.{kind}.status invalid")
    return errors

def cmd_validate(args):
    data=load(args.file); errors=validate_week(data)
    print(json.dumps({"file":str(args.file),"week_id":data.get("week_id"),"economic":len(data.get("events",{}).get("economic",[])),"earnings":len(data.get("events",{}).get("earnings",[])),"errors":errors},ensure_ascii=False,indent=2))
    return 1 if errors else 0

def cmd_upsert(args):
    path=Path(args.file); data=load(path); kind=args.kind
    if kind not in ("economic","earnings"): raise ValueError("kind must be economic or earnings")
    incoming=load(args.event)
    if isinstance(incoming,list): incoming=incoming[0]
    if not incoming.get("id"): raise ValueError("event.id is required")
    rows=data["events"][kind]; old=next((x for x in rows if x.get("id")==incoming["id"]),None)
    if old and old == incoming:
        print(json.dumps({"action":"unchanged","event_id":incoming["id"],"week_id":data["week_id"]},ensure_ascii=False))
        return 0
    action="updated" if old else "inserted"
    if old: rows[rows.index(old)]=incoming
    else: rows.append(incoming)
    now=args.at or datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    data["updated_at"]=now
    data.setdefault("audit",[]).append({"at":now,"action":"event_"+action,"event_id":incoming["id"],"note":"Idempotent upsert"})
    errors=validate_week(data)
    if errors: raise ValueError("; ".join(errors))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"action":action,"event_id":incoming["id"],"week_id":data["week_id"]},ensure_ascii=False))
    return 0

def cmd_snapshot(args):
    data=load(args.file); report_day=date.fromisoformat(args.report_date)
    errors=validate_week(data)
    if errors: raise ValueError("current week invalid: "+"; ".join(errors))
    start=date.fromisoformat(data["week_start"]); end=date.fromisoformat(data["week_end"])
    if not start <= report_day <= end: raise ValueError("report date outside week")
    result={"meta":{"report_date":args.report_date,"week_id":data["week_id"],"timezone":"Asia/Taipei","database_updated_at":data.get("updated_at"),"wr_version":data.get("wr_version"),"previous_week_id":None},"economic_calendar":[],"earnings_calendar":[],"coverage":{}}
    for kind in ("economic","earnings"):
        key="economic_calendar" if kind=="economic" else "earnings_calendar"
        rows=[x for x in data["events"][kind] if int(x.get("importance_stars",0)) in (4,5)]
        rows.sort(key=lambda x:parse_dt(x["event_date"]))
        result[key]=rows
        result["coverage"][key]=data["coverage"][kind]
    if args.previous_week_file:
        prev=load(args.previous_week_file)
        prev_errors=validate_week(prev)
        if prev_errors: raise ValueError("previous week invalid: "+"; ".join(prev_errors))
        if prev.get("status") not in {"archive_candidate","archived"}:
            raise ValueError("previous week must be archive_candidate or archived")
        expected_previous_monday=start-timedelta(days=7)
        if date.fromisoformat(prev["week_start"]) != expected_previous_monday:
            raise ValueError("previous-week file is not the immediately preceding ISO week")
        result["meta"]["previous_week_id"]=prev.get("week_id")
        for kind in ("economic","earnings"):
            key="previous_economic_calendar" if kind=="economic" else "previous_earnings_calendar"
            rows=[x for x in prev["events"][kind] if int(x.get("importance_stars",0))==5 and x.get("status")=="released"]
            rows.sort(key=lambda x:parse_dt(x["event_date"]).date(),reverse=True)
            result[key]=rows
            result["coverage"][key]=prev["coverage"][kind]
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":args.output,"economic":len(result["economic_calendar"]),"earnings":len(result["earnings_calendar"]),"coverage":{k:v["status"] for k,v in result["coverage"].items()}},ensure_ascii=False,indent=2))
    return 0


def cmd_apply_snapshot(args):
    content=load(args.content); snap=load(args.snapshot)
    report_date=content.get("meta",{}).get("report_date")
    if report_date != snap.get("meta",{}).get("report_date"):
        raise ValueError("daily content and calendar snapshot report_date mismatch")
    array_keys=("economic_calendar","earnings_calendar","previous_economic_calendar","previous_earnings_calendar")
    coverage_keys=array_keys
    for key in array_keys:
        if not isinstance(snap.get(key),list): raise ValueError("snapshot missing calendar array "+key)
        content[key]=snap[key]
    content.setdefault("coverage",{})
    for key in coverage_keys:
        if not isinstance(snap.get("coverage",{}).get(key),dict):
            raise ValueError("snapshot missing coverage "+key)
        content["coverage"][key]=snap["coverage"][key]
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(content,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(output),"report_date":report_date,
      "calendar_counts":{key:len(content[key]) for key in array_keys},
      "coverage":{key:content["coverage"][key]["status"] for key in coverage_keys},
      "non_calendar_content_preserved":True},ensure_ascii=False,indent=2))
    return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("validate"); v.add_argument("--file",required=True); v.set_defaults(fn=cmd_validate)
    u=sub.add_parser("upsert"); u.add_argument("--file",required=True); u.add_argument("--kind",required=True); u.add_argument("--event",required=True); u.add_argument("--at"); u.set_defaults(fn=cmd_upsert)
    s=sub.add_parser("snapshot"); s.add_argument("--file",required=True); s.add_argument("--report-date",required=True); s.add_argument("--output",required=True); s.add_argument("--previous-week-file"); s.set_defaults(fn=cmd_snapshot)
    m=sub.add_parser("apply-snapshot"); m.add_argument("--content",required=True); m.add_argument("--snapshot",required=True); m.add_argument("--output",required=True); m.set_defaults(fn=cmd_apply_snapshot)
    a=p.parse_args()
    try: return a.fn(a)
    except Exception as exc: print("ERROR:",exc,file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
