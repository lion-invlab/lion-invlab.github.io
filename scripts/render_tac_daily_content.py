#!/usr/bin/env python3
"""Render validated TAC editorial JSON into an existing market-rendered mother-template copy."""
from __future__ import annotations
import argparse, copy, json, sys
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = ROOT / "scripts" / "tac_html_binding_map.json"
TZ = ZoneInfo("Asia/Taipei")
WD = ("一", "二", "三", "四", "五", "六", "日")
PROTECTED = {ROOT/"index.html", ROOT/"TAC_WORK_RULES.md",
 ROOT/"母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
 ROOT/"母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
 ROOT/"母版專區/mother-template-manifest.json"}

def read_json(p): return json.loads(p.read_text(encoding="utf-8"))
def dt(v):
    x=__import__("datetime").datetime.fromisoformat(v.replace("Z","+00:00"))
    if x.tzinfo is None: raise ValueError(f"timezone missing: {v}")
    return x.astimezone(TZ)
def date_label(v):
    x=dt(v); return f"{x.month}/{x.day}（{WD[x.weekday()]}）"
def slot(parent, selector, label):
    found=parent.select(selector)
    if len(found)!=1: raise ValueError(f"{label}: expected one {selector}, found {len(found)}")
    return found[0]
def put(node, value):
    node.clear(); node.append(NavigableString(str(value)))
def source_link(anchor, src):
    url=src["url"]
    if not url.startswith(("https://","http://")): raise ValueError("source URL must be HTTP(S)")
    anchor["href"]=url; anchor["target"]="_blank"
    rel=list(anchor.get("rel",[]))
    if "noopener" not in rel: rel.append("noopener")
    anchor["rel"]=rel
    label=src["name"]
    if src.get("published_at"): label += "｜發布 "+dt(src["published_at"]).strftime("%Y/%m/%d %H:%M")
    label += "｜擷取 "+dt(src["observed_at"]).strftime("%Y/%m/%d %H:%M")+"（台灣時間）"
    if src.get("notes"): label += "｜"+src["notes"]
    put(anchor,label)
def news(soup, selector, records, count, name):
    box=slot(soup,selector,name); cards=box.select(".newsitem")
    if len(cards)!=count or len(records)!=count:
        raise ValueError(f"{name}: need {count} template/content cards, got {len(cards)}/{len(records)}")
    for i,(card,item) in enumerate(zip(cards,records),1):
        if item["status"]!="verified": raise ValueError(f"{name}[{i}] not verified")
        put(slot(card,"h3",name+" headline"),(f"{i}. " if name=="focus_news" else f"{i:02d}｜")+item["headline"])
        put(slot(card,"p",name+" summary"),item["summary"])
        links=card.select(".newsmeta a")
        if len(links)!=1: raise ValueError(f"{name}[{i}]: expected one source link")
        source_link(links[0],item["source"])

def update_news_meta(soup, data):
    start=data["meta"].get("news_window_start"); end=data["meta"].get("news_window_end")
    if not start or not end: raise ValueError("news window start/end required for publication")
    window=dt(start).strftime("%Y/%m/%d %H:%M")+"–"+dt(end).strftime("%Y/%m/%d %H:%M")+"（台灣時間）"
    for sel,label in (("#global-focus","全球焦點"),("#headlines","市場熱門頭條")):
        box=slot(soup,sel,label)
        metas=box.select(".tab-panel-meta")
        if len(metas)!=1: raise ValueError(label+" metadata slot missing or duplicated")
        put(metas[0],label+"｜報告日期 "+data["meta"]["report_date"].replace("-","/")+"｜時間窗："+window)
        for warning in box.select(".news-window-warning"):
            put(warning,"新聞時間窗｜"+window+"。本區內容依原始報導發布時間篩選；來源與時間戳逐則列示。")

def update_section_dates(soup, report_day):
    monday=report_day-timedelta(days=report_day.weekday()); friday=monday+timedelta(days=4)
    span=f"{monday.month:02d}/{monday.day:02d}～{friday.month:02d}/{friday.day:02d}"
    for sel in ("#calendar .title small","#earnings .title small"):
        put(slot(soup,sel,"current week date range"),span+"｜台灣時間 UTC+8")
    if report_day.weekday()==0:
        prev_start=monday-timedelta(days=7); prev_end=prev_start+timedelta(days=4)
        prev=f"{prev_start.month:02d}/{prev_start.day:02d}～{prev_end.month:02d}/{prev_end.day:02d}"
        for sel in ("#last-week-calendar .title small","#last-week-earnings .title small"):
            put(slot(soup,sel,"previous week date range"),prev+"｜台灣時間 UTC+8")
    title=slot(soup,"#view .today-focus-title","observation title")
    put(title,"今日觀察重點｜"+report_day.strftime("%Y/%m/%d")+"（"+WD[report_day.weekday()]+"）")

def verify_template_controls(before, after):
    def radio_ids(s):
        return [(x.get("id"),x.get("name"),x.get("type")) for x in s.select('input[type="radio"]')]
    def label_refs(s):
        return [(x.get("for"),x.get_text(" ",strip=True)) for x in s.select("label[for]")]
    if radio_ids(before)!=radio_ids(after): raise ValueError("radio tab controls changed during editorial render")
    if label_refs(before)!=label_refs(after): raise ValueError("tab/plus-control labels changed during editorial render")
    if [str(x) for x in before.select("style,script")] != [str(x) for x in after.select("style,script")]:
        raise ValueError("template CSS or JavaScript changed during editorial render")
    for selector in ("#news-scan","#view","#calendar","#earnings"):
        if len(before.select(selector))!=len(after.select(selector)):
            raise ValueError("approved outer section count changed: "+selector)

def summary(soup, analysis):
    cards=soup.select("main.wrap > section.grid.two article.bluf")
    if len(cards)!=1: raise ValueError("approved summary/BLUF card not uniquely found")
    item=analysis["summary"]; ok=item["status"]=="verified"
    put(slot(cards[0],"h1","summary headline"),item.get("headline") if ok else "總結｜待核實")
    put(slot(cards[0],"p","summary body"),item.get("text") if ok else "總結內容尚未完成來源核對；不沿用母版舊期文字。")
def observations(soup, analysis):
    selectors={"market_view":"#view .focus-panel.focus-market .key",
      "key_levels":"#view .focus-panel.focus-levels .key",
      "core_observations":"#view .focus-panel.focus-core .callout"}
    for key,sel in selectors.items():
        node=slot(soup,sel,"observation "+key)
        item=analysis["market_observation_highlights"][key]
        text=item.get("text") if item["status"]=="verified" else None
        keep=[copy.deepcopy(x) for x in node.find_all("details",recursive=False)] if key=="key_levels" else []
        node.clear()
        for i,line in enumerate((text or "待核實：本分頁內容尚未完成來源核對。").splitlines()):
            if i: node.append(soup.new_tag("br"))
            node.append(NavigableString(line))
        for x in keep: node.append(x)
def sentiment(soup, analysis):
    boxes=soup.select("#sentiment .sent > .sbox")
    if not boxes: raise ValueError("market sentiment interpretation box missing")
    box=boxes[-1]; label=box.select_one(".label")
    if label is None: raise ValueError("market sentiment label missing")
    targets=[x for x in box.find_all(["div","p"],recursive=False) if "label" not in x.get("class",[])]
    if not targets:
        target=soup.new_tag("div"); target["style"]="font-size:14px;line-height:1.7;margin-top:8px"; box.append(target)
    else: target=targets[-1]
    item=analysis["market_sentiment"]
    put(target,item.get("text") if item["status"]=="verified" else "待核實：市場情緒判讀尚未完成來源核對。")
def event_bucket(item, report_day):
    d=dt(item["event_date"]).date()
    if item["status"]=="released": return "published"
    if d<report_day: return "published"
    return "today" if d==report_day else "upcoming"
def new_anchor(soup,node,src):
    node.clear(); a=soup.new_tag("a"); a["target"]="_blank"; a["rel"]=["noopener"]; node.append(a); source_link(a,src)
def econ_card(proto,item,soup):
    card=copy.deepcopy(proto); meta=slot(card,".econ-meta","econ meta")
    for sel,val in ((".econ-date",date_label(item["event_date"])),
      (".econ-time",dt(item["event_date"]).strftime("%H:%M")),
      (".econ-country",item["region"]),(".econ-name",item["event_name"]),(".econ-stars","★★★")):
        put(slot(meta,sel,"econ "+sel),val)
    card["class"]=[c for c in card.get("class",[]) if c not in {"five-star","four-star","two-star","one-star"}]
    if "three-star" not in card["class"]: card["class"].append("three-star")
    fields=slot(card,".econ-details","econ details").select(".econ-field")
    if len(fields)<5: raise ValueError("econ card prototype has fewer than five detail fields")
    vals=[("前值",item.get("previous") if item.get("previous") is not None else "待核實"),
      ("市場預估",item.get("forecast") if item.get("forecast") is not None else "待核實"),
      ("實際",item.get("actual") if item.get("actual") is not None else ("尚未公布" if item["status"]=="upcoming" else "待核實")),
      ("市場影響",item.get("impact_judgment") or "待核實")]
    for f,(lab,val) in zip(fields[:4],vals):
        put(slot(f,"label","econ field label"),lab); put(slot(f,".econ-value","econ field value"),val)
    f=fields[4]; put(slot(f,"label","econ source label"),"資料來源")
    new_anchor(soup,slot(f,".econ-value","econ source value"),item["source"])
    return card
def earnings_card(proto,item,soup):
    card=copy.deepcopy(proto); main=slot(card,".earnings-summary-main","earnings main")
    session={"before_market":"美股盤前","after_market":"美股盤後","during_market":"盤中","unknown":"公布時段待核實"}[item["session"]]
    for sel,val in ((".earnings-us-date",date_label(item["event_date"])),
      (".earnings-tw-date",session+"｜台灣時間"),(".earnings-company-name",item["company"]),
      (".earnings-company-sub",(item.get("ticker") or "代號待核實")+"｜財報")):
        put(slot(main,sel,"earnings "+sel),val)
    stars=slot(main,".earnings-stars","earnings stars")
    card["class"]=[c for c in card.get("class",[]) if c not in {"five-star-earnings","four-star-earnings","three-star-earnings"}]
    company=main.select_one(".earnings-company-name")
    if company and "five-star-company" in company.get("class",[]): company["class"].remove("five-star-company")
    if item.get("importance_stars")==3 and item["importance_basis"]=="source_rating":
        put(stars,"★★★"); card["class"].append("three-star-earnings")
    else: put(stars,"未評星")
    fields=slot(card,".earnings-accordion-details","earnings details").select(".earnings-detail-field")
    if len(fields)<4: raise ValueError("earnings card prototype has fewer than four detail fields")
    eps=f"預估：{item.get('eps_estimate') if item.get('eps_estimate') is not None else '待核實'}；實際：{item.get('eps_actual') if item.get('eps_actual') is not None else ('尚未公布' if item['status']=='upcoming' else '待核實')}"
    rev=f"預估：{item.get('revenue_estimate') if item.get('revenue_estimate') is not None else '待核實'}；實際：{item.get('revenue_actual') if item.get('revenue_actual') is not None else ('尚未公布' if item['status']=='upcoming' else '待核實')}"
    vals=[("公布時段",session+"；實際發布時間以公司公告為準。"),("EPS 預估／實際",eps),
      ("營收預估／實際",rev),("財報判讀與股價反應",item.get("stock_price_reaction") or "待核實")]
    for f,(lab,val) in zip(fields[:4],vals):
        put(slot(f,"label","earnings field label"),lab); put(slot(f,".earnings-detail-value","earnings field value"),val)
    if len(fields)>=5: source_field=fields[4]
    else:
        source_field=copy.deepcopy(fields[0]); slot(card,".earnings-accordion-details","earnings details").append(source_field)
    put(slot(source_field,"label","earnings source label"),"資料來源")
    new_anchor(soup,slot(source_field,".earnings-detail-value","earnings source value"),item["source"])
    return card
def calendar_panel(section, records, kind, report_day, coverage, soup, proto=None):
    panel=slot(section,".week-econ-panels" if kind=="economic" else ".week-earnings-panels",kind+" panels")
    groups=panel.find_all("div",class_="calendar-status-group",recursive=False)
    if len(groups)!=3: raise ValueError(f"{kind}: expected 3 existing tab groups, found {len(groups)}")
    cls="econ-event" if kind=="economic" else "earnings-accordion"
    list_cls="econ-event-list" if kind=="economic" else "earnings-accordion-list"
    if proto is None:
        prototypes=panel.select("."+cls)
        if not prototypes: raise ValueError(kind+" event card prototype missing")
        proto=prototypes[0]
    buckets={"today":[],"upcoming":[],"published":[]}
    for item in records: buckets[event_bucket(item,report_day)].append(item)
    for items in buckets.values(): items.sort(key=lambda x:dt(x["event_date"]))
    for bucket,group in zip(("today","upcoming","published"),groups):
        heading=group.select_one(".calendar-status-heading")
        if heading is None: raise ValueError(kind+" status heading missing")
        group.clear(); heading["class"]=["calendar-status-heading",bucket]
        put(heading,{"today":"今日公布","upcoming":"即將公布","published":"已公布"}[bucket]+"｜依台灣時間排序")
        group.append(heading)
        if buckets[bucket]:
            listing=soup.new_tag("div",attrs={"class":list_cls})
            for item in buckets[bucket]:
                listing.append(econ_card(proto,item,soup) if kind=="economic" else earnings_card(proto,item,soup))
            group.append(listing)
        else:
            empty=soup.new_tag("div",attrs={"class":"calendar-status-empty"})
            put(empty,"已完成來源檢查，目前沒有符合篩選規則的事件。" if coverage["status"]=="complete"
                else "待核實：來源擷取尚未完成；目前沒有資料不代表沒有事件。")
            group.append(empty)
def previous_week(soup,kind,records,coverage,report_day,prototype):
    sid="last-week-calendar" if kind=="economic" else "last-week-earnings"
    sec=slot(soup,"#"+sid,sid)
    collapse=slot(sec,"details."+("last-week-calendar-collapse" if kind=="economic" else "last-week-earnings-collapse"),sid+" collapse")
    group=collapse.select_one(".calendar-status-group")
    if group is None: raise ValueError(sid+" status group missing")
    heading=group.select_one(".calendar-status-heading")
    if heading is None: raise ValueError(sid+" heading missing")
    list_cls="econ-event-list" if kind=="economic" else "earnings-accordion-list"
    if prototype is None: raise ValueError(sid+" card prototype missing")
    group.clear(); heading["class"]=["calendar-status-heading","published"]; put(heading,"上週已公布｜依日期排序"); group.append(heading)
    if records:
        listing=soup.new_tag("div",attrs={"class":list_cls})
        for item in records:
            if item["status"]!="released": raise ValueError(sid+" contains unreleased event "+item["id"])
            listing.append(econ_card(prototype,item,soup) if kind=="economic" else earnings_card(prototype,item,soup))
        group.append(listing)
    else:
        empty=soup.new_tag("div",attrs={"class":"calendar-status-empty"})
        put(empty,"已完成來源檢查，上週沒有符合篩選規則的事件。" if coverage["status"]=="complete"
            else "待核實：上週來源擷取尚未完成；不可沿用舊期事件。")
        group.append(empty)
    sm=collapse.select_one("summary")
    if sm: put(sm,"展開上週"+("經濟" if kind=="economic" else "財報")+"行事曆（"+
      (report_day-timedelta(days=7)).strftime("%m/%d")+"～"+(report_day-timedelta(days=3)).strftime("%m/%d")+"）")

def render(content_path,input_html,output_html):
    data=read_json(content_path)
    from validate_tac_daily_content import load_validator,validate_report_rules
    validator,_=load_validator(); errs=list(validator.iter_errors(data))+[ValueError(x) for x in validate_report_rules(data)]
    if errs: raise ValueError("content validation failed: "+"; ".join(getattr(e,"message",str(e)) for e in errs[:10]))
    binding=read_json(BINDING_PATH)
    editorial=binding.get("editorial_content",{})
    if editorial.get("schema_version")!=2 or editorial.get("renderer")!="scripts/render_tac_daily_content.py":
        raise ValueError("runtime HTML binding map is not connected to editorial schema v2")
    rd=date.fromisoformat(data["meta"]["report_date"]); typ="monday" if rd.weekday()==0 else "weekday"
    if rd.weekday()>4 or data["meta"]["template_type"]!=typ: raise ValueError("report date/template mismatch")
    if typ=="weekday":
        for k in ("previous_economic_calendar","previous_earnings_calendar"):
            if data["coverage"][k]["status"]!="not_applicable": raise ValueError(k+" must be not_applicable for weekday reports")
    for k,n in (("focus_news",5),("market_headlines",10)):
        if len(data[k])!=n: raise ValueError(f"{k}: exactly {n} records required; got {len(data[k])}")
        if data["coverage"][k]["status"]!="complete":
            raise ValueError(k+" source coverage must be complete before rendering")
    if not input_html.is_file(): raise ValueError("market-rendered input HTML missing")
    soup=BeautifulSoup(input_html.read_text(encoding="utf-8"),"html.parser")
    before=copy.deepcopy(soup)
    meta=slot(soup,'meta[name="report-date"]',"report date")
    if meta.get("content")!=data["meta"]["report_date"]: raise ValueError("HTML/content report date mismatch")
    if not soup.title or data["meta"]["report_date"].replace("-","/") not in soup.title.get_text(): raise ValueError("HTML title/report date mismatch")
    update_news_meta(soup,data)
    update_section_dates(soup,rd)
    summary(soup,data["analysis"])
    news(soup,"#global-focus",data["focus_news"],5,"focus_news")
    news(soup,"#headlines",data["market_headlines"],10,"market_headlines")
    observations(soup,data["analysis"]); sentiment(soup,data["analysis"])
    econ_nodes=soup.select("#calendar .econ-event")
    earn_nodes=soup.select("#earnings .earnings-accordion")
    if not econ_nodes or not earn_nodes: raise ValueError("approved calendar event-card prototypes missing")
    econ_proto=copy.deepcopy(econ_nodes[0]); earn_proto=copy.deepcopy(earn_nodes[0])
    calendar_panel(slot(soup,"#calendar","economic calendar"),data["economic_calendar"],"economic",rd,data["coverage"]["economic_calendar"],soup,econ_proto)
    calendar_panel(slot(soup,"#earnings","earnings calendar"),data["earnings_calendar"],"earnings",rd,data["coverage"]["earnings_calendar"],soup,earn_proto)
    current_start=rd-timedelta(days=rd.weekday()); current_end=current_start+timedelta(days=4)
    for group_name in ("economic_calendar","earnings_calendar"):
        for item in data[group_name]:
            event_day=dt(item["event_date"]).date()
            if not current_start<=event_day<=current_end:
                raise ValueError(group_name+" event outside current Monday-Friday report week: "+item["id"])
    if typ=="monday":
        start=rd-timedelta(days=7); end=start+timedelta(days=4)
        for k in ("previous_economic_calendar","previous_earnings_calendar"):
            for e in data[k]:
                if not start<=dt(e["event_date"]).date()<=end: raise ValueError(k+" event outside previous Monday-Friday window")
        previous_week(soup,"economic",data["previous_economic_calendar"],data["coverage"]["previous_economic_calendar"],rd,econ_proto)
        previous_week(soup,"earnings",data["previous_earnings_calendar"],data["coverage"]["previous_earnings_calendar"],rd,earn_proto)
    verify_template_controls(before,soup)
    if output_html.resolve() in PROTECTED or output_html.resolve()==input_html.resolve(): raise ValueError("refusing to overwrite protected/input file")
    output_html.parent.mkdir(parents=True,exist_ok=True); output_html.write_text(str(soup),encoding="utf-8")
    return {"output":str(output_html),"report_date":data["meta"]["report_date"],"template_type":typ,
      "focus_news":len(data["focus_news"]),"market_headlines":len(data["market_headlines"]),
      "economic_events":len(data["economic_calendar"]),"earnings_events":len(data["earnings_calendar"]),
      "previous_economic_events":len(data["previous_economic_calendar"]),"previous_earnings_events":len(data["previous_earnings_calendar"]),
      "incomplete_coverage":[k for k,v in data["coverage"].items() if v["status"]=="incomplete"]}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--content",type=Path,required=True); p.add_argument("--input-html",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try: print(json.dumps(render(a.content,a.input_html,a.output),ensure_ascii=False,indent=2)); return 0
    except Exception as e: print("ERROR: "+str(e),file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
