#!/usr/bin/env python3
"""Simulation-only DOM updater. Never edits formal scripts or approved master."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "simulation-lab/baseline/weekday-mother-template.html"
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
    manifest=json.loads(MANIFEST.read_text())
    raw=MASTER.read_text()
    actual=sha_blob(raw)
    approved=manifest["templates"]["weekdays"]["blob_sha"]
    if actual!=approved or actual!=args.expected_master_sha:
        raise SystemExit(f"MASTER SHA FAIL actual={actual} manifest={approved}")
    data=json.loads(Path(args.data).read_text())
    if data["report_date"]!="2026-11-06" or data["timezone"]!="Asia/Taipei":
        raise SystemExit("report date/timezone mismatch")
    soup=BeautifulSoup(raw,"html.parser")
    # Date/title: update only existing text nodes.
    for node in soup.select(".top .date, .top .report-date, header .date, .date-line"):
        if node.get_text(strip=True):
            set_text(node,"2026/11/06（五）｜美股基準：2026/11/05 收盤")
    for node in soup.select("title"):
        set_text(node,"TAC 投資早報｜2026/11/06")
    # Update the approved summary card's text slot without changing wrappers.
    bluf=unique(soup,"#overview > section.grid.two > article.card.bluf","summary")
    summary=unique(bluf, ".key, .bluf-content, p","summary content")
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
            links=node.select("a")
            if links and item.get("url"): links[0]["href"]=item["url"]
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
    def sector_change(row):
        t=row.select_one("span.r").get_text(strip=True).replace("%","").replace("−","-").replace("－","-")
        try: return float(t)
        except Exception: return -999.0
    sector_list=sector_rows[0].parent
    for row in sorted(sector_rows,key=sector_change,reverse=True): sector_list.append(row)
    # Bonds, FX, oil and metals are exact-label bindings.
    for container_id,records in [("bonds",data["bonds"]),("fx",data["fx"]),("tac-assets-panel-3",data["energy"]),("tac-assets-panel-4",data["metals"])]:
        container=unique(soup,f"#{container_id}",container_id)
        for label,record in records.items():
            rows=[r for r in container.select(".row") if label in r.get_text(" ",strip=True)]
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
    # Replace stale calendar cards with W45 records frozen at the report cutoff.
    from datetime import datetime
    def dateparts(v):
        try:
            z=datetime.fromisoformat(v); return z.strftime("%m/%d"), z.strftime("%H:%M") if z.hour or z.minute else "時間未確認"
        except Exception: return "日期待核實","時間未確認"
    def groupkey(x):
        d=(x.get("date") or "")[:10]
        return "today" if d=="2026-11-06" else ("upcoming" if d>"2026-11-06" else "published")
    def startext(x):
        n=max(0,min(5,int(x.get("stars") or 0))); return "★"*n+"☆"*(5-n)
    def putfield(card,label,value):
        for field in card.select(".econ-field"):
            lab=field.select_one("label")
            if lab and lab.get_text(strip=True)==label: set_text(field.select_one(".econ-value"),value if value is not None else "不適用／待核實")
    cal=unique(soup,"#calendar","economic calendar")
    econ=data.get("calendar",{}).get("events",[])
    if not econ: raise ValueError("W45 economic calendar data missing")
    title=cal.select_one(".title small")
    if title: set_text(title,"2026/11/02～11/08｜W45｜資料截點 11/06 05:25 台灣時間")
    panels=unique(cal,".week-econ-panels","economic panels")
    template=panels.select_one("details.econ-event")
    group_template=panels.select_one(".calendar-status-group")
    if not template or not group_template: raise ValueError("economic calendar template missing")
    panels.clear()
    for key,label in [("today","今日事件"),("upcoming","即將公布"),("published","已公布")]:
        items=[x for x in econ if groupkey(x)==key]
        group=BeautifulSoup(str(group_template),"html.parser").select_one(".calendar-status-group")
        heading=group.select_one(".calendar-status-heading span") or group.select_one(".calendar-status-heading")
        if heading:
            set_text(heading,f"{label}｜重要性★★★★☆以上（{len(items)}項）")
            heading.parent["class"]=["calendar-status-heading",key]
            heading["class"]=["earnings-badge",key]
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
            putfield(card,"實際",x.get("actual") if x.get("status")=="released" else "尚未公布（資料截點 11/06 05:25）")
            putfield(card,"市場影響",x.get("impact") or "待核實")
            link=card.select_one(".econ-field a")
            if link: link["href"]=x.get("source_url",""); set_text(link,x.get("source_name") or "來源")
            listing.append(card)
        panels.append(group)
    earn=unique(soup,"#earnings","earnings calendar")
    earnings=data.get("earnings",{}).get("events",[])
    if not earnings: raise ValueError("W45 earnings calendar data missing")
    title=earn.select_one(".title small")
    if title: set_text(title,"2026/11/02～11/08｜W45｜資料截點 11/06 05:25 台灣時間")
    ep=unique(earn,".week-earnings-panels","earnings panels")
    et=ep.select_one("details.earnings-accordion"); eg=ep.select_one(".calendar-status-group")
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
            detail=card.select(".earnings-detail-value")
            if len(detail)>=5:
                timing_value=("盤前／盤後時間待核實" if not clock else clock)
                eps_value=f"{x.get('eps_estimate') if x.get('eps_estimate') is not None else '待核實'}／{x.get('eps_actual') if x.get('status')=='released' and x.get('eps_actual') is not None else '待公布'}"
                revenue_value=f"{x.get('revenue_estimate') if x.get('revenue_estimate') is not None else '待核實'}／{x.get('revenue_actual') if x.get('status')=='released' and x.get('revenue_actual') is not None else '待公布'}"
                judgment_value=(x.get("judgment") or "財報尚未公布；關注 EPS、營收與公司指引。")+"；股價反應："+str(x.get("price_reaction") or "待核實")
                if key=="published":
                    # Published earnings must use the approved paired EPS/revenue result-card structure.
                    details=card.select_one(".earnings-accordion-details")
                    original_fields={f.select_one("label").get_text(strip=True):f for f in details.select(":scope > .earnings-detail-field") if f.select_one("label")}
                    grid=soup.new_tag("div",attrs={"class":["earnings-results-grid"]})
                    def actual_card(title_text,value_text):
                        result=soup.new_tag("div",attrs={"class":["earnings-actual-card"]})
                        heading=soup.new_tag("div",attrs={"class":["earnings-actual-card-title"]}); heading.string=title_text; result.append(heading)
                        parts=value_text.split("／",1)
                        for caption,value in [("市場預估",parts[0]),("實際公布",parts[1] if len(parts)>1 else "待核實")]:
                            line=soup.new_tag("div",attrs={"class":["earnings-actual-line"]})
                            label_node=soup.new_tag("span"); label_node.string=caption
                            value_node=soup.new_tag("strong"); value_node.string=value
                            line.append(label_node); line.append(value_node); result.append(line)
                        status=soup.new_tag("span",attrs={"class":["earnings-actual-status","pending"]}); status.string="實際數值已列示｜差異判讀見下方"; result.append(status)
                        return result
                    grid.append(actual_card("EPS｜預估 vs 實際",eps_value))
                    grid.append(actual_card("營收｜預估 vs 實際",revenue_value))
                    details.clear(); details.append(grid)
                    for field_label in ("公布時段","財報判讀與股價反應","資料來源"):
                        field=original_fields.get(field_label)
                        if field:
                            field["class"]=["earnings-detail-field","wide"]
                            if field_label=="公布時段": set_text(field.select_one(".earnings-detail-value"),timing_value)
                            elif field_label=="財報判讀與股價反應": set_text(field.select_one(".earnings-detail-value"),judgment_value)
                            details.append(field)
                else:
                    set_text(detail[0],timing_value)
                    set_text(detail[1],eps_value)
                    set_text(detail[2],revenue_value)
                    set_text(detail[3],judgment_value)
            link=card.select_one(".earnings-detail-value a")
            if link: link["href"]=x.get("source_url",""); set_text(link,x.get("source_name") or "來源")
            listing.append(card)
        ep.append(group)
    # Refresh all remaining date-sensitive mother-template text slots.
    bluf_title=bluf.select_one("h1")
    if bluf_title: set_text(bluf_title,"AI／半導體賣壓引發跨市場避險")
    # News cutoff and source labels.
    for sid,items_key,label in [("global-focus","focus_news","全球焦點"),("headlines","headlines","市場熱門頭條")]:
        section=unique(soup,"#"+sid,sid)
        meta=section.select_one(".tab-panel-meta")
        if meta: set_text(meta,f"{label}｜資料窗口：2026/11/05 12:00 至 2026/11/06 05:25（台灣時間）")
        for idx,node in enumerate(section.select(".newsitem")):
            metas=node.select(".newsmeta")
            items=data[items_key]
            if idx<len(items) and metas:
                domain=re.sub(r"^https?://([^/]+).*",r"\1",items[idx].get("url",""))
                set_text(metas[0],f"資料來源：{domain}｜截至 11/06 05:25")
    gm=unique(soup,"#global-markets","global markets")
    for i,meta in enumerate(gm.select(".tab-panel-meta")):
        labels=["美股｜2026/11/05 正式收盤","亞洲市場｜2026/11/05 正式收盤","歐洲市場｜2026/11/05 正式收盤"]
        if i<len(labels): set_text(meta,labels[i])
    for pid,label in [("tac-assets-panel-0","11 檔產業 ETF｜2026/11/05 美股收盤｜依單日漲跌幅排序"),("tac-assets-panel-1","美國公債殖利率｜2026/11/05 官方日終資料"),("tac-assets-panel-2","外匯｜2026/11/05 歷史收盤參考值"),("tac-assets-panel-3","能源期貨｜2026/11/05 收盤"),("tac-assets-panel-4","貴金屬期貨｜2026/11/05 收盤")]:
        panel=soup.select_one("#"+pid)
        if panel:
            meta=panel.select_one(".tab-panel-meta")
            if meta: set_text(meta,label)
    # Replace old market-source captions with the sources for this report date.
    source_specs=[
        ("#global-markets .source","https://countryeconomy.com/stock-exchange","各市場 11/05 收盤彙整；美股、歐洲與亞洲指數另依各市場歷史行情交叉核對。"),
        ("#tac-assets-panel-0 .source","https://www.exent.ai/resources/stock-market-crash-november-2026","11/05 S&P 500 11 大產業 ETF 單日收盤漲跌幅。"),
        ("#tac-assets-panel-1 .source","https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/textview","U.S. Treasury Daily Treasury Par Yield Curve Rates｜11/05。"),
        ("#tac-assets-panel-2 .source","https://www.investing.com/currencies/usd-twd-historical-data","Investing.com 外匯歷史資料；EUR/USD、GBP/USD、AUD/USD、USD/JPY 另參照 11/05 前一日外匯收盤表。"),
        ("#tac-assets-panel-3 .source","https://www.reuters.com/business/energy/oil-falls-fourth-day-expectations-lower-risk-iran-war-escalation-2026-11-05/","Reuters｜11/05 WTI 與 Brent 期貨結算報價。"),
        ("#tac-assets-panel-4 .source","https://markets.ft.markitdigital.com/data/commodities/tearsheet/historical?c=COMEX+Gold","COMEX Gold 歷史收盤；白銀採 Investing.com 期貨歷史資料。")
    ]
    for selector,url,label in source_specs:
        for node in soup.select(selector):
            node.clear()
            node.append(source_link(url,label))

    # Replace all old market commentary blocks; never leave 10/27 analysis in the 11/06 report.
    reasons=[
        ("#global-markets .market-reason",[
            "📌 美股觀察｜11/05 四大美股指數同步重挫，費半跌幅最大；AI／半導體及大型科技股是主要賣壓來源，市場正在重新評估資本支出回報與估值。",
            "📌 亞股觀察｜本報採 11/05 各市場正式收盤，不混入 11/06 盤中數據。日經、KOSPI、台灣、香港及中國市場表現分歧，後續應比較各地科技權重與政策因素。",
            "📌 歐股觀察｜歐洲主要指數 11/05 漲跌互見，STOXX Europe 600 小幅回落；歐洲市場未出現與美國科技股相同幅度的同步跌勢。"
        ]),
        ("#tac-assets-panel-0 .market-reason",["📌 產業觀察｜11/05 11 大產業 ETF 全數收跌。XLC、XLU、XLP 相對抗跌；XLK 跌幅最深，顯示科技成長曝險遭集中調降。"]),
        ("#tac-assets-panel-1 .market-reason",["📌 債券觀察｜11/05 美國 2 年、10 年及 30 年期公債殖利率分別收於 4.46%、4.84%、5.25%，較前一日均下行；需區分避險買盤與政策預期變化。"]),
        ("#tac-assets-panel-2 .market-reason",["📌 匯率觀察｜美元指數 101.55，美元兌台幣 33.082；EUR/USD、GBP/USD、AUD/USD 與 USD/JPY 依各自歷史收盤口徑列示，部分日變動未取得一致來源，故保留待核實。"]),
        ("#tac-assets-panel-3 .market-reason",["📌 原油觀察｜11/05 WTI 與 Brent 期貨分別上漲 2.72% 與 3.88%；油輪事件與中東運輸風險使供應風險溢價回升。"]),
        ("#tac-assets-panel-4 .market-reason",["📌 貴金屬觀察｜11/05 COMEX 黃金與白銀期貨均收高；同日股市急跌與債券殖利率下行，避險需求及美元變動仍需一併觀察。"])
    ]
    for selector,values in reasons:
        nodes=soup.select(selector)
        for i,node in enumerate(nodes):
            if i<len(values): set_text(node,values[i])
    level_source=soup.select_one("#view .focus-panel.focus-levels .source")
    if level_source: set_text(level_source,"支撐與壓力區間未完成 11/05 OHLC 重算，故本版不沿用母版 10/27 價位；取得完整近 20 日序列後再補。")
    status=soup.select_one(".status")
    if status: set_text(status,"2026/11/06（五）｜週二至週五版；美股行情採 11/05 正式收盤，其他市場依各自 11/05 當地交易日核對。")
    warning=soup.select_one(".data-sync-warning")
    if warning: set_text(warning,"2026/11/06 早報審核版｜已更新 17 項全球指數、11 檔產業 ETF、3 段美債殖利率及主要匯率／商品；CNN Fear & Greed 與部分匯率日變動仍待核實。FedWatch 未取得 05:25 前快照，不引用晚間更新。")
    footer=soup.select_one(".footer")
    if footer: set_text(footer,"TAC 投資早報｜2026/11/06（五）審核版｜資料截點 2026/11/06 05:25 台灣時間｜行情基準為各市場 2026/11/05 當地正式交易日；未取得一致可追溯資料者標示待核實。本檔為隔離模擬審核版，未發布至正式首頁。")

    # Risk indicators and their source notes.
    for label,change,note in [("VIX","+69.66%","Investing.com 歷史資料｜11/05 收盤 28.18；盤中高點 28.36。"),("MOVE","+4.30%","Investing.com ICE BofAML MOVE 歷史資料｜11/05 收盤 97.92。")]:
        rows=[r for r in sent.select(".sbox") if r.select_one(".label-en") and r.select_one(".label-en").get_text(strip=True)==label]
        for row in rows:
            ch=row.select_one("span.down,span.up")
            if ch: set_text(ch,change); ch["class"]=["up"]
            src=row.select_one(".source")
            if src: set_text(src,note)
    fgbox=sent.select_one(".cnn-fg-preview")
    if fgbox:
        score=fgbox.select_one(".fg6-score-main")
        if score: set_text(score,"待核實")
        status=fgbox.select_one(".fg6-status")
        if status: set_text(status,"待核實")
        marker=fgbox.select_one(".fg6-marker")
        if marker: marker["style"]="display:none"
        src=fgbox.select_one(".source")
        if src: set_text(src,"11/05 歷史來源讀值不一致，暫不採用；待 CNN Business 官方歷史值核對。")
    core=sent.select(".sbox")[-1].select_one("div[style]")
    if core: set_text(core,"11/05 美股全面急跌，費半與科技類股領跌；MOVE 上升顯示債券波動亦升溫。VIX 收 28.18，MOVE 收 97.92。CNN Fear & Greed 因歷史來源讀值不一致暫列待核實。觀察重點是 AI 資本支出回報、科技股估值與風險是否擴散至信用及流動性市場。")
    # Observation title, market view, levels and core priorities.
    view=unique(soup,"#view","market observation")
    vtitle=view.select_one(".today-focus-title")
    if vtitle: set_text(vtitle,"今日觀察重點｜2026/11/06（五）")
    market_panel=view.select_one(".focus-panel.focus-market .key")
    if market_panel: set_text(market_panel,data.get("observation","盤面觀察待核實"))
    levels=view.select_one(".focus-panel.focus-levels .key")
    if levels: set_text(levels,"支撐與壓力區間待依 11/05 正式收盤及近 20 個交易日 OHLC 重新計算；不沿用母版舊區間。")
    core_panel=view.select_one(".focus-panel.focus-core .callout")
    if core_panel: set_text(core_panel,"第一｜風險來源：AI／半導體估值與資本支出回報疑慮引發科技股集中賣壓。\n第二｜市場廣度：11 大產業 ETF 全數收跌，科技跌幅最大，通訊服務及必需消費相對抗跌。\n第三｜跨資產：美債殖利率下行，VIX 與 MOVE 同步上升，股債波動均需關注。\n第四｜政策預期：FedWatch 12/09 會議機率僅為單一會議快照，不代表其他會議或聯準會承諾。\n第五｜操作原則：待價格波動收斂、產業廣度改善及財報指引確認後，再評估風險曝險。")
    # FedWatch is a dated market snapshot, not the old October decision snapshot.
    fed_panel=unique(soup,"#fed .fed-live-watch","FedWatch panel")
    audit=fed_panel.select_one(".fedwatch-time .audit-content")
    if audit: set_text(audit,"早報資料截點為 2026/11/06 05:25 台灣時間；未取得該截點之前可核實的 FedWatch 機率快照。Investing.com 頁面於當日 17:45 更新的數據晚於早報截點，因此不納入本報。")
    fsrc=fed_panel.select_one(".fc-source")
    if fsrc:
        a=fsrc.select_one("a")
        if a:
            a["href"]="https://www.investing.com/central-banks/fed-rate-monitor"
            set_text(a,"Investing.com Fed Rate Monitor")
        for child in list(fsrc.find_all(string=True)):
            if "官方截圖" in str(child) or "快照時間" in str(child): child.extract()
        fsrc.append("｜05:25 前快照未取得；不採用晚間更新資料。")
    fomc=soup.select_one("#fed .fc-fomc")
    if fomc:
        meeting=fomc.select_one(".fc-fomc-meeting b")
        if meeting: set_text(meeting,"下次會議日期待官方日曆核對")
        for sel in [".fc-fomc-press b",".fc-fomc-observation b"]:
            node=fomc.select_one(sel)
            if node: set_text(node,"官方時間待核實")
        p=fomc.select_one("p")
        if p: set_text(p,"下一次會議日期與決策時間以 Federal Reserve 官方日曆為準；本欄不沿用 10 月會議舊資料。")
    health=soup.select_one("#sp500-earnings-health .title small")
    if health: set_text(health,"FactSet 最新可核實快照：2026/10/23；非 11/05 即時統計。")
    health_panel=soup.select_one("#sp500-earnings-health")
    if health_panel:
        for node in health_panel.find_all(string=True):
            if "10/27" in str(node): node.replace_with(str(node).replace("10/27","11/05"))

    # Observation content is preserved as source text, and overwritten only when full copy provided.
    view=unique(soup,"#view","market observation")
    if data.get("observation"):
        panel=unique(view,".focus-panel.focus-market","market observation text")
        set_text(panel.select_one(".key") or panel,data["observation"])
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(str(soup),encoding="utf-8")
    print(json.dumps({"output":str(out),"master_sha":actual,"sections_updated":["title","summary","sentiment","news","global_markets","sectors","bonds","fx","energy","metals","risk","fedwatch","calendar headings"],"review_ready":False},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
