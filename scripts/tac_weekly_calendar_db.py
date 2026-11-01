#!/usr/bin/env python3
"""TAC weekly calendar database prototype (stdlib only)."""
import argparse, json, re, sys
from datetime import date, datetime
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
    if not re.fullmatch(r"\d{4}-W\d{2}", str(data.get("week_id",""))): errors.append("invalid ISO week_id")
    try:
        start=date.fromisoformat(data["week_start"]); end=date.fromisoformat(data["week_end"])
        if end < start: errors.append("week_end precedes week_start")
    except Exception: errors.append("week_start/week_end must be ISO dates")
    events=data.get("events",{})
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
                if "start" in locals() and not (start <= dt.date() <= end):
                    errors.append(prefix+": event outside declared week")
            except Exception as exc: errors.append(prefix+": "+str(exc))
            stars=item.get("importance_stars")
            if not isinstance(stars,int) or not 1 <= stars <= 5: errors.append(prefix+": importance_stars must be integer 1..5")
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
    action="updated" if old else "inserted"
    if old: rows[rows.index(old)]=incoming
    else: rows.append(incoming)
    now=args.at or datetime.now().astimezone().isoformat(timespec="seconds")
    data["updated_at"]=now
    data.setdefault("audit",[]).append({"at":now,"action":"event_"+action,"event_id":incoming["id"],"note":"Idempotent upsert"})
    errors=validate_week(data)
    if errors: raise ValueError("; ".join(errors))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"action":action,"event_id":incoming["id"],"week_id":data["week_id"]},ensure_ascii=False))
    return 0

def cmd_snapshot(args):
    data=load(args.file); report_day=date.fromisoformat(args.report_date)
    start=date.fromisoformat(data["week_start"]); end=date.fromisoformat(data["week_end"])
    if not start <= report_day <= end: raise ValueError("report date outside week")
    result={"meta":{"report_date":args.report_date,"week_id":data["week_id"],"timezone":"Asia/Taipei","database_updated_at":data.get("updated_at"),"wr_version":data.get("wr_version")},"economic_calendar":[],"earnings_calendar":[],"coverage":{}}
    for kind in ("economic","earnings"):
        key="economic_calendar" if kind=="economic" else "earnings_calendar"
        rows=[x for x in data["events"][kind] if int(x.get("importance_stars",0)) in (4,5)]
        rows.sort(key=lambda x:parse_dt(x["event_date"]))
        result[key]=rows
        result["coverage"][key]=data["coverage"][kind]
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":args.output,"economic":len(result["economic_calendar"]),"earnings":len(result["earnings_calendar"]),"coverage":{k:v["status"] for k,v in result["coverage"].items()}},ensure_ascii=False,indent=2))
    return 0

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("validate"); v.add_argument("--file",required=True); v.set_defaults(fn=cmd_validate)
    u=sub.add_parser("upsert"); u.add_argument("--file",required=True); u.add_argument("--kind",required=True); u.add_argument("--event",required=True); u.add_argument("--at"); u.set_defaults(fn=cmd_upsert)
    s=sub.add_parser("snapshot"); s.add_argument("--file",required=True); s.add_argument("--report-date",required=True); s.add_argument("--output",required=True); s.set_defaults(fn=cmd_snapshot)
    a=p.parse_args()
    try: return a.fn(a)
    except Exception as exc: print("ERROR:",exc,file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
