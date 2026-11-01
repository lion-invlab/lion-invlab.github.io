#!/usr/bin/env python3
"""Conservative adapter for one selected live FedWatch source."""
import argparse, json, re, sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

URL = "https://www.investing.com/central-banks/fed-rate-monitor"
EXPECTED = {"3.75-4.00", "4.00-4.25"}
OFFSETS = {"EDT":-4,"EST":-5,"CDT":-5,"CST":-6,"MDT":-6,"MST":-7,"PDT":-7,"PST":-8}
MONTHS = {m:i for i,m in enumerate(("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"),1)}

def source_time(s):
    m=re.fullmatch(r"([A-Za-z]{3}) (\d{1,2}), (\d{4}) (\d{1,2}):(\d{2})\s*(AM|PM)\s*(EDT|EST|CDT|CST|MDT|MST|PDT|PST)",s.strip(),re.I)
    if not m: raise ValueError("來源更新時間格式無法解析")
    mon,day,year,hour,minute,ampm,zone=m.groups()
    h=int(hour)%12+(12 if ampm.upper()=="PM" else 0)
    local=datetime(int(year),MONTHS[mon.title()],int(day),h,int(minute))
    return (local-timedelta(hours=OFFSETS[zone.upper()])).replace(tzinfo=timezone.utc)

def rate_band(s):
    m=re.fullmatch(r"\s*(\d+(?:\.\d{1,3})?)\s*-\s*(\d+(?:\.\d{1,3})?)\s*",str(s))
    if not m: raise ValueError("利率區間格式無法解析")
    return f"{float(m.group(1)):.2f}-{float(m.group(2)):.2f}"

def convert(d, report_date, now=None):
    now=now or datetime.now(timezone.utc)
    name=d.get("selected_source"); url=d.get("source_url")
    meeting=None; updated=None; probs=[]; status="pending_verification"; reasons=[]
    if d.get("status")!="selected_for_review":
        reasons.append("來源選擇器沒有選出有效來源")
    else:
        try:
            if name!="Investing.com Fed Rate Monitor" or url!=URL:
                raise ValueError("目前僅接受已定義的 Investing.com 即時備援資料契約")
            stamps=d.get("source_updated_at")
            if not isinstance(stamps,list) or len(stamps)!=1: raise ValueError("來源更新時間缺漏或不唯一")
            updated=source_time(stamps[0])
            observed=datetime.fromisoformat(d["source_observed_at"].replace("Z","+00:00"))
            age=(now-updated).total_seconds()/3600
            if age < -1 or age > 72: raise ValueError("來源更新時間超過 72 小時有效窗")
            if abs((now-observed).total_seconds())>6*3600: raise ValueError("擷取時間不是本次執行時的近期資料")
            rd=date.fromisoformat(report_date)
            choices=[]
            for m in d.get("meetings",[]):
                try: md=datetime.strptime(m["meeting_date"],"%b %d, %Y").date()
                except Exception: md=date.fromisoformat(m["meeting_date"])
                if md>rd: choices.append((md,m))
            if not choices: raise ValueError("找不到報告日之後的會議")
            md,m=sorted(choices,key=lambda x:x[0])[0]; meeting=md.isoformat()
            parsed=[]
            for p in m.get("probabilities",[]):
                band=rate_band(p["target_rate"]); value=float(p["probability"])
                if not 0<=value<=100: raise ValueError("機率超出 0–100")
                parsed.append((band,value))
            if len(parsed)!=2 or len({x[0] for x in parsed})!=2: raise ValueError("來源不是兩個唯一利率區間；母版固定只有兩格")
            if {x[0] for x in parsed}!=EXPECTED: raise ValueError("來源利率區間與母版固定兩格不一致")
            if abs(sum(x[1] for x in parsed)-100)>.5: raise ValueError("機率合計不約等於 100%")
            probs=[{"rate_range":a.split("-")[0]+"%–"+a.split("-")[1]+"%","probability":b} for a,b in parsed]
            status="verified"
            reasons.append("單一即時來源、下一場會議、母版兩個利率區間及機率合計均通過驗證")
        except Exception as e: reasons.append("待核實："+str(e))
    source={"name":name,"url":url} if name and url else None
    observed=d.get("source_observed_at")
    notes=" ".join(reasons)
    if observed: notes+=f"；實際擷取時間 {observed}"
    if d.get("source_updated_at"): notes+=f"；來源 Updated {d['source_updated_at']}"
    return {"report_date":report_date,"fedwatch":{"target_meeting":meeting,"updated_at":updated.isoformat() if updated else None,"source":source,"probabilities":probs if status=="verified" else [],"status":status,"notes":notes or "沒有可驗證的即時來源，不沿用舊值"}}

def self_test():
    d={"status":"selected_for_review","selected_source":"Investing.com Fed Rate Monitor","source_url":URL,"source_observed_at":"2026-11-01T00:00:00Z","source_updated_at":["Oct 31, 2026 12:35AM EDT"],"meetings":[{"meeting_date":"Dec 9, 2026","probabilities":[{"target_rate":"3.75-4.00","probability":90},{"target_rate":"4.00-4.25","probability":10}]}]}
    now=datetime(2026,11,1,1,tzinfo=timezone.utc)
    x=convert(d,"2026-11-02",now)["fedwatch"]
    assert x["status"]=="verified" and x["updated_at"]=="2026-10-31T04:35:00+00:00"
    extra=json.loads(json.dumps(d)); extra["meetings"][0]["probabilities"].append({"target_rate":"4.25-4.50","probability":0})
    assert convert(extra,"2026-11-02",now)["fedwatch"]["status"]=="pending_verification"
    stale=json.loads(json.dumps(d)); stale["source_updated_at"]=["Oct 27, 2026 12:35AM EDT"]
    assert convert(stale,"2026-11-02",now)["fedwatch"]["status"]=="pending_verification"
    print("PASS: timestamp conversion; exact mother-range contract; extra band and stale data rejected")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--selected"); p.add_argument("--report-date"); p.add_argument("--output"); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if a.self_test: self_test(); return
    if not all((a.selected,a.report_date,a.output)): p.error("selected, report-date and output required")
    d=json.loads(Path(a.selected).read_text(encoding="utf-8")); out=convert(d,a.report_date)
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["fedwatch"]["status"],"meeting":out["fedwatch"]["target_meeting"],"source":out["fedwatch"]["source"],"notes":out["fedwatch"]["notes"]},ensure_ascii=False))
if __name__=="__main__":
    try: main()
    except Exception as e: print("FAIL:",e,file=sys.stderr); raise SystemExit(1)
