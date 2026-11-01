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
US_TZ = ZoneInfo("America/New_York")
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
        prefix=f"{i}. " if name=="focus_news" else f"{i:02d}｜"
        put(slot(card,"h3",name+" headline"),prefix+item["headline"])
        put(slot(card,"p",name+" summary"),item["summary"])
        meta=slot(card,".newsmeta",name+" source metadata")
        links=meta.select("a")
        if not links: raise ValueError(f"{name}[{i}]: source link template missing")
        anchor=copy.deepcopy(links[0])
        source_link(anchor,item["source"])
        meta.clear(); meta.append(anchor)

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
        body=item.get("text") if item["status"]=="verified" else None
        body=body or "待核實：本分頁內容尚未完成來源核對。"
        details=[copy.deepcopy(x) for x in node.find_all("details",recursive=False)]
        heading=copy.deepcopy(node.find("b",recursive=False))
        node.clear()
        if key in {"market_view","core_observations"} and heading is not None:
            # Keep the approved mother heading text unchanged.
            node.append(heading); node.append(soup.new_tag("br"))
            node.append(NavigableString(body))
        elif key=="key_levels":
            for i,line in enumerate(body.splitlines()):
                if i: node.append(soup.new_tag("br"))
                if "：" in line:
                    label,rest=line.split("：",1)
                    b=soup.new_tag("b"); put(b,label+"："); node.append(b)
                    node.append(NavigableString(rest))
                elif ":" in line:
                    label,rest=line.split(":",1)
                    b=soup.new_tag("b"); put(b,label+":"); node.append(b)
                    node.append(NavigableString(rest))
                else: node.append(NavigableString(line))
        else:
            node.append(NavigableString(body))
        for detail in details: node.append(detail)

def update_calendar_sources(soup, data):
    for section_id,coverage_key,label in (
      ("calendar","economic_calendar","本週經濟行事曆"),
      ("earnings","earnings_calendar","本週財報行事曆")):
        section=slot(soup,"#"+section_id,label)
        article=slot(section,"article.calendar-card",label+" article")
        title_meta=slot(article,".title small",label+" title metadata")
        coverage=data["coverage"][coverage_key]
        complete=coverage["status"]=="complete"
        if complete and coverage_key=="economic_calendar":
            note="來源覆蓋已完成；僅顯示 Investing.com 原生最高三星經濟事件。"
        elif complete:
            note="來源覆蓋已完成；財報重要性依 WR 與來源證據呈現。"
        elif coverage_key=="earnings_calendar":
            note="來源擷取尚未完成；目前沒有資料不代表沒有重要事件；財報重要性依已核實來源與 WR 判斷，請勿視為完整日程。"
        else:
            note="來源擷取尚未完成；目前沒有資料不代表沒有重要事件；僅收錄 Investing.com 原生最高三星經濟事件，請勿視為完整日程。"
        put(title_meta,f"報告日期 {data['meta']['report_date']}｜{note}；所有時間採台灣時間。")
        # The locked mothers keep a static guidance note and a separate
        # source-provenance note inside each calendar card. Update only the
        # final .source node; do not overwrite the explanatory guidance.
        source_nodes=article.select(".source")
        # The Monday mother has a separate global provenance note; the locked
        # Tue-Fri mother intentionally relies on per-event source fields and
        # has no global .source node. Never add or invent a DOM slot.
        source_node=source_nodes[-1] if source_nodes else None
        if source_node is None:
            continue
        if complete:
            source_note="來源覆蓋已完成；事件日期、發布時間及實際值依來源逐項核對。"
        else:
            source_note="來源擷取尚未完成；已清除母版舊期來源說明與事件，不沿用過期日程。"
        # Keep the existing source link element, but repoint it to the live calendar landing page.
        existing_anchor=source_node.find("a",recursive=False)
        if existing_anchor is not None:
            for child in list(source_node.children):
                if isinstance(child,NavigableString):
                    child.replace_with(NavigableString(source_note+" "))
            src_refs=coverage.get("source_refs") or ["https://hk.investing.com/economic-calendar/"]
            src_url=src_refs[0] if src_refs else "https://hk.investing.com/economic-calendar/"
            source_link(existing_anchor,{"name":"Investing.com 香港站行事曆","url":src_url,
                "observed_at":coverage.get("checked_at") or data["meta"]["generated_at"]})
        else:
            put(source_node,source_note)

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
def calendar_sort_key(item, bucket):
    event_time=dt(item["event_date"])
    known=item.get("time_known",True) is not False
    stars=int(item.get("importance_stars",0))
    # Unknown-time events belong at the end of each tab. Use only their
    # verified Taiwan calendar date, then TAC importance; never rank them
    # using a fabricated clock time. Python's stable sort preserves source
    # order when date/time and importance are identical.
    if bucket=="published":
        if known:
            return (0,-event_time.timestamp(),-stars)
        return (1,-event_time.date().toordinal(),-stars)
    if known:
        return (0,event_time.timestamp(),-stars)
    return (1,event_time.date().toordinal(),-stars)
def event_time_label(item):
    return "時間待核實" if item.get("time_known",True) is False else dt(item["event_date"]).strftime("%H:%M")
def new_anchor(soup,node,src):
    node.clear(); a=soup.new_tag("a"); a["target"]="_blank"; a["rel"]=["noopener"]; node.append(a); source_link(a,src)
def econ_card(proto,item,soup):
    card=copy.deepcopy(proto)
    if len(card.select("summary"))!=1:
        raise ValueError("economic event prototype must preserve exactly one native details summary control")
    meta=slot(card,".econ-meta","econ meta")
    for sel,val in ((".econ-date",date_label(item["event_date"])),
      (".econ-time",event_time_label(item)),
      (".econ-country",item["region"]),(".econ-name",item["event_name"]),(".econ-stars","★"*item["importance_stars"]+"☆"*(5-item["importance_stars"]))):
        put(slot(meta,sel,"econ "+sel),val)
    card["class"]=[c for c in card.get("class",[]) if c not in {"five-star","four-star","three-star","two-star","one-star"}]
    rating=item["importance_stars"]
    if rating != 3: raise ValueError("economic event must use Investing.com native highest 3-star rating")
    card["class"].append("three-star")
    details=slot(card,".econ-details","econ details")
    fields=details.select(".econ-field")
    if len(fields)<4: raise ValueError("econ card prototype must have at least four detail fields")
    if len(fields)<5:
        impact_field=copy.deepcopy(fields[-1])
        details.insert(len(fields)-1,impact_field)
        fields=details.select(".econ-field")
    vals=[("前值",item.get("previous") if item.get("previous") is not None else "待核實"),
      ("市場預估",item.get("forecast") if item.get("forecast") is not None else "待核實"),
      ("實際",item.get("actual") if item.get("actual") is not None else ("尚未公布" if item["status"]=="upcoming" else "待核實")),
      ("市場影響",item.get("impact_judgment") or "待核實")]
    for f,(lab,val) in zip(fields[:4],vals):
        put(slot(f,"label","econ field label"),lab); put(slot(f,".econ-value","econ field value"),val)
    f=fields[4]; put(slot(f,"label","econ source label"),"資料來源")
    source_node=slot(f,".econ-value","econ source value")
    new_anchor(soup,source_node,item["source"])
    if item.get("consensus_source"):
        source_node.append(NavigableString("；"))
        a=soup.new_tag("a"); a["target"]="_blank"; a["rel"]=["noopener"]; source_node.append(a); source_link(a,item["consensus_source"])
    return card
def dt_us(v):
    x=__import__("datetime").datetime.fromisoformat(v.replace("Z","+00:00"))
    if x.tzinfo is None: raise ValueError(f"timezone missing: {v}")
    return x.astimezone(US_TZ)
def number_text(value):
    if value is None: return None
    return f"{value:,.2f}" if isinstance(value,(int,float)) else str(value)
def eps_text(value,item):
    if value is None: return "尚未公布" if item["status"]=="upcoming" else "待核實"
    currency=item.get("eps_currency")
    prefix={"USD":"US$","TWD":"NT$","EUR":"€","GBP":"£"}.get(currency,(currency+" ") if currency else "")
    if not currency: prefix="幣別待核實 "
    return prefix+number_text(value)
def revenue_text(value,item):
    if value is None: return "尚未公布" if item["status"]=="upcoming" else "待核實"
    currency=item.get("revenue_currency")
    prefix={"USD":"US$","TWD":"NT$","EUR":"€","GBP":"£"}.get(currency,(currency+" ") if currency else "")
    if not currency: prefix="幣別待核實 "
    unit=item.get("revenue_unit")
    suffix={"B":"B","M":"M","億":"億","million":" million","billion":" billion"}.get(unit,(" "+unit) if unit else "")
    if not unit: suffix="（單位待核實）"
    return prefix+number_text(value)+suffix
def earnings_card(proto,item,soup):
    card=copy.deepcopy(proto)
    if len(card.select(".earnings-accordion-toggle"))!=1:
        raise ValueError("earnings prototype must preserve exactly one existing expand control")
    main=slot(card,".earnings-summary-main","earnings main")
    tw=dt(item["event_date"]); us=dt_us(item["event_date"]); time_known=item.get("time_known",True)
    session_labels={"before_market":"盤前公布","after_market":"盤後公布","during_market":"盤中公布","unknown":"公布時段待核實"}
    session=session_labels[item["session"]]
    us_day=us.date() if time_known else (tw.date()-timedelta(days=1) if item["session"]=="after_market" else tw.date())
    time_type=item.get("time_type","release_time")
    time_label="電話會議" if time_type=="call_time" else ("公布時間" if time_type=="release_time" else "時段")
    us_header=f"美股 {us_day.month}/{us_day.day}（{WD[us_day.weekday()]}）{session}｜{time_label} {us:%H:%M} ET" if time_known else f"美股 {us_day.month}/{us_day.day}（{WD[us_day.weekday()]}）{session}｜{time_label}未公告"
    tw_header=f"台灣 {tw.month}/{tw.day}（{WD[tw.weekday()]}）{tw:%H:%M} UTC+8（{time_label}）" if time_known else f"台灣 {tw.month}/{tw.day}（{WD[tw.weekday()]}）｜{time_label}未公告"
    for sel,val in ((".earnings-us-date",us_header),
      (".earnings-tw-date",tw_header),
      (".earnings-company-name",item["company"]),
      (".earnings-company-sub",(item.get("ticker") or "代號待核實")+"｜"+(item.get("industry") or "產業待核實")+(("｜"+item["reporting_period"]) if item.get("reporting_period") else ""))):
        put(slot(main,sel,"earnings "+sel),val)
    stars=slot(main,".earnings-stars","earnings stars")
    rating=item["importance_stars"]
    if rating not in {4,5}: raise ValueError("earnings event must have TAC 4- or 5-star rating")
    put(stars,"★"*rating+"☆"*(5-rating))
    card["class"]=[x for x in card.get("class",[]) if x not in {"five-star-earnings","four-star-earnings","three-star-earnings"}]
    company=main.select_one(".earnings-company-name")
    if company and "five-star-company" in company.get("class",[]): company["class"].remove("five-star-company")
    if rating==5:
        card["class"].append("five-star-earnings")
        if company and "five-star-company" not in company.get("class",[]): company["class"].append("five-star-company")
    else:
        card["class"].append("four-star-earnings")
    details=slot(card,".earnings-accordion-details","earnings details")
    results=details.select_one(".earnings-results-grid")
    released=item["status"]=="released"
    if results is not None:
        result_cards=results.select(".earnings-actual-card")
        if len(result_cards)!=2: raise ValueError("earnings result grid must contain EPS and revenue cards")
        for result_card,title,actual,estimate,status_key,formatter,basis_note in (
          (result_cards[0],"EPS",item.get("eps_actual"),item.get("eps_estimate"),"eps_comparison_status",eps_text,
           "口徑："+(item.get("eps_basis") or "待核實")),
          (result_cards[1],"營收",item.get("revenue_actual"),item.get("revenue_estimate"),"revenue_comparison_status",revenue_text,
           "單位："+((item.get("revenue_currency") or "幣別待核實")+"/"+(item.get("revenue_unit") or "單位待核實")))):
            put(slot(result_card,".earnings-actual-card-title","earnings result title"),title)
            lines=result_card.select(".earnings-actual-line")
            if len(lines)!=2: raise ValueError("earnings result card must have actual and estimate lines")
            put(slot(lines[0],"strong","earnings actual"),formatter(actual,item))
            put(slot(lines[1],"strong","earnings estimate"),formatter(estimate,item) if estimate is not None else "市場預估未取得")
            status=result_card.select_one(".earnings-actual-status")
            if actual is None:
                status_label="尚未公布" if item["status"]=="upcoming" else "待核實／無可比共識"
                status_class="pending"
            else:
                mapping={"beat":("高於預期","beat"),"met":("符合預期","beat"),"miss":("低於預期","miss"),
                  "pending_verification":("待核實","pending"),"not_comparable":("無可比共識","pending")}
                status_label,status_class=mapping.get(item.get(status_key),("待核實／無可比共識","pending"))
            result_card["class"]=[x for x in result_card.get("class",[]) if x not in {"beat","miss","pending"}]+[status_class]
            if status: put(status,status_label); status["class"]=["earnings-actual-status",status_class]
            note=result_card.select_one(".earnings-actual-note")
            note_text = item.get("eps_note") if title == "EPS" else item.get("revenue_note")
            if note:
                put(note, note_text or (basis_note + "；補充說明待核實"))
        fields=details.select(".earnings-detail-field")
        target_count=5
        if not fields: raise ValueError("earnings prototype must contain detail-field templates")
        while len(fields)<target_count:
            clone=copy.deepcopy(fields[-1]); details.append(clone); fields=details.select(".earnings-detail-field")
        tw_label=f"台灣時間 {tw:%Y/%m/%d %H:%M}（UTC+8，{time_label}）" if time_known else f"台灣日期 {tw:%Y/%m/%d}（{time_label}未公告）"
        us_label=f"美股 {us:%Y/%m/%d %H:%M} ET（{session}，{time_label}）" if time_known else f"美股日期 {us_day:%Y/%m/%d}（{session}，{time_label}未公告）"
        eps_detail=f"市場預估：{eps_text(item.get('eps_estimate'),item)}；實際：{eps_text(item.get('eps_actual'),item)}；口徑：{item.get('eps_basis') or '待核實'}。"+(("備註："+item["eps_note"]) if item.get("eps_note") else "")
        rev_detail=f"市場預估：{revenue_text(item.get('revenue_estimate'),item)}；實際：{revenue_text(item.get('revenue_actual'),item)}；幣別／單位：{item.get('revenue_currency') or '待核實'}／{item.get('revenue_unit') or '待核實'}。"+(("備註："+item["revenue_note"]) if item.get("revenue_note") else "")
        if released:
            values=[
              ("公布時段",us_label+"；"+tw_label),
              ("EPS 預估／實際",eps_detail),
              ("營收預估／實際",rev_detail),
              ("財報判讀與股價反應",(item.get("financial_judgment") or "財報判讀待核實")+"；股價反應："+(item.get("stock_price_reaction") or "待核實")+"（"+(item.get("stock_price_reaction_window") or "觀察時段待核實")+"）。"),
              ("資料來源",None)]
        else:
            values=[
              ("公布時段",us_label+"；"+tw_label),
              ("EPS 預估／實際",eps_detail),
              ("營收預估／實際",rev_detail),
              ("財報判讀與股價反應","財報尚未公布；公布後更新實際值、比較結果及股價反應。"),
              ("資料來源",None)]
        for f,(lab,val) in zip(fields[:target_count],values):
            put(slot(f,"label","earnings detail label"),lab)
            value_node=slot(f,".earnings-detail-value","earnings detail value")
            if val is not None: put(value_node,val)
        source_field=fields[target_count-1]
        value_node=slot(source_field,".earnings-detail-value","earnings source value")
        value_node.clear()
        source_items=[
          ("公司 IR／正式公告",item.get("source")),
          ("市場共識",item.get("consensus_source")),
          ("股價反應",item.get("price_reaction_source"))]
        emitted=0
        for label,src in source_items:
            if src:
                if emitted: value_node.append(NavigableString("；"))
                a=soup.new_tag("a"); source_link(a,src); value_node.append(a); emitted+=1
            elif label!="公司 IR／正式公告":
                if emitted: value_node.append(NavigableString("；"))
                value_node.append(NavigableString(label+"來源待核實")); emitted+=1
    else:
        if released:
            raise ValueError("published earnings card prototype must contain EPS and revenue result cards")
        fields=details.select(".earnings-detail-field")
        if not fields: raise ValueError("upcoming earnings prototype must contain detail-field templates")
        while len(fields)<3:
            clone=copy.deepcopy(fields[-1]); details.append(clone); fields=details.select(".earnings-detail-field")
        tw_label=f"台灣時間 {tw:%Y/%m/%d %H:%M}（UTC+8）"
        us_label=f"美股 {us:%Y/%m/%d %H:%M} ET（{session}）"
        eps_detail=f"EPS 預估：{eps_text(item.get('eps_estimate'),item)}；口徑：{item.get('eps_basis') or '待核實'}。"
        rev_detail=f"營收預估：{revenue_text(item.get('revenue_estimate'),item)}；幣別／單位：{item.get('revenue_currency') or '待核實'}／{item.get('revenue_unit') or '待核實'}。"
        values=[("公布時段",us_label+"；"+tw_label),("預估資訊",eps_detail+" "+rev_detail),("資料來源",None)]
        for field,(label,value) in zip(fields[:3],values):
            put(slot(field,"label","earnings detail label"),label)
            value_node=slot(field,".earnings-detail-value","earnings detail value")
            if value is not None: put(value_node,value)
        source_field=fields[2]
        value_node=slot(source_field,".earnings-detail-value","earnings source value")
        value_node.clear()
        source_items=[("公司 IR／日期公告",item.get("source")),("EPS 共識",item.get("consensus_source"))]
        emitted=0
        for label,src in source_items:
            if src:
                if emitted: value_node.append(NavigableString("；"))
                a=soup.new_tag("a"); source_link(a,src); value_node.append(a); emitted+=1
            elif emitted==0:
                value_node.append(NavigableString(label+"來源待核實")); emitted+=1
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
    for bucket,items in buckets.items(): items.sort(key=lambda x:calendar_sort_key(x,bucket))
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
    # WR v3.10: prior-week panels retain only provider-native three-star economic events; earnings retain documented source-native rating or explicitly unrated major-event assessment.
    # Filter in the renderer as a second guard; do not rely on JSON assembly.
    eligible=[item for item in records if int(item.get("importance_stars",0))==3]
    # Prior-week archive order is date-only; do not infer same-day sequence
    # from clock times, especially when an event's exact time is unverified.
    eligible.sort(key=lambda item: dt(item["event_date"]).date(), reverse=True)
    group.clear(); heading["class"]=["calendar-status-heading","published"]; put(heading,"上週已公布｜僅最高三星經濟事件・依日期由新到舊"); group.append(heading)
    if eligible:
        listing=soup.new_tag("div",attrs={"class":list_cls})
        for item in eligible:
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
    expected_map={
      "summary":"main.wrap > section.grid.two article.bluf",
      "focus_news":"#global-focus","market_headlines":"#headlines",
      "economic_calendar":"#calendar","earnings_calendar":"#earnings",
      "previous_economic_calendar":"#last-week-calendar",
      "previous_earnings_calendar":"#last-week-earnings","observations":"#view"
    }
    for key,selector in expected_map.items():
        if editorial.get(key,{}).get("container")!=selector:
            raise ValueError("runtime binding map selector mismatch: "+key)
    if editorial["focus_news"].get("count")!=5 or editorial["market_headlines"].get("count")!=10:
        raise ValueError("runtime binding map news counts do not match TAC contract")
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
    if input_html.resolve() in PROTECTED: raise ValueError("input must be a generated market-rendered copy, never an approved mother or homepage")
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
    econ_proto=copy.deepcopy(econ_nodes[0]); earn_source=next((n for n in earn_nodes if n.select_one(".earnings-results-grid")),earn_nodes[0]); earn_proto=copy.deepcopy(earn_source)
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
        prev_econ_nodes=soup.select("#last-week-calendar .econ-event")
        prev_earn_nodes=soup.select("#last-week-earnings .earnings-accordion")
        if not prev_econ_nodes or not prev_earn_nodes:
            raise ValueError("Monday mother must contain previous-week event-card prototypes")
        previous_week(soup,"economic",data["previous_economic_calendar"],data["coverage"]["previous_economic_calendar"],rd,copy.deepcopy(prev_econ_nodes[0]))
        previous_week(soup,"earnings",data["previous_earnings_calendar"],data["coverage"]["previous_earnings_calendar"],rd,copy.deepcopy(prev_earn_nodes[0]))
    # Apply coverage notes after all calendar panel rendering so the final
    # visible metadata cannot be overwritten by subsequent calendar assembly.
    update_calendar_sources(soup,data)
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
