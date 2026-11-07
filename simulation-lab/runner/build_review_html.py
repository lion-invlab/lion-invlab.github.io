#!/usr/bin/env python3
"""Simulation-only DOM updater. Never edits formal scripts or approved master."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "simulation-lab/baseline/mother-template-manifest.json"

def sha_blob(text: str) -> str:
    b=text.encode("utf-8")
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def set_text(node, value):
    node.clear()
    node.append(str(value))

def unique(root, selector, label):
    nodes=root.select(selector)
    if len(nodes)!=1:
        raise ValueError(f"{label}: selector {selector!r} count={len(nodes)}")
    return nodes[0]

def source_link(url, label):
    a=BeautifulSoup("", "html.parser").new_tag("a", href=url, target="_blank", rel="noopener")
    a.string=label
    return a

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-master-sha", required=True)
    args=ap.parse_args()
    data=json.loads(Path(args.data).read_text())
    report_date=datetime.fromisoformat(data["report_date"]).date()
    if data.get("timezone")!="Asia/Taipei": raise SystemExit("timezone mismatch")
    monday = report_date.weekday()==0
    manifest=json.loads(MANIFEST.read_text())
    template_record = manifest["templates"]["monday" if monday else "weekdays"]
    master_path = ROOT / template_record.get("simulation_path", "simulation-lab/baseline/weekday-mother-template.html")
    raw = master_path.read_text(encoding="utf-8")
    actual=sha_blob(raw)
    approved=template_record["simulation_blob_sha"]
    if actual!=approved or actual!=args.expected_master_sha:
        raise SystemExit(f"SIMULATION MASTER SHA FAIL actual={actual} manifest={approved} expected={args.expected_master_sha}")
    if report_date.weekday()>=5: raise SystemExit("weekend report date is not allowed")
    report_iso=report_date.isoformat()
    report_label=f"{report_date.year}/{report_date.month:02d}/{report_date.day:02d}"
    report_weekday="一二三四五六日"[report_date.weekday()]
    report_cutoff=f"{report_label} 05:25"
    previous_trade=data.get("trading_date","待核實")
    report_context=f"週一版；美股行情採 {previous_trade} 正式收盤，其他市場依各自最近交易日核對。" if monday else f"週二至週五版；行情採 {previous_trade} 最近正式收盤。"
    soup=BeautifulSoup(raw,"html.parser")
    # Normalize the two Monday previous-week disclosure controls to the economic-calendar reference layout.
    disclosure_css = """
<style id="tac-last-week-disclosure-unified-v1">
#last-week-calendar .last-week-calendar-collapse > summary,
#last-week-earnings .last-week-earnings-collapse > summary {
  display:flex !important;
  align-items:center !important;
  justify-content:flex-start !important;
  gap:8px !important;
  padding:10px 12px !important;
  text-align:left !important;
  font-size:13px !important;
  font-weight:850 !important;
  line-height:1.35 !important;
  color:#6b7077 !important;
  list-style:none !important;
}
#last-week-calendar .last-week-calendar-collapse > summary::-webkit-details-marker,
#last-week-earnings .last-week-earnings-collapse > summary::-webkit-details-marker { display:none !important; }
#last-week-calendar .last-week-calendar-collapse > summary::before,
#last-week-earnings .last-week-earnings-collapse > summary::before {
  content:"▸" !important;
  display:inline-block !important;
  flex:0 0 auto !important;
  width:auto !important;
  height:auto !important;
  margin:0 !important;
  padding:0 !important;
  border:0 !important;
  background:transparent !important;
  color:#6b7077 !important;
  font-size:11px !important;
  line-height:1 !important;
}
#last-week-calendar .last-week-calendar-collapse[open] > summary::before,
#last-week-earnings .last-week-earnings-collapse[open] > summary::before { transform:rotate(90deg) !important; }
</style>
"""
    head = soup.select_one("head")
    if head is None: raise ValueError("HTML head missing; cannot install display normalization")
    head.append(BeautifulSoup(disclosure_css, "html.parser").style)

    # Rebuild both disclosure labels with explicit marker/text spans. This avoids
    # inherited native markers and inconsistent pseudo-element spacing.
    for selector, marker_class, text_class in [
        ("#last-week-calendar .last-week-calendar-collapse > summary", "tac-disclosure-marker", "tac-disclosure-label"),
        ("#last-week-earnings .last-week-earnings-collapse > summary", "tac-disclosure-marker", "tac-disclosure-label"),
    ]:
        summary_node = unique(soup, selector, "previous-week disclosure summary")
        label_text = summary_node.get_text(" ", strip=True)
        label_text = re.sub(r"^展開\\s*", "", label_text)
        summary_node.clear()
        marker = soup.new_tag("span", attrs={"class": marker_class, "aria-hidden": "true"})
        marker.string = "▸"
        label = soup.new_tag("span", attrs={"class": text_class})
        label.string = "展開" + label_text
        summary_node.append(marker)
        summary_node.append(label)

    # Preserve all mother-template layout styles; override only sidebar internals below.
    disclosure_layout_css = """
<style id="tac-simulation-layout-authority-v1">
/* Explicit marker-to-label spacing; does not depend on flex-gap support. */
#last-week-calendar .last-week-calendar-collapse > summary,
#last-week-earnings .last-week-earnings-collapse > summary {
  display:flex!important; align-items:center!important; justify-content:flex-start!important;
  gap:0!important; box-sizing:border-box!important; width:100%!important;
  padding:10px 12px!important; text-align:left!important; list-style:none!important;
}
#last-week-calendar .last-week-calendar-collapse > summary::before,
#last-week-earnings .last-week-earnings-collapse > summary::before { content:none!important; display:none!important; }
#last-week-calendar .last-week-calendar-collapse > summary::-webkit-details-marker,
#last-week-earnings .last-week-earnings-collapse > summary::-webkit-details-marker { display:none!important; }
.tac-disclosure-marker {
  display:inline-flex!important; flex:0 0 14px!important; width:14px!important;
  align-items:center!important; justify-content:center!important;
  margin:0 12px 0 0!important; padding:0!important; font-size:13px!important; line-height:1!important;
}
.tac-disclosure-label { display:block!important; flex:0 1 auto!important; min-width:0!important;
  margin:0!important; padding:0!important; font:inherit!important; line-height:1.4!important; text-align:left!important; }
#last-week-calendar .last-week-calendar-collapse[open] .tac-disclosure-marker,
#last-week-earnings .last-week-earnings-collapse[open] .tac-disclosure-marker { transform:rotate(90deg)!important; }

/* Single authoritative sidebar layout for desktop and mobile. */
.tac-side-tools { box-sizing:border-box!important; display:flex!important; flex-direction:column!important;
  min-height:0!important; overflow-x:hidden!important; overflow-y:auto!important;
  overscroll-behavior:contain!important; -webkit-overflow-scrolling:touch!important; }
.tac-side-tools > * { flex-shrink:0!important; }
.tac-side-tools .tac-history-mini { display:block!important; box-sizing:border-box!important;
  flex:0 0 auto!important; min-height:max-content!important; height:auto!important; max-height:none!important; overflow:visible!important; }
.tac-side-tools .tac-history-mini button { display:block!important; box-sizing:border-box!important;
  flex:0 0 auto!important; width:100%!important; min-height:42px!important; height:auto!important;
  white-space:normal!important; line-height:1.35!important; padding:10px 8px!important; }
.tac-side-tools .tac-side-foot { flex:0 0 auto!important; margin-top:10px!important; }
@media(min-width:1100px) { .tac-side-tools { position:fixed!important; z-index:10000!important;
  left:0!important; top:0!important; bottom:0!important; width:208px!important; height:auto!important;
  max-height:none!important; padding:22px 14px!important; gap:9px!important; } }
@media(max-width:1099px) { .tac-side-tools { position:fixed!important; z-index:100001!important;
  left:0!important; top:0!important; bottom:0!important; width:min(82vw,310px)!important;
  height:auto!important; max-height:none!important;
  padding:22px 16px calc(22px + env(safe-area-inset-bottom))!important; gap:9px!important; } }
</style>
"""
    # Append last in body so this authority overrides all template-local sidebar rules.
    layout_style = BeautifulSoup(disclosure_layout_css, "html.parser").style
    if soup.body is None: raise ValueError("HTML body missing; cannot install layout authority")
    soup.body.append(layout_style)

    fed_title = soup.select_one(".fed-live-title")
    if fed_title: set_text(fed_title, "Fed 限時動態")
    for anchor in soup.select("#tac-assets-panel-3 .energy-card .row > b a"):
        label = anchor.get_text(" ", strip=True)
        if label == "WTI原油期貨": set_text(anchor, "WTI 原油期貨")
        elif label == "Brent原油期貨": set_text(anchor, "Brent 原油期貨")
    # Date/title: update only existing text nodes.
    for node in soup.select(".top .report-date, header .report-date"):
        if node.get_text(strip=True):
            # Keep the approved compact inline header; market-basis detail belongs in report content, not the masthead.
            set_text(node,f"｜{report_label}（{report_weekday}）")
    for node in soup.select(".top .date, header .date, .date-line"):
        if node.get_text(strip=True):
            set_text(node,f"{report_label}（{report_weekday}）")
    for node in soup.select("title"):
        set_text(node,f"TAC 投資早報｜{report_label}")
    # Update the approved summary card's text slot without changing wrappers.
    bluf=unique(soup,"#overview > section.grid.two > article.card.bluf","summary")
    summary=unique(bluf, ".key, .bluf-content, p","summary content")
    if data.get("summary_points"):
        summary.clear()
        for idx,point in enumerate(data["summary_points"]):
            label=soup.new_tag("strong"); label.string=point["label"]
            summary.append(label)
            summary.append("｜"+point["text"])
            if idx < len(data["summary_points"])-1:
                summary.append(soup.new_tag("br"))
    else:
        set_text(summary,data["summary"])
    # Market sentiment narrative: keep card structure, replace the narrative paragraph only.
    sent=unique(soup,"#sentiment","sentiment")
    paragraphs=sent.select("p")
    if paragraphs: set_text(paragraphs[0],data["sentiment"])
    # Global Focus News and headlines use .newsitem nodes, not list items.
    for section_id, items_key, expected in [("global-focus","focus_news",5),("headlines","headlines",10)]:
        box=unique(soup,f"#{section_id}",section_id)
        nodes=box.select(".newsitem")
        items=data[items_key]
        if len(nodes)<expected: raise ValueError(f"{section_id}: mother cards {len(nodes)} < {expected}")
        for idx,item in enumerate(items[:expected]):
            node=nodes[idx]
            title=unique(node,".news-title, h3, h4, strong",f"{section_id}[{idx}] title")
            set_text(title,item["title"])
            summary_nodes=node.select(".news-summary, p, .summary")
            if summary_nodes: set_text(summary_nodes[0],item["summary"])
            # News headlines are plain text; only the source line below is clickable.
    # Update existing global-market value slots by exact Chinese label.
    gm=unique(soup,"#global-markets","global markets")
    for label,record in data["global_markets"].items():
        rows=[r for r in gm.select(".row") if label in r.get_text(" ",strip=True)]
        if len(rows)!=1: raise ValueError(f"global market row {label!r} count={len(rows)}")
        vals=rows[0].select("span.r")
        if len(vals)<1: raise ValueError(f"global market value slot missing: {label}")
        set_text(vals[0],record.get("display","待核實"))
        if len(vals)>1 and record.get("change_display") is not None:
            set_text(vals[1],record["change_display"])
    # Industry ETF rows: keep exact original 11 rows and order by verified % change.
    sectors=unique(soup,"#tac-assets-panel-0","sector panel")
    sector_rows=sectors.select(".sector-row")
    if len(sector_rows)!=11: raise ValueError(f"sector row count={len(sector_rows)}")
    for row in sector_rows:
        ticker_match=re.search(r"\b(XLK|XLY|XLB|XLU|XLI|XLV|XLF|XLC|XLRE|XLP|XLE)\b",row.get_text(" ",strip=True))
        if not ticker_match: raise ValueError("unidentified sector ETF row")
        ticker=ticker_match.group(1)
        slot=unique(row,"span.r",f"ETF {ticker} value")
        set_text(slot,data["sectors"].get(ticker,"待核實"))
    # Sort verified daily changes descending; unknown values stay after verified rows.
    # Python's stable sort preserves the original ETF order when changes are equal.
    def sector_ticker(row):
        match=re.search(r"\b(XLK|XLY|XLB|XLU|XLI|XLV|XLF|XLC|XLRE|XLP|XLE)\b",row.get_text(" ",strip=True))
        if not match: raise ValueError("unidentified sector ETF row during ranking")
        return match.group(1)
    def sector_change(row):
        raw=row.select_one("span.r").get_text(strip=True)
        normalized=raw.replace("%","").replace("−","-").replace("－","-").replace("+","").strip()
        if not re.fullmatch(r"-?\d+(?:\.\d+)?",normalized):
            return None
        return float(normalized)
    ranked=[]
    for row in sector_rows:
        ticker=sector_ticker(row)
        change=sector_change(row)
        ranked.append((row,ticker,change))
    ranked.sort(key=lambda item: (item[2] is None, -(item[2] if item[2] is not None else 0)))
    sector_list=sector_rows[0].parent
    for rank,(row,ticker,change) in enumerate(ranked, start=1):
        rank_node=unique(row,".rank",f"ETF {ticker} rank")
        set_text(rank_node,str(rank))
        value_node=unique(row,"span.r",f"ETF {ticker} value")
        if change is None:
            set_text(value_node,"待核實")
            value_node["class"]=["r","pending"]
        else:
            value_node["class"]=["r","up" if change>0 else "down" if change<0 else "flat"]
        sector_list.append(row)
    # Hard gate: displayed order, rank labels and values must agree.
    displayed=sector_list.select(".sector-row")
    if len(displayed)!=11:
        raise ValueError(f"sector ranking output count={len(displayed)}")
    parsed=[]
    for expected_rank,row in enumerate(displayed,start=1):
        rank_text=unique(row,".rank","sector rank").get_text(strip=True)
        if rank_text!=str(expected_rank):
            raise ValueError(f"sector rank mismatch: expected {expected_rank}, got {rank_text}")
        parsed.append(sector_change(row))
    verified=[x for x in parsed if x is not None]
    if verified!=sorted(verified,reverse=True):
        raise ValueError("sector ETF order is not descending by verified daily change")
    if any(x is None for x in parsed[:-1]):
        raise ValueError("unverified sector ETF appears before a verified ETF")
    # Bonds, FX, oil and metals are exact-label bindings.
    for container_id,records in [("bonds",data["bonds"]),("fx",data["fx"]),("tac-assets-panel-3",data["energy"]),("tac-assets-panel-4",data["metals"])]:
        container=unique(soup,f"#{container_id}",container_id)
        for label,record in records.items():
            # Display labels may add Latin/Chinese spacing (e.g. "WTI 原油期貨").
            # Match the stable semantic label independent of presentation whitespace.
            normalized_label="".join(str(label).split())
            rows=[r for r in container.select(".row")
                  if normalized_label in "".join(r.get_text(" ",strip=True).split())]
            if len(rows)!=1: raise ValueError(f"{container_id}/{label}: rows={len(rows)}")
            vals=rows[0].select("span.r")
            if not vals: raise ValueError(f"missing value {container_id}/{label}")
            set_text(vals[0],record.get("display","待核實"))
            if len(vals)>1 and record.get("change_display") is not None: set_text(vals[1],record["change_display"])
    # VIX/MOVE/F&G status slots; do not infer a value.
    for key,label in [("vix","VIX"),("move","MOVE")]:
        rows=[r for r in sent.select(".sbox") if (r.select_one(".label-en") and r.select_one(".label-en").get_text(" ",strip=True).strip()==label)]
        if not rows: raise ValueError(f"{label} row not found")
        # The approved mother repeats VIX in its overview and risk strip; update both existing slots.
        for idx,row in enumerate(rows):
            strong=row.select("strong")
            if not strong: raise ValueError(f"{label} value slot missing")
            set_text(strong[-1],data["risk"][key].get("display","待核實"))
    fg=sent.select(".cnn-fg-preview")
    if fg:
        score=fg[0].select_one(".fg6-score-main")
        if score: set_text(score,data["risk"]["fear_greed"].get("display","待核實"))
    # FedWatch: only use a snapshot available before the 05:25 report cutoff.
    fed=unique(soup,"#fed .fed-live-watch","FedWatch panel")
    outcomes=data["fedwatch"]["probabilities"]
    rows=fed.select(".fc-prob")
    if len(rows)!=2: raise ValueError("approved master has exactly two probability cards")
    bar=fed.select_one(".fc-split-bar")
    if not outcomes:
        for row in rows:
            set_text(unique(row,"strong","probability"),"待核實")
            set_text(unique(row,".fc-range","range"),"未取得 05:25 前快照")
            set_text(unique(row,".fc-prob-label span:not(.fc-dot)","label"),"機率資料待核實")
        if bar: bar["style"]="display:none"
        for legend in fed.select(".fc-split-legend"): set_text(legend,"未取得 05:25 前可用快照")
    else:
        total=sum(float(x["probability"]) for x in outcomes)
        if abs(total-100)>0.2: raise ValueError(f"FedWatch distribution totals {total}")
        hold=[x for x in outcomes if x["outcome"]=="hold"]
        nonhold=[x for x in outcomes if x["outcome"]!="hold"]
        if len(hold)!=1: raise ValueError("cannot safely aggregate multiple hold outcomes")
        set_text(unique(rows[0],"strong","hold prob"),f'{float(hold[0]["probability"]):.1f}%')
        set_text(unique(rows[0],".fc-range","hold range"),hold[0]["rate_range"])
        set_text(unique(rows[0],".fc-prob-label span:not(.fc-dot)","hold label"),"維持不變")
        set_text(unique(rows[1],"strong","non-hold prob"),f'{sum(float(x["probability"]) for x in nonhold):.1f}%')
        set_text(unique(rows[1],".fc-range","non-hold range"),"；".join(f'{x["outcome"]} {float(x["probability"]):.1f}%（{x["rate_range"]}）' for x in nonhold))
        set_text(unique(rows[1],".fc-prob-label span:not(.fc-dot)","non-hold label"),"政策區間變動（合計）")
        if bar:
            spans=bar.select("span")
            if len(spans)==2:
                spans[0]["style"]="width:"+str(float(hold[0]["probability"]))+"%"
                spans[1]["style"]="width:"+str(sum(float(x["probability"]) for x in nonhold))+"%"
            bar["aria-label"]="；".join(f'{x["rate_range"]} {float(x["probability"]):.1f}%' for x in outcomes)
        legend=fed.select(".fc-split-legend b")
        if len(legend)==2:
            set_text(legend[0],f'{float(hold[0]["probability"]):.1f}%')
            set_text(legend[1],f'{sum(float(x["probability"]) for x in nonhold):.1f}%')
    ts=data["fedwatch"].get("updated_at_tw","未取得 05:25 前快照")
    for span in fed.select(".fc-split-head span"):
        if "資料時間" in span.get_text() or "官方截圖" in span.get_text() or "Investing.com" in span.get_text():
            set_text(span,f"Fed Rate Monitor｜{ts}")
    # Replace current-week calendar cards from the current W46 records.
    def dateparts(v):
        try:
            z=datetime.fromisoformat(v); return z.strftime("%m/%d"), z.strftime("%H:%M") if z.hour or z.minute else "時間未確認"
        except Exception: return "日期待核實","時間未確認"
    def groupkey(x):
        d=(x.get("date") or "")[:10]
        return "today" if d==report_iso else ("upcoming" if d>report_iso else "published")
    def startext(x):
        n=max(0,min(5,int(x.get("stars") or 0))); return "★"*n+"☆"*(5-n)
    def putfield(card,label,value):
        for field in card.select(".econ-field"):
            lab=field.select_one("label")
            if lab and lab.get_text(strip=True)==label: set_text(field.select_one(".econ-value"),value if value is not None else "不適用／待核實")
    cal=unique(soup,"#calendar","economic calendar")
    econ=data.get("calendar",{}).get("events",[])
    if not econ: raise ValueError("current-week economic calendar data missing")
    title=cal.select_one(".title small")
    if title: set_text(title,"%s～%s｜%s｜資料截點 %s 台灣時間" % (data["calendar"]["week_start"],data["calendar"]["week_end"],data["calendar"]["week_id"],report_cutoff))
    panels=unique(cal,".week-econ-panels","economic panels")
    template=panels.select_one("details.econ-event")
    group_template=next((g for g in panels.select(".calendar-status-group") if g.select_one(".econ-event-list")),None)
    if not template or not group_template: raise ValueError("economic calendar template missing")
    panels.clear()
    for key,label in [("today","今日事件"),("upcoming","即將公布"),("published","已公布")]:
        items=[x for x in econ if groupkey(x)==key]
        group=BeautifulSoup(str(group_template),"html.parser").select_one(".calendar-status-group")
        heading=group.select_one(".calendar-status-heading")
        if heading:
            set_text(heading,f"{label}｜重要性★★★★☆以上（{len(items)}項）")
            heading["class"]=["calendar-status-heading",key]
        listing=group.select_one(".econ-event-list"); listing.clear()
        for x in items:
            card=BeautifulSoup(str(template),"html.parser").select_one("details.econ-event")
            day,clock=dateparts(x.get("date",""))
            if not x.get("time_known",False): clock="時間未確認"
            for sel,val in [(".econ-date",day),(".econ-time",clock),(".econ-country",x.get("region","")),(".econ-name",x.get("name","")),(".econ-stars",startext(x))]:
                node=card.select_one(sel)
                if node: set_text(node,val)
            card["class"]=["econ-event","five-star" if int(x.get("stars") or 0)>=5 else "four-star"]
            putfield(card,"前值",x.get("previous")); putfield(card,"市場預估",x.get("forecast"))
            putfield(card,"實際",x.get("actual") if x.get("status")=="released" else f"尚未公布（資料截點 {report_cutoff}）")
            putfield(card,"市場影響",x.get("impact") or "待核實")
            link=card.select_one(".econ-field a")
            if link: link["href"]=x.get("source_url",""); set_text(link,x.get("source_name") or "來源")
            listing.append(card)
        panels.append(group)
    earn=unique(soup,"#earnings","earnings calendar")
    earnings=data.get("earnings",{}).get("events",[])
    if not earnings: raise ValueError("current-week earnings calendar data missing")
    title=earn.select_one(".title small")
    if title: set_text(title,"%s～%s｜%s｜資料截點 %s 台灣時間" % (data["earnings"]["week_start"],data["earnings"]["week_end"],data["earnings"]["week_id"],report_cutoff))
    ep=unique(earn,".week-earnings-panels","earnings panels")
    et=ep.select_one("details.earnings-accordion"); eg=next((g for g in ep.select(".calendar-status-group") if g.select_one(".earnings-accordion-list")),None)
    if not et or not eg: raise ValueError("earnings calendar template missing")
    ep.clear()
    for key,label in [("today","今日事件"),("upcoming","即將公布"),("published","已公布")]:
        items=[x for x in earnings if groupkey(x)==key]
        group=BeautifulSoup(str(eg),"html.parser").select_one(".calendar-status-group")
        heading=group.select_one(".calendar-status-heading")
        if heading:
            set_text(heading,f"{label}｜TAC 四星／五星（{len(items)}家）")
            heading["class"]=["calendar-status-heading",key]
        listing=group.select_one(".earnings-accordion-list"); listing.clear()
        for x in items:
            card=BeautifulSoup(str(et),"html.parser").select_one("details.earnings-accordion")
            day,clock=dateparts(x.get("date",""))
            if not x.get("time_known",False): clock="時間未確認"
            fields=[(".earnings-us-date",day),(".earnings-tw-date",("盤前" if x.get("session")=="before_market" else "盤後" if x.get("session")=="after_market" else "時段待核實")+"；"+clock),(".earnings-company-name",x.get("company","")),(".earnings-company-sub",str(x.get("ticker",""))+"｜"+str(x.get("industry",""))),(".earnings-stars",startext(x))]
            for sel,val in fields:
                node=card.select_one(sel)
                if node: set_text(node,val)
            # Every earnings card uses the same five vertically stacked information fields.
            details=card.select_one(".earnings-accordion-details")
            if details is None: raise ValueError("earnings card detail container missing")
            timing_value=("時間待核實" if not x.get("time_known",False) else clock)
            session_label={"before_market":"盤前","after_market":"盤後"}.get(x.get("session"),"時段待核實")
            timing_status=("即將公布" if x.get("status")!="released" else "已公布")
            eps_est=x.get("eps_estimate_display") or (str(x.get("eps_estimate")) if x.get("eps_estimate") is not None else "待核實")
            eps_act=x.get("eps_actual_display") or (str(x.get("eps_actual")) if x.get("eps_actual") is not None else ("待公布" if x.get("status")!="released" else "待核實"))
            rev_est=x.get("revenue_estimate_display") or (str(x.get("revenue_estimate")) if x.get("revenue_estimate") is not None else "待核實")
            rev_act=x.get("revenue_actual_display") or (str(x.get("revenue_actual")) if x.get("revenue_actual") is not None else ("待公布" if x.get("status")!="released" else "待核實"))
            eps_value=f"共識 {eps_est}；實際 {eps_act}"
            revenue_value=f"共識 {rev_est}；實際 {rev_act}"
            judgment_value=(x.get("judgment") or ("財報尚未公布，公布後依公司實際值、同口徑共識及股價反應更新。" if x.get("status")!="released" else "財報判讀待核實。"))
            if x.get("price_reaction"):
                judgment_value += " 股價反應："+str(x.get("price_reaction"))
            else:
                judgment_value += " 股價反應："+("尚未公布" if x.get("status")!="released" else "待核實")
            source_value=soup.new_tag("a",href=x.get("source_url",""),target="_blank",rel="noopener")
            source_value.string=x.get("source_name") or "來源待核實"
            field_specs=[
                ("公布時段／狀態",f"{timing_status}；{day}（{session_label}；{timing_value} 台灣時間）"),
                ("EPS 預估／實際",eps_value),
                ("營收預估／實際",revenue_value),
                ("財報判讀與股價反應",judgment_value),
                ("資料來源",source_value),
            ]
            prototype=details.select_one(".earnings-detail-field")
            if prototype is None: raise ValueError("earnings detail field prototype missing")
            details.clear()
            for field_label,field_value in field_specs:
                field=BeautifulSoup(str(prototype),"html.parser").select_one(".earnings-detail-field")
                field["class"]=["earnings-detail-field","wide"]
                label_node=field.select_one("label")
                value_node=field.select_one(".earnings-detail-value")
                if label_node: set_text(label_node,field_label)
                if value_node:
                    value_node.clear()
                    if hasattr(field_value,"name"): value_node.append(field_value)
                    else: set_text(value_node,field_value)
                details.append(field)
            link=card.select_one(".earnings-detail-value a")
            if link: link["href"]=x.get("source_url",""); set_text(link,x.get("source_name") or "來源")
            listing.append(card)
        ep.append(group)
    # Monday retrospective: populate dedicated prior-week sections from W45 only.
    if monday:
        last_econ = data.get("last_week_calendar", {})
        last_earn = data.get("last_week_earnings", {})
        lw = unique(soup, "#last-week-calendar", "last-week economic calendar")
        lw_title = lw.select_one(".title small")
        if lw_title:
            set_text(lw_title, f"{last_econ.get('week_start','')}～{last_econ.get('week_end','')}｜{last_econ.get('week_id','')}｜上週五星事件")
        lw_details = unique(lw, "details.last-week-calendar-collapse", "last-week economic collapse")
        lw_list = unique(lw_details, ".econ-event-list", "last-week economic list")
        lw_template = lw_list.select_one("details.econ-event")
        if lw_template is None: raise ValueError("Monday mother last-week economic card template missing")
        lw_list.clear()
        for x in last_econ.get("events", []):
            if int(x.get("stars") or 0) < 5 or x.get("status") != "released": continue
            card = BeautifulSoup(str(lw_template), "html.parser").select_one("details.econ-event")
            day, clock = dateparts(x.get("date", ""))
            if not x.get("time_known", False): clock = "時間未確認"
            for sel, val in [(".econ-date", day), (".econ-time", clock), (".econ-country", x.get("region", "")), (".econ-name", x.get("name", "")), (".econ-stars", startext(x))]:
                node = card.select_one(sel)
                if node: set_text(node, val)
            fields = {"前值": x.get("previous"), "預估": x.get("forecast"), "實際": x.get("actual"), "市場影響": x.get("impact")}
            for field in card.select(".econ-field"):
                label = field.select_one("label"); value = field.select_one(".econ-value")
                if not label or not value: continue
                key = label.get_text(strip=True)
                if key in fields: set_text(value, fields[key] if fields[key] is not None else "不適用／待核實")
                if key == "來源":
                    value.clear()
                    if x.get("source_url"): value.append(source_link(x["source_url"], x.get("source_name") or "來源"))
                    else: value.append("來源待核實")
            lw_list.append(card)
        if not lw_list.select("details.econ-event"): raise ValueError("W45 has no verified five-star published economic events")
        lw_range=f"{last_econ.get('week_start','')[5:7]}/{last_econ.get('week_start','')[8:10]}～{last_econ.get('week_end','')[5:7]}/{last_econ.get('week_end','')[8:10]}"
        lw_summary=lw_details.select_one("summary")
        if lw_summary: set_text(lw_summary, f"展開上週經濟行事曆（{lw_range}）")
        lw_heading=lw.select_one(".calendar-status-heading.published")
        if lw_heading: set_text(lw_heading, "上週已公布｜全球五顆星重要經濟事件")
        le = unique(soup, "#last-week-earnings", "last-week earnings")
        le_title = le.select_one(".title small")
        if le_title: set_text(le_title, f"{last_earn.get('week_start','')}～{last_earn.get('week_end','')}｜{last_earn.get('week_id','')}｜上週五星財報")
        le_details = unique(le, "details.last-week-earnings-collapse", "last-week earnings collapse")
        le_list = unique(le_details, ".earnings-accordion-list", "last-week earnings list")
        le_template = le_list.select_one("details.earnings-accordion")
        if le_template is None: raise ValueError("Monday mother last-week earnings card template missing")
        le_list.clear()
        for x in last_earn.get("events", []):
            if int(x.get("stars") or 0) < 5 or x.get("status") != "released": continue
            card = BeautifulSoup(str(le_template), "html.parser").select_one("details.earnings-accordion")
            day, clock = dateparts(x.get("date", ""))
            if not x.get("time_known", False): clock = "時間未確認"
            fields = [(".earnings-us-date", day), (".earnings-tw-date", ("盤前" if x.get("session")=="before_market" else "盤後" if x.get("session")=="after_market" else "時段待核實")+"；"+clock), (".earnings-company-name", x.get("company","")), (".earnings-company-sub", str(x.get("ticker",""))+"｜"+str(x.get("industry",""))), (".earnings-stars", startext(x))]
            for sel, val in fields:
                node = card.select_one(sel)
                if node: set_text(node, val)
            details = card.select_one(".earnings-accordion-details")
            if details:
                grid = details.select_one(".earnings-results-grid")
                if grid:
                    grid.clear()
                    for label, actual, estimate, actual_display, estimate_display, comparison in [
                        ("EPS", x.get("eps_actual"), x.get("eps_estimate"), x.get("eps_actual_display"), x.get("eps_estimate_display"), x.get("eps_comparison_status")),
                        ("營收", x.get("revenue_actual"), x.get("revenue_estimate"), x.get("revenue_actual_display"), x.get("revenue_estimate_display"), x.get("revenue_comparison_status"))
                    ]:
                        state = comparison if comparison in ("beat","miss","inline") else "pending"
                        status_text = {"beat":"優於預期","miss":"低於預期","inline":"符合預期","pending":"比較口徑待核實"}[state]
                        result = soup.new_tag("div", attrs={"class":["earnings-actual-card",state]})
                        h = soup.new_tag("div", attrs={"class":["earnings-actual-card-title"]}); h.string=label; result.append(h)
                        for caption, val, formatted in [("實際", actual, actual_display), ("預期", estimate, estimate_display)]:
                            line=soup.new_tag("div", attrs={"class":["earnings-actual-line"]})
                            lab=soup.new_tag("span"); lab.string=caption
                            strong=soup.new_tag("strong"); strong.string=formatted or (str(val) if val is not None else "待核實")
                            line.append(lab); line.append(strong); result.append(line)
                        status=soup.new_tag("div", attrs={"class":["earnings-actual-status",state]}); status.string=status_text; result.append(status)
                        if label=="EPS" and state=="pending" and x.get("eps_basis"):
                            note=soup.new_tag("div", attrs={"class":["earnings-actual-note"]})
                            note.string="EPS口徑："+str(x.get("eps_basis"))
                            result.append(note)
                        grid.append(result)
                for field in details.select(".earnings-detail-field"):
                    label = field.select_one("label"); value = field.select_one(".earnings-detail-value")
                    if not label or not value: continue
                    name = label.get_text(strip=True)
                    if name in ("財報判讀","財報判讀與股價反應"):
                        set_text(value, (x.get("judgment") or "財報數據及市場預期口徑待核實")+"；股價反應："+str(x.get("price_reaction") or "待核實"))
                    elif name in ("公布時段","股價當日表現"):
                        set_text(value, "公布時段："+clock+"；股價反應："+str(x.get("price_reaction") or "待核實"))
                    elif name in ("來源","資料來源"):
                        value.clear()
                        if x.get("source_url"): value.append(source_link(x["source_url"], x.get("source_name") or "來源"))
                        else: value.append("來源待核實")
            le_list.append(card)
        if not le_list.select("details.earnings-accordion"): raise ValueError("W45 has no verified five-star published earnings")
        le_range=f"{last_earn.get('week_start','')[5:7]}/{last_earn.get('week_start','')[8:10]}～{last_earn.get('week_end','')[5:7]}/{last_earn.get('week_end','')[8:10]}"
        le_summary=le_details.select_one("summary")
        if le_summary: set_text(le_summary, f"展開上週財報行事曆（{le_range}）")
        le_heading=le.select_one(".calendar-status-heading.published")
        if le_heading: set_text(le_heading, "上週已公布｜五星財報，依公布日期排序")
        le_source=le.select_one(".source")
        if le_source: set_text(le_source, f"排序依美國公司實際公布日期（{le_range.replace('～','→')}）；台灣時間另列。僅納入重要性五星的已公布代表性公司，非所有市場財報完整清單。EPS 及營收採 GAAP／非 GAAP 時已註明口徑；未能核實的欄位明確標示待核。")


    # Remove stale mother-template dates from news, CNN, FactSet and FedWatch panels.
    news_window = soup.select_one("#news-scan .news-window-warning")
    if news_window:
        set_text(news_window, f"新聞時間窗｜2026/11/06 12:00–{report_cutoff}（台灣時間）。焦點新聞與市場熱門頭條均逐則核對原始報導及發布時間；未符合時間窗的資料不納入。")
    health = soup.select_one("#sp500-earnings-health")
    if health:
        health_title = health.select_one(".title small")
        if health_title:
            set_text(health_title, "FactSet 歷史快照：2026/10/23（截至當時24%成份股已公布；非11/06即時統計）")
        for node in health.find_all(string=True):
            if "179 家標普500公司預計" in str(node) or "179家標普500公司預計" in str(node):
                node.replace_with("本週重點財報時程請參考下方 W46 財報行事曆；本區數據僅為10/23歷史快照。")
    fed = soup.select_one("#fed")
    if fed:
        meeting = fed.select_one(".fc-fomc-meeting b")
        if meeting: set_text(meeting, "2026/12/08–12/09")
        press = fed.select_one(".fc-fomc-press b")
        if press: set_text(press, "2026/12/10 03:30")
        rate = fed.select_one(".fc-fomc-rate b")
        if rate: set_text(rate, "3.75%–4.00%")
        rate_date = fed.select_one(".fc-fomc-rate small")
        if rate_date: set_text(rate_date, "Fed官方最新資料：2026/10/29")
        observation = fed.select_one(".fc-fomc-observation b")
        if observation: set_text(observation, "10/28聯準會維持3.75%–4.00%；12/09會議機率因未取得05:25前快照，暫不填列。")
        fed_source = fed.select_one(".fc-source")
        if fed_source:
            fed_source.clear()
            fed_source.append("資料來源：")
            for url, label in [
                ("https://www.investing.com/central-banks/fed-rate-monitor","Investing.com Fed Rate Monitor"),
                ("https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html","CME FedWatch"),
                ("https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm","Fed 10/28官方聲明"),
                ("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm","Fed官方會議日曆")
            ]:
                fed_source.append(source_link(url,label)); fed_source.append("｜")
            fed_source.append("本次資料截點未取得可核實的機率快照，故不填入推估機率。")
        watch=fed.select_one(".fed-live-watch")
        if watch:
            bar=watch.select_one(".fc-split-bar")
            if bar:
                bar["aria-label"]="未取得 2026/11/09 05:25 前可核實的 FedWatch 機率快照"
                bar["style"]="display:none"
            note=watch.select_one("details > div")
            if note:
                set_text(note,"本次報告資料截點為 2026/11/09 05:25（台灣時間）。未取得該截點前可核實的 CME FedWatch／Investing.com Fed Rate Monitor 機率快照，因此本版不展示 10 月舊截圖，也不以其他日期或自行估算的機率代替。請以 CME FedWatch 與 Investing.com Fed Rate Monitor 當日官方／即時資料為準。")
    fg = soup.select_one(".cnn-fg-preview")
    if fg:
        date_node = fg.select_one(".fg6-date")
        if date_node: set_text(date_node, f"CNN Fear & Greed｜{previous_trade}官方歷史讀值未能載入；不沿用母版舊值")
        score = fg.select_one(".fg6-score")
        if score: set_text(score, "待核實")
        klass = fg.select_one(".fg6-class")
        if klass: set_text(klass, "官方讀值待核實")
        explain = fg.select_one(".fg6-explain")
        if explain: set_text(explain, "本次未能取得CNN官方歷史讀值，暫不判定市場恐懼或貪婪程度。")
        src = fg.select_one(".source")
        if src:
            src.clear()
            src.append("資料來源：")
            src.append(source_link("https://www.cnn.com/markets/fear-and-greed","CNN Business｜Fear & Greed Index"))
            src.append("｜官方頁面本次未載入讀值。")

    # Refresh all remaining date-sensitive mother-template text slots.
    bluf_title=bluf.select_one("h1")
    if bluf_title: set_text(bluf_title,data.get("summary_title","本週市場主軸與風險觀察"))
    # News cutoff and source labels.
    for sid,items_key,label in [("global-focus","focus_news","全球焦點"),("headlines","headlines","市場熱門頭條")]:
        section=unique(soup,"#"+sid,sid)
        meta=section.select_one(".tab-panel-meta")
        if meta: set_text(meta,f"{label}｜資料窗口：2026/11/06 12:00 至 {report_cutoff}（台灣時間）")
        items=data[items_key]
        if not items:
            raise ValueError(f"{sid} has no verified news items")
        for old_node in section.select(".newsitem"):
            old_node.decompose()
        for idx,item in enumerate(items):
            if not item.get("url") or not item.get("published_at_tw") or not item.get("title") or not item.get("summary"):
                raise ValueError(f"{sid}[{idx}] missing title, summary, original URL or verified Taiwan publication time")
            if not item["url"].startswith("https://"):
                raise ValueError(f"{sid}[{idx}] non-HTTPS source URL")
            node=soup.new_tag("div",attrs={"class":["newsitem"]})
            heading=soup.new_tag("h3")
            # Preserve the numbering convention used by the approved mother template.
            number_prefix = f"{idx+1}. " if sid=="global-focus" else f"{idx+1:02d}｜"
            heading.string=number_prefix + item["title"]
            paragraph=soup.new_tag("p")
            paragraph.string=item["summary"]
            meta_line=soup.new_tag("div",attrs={"class":["newsmeta"]})
            domain=re.sub(r"^https?://([^/]+).*",r"\1",item["url"])
            meta_line.append("資料來源：")
            meta_line.append(source_link(item["url"],domain))
            meta_line.append("｜發布："+item["published_at_tw"])
            meta_line.append(f"｜截稿 {report_cutoff}")
            node.append(heading)
            node.append(paragraph)
            node.append(meta_line)
            section.append(node)
    focus_urls={x.get("url") for x in data.get("focus_news",[])}
    headline_urls={x.get("url") for x in data.get("headlines",[])}
    if focus_urls & headline_urls:
        raise ValueError("duplicate original news URL across Global Focus and Market Headlines")
    gm=unique(soup,"#global-markets","global markets")
    for i,meta in enumerate(gm.select(".tab-panel-meta")):
        labels=[f"美股｜{previous_trade} 正式收盤",f"亞洲市場｜{previous_trade} 最近正式收盤",f"歐洲市場｜{previous_trade} 最近正式收盤"]
        if i<len(labels): set_text(meta,labels[i])
    for pid,label in [("tac-assets-panel-0",f"11 檔產業 ETF｜{previous_trade} 美股收盤｜依單日漲跌幅排序"),("tac-assets-panel-1",f"美國公債殖利率｜{previous_trade} 官方日終資料"),("tac-assets-panel-2",f"外匯｜{previous_trade} 歷史收盤參考值"),("tac-assets-panel-3",f"能源期貨｜{previous_trade} 收盤"),("tac-assets-panel-4",f"貴金屬期貨｜{previous_trade} 收盤")]:
        panel=soup.select_one("#"+pid)
        if panel:
            meta=panel.select_one(".tab-panel-meta")
            if meta: set_text(meta,label)
    # Replace old market-source captions with the sources for this report date.
    source_specs=[
        ("#global-markets .source","https://www.reuters.com/business/nasdaq-futures-rise-after-steep-ai-selloff-chip-stocks-stabilize-2026-11-06/","Reuters｜11/06 美股收盤"),
        ("#tac-assets-panel-1 .source","https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data","Investing.com｜11/06 美國公債殖利率歷史資料"),
        ("#tac-assets-panel-3 .source","https://www.investing.com/commodities/crude-oil-historical-data","Investing.com｜11/06 WTI／Brent 期貨歷史報價"),
        ("#tac-assets-panel-4 .source","https://www.investing.com/commodities/gold-historical-data","Investing.com｜11/06 黃金／白銀期貨歷史報價")
    ]
    for selector,url,label in source_specs:
        for node in soup.select(selector):
            node.clear()
            node.append(source_link(url,label))
    for node in soup.select("#global-markets .source"):
        node.append("｜")
        node.append(source_link("https://apnews.com/article/806f71d95105bc7efbc760b194dd8cad","AP｜亞洲／歐洲收盤"))
        node.append("｜")
        node.append(source_link("https://indexes.nasdaq.com/Index/Overview/SOX","Nasdaq｜SOX"))
    for node in soup.select("#tac-assets-panel-0 .source"):
        node.clear()
        node.append("Yahoo Finance 歷史行情（11/06 收盤漲跌幅）：")
        for ticker in ("XLK","XLY","XLB","XLU","XLI","XLV","XLF","XLC","XLRE","XLP","XLE"):
            node.append(source_link(f"https://finance.yahoo.com/quote/{ticker}/history/",ticker))
            node.append(" ")
    for node in soup.select("#tac-assets-panel-2 .source"):
        node.clear()
        node.append("Investing.com 歷史匯率（11/06）：")
        for url,label in [
            ("https://www.investing.com/indices/usdollar-historical-data","DXY"),
            ("https://www.investing.com/currencies/usd-twd-historical-data","USD/TWD"),
            ("https://www.investing.com/currencies/eur-usd-historical-data","EUR/USD"),
            ("https://www.investing.com/currencies/gbp-usd-historical-data","GBP/USD"),
            ("https://www.investing.com/currencies/aud-usd-historical-data","AUD/USD"),
            ("https://www.investing.com/currencies/usd-jpy-historical-data","USD/JPY")
        ]:
            node.append(source_link(url,label)); node.append(" ")


    # Replace all old market commentary blocks; never leave 10/27 analysis in the 11/06 report.
    # Market commentary is bound by semantic market key, never by array position.
    market_comments=data.get("market_comments",{}).get("global_markets",[])
    # Keep selecting the already-approved commentary bodies by their source keys,
    # while presenting consistent concise labels in all three global-market tabs.
    source_prefixes = {
        "us": "📌 美股觀察",
        "asia": "📌 亞洲市場觀察",
        "europe": "📌 歐洲市場觀察",
    }
    display_prefixes = {
        "us": "📌 美股摘要",
        "asia": "📌 亞股摘要",
        "europe": "📌 歐股摘要",
    }
    global_comment_map = {
        key: next((x for x in market_comments if x.startswith(prefix)), None)
        for key, prefix in source_prefixes.items()
    }
    global_panels = [
        ("#tac-global-panel-0 .market-reason", "us"),
        ("#tac-global-panel-1 .market-reason", "asia"),
        ("#tac-global-panel-2 .market-reason", "europe"),
    ]
    for selector, key in global_panels:
        node=unique(soup,selector,f"{key} global-market commentary")
        value=global_comment_map.get(key)
        source_prefix=source_prefixes[key]
        if not value or not value.startswith(source_prefix):
            raise ValueError(f"missing or mismatched {key} market commentary")
        display_value=display_prefixes[key] + value[len(source_prefix):]
        set_text(node,display_value)
        if not node.get_text(" ",strip=True).startswith(display_prefixes[key]):
            raise ValueError(f"{key} market commentary binding validation failed")

    reasons=[
        ("#tac-assets-panel-0 .market-reason",[data.get("market_comments",{}).get("sectors","📌 產業觀察｜11 檔產業 ETF 報價待核實。")]),
        ("#tac-assets-panel-1 .market-reason",[data.get("market_comments",{}).get("bonds","📌 債券觀察｜殖利率待核實。")]),
        ("#tac-assets-panel-2 .market-reason",[data.get("market_comments",{}).get("fx","📌 匯率觀察｜匯率待核實。")]),
        ("#tac-assets-panel-3 .market-reason",[data.get("market_comments",{}).get("energy","📌 能源觀察｜期貨報價待核實。")]),
        ("#tac-assets-panel-4 .market-reason",[data.get("market_comments",{}).get("metals","📌 貴金屬觀察｜期貨報價待核實。")])
    ]
    for selector,values in reasons:
        nodes=soup.select(selector)
        for i,node in enumerate(nodes):
            if i<len(values): set_text(node,values[i])
    level_source=soup.select_one("#view .focus-panel.focus-levels .source")
    if level_source: set_text(level_source,f"支撐與壓力區間尚未完成 {previous_trade} OHLC 與近 20 日序列重算；本版不沿用母版舊價位。")
    status=soup.select_one(".status")
    if status: set_text(status,f"{report_label}（{report_weekday}）｜{report_context}")
    warning=soup.select_one(".data-sync-warning")
    if warning: set_text(warning,f"{report_label} 早報審核版｜"+data.get("warning_note","市場資料依各自來源與交易日更新；待核實項目不以估值補齊。"))
    footer=soup.select_one(".footer")
    if footer: set_text(footer,f"TAC 投資早報｜{report_label}（{report_weekday}）審核版｜資料截點 {report_cutoff} 台灣時間｜行情基準為各市場最近正式交易日；未取得一致可追溯資料者標示待核實。本檔為隔離模擬審核版，未發布至正式首頁。")

    # Risk indicators and their source notes.
    for label in ("VIX","MOVE"):
        rdata=data.get("risk",{}).get(label.lower(),{})
        change=rdata.get("change_display","待核實")
        rows=[r for r in sent.select(".sbox") if r.select_one(".label-en") and r.select_one(".label-en").get_text(strip=True)==label]
        for row in rows:
            ch=row.select_one("span.down,span.up,span.warn,span.pending")
            if ch:
                set_text(ch,change)
                ch["class"]=["pending"] if change=="待核實" else (["down"] if "−" in str(change) or "-" in str(change) else ["up"])
            src=row.select_one(".source")
            if src:
                if label=="VIX" and rdata.get("display")!="待核實":
                    src.clear(); src.append(source_link("https://www.investing.com/indices/volatility-s-p-500-historical-data?cid=1096487","Investing.com｜11/06 VIX收盤"))
                elif label=="MOVE" and rdata.get("display")!="待核實":
                    src.clear(); src.append(source_link("https://www.investing.com/indices/ice-bofaml-move-historical-data","Investing.com｜最新可得11/05收盤"))
                else:
                    src.clear()
                    src.append(source_link("https://www.cnn.com/markets/fear-and-greed","CNN Business｜官方指數頁；本次頁面未載入最新讀值"))
    fgbox=sent.select_one(".cnn-fg-preview")
    if fgbox:
        score=fgbox.select_one(".fg6-score-main")
        if score: set_text(score,"待核實")
        status=fgbox.select_one(".fg6-status")
        if status: set_text(status,"待核實")
        marker=fgbox.select_one(".fg6-marker")
        if marker: marker["style"]="display:none"
        src=fgbox.select_one(".source")
        if src:
            src.clear(); src.append("資料來源："); src.append(source_link("https://www.cnn.com/markets/fear-and-greed","CNN Business｜官方指數頁")); src.append("｜本次頁面未載入最新讀值。")
    core=sent.select(".sbox")[-1].select_one("div[style]")
    if core: set_text(core,data["sentiment"])
    # Observation title, market view, levels and core priorities.
    view=unique(soup,"#view","market observation")
    vtitle=view.select_one(".today-focus-title")
    if vtitle: set_text(vtitle,f"盤面觀察重點｜{report_label}（{report_weekday}）")
    market_panel=view.select_one(".focus-panel.focus-market .key")
    if market_panel: set_text(market_panel,data.get("observation","盤面觀察待核實"))
    levels=view.select_one(".focus-panel.focus-levels .key")
    if levels: set_text(levels,f"支撐與壓力區間待依 {previous_trade} 正式收盤及近 20 個交易日 OHLC 重新計算；不沿用母版舊區間。")
    core_panel=view.select_one(".focus-panel.focus-core .callout")
    if core_panel: set_text(core_panel,data.get("observation","盤面觀察待核實"))
    # FedWatch is a dated market snapshot, not the old October decision snapshot.
    fed_panel=unique(soup,"#fed .fed-live-watch","FedWatch panel")
    audit=fed_panel.select_one(".fedwatch-time .audit-content")
    if audit: set_text(audit,f"早報資料截點為 {report_cutoff} 台灣時間；未取得符合本次截點的可核實 FedWatch 機率快照時，不引用晚間或盤中更新資料。")
    fsrc=fed_panel.select_one(".fc-source")
    if fsrc:
        a=fsrc.select_one("a")
        if a:
            a["href"]="https://www.investing.com/central-banks/fed-rate-monitor"
            set_text(a,"Investing.com Fed Rate Monitor")
        for child in list(fsrc.find_all(string=True)):
            if "官方截圖" in str(child) or "快照時間" in str(child): child.extract()
        
    fomc=soup.select_one("#fed .fc-fomc")
    if fomc:
        meeting=fomc.select_one(".fc-fomc-meeting b")
        if meeting: set_text(meeting,"2026/12/08–12/09")
        press=fomc.select_one(".fc-fomc-press b")
        if press: set_text(press,"2026/12/10 03:30")
        observation=fomc.select_one(".fc-fomc-observation b")
        if observation: set_text(observation,"10/28聯準會維持3.75%–4.00%；12/09會議機率因未取得05:25前快照，暫不填列。")
        p=fomc.select_one("p")
        if p: set_text(p,"下一次會議日期與決策時間以 Federal Reserve 官方日曆為準；本欄不沿用 10 月會議舊資料。")
    health=soup.select_one("#sp500-earnings-health .title small")
    if health: set_text(health,"FactSet 歷史快照：2026/10/23；非11/06即時統計。")
    health_panel=soup.select_one("#sp500-earnings-health")
    if health_panel:
        for node in health_panel.find_all(string=True):
            if "179" in str(node) and "10/26" in str(node): node.replace_with("本週重點財報時程請參考下方 W46 財報行事曆；本區數據僅為10/23歷史快照。")

    # Refresh regional market tabs so no October mother-template quotes survive.
    region_specs = [
        ("#asia", {"台灣加權指數":"台灣加權指數","香港恆生指數":"香港恆生指數","上海綜合指數":"上海綜合指數","深證成指":"深證成指","日經225":"日經 225","韓國KOSPI":"韓國 KOSPI"}, 0, "亞洲市場｜2026/11/06各市場當地正式收盤", [
            ("https://apnews.com/article/806f71d95105bc7efbc760b194dd8cad","AP市場報導"),
            ("https://www.investing.com/indices/japan-ni225-historical-data","Nikkei 225"),
            ("https://www.investing.com/indices/kospi-historical-data","KOSPI"),
            ("https://www.investing.com/indices/taiwan-weighted-historical-data","TWSE"),
            ("https://www.investing.com/indices/hang-sen-40-historical-data","Hang Seng"),
            ("https://www.investing.com/indices/shanghai-composite-historical-data","Shanghai"),
            ("https://www.investing.com/indices/shenzhen-composite-historical-data","Shenzhen")
        ]),
        ("#tac-region-panel-2", {"英國FTSE 100":"英國 FTSE 100","德國DAX":"德國 DAX","法國CAC 40":"法國 CAC 40"}, 1, "歐洲市場｜2026/11/06各市場當地正式收盤", [
            ("https://www.investing.com/indices/uk-100-historical-data","FTSE 100"),
            ("https://www.investing.com/indices/germany-30-historical-data","DAX"),
            ("https://www.investing.com/indices/france-40-historical-data","CAC 40"),
            ("https://www.investing.com/indices/stoxx-600-historical-data","STOXX Europe 600")
        ])
    ]
    for selector, row_map, comment_index, meta_text, links in region_specs:
        panel = soup.select_one(selector)
        if panel is None: raise ValueError(f"Regional market panel missing: {selector}")
        meta = panel.select_one(".tab-panel-meta")
        if meta: set_text(meta, meta_text)
        for row in panel.select(".row"):
            label = row.select_one("a.global-index-link")
            if not label: continue
            key = row_map.get(label.get_text(strip=True))
            record = data.get("global_markets", {}).get(key) if key else None
            spans = row.select("span.r")
            if record and len(spans) >= 2:
                set_text(spans[0], record.get("display","待核實"))
                change = record.get("change_display","待核實")
                set_text(spans[1], change)
                state = "up" if "+" in str(change) else "down" if ("−" in str(change) or "-" in str(change)) else "flat"
                spans[1]["class"] = ["r", state]
        reason = panel.select_one(".market-reason")
        if reason: set_text(reason, data["market_comments"]["global_markets"][comment_index])
        source = panel.select_one(".source")
        if source:
            source.clear()
            source.append("資料來源：")
            for url, label in links:
                source.append(source_link(url,label)); source.append(" ")

    # Observation content is preserved as source text, and overwritten only when full copy provided.
    view=unique(soup,"#view","market observation")
    if data.get("observation"):
        panel=unique(view,".focus-panel.focus-market","market observation text")
        set_text(panel.select_one(".key") or panel,data["observation"])
    # Normalize instrument-name typography across every market quote panel.
    # Keep English tickers/sub-labels, prices, percentage changes and section headings untouched.
    instrument_css = """
<style id="tac-market-instrument-name-unified-v2">
/* Identical Chinese instrument-name typography in every quote panel. */
#global-markets .row > b,
#asia .row > b,
[id^="tac-region-panel-"] .row > b,
#industry-bonds-fx-commodities .row > b,
#industry-bonds-fx-commodities .sector-label b,
#industry-bonds-fx-commodities .energy-card .row b,
#industry-bonds-fx-commodities .energy-card .row b a {
  font-size:16px !important;
  font-weight:700 !important;
  line-height:1.35 !important;
  letter-spacing:normal !important;
  transform:none !important;
}
@media(max-width:700px) {
  #global-markets .row > b,
  #asia .row > b,
  [id^="tac-region-panel-"] .row > b,
  #industry-bonds-fx-commodities .row > b,
  #industry-bonds-fx-commodities .sector-label b,
  #industry-bonds-fx-commodities .energy-card .row b,
  #industry-bonds-fx-commodities .energy-card .row b a {
    font-size:16px !important;
    font-weight:700 !important;
    line-height:1.35 !important;
    letter-spacing:normal !important;
    transform:none !important;
  }
}
</style>
"""
    existing_typography = soup.select_one("#tac-market-instrument-name-unified-v2")
    if existing_typography:
        existing_typography.replace_with(BeautifulSoup(instrument_css, "html.parser").style)
    else:
        head = soup.select_one("head")
        if head is None: raise ValueError("HTML head missing; cannot install unified instrument typography")
        head.append(BeautifulSoup(instrument_css, "html.parser").style)
    # Verify the expected market-name groups exist before emitting the review HTML.
    typography_targets = {
        "global indices": "#global-markets .row > b",
        "regional indices": "[id^='tac-region-panel-'] .row > b",
        "sector ETF names": "#industry-bonds-fx-commodities .sector-label b",
        "bonds/FX/commodities": "#industry-bonds-fx-commodities .row > b",
    }
    typography_counts = {name: len(soup.select(selector)) for name, selector in typography_targets.items()}
    if any(count == 0 for count in typography_counts.values()):
        raise ValueError(f"unified instrument typography target missing: {typography_counts}")
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(str(soup),encoding="utf-8")
    print(json.dumps({"output":str(out),"master_sha":actual,"report_date":report_iso,"template":"monday" if monday else "weekdays","sections_updated":["title","summary","sentiment","news","global_markets","sectors","bonds","fx","energy","metals","risk","fedwatch","calendar headings"],"review_ready":False},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
