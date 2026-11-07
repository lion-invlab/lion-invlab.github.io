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

def set_market_observation(node, title, value):
    """Render every observation block with the same heading + paragraph DOM."""
    raw = str(value or "").strip()
    if "｜" in raw and raw.startswith("📌"):
        raw = raw.split("｜", 1)[1].strip()
    node.clear()
    heading = BeautifulSoup("", "html.parser").new_tag("b")
    heading.string = title
    node.append(heading)
    node.append(BeautifulSoup("<br/>", "html.parser").br)
    node.append(raw)

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
    ap.add_argument("--key-levels-live", help="optional live OHLC capture envelope produced by collect_key_levels_ohlc.py")
    args=ap.parse_args()
    data=json.loads(Path(args.data).read_text())
    is_live_key_levels = False
    if args.key_levels_live:
        live=json.loads(Path(args.key_levels_live).read_text(encoding="utf-8"))
        if live.get("report_date") != data.get("report_date"):
            raise ValueError("live key-level report_date does not match report JSON")
        is_live_key_levels = (
            bool(live.get("captured_at_taipei"))
            and live.get("captured_at_taipei") != "fixture-only"
            and live.get("source") != "deterministic fixture; not live market data"
        )
        levels=live.get("key_levels")
        if not isinstance(levels, dict) or levels.get("baseline_date") != live.get("trading_date"):
            raise ValueError("live key-level baseline_date/trading_date mismatch")
        required_keys=("dow","sp500","nasdaq","sox","russell2000")
        rows=levels.get("items")
        if not isinstance(rows,list) or [row.get("key") for row in rows] != list(required_keys):
            raise ValueError("live key-level artifact must contain the five required indices in canonical order")
        for row in rows:
            if row.get("trading_date") != live.get("trading_date") or row.get("quote_type") != "cash_index":
                raise ValueError(f"live key-level row has invalid trading date or quote type: {row.get('key')}")
            if not row.get("source_name") or not str(row.get("url","")).startswith("https://"):
                raise ValueError(f"live key-level row missing source attribution: {row.get('key')}")
            if not all(row.get(field) for field in ("s1","p","r1","ohlc")):
                raise ValueError(f"live key-level row missing calculated levels/OHLC: {row.get('key')}")
        data["key_levels"]=levels
    # Fail closed on quote records without a traceable source and item-level date.
    # A top-level trading_date is not evidence that every market item was updated that day.
    market_groups = ["global_markets", "bonds", "fx", "energy", "metals"]
    for group_name in market_groups:
        for item_name, record in data.get(group_name, {}).items():
            source = record.get("source") if isinstance(record, dict) else None
            if not isinstance(source, dict) or not source.get("name") or not source.get("url") or not source.get("data_date"):
                if isinstance(record, dict):
                    record["display"] = "待核實"
                    record["change_display"] = "待核實"
                    record["qa_status"] = "missing_item_source_or_date"
    for key in ["vix", "move", "fear_greed"]:
        record = data.get("risk", {}).get(key, {})
        source = record.get("source") if isinstance(record, dict) else None
        item_date = (source or {}).get("data_date") or record.get("as_of_date") or record.get("as_of")
        if not isinstance(source, dict) or not source.get("name") or not source.get("url") or not item_date:
            record["display"] = "待核實"
            record["change_display"] = "待核實"
            record["qa_status"] = "missing_item_source_or_date"
    sector_sources = data.get("sector_sources", {})
    for ticker in list(data.get("sectors", {})):
        source = sector_sources.get(ticker, {})
        if not source.get("name") or not source.get("url") or not source.get("data_date"):
            data["sectors"][ticker] = "待核實"
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
    if monday:
        head.append(BeautifulSoup(disclosure_css, "html.parser").style)

    # Rebuild both disclosure labels with explicit marker/text spans. This avoids
    # inherited native markers and inconsistent pseudo-element spacing.
    if monday:
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
    # Rebuild every news card's complete data-bearing fields from the current JSON.
    # Never retain mother-template source URLs, publication timestamps or report-window labels.
    from urllib.parse import urlparse
    # Derive the report-specific news window before rendering either news section.
    news_window_start = (report_date - timedelta(days=3 if monday else 1)).strftime("%Y/%m/%d")
    news_window_start_label = news_window_start + " 12:00"
    news_window_end_label = report_cutoff
    news_window_label = f"{news_window_start_label}–{news_window_end_label}（台灣時間）"
    for section_id, items_key, expected, section_label in [
        ("global-focus","focus_news",5,"全球焦點"),
        ("headlines","headlines",10,"市場熱門頭條")
    ]:
        box=unique(soup,f"#{section_id}",section_id)
        nodes=box.select(".newsitem")
        items=data[items_key]
        if len(items)!=expected:
            raise ValueError(f"{items_key}: expected exactly {expected} current records, got {len(items)}")
        if len(nodes)<expected:
            raise ValueError(f"{section_id}: mother cards {len(nodes)} < {expected}")
        for idx,item in enumerate(items):
            if not item.get("title") or not item.get("summary") or not item.get("url") or not item.get("published_at_tw"):
                raise ValueError(f"{items_key}[{idx}]: title/summary/url/published_at_tw required")
            if not str(item["url"]).startswith("https://"):
                raise ValueError(f"{items_key}[{idx}]: non-HTTPS source URL")
            node=nodes[idx]
            title=unique(node,".news-title, h3, h4, strong",f"{section_id}[{idx}] title")
            prefix=(f"{idx+1}. " if section_id=="global-focus" else f"{idx+1:02d}｜")
            set_text(title,prefix+item["title"])
            summary_nodes=node.select(".news-summary, p, .summary")
            if not summary_nodes:
                raise ValueError(f"{section_id}[{idx}]: summary slot missing")
            set_text(summary_nodes[0],item["summary"])
            meta=unique(node,".newsmeta",f"{section_id}[{idx}] source metadata")
            meta.clear()
            host=urlparse(item["url"]).hostname or "原始來源"
            source=soup.new_tag("a",href=item["url"],target="_blank",rel="noopener")
            source.string=f"{host}｜發布 {item['published_at_tw']}（台灣時間）｜閱讀原文 ↗"
            meta.append(source)
        # Keep the report date and window visible in both news section headers.
        panel_meta=box.select_one(".tab-panel-meta")
        if panel_meta:
            set_text(panel_meta,f"{section_label}｜報告日期 {report_label}｜新聞時間窗：{news_window_label}")
        warning=box.select_one(".news-window-warning")
        if warning and section_id=="global-focus":
            set_text(warning,f"新聞時間窗｜{news_window_label}（台灣時間）。以下 5 則逐則列出發布時間與原始來源；不以行情報價或波動率數據充當新聞。")
    # Replace stale mother-template market snapshot labels; never leave its old 10/23 dates.
    for section_id, section_label in [
        ("global-markets", "全球主要股市"),
        ("bonds", "美債殖利率"),
        ("fx", "外匯"),
        ("tac-assets-panel-3", "能源期貨"),
        ("tac-assets-panel-4", "貴金屬期貨"),
    ]:
        section = unique(soup, f"#{section_id}", section_label)
        for meta in section.select(".tab-panel-meta"):
            set_text(meta, f"{section_label}｜報告基準日 {previous_trade}；各項報價日期、交易型態與來源以逐筆核實資料為準，未附完整來源者標示待核實。")
        for detail in section.select("details.source-details"):
            body = detail.select_one(".source")
            if body:
                set_text(body, f"本區報告基準日：{previous_trade}。逐項來源與報價日期需以當次資料快照核對；若該項未附可核實來源，不沿用母版舊來源，該項應視為待核實。")
    # Region quote rows are separate DOM nodes from the U.S. market tab.
    region_rows = {
        "香港恆生指數":"香港恆生指數", "上海綜合指數":"上海綜合指數", "深證成指":"深證成指",
        "日經 225":"日經 225", "韓國 KOSPI":"韓國 KOSPI", "台灣加權指數":"台灣加權指數",
        "新加坡海峽時報指數 STI":"新加坡海峽時報指數 STI", "澳洲 S&P/ASX 200":"澳洲 S&P/ASX 200",
        "英國 FTSE 100":"英國 FTSE 100", "德國 DAX":"德國 DAX", "法國 CAC 40":"法國 CAC 40",
        "STOXX Europe 600":"STOXX Europe 600",
    }
    # The two approved mothers expose regional quotes in different, SHA-locked DOM locations.
    # Monday retains legacy regional panels; Tue-Fri uses the three native global-market tabs.
    region_panel_specs = [
        ("#asia" if monday else "#tac-global-panel-1", "亞洲", 0),
        ("#tac-region-panel-2" if monday else "#tac-global-panel-2", "歐洲", 1),
    ]
    for selector, region_label, comment_index in region_panel_specs:
        panel = unique(soup, selector, f"{region_label} regional quote panel")
        for row in panel.select(".row"):
            label_node = row.select_one("a.global-index-link")
            if not label_node:
                continue
            key = region_rows.get(label_node.get_text(" ", strip=True))
            if not key:
                continue
            record = data.get("global_markets", {}).get(key, {})
            values = row.select("span.r")
            if len(values) >= 2:
                set_text(values[0], record.get("display", "待核實"))
                change = str(record.get("change_display", "待核實"))
                set_text(values[1], change)
                state = "up" if change.startswith("+") else "down" if change.startswith(("−", "-")) else "flat"
                values[1]["class"] = ["r", state] if change != "待核實" else ["r", "warn"]
        meta = panel.select_one(".tab-panel-meta")
        if meta:
            set_text(meta, f"{region_label}市場｜逐項行情以各自資料日期及來源註記；未附來源者顯示待核實。")
        reason = panel.select_one(".market-reason")
        if reason:
            comments = data.get("market_comments", {}).get("global_markets", [])
            if comment_index < len(comments):
                set_text(reason, comments[comment_index])
        for details_node in panel.select("details.source-details, details.region-source"):
            body = details_node.select_one(".source")
            if body:
                body.clear()
                for label, record in data.get("global_markets", {}).items():
                    if label not in region_rows:
                        continue
                    src = record.get("source") if isinstance(record, dict) else None
                    if isinstance(src, dict) and src.get("name") and src.get("url") and src.get("data_date"):
                        body.append(f"{label}｜{src['name']}｜{src['data_date']}｜")
                        body.append(source_link(src["url"], "來源"))
                        body.append("；")
    # All observation cards use the same semantic DOM: bold 📌 heading + line break + paragraph.
    # Target the active global-market tab panels explicitly; the former #asia / #tac-region-panel-2
    # selectors belonged to legacy region tabs and left the visible Asia tab stale.
    narrative_targets = [
        ("#tac-global-panel-0", "📌 美股觀察", "global_markets", 2),
        ("#tac-global-panel-1", "📌 亞股觀察", "global_markets", 3),
        ("#tac-global-panel-2", "📌 歐股觀察", "global_markets", 4),
        ("#asia", "📌 亞股摘要", "global_markets", 0),
        ("#tac-region-panel-2", "📌 歐股摘要", "global_markets", 1),
        ("#tac-assets-panel-0", "📌 產業觀察", "sectors", None),
        ("#bonds", "📌 債券觀察", "bonds", None),
        ("#fx", "📌 匯率觀察", "fx", None),
        ("#tac-assets-panel-3", "📌 原油觀察", "energy", None),
        ("#tac-assets-panel-4", "📌 貴金屬觀察", "metals", None),
    ]
    for selector, heading, group_key, idx in narrative_targets:
        section = soup.select_one(selector)
        if section is None:
            continue
        note = section.select_one(".market-reason")
        if note:
            if group_key == "global_markets":
                comments = data.get("market_comments", {}).get(group_key, [])
                value = comments[idx] if idx is not None and idx < len(comments) else ""
            else:
                value = data.get("market_comments", {}).get(group_key, "")
            if value:
                set_market_observation(note, heading, value)
    # Ensure all quote cards carry current per-item dates in the visible heading.
    # Current report label belongs to source link and section only; never duplicate timezone suffixes.
    for market_section in soup.select("#global-markets, #bonds, #fx, #tac-assets-panel-3, #tac-assets-panel-4"):
        meta_node = market_section.select_one(".tab-panel-meta")
        if meta_node:
            title_text = market_section.select_one(".tac-section-heading h2, .title")
            title_label = title_text.get_text(" ", strip=True) if title_text else "市場行情"
            set_text(meta_node, f"{title_label}｜資料基準 {previous_trade}；各品項日期與交易型態依來源逐項列示。")
    # Refresh report masthead, status banner and footer for this report date.
    for node in soup.select(".top .status, header .status, .status"):
        if node.get_text(strip=True):
            set_text(node, f"{report_label}（{report_weekday}）｜週一審核版；行情資料基準 {previous_trade}，各指標依項目日期與來源判讀")
    for warning in soup.select(".data-sync-warning"):
        scope_note = "五項關鍵價位已採即時 OHLC 擷取；其餘行情、新聞及行事曆仍為模擬 fixture，並非完整 live-data E2E。" if is_live_key_levels else "資料流為固定 JSON fixture → HTML 組裝器，並非 live data E2E。"
        set_text(warning, f"模擬審核版｜報告日期 {report_iso}｜{scope_note} 缺少來源／日期的行情依 fail-closed 規則顯示待核實；本檔僅供模擬區審核，未發布至正式首頁。")
    footer = soup.select_one("footer.footer")
    if footer:
        scope_note = "五項關鍵價位採即時 OHLC 擷取；其餘行情、新聞與行事曆仍為模擬 fixture，非完整 live-data E2E" if is_live_key_levels else "本版由固定 JSON fixture 組裝，非 live data E2E"
        set_text(footer, f"TAC 投資早報｜{report_label}（{report_weekday}）審核版｜行情資料基準 {previous_trade}｜缺少來源或日期的項目明確標示待核實；{scope_note}。資訊整理與教育用途，不構成投資建議。")
    # Remove duplicate timezone suffix from preformatted window label.
    news_window_label = news_window_label.replace("（台灣時間）", "")
    # The three Today Focus tabs are updated atomically below; do not clear their approved DOM here.
    # Update only the explicitly historical FactSet snapshot; its historical date remains intentional.
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
    ranked_rows_for_source = [row for row, _, _ in ranked]
    # Sector source list explicitly calls out every item without complete provenance.
    sector_meta = soup.select_one("#tac-assets-panel-0 .tab-panel-meta")
    if sector_meta:
        set_text(sector_meta, f"11檔產業ETF單日漲跌幅｜{previous_trade}美股收盤｜僅依可追溯來源與資料日期核實；缺漏者待核實")
    sector_source = soup.select_one("#tac-assets-panel-0 details .source")
    if sector_source:
        sector_source.clear()
        for ticker in [x[1] for x in ranked]:
            src = data.get("sector_sources", {}).get(ticker, {})
            if src.get("name") and src.get("url") and src.get("data_date"):
                sector_source.append(f"{ticker}｜{src['name']}｜{src['data_date']}｜")
                sector_source.append(source_link(src["url"], "來源"))
                sector_source.append("；")
            else:
                sector_source.append(f"{ticker}｜待核實（缺來源或資料日期）；")
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
    displayed_tickers=[]
    displayed_changes=[]
    for expected_rank,row in enumerate(displayed,start=1):
        rank_text=unique(row,".rank","sector rank").get_text(strip=True)
        if rank_text!=str(expected_rank):
            raise ValueError(f"sector rank mismatch: expected {expected_rank}, got {rank_text}")
        displayed_tickers.append(sector_ticker(row))
        displayed_changes.append(sector_change(row))
    expected_tickers=[ticker for _,ticker,_ in ranked]
    if displayed_tickers!=expected_tickers:
        raise ValueError("sector ETF DOM order differs from computed ranking order")
    verified=[x for x in displayed_changes if x is not None]
    if verified!=sorted(verified,reverse=True):
        raise ValueError("sector ETF order is not descending by verified daily change")
    first_pending=next((i for i,x in enumerate(displayed_changes) if x is None),len(displayed_changes))
    if any(x is not None for x in displayed_changes[first_pending:]):
        raise ValueError("verified sector ETF appears after an unverified ETF")
    # The sector ETF panel also carries source prose and a dated heading; refresh both.
    sector_meta = sectors.select_one(".tab-panel-meta")
    if sector_meta:
        set_text(sector_meta, f"11檔產業ETF單日漲跌幅｜{previous_trade}美股收盤｜已核實項目依單日漲跌幅降序；未核實項目列後")
    sector_source = sectors.select_one("details.sector-source .source") or sectors.select_one("details.source-details .source")
    if sector_source:
        sector_source.clear()
        verified_sector_lines = []
        for ticker in [sector_ticker(row) for row in ranked_rows_for_source]:
            item = data.get("sector_sources", {}).get(ticker, {})
            if item.get("name") and item.get("url") and item.get("data_date"):
                sector_source.append(f"{ticker}｜{item['name']}｜{item['data_date']}｜")
                sector_source.append(source_link(item["url"], "原始來源"))
                sector_source.append("；")
        pending_tickers = [ticker for ticker in data.get("sectors", {}) if ticker not in data.get("sector_sources", {})]
        if pending_tickers:
            sector_source.append("未核實（缺來源／日期，未沿用母版數據）： " + "、".join(pending_tickers))
    # Date and item provenance in every region tab are updated from the same records.
    for selector, _, _ in region_panel_specs:
        panel = soup.select_one(selector)
        if panel:
            region_meta = panel.select_one(".tab-panel-meta")
            if region_meta:
                set_text(region_meta, f"{selector}｜市場報價資料基準 {previous_trade}；無逐項來源與日期者顯示待核實。")
    # Classify global market moves according to the report color convention (rise red, fall green).
    for row in gm.select(".row"):
        spans = row.select("span.r")
        if len(spans) >= 2:
            change = spans[1].get_text(strip=True)
            state = "up" if change.startswith("+") else "down" if change.startswith(("−", "-")) else "flat"
            spans[1]["class"] = ["r", state] if change != "待核實" else ["r", "warn"]
    # Replace all remaining old source paragraphs in risk and market cards with current evidence state.
    # Refresh quote metadata for every instrument group; unresolved rows are explicitly listed.
    for group_id, records in [
        ("global-markets", data.get("global_markets", {})),
        ("bonds", data.get("bonds", {})),
        ("fx", data.get("fx", {})),
        ("tac-assets-panel-3", data.get("energy", {})),
        ("tac-assets-panel-4", data.get("metals", {})),
    ]:
        group = soup.select_one("#" + group_id)
        if not group:
            continue
        summary = []
        for instrument, record in records.items():
            source = record.get("source") if isinstance(record, dict) else None
            if isinstance(source, dict) and source.get("name") and source.get("url") and source.get("data_date"):
                summary.append((instrument, source))
        for details_node in group.select("details.source-details"):
            source_node = details_node.select_one(".source")
            if source_node:
                source_node.clear()
                if summary:
                    for instrument, source in summary:
                        source_node.append(f"{instrument}｜{source['name']}｜{source['data_date']}｜")
                        source_node.append(source_link(source["url"], "原始資料"))
                        source_node.append("；")
                else:
                    source_node.append("本區沒有具備來源、URL 與逐項資料日期的可核實報價；相關值已標示待核實。")
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
    # Refresh risk quote value, move, source and date together. Never retain mother-template quote annotations.
    for key,label in [("vix","VIX"),("move","MOVE")]:
        record = data["risk"][key]
        rows=[r for r in sent.select(".sbox") if (r.select_one(".label-en") and r.select_one(".label-en").get_text(" ",strip=True).strip()==label)]
        if not rows: raise ValueError(f"{label} row not found")
        source = record.get("source") or {}
        is_verified = bool(source.get("name") and source.get("url") and source.get("data_date"))
        if key == "move" and str(record.get("as_of_date", "")).startswith("未取得"):
            is_verified = False
        if not is_verified:
            record["display"] = "待核實"
            record["change_display"] = "待核實"
        for row in rows:
            strong=row.select("strong")
            if not strong: raise ValueError(f"{label} value slot missing")
            set_text(strong[-1],record.get("display","待核實"))
            change_nodes = row.select(".up, .down, .warn, .flat")
            if change_nodes:
                change_node = change_nodes[0]
                set_text(change_node,record.get("change_display","待核實"))
                change_text = str(record.get("change_display","待核實"))
                change_state = "up" if change_text.startswith("+") else "down" if change_text.startswith(("−","-")) else "flat"
                change_node["class"] = [change_state] if change_text != "待核實" else ["warn"]
            source_node = row.select_one(".source-details .source")
            if source_node:
                source_node.clear()
                if is_verified:
                    source_node.append(f'{source.get("name")}｜資料日期 {source.get("data_date")}｜')
                    if source.get("url"):
                        source_node.append(source_link(source["url"], "查看原始資料"))
                    if source.get("note"):
                        source_node.append("｜" + str(source["note"]))
                else:
                    reason = "來源或資料日期未核實，母版舊數值及變動率已清除。"
                    if record.get("as_of_date"):
                        reason = str(record["as_of_date"]) + "；" + reason
                    source_node.append(reason)
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
        current_range=data["fedwatch"].get("current_target_range")
        if len(hold)!=1 or not current_range:
            raise ValueError("FedWatch requires one hold outcome and the official current target range")
        if hold[0].get("rate_range") != current_range:
            raise ValueError(f"FedWatch hold range {hold[0].get('rate_range')} does not match current target range {current_range}")
        # A single +25 bp outcome must be exactly one quarter-point above the current range.
        hikes=[x for x in nonhold if x.get("outcome")=="hike"]
        cuts=[x for x in nonhold if x.get("outcome")=="cut"]
        if hikes and cuts:
            raise ValueError("FedWatch cannot mix hike and cut outcomes in this two-card summary")
        if hikes and len(hikes)==1:
            nums=[float(v) for v in re.findall(r"\d+(?:\.\d+)?", str(hikes[0].get("rate_range","")))]
            current_nums=[float(v) for v in re.findall(r"\d+(?:\.\d+)?", str(current_range))]
            if len(nums)!=2 or len(current_nums)!=2 or abs(nums[0]-(current_nums[0]+0.25))>0.001 or abs(nums[1]-(current_nums[1]+0.25))>0.001:
                raise ValueError("FedWatch hike range must be exactly +25 bp above the official current target range")
        directions={x.get("outcome") for x in nonhold}
        if directions=={"hike"}:
            nonhold_label="升息一碼" if len(nonhold)==1 else "升息機率（合計）"
        elif directions=={"cut"}:
            nonhold_label="降息一碼" if len(nonhold)==1 else "降息機率（合計）"
        else:
            nonhold_label="政策區間變動（合計）"
        set_text(unique(rows[0],"strong","hold prob"),f'{float(hold[0]["probability"]):.1f}%')
        set_text(unique(rows[0],".fc-range","hold range"),current_range)
        set_text(unique(rows[0],".fc-prob-label span:not(.fc-dot)","hold label"),"維持不變")
        set_text(unique(rows[1],"strong","non-hold prob"),f'{sum(float(x["probability"]) for x in nonhold):.1f}%')
        set_text(unique(rows[1],".fc-range","non-hold range"),"；".join(f'{x["rate_range"]} {float(x["probability"]):.1f}%' for x in nonhold))
        set_text(unique(rows[1],".fc-prob-label span:not(.fc-dot)","non-hold label"),nonhold_label)
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
    # Replace stale mother-template disclaimer with the actual verified snapshot state.
    snapshot_note = f"Investing.com Fed Rate Monitor｜目標會議 {data['fedwatch'].get('target_meeting','待核實')}｜更新時間 {ts}。"
    snapshot_detail = fed.select_one("details")
    if snapshot_detail:
        detail_body = snapshot_detail.select_one("div")
        if detail_body:
            set_text(detail_body, snapshot_note + " 本版採頁面所列機率分布，非舊截圖或自行估算。")
    source_line = fed.select_one(".fc-source")
    if source_line:
        for text_node in list(source_line.find_all(string=True)):
            if "本次資料截點未取得可核實的機率快照" in str(text_node):
                text_node.replace_with("｜" + snapshot_note)
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
        set_text(news_window, f"新聞時間窗｜{news_window_label}（台灣時間）。焦點新聞與市場熱門頭條均逐則核對原始報導及發布時間；未符合時間窗的資料不納入。")
    health = soup.select_one("#sp500-earnings-health")
    if health:
        # FactSet's latest official Q3 2026 earnings-season update (published 11/06).
        # Preserve the existing health-dashboard card and visual system; replace only its content.
        from bs4 import BeautifulSoup as _BS
        health.clear()
        _health_fragment = _BS("""
<div class="title">S&amp;P 500｜本季盈餘健康度 <small>FactSet｜2026/11/06（Q3 2026，88% 成份股已公布）</small></div>
<div style="margin-top:10px;padding:14px 15px;background:#f1f6fb;border:1px solid #d6e3ee;border-left:5px solid #c62828;border-radius:11px;color:#202124">
<div style="font-size:11px;font-weight:850;color:#626a73;margin-bottom:5px">TAC 核心判讀</div>
<div style="font-size:18px;line-height:1.45;font-weight:950;margin-bottom:6px;color:#202124">獲利成長強勁，但超預期幅度偏低；企業基本面呈現「高成長、低驚喜」。</div>
<div style="font-size:13px;line-height:1.7;color:#30343a">截至 11/06，標普 500 有 88% 成份股公布 Q3 財報；84% EPS 優於預期，高於五年均值 78%，但平均僅超預期 2.7%，遠低於五年均值 7.5%。混合盈餘年增 31.4%，已連續第三季高於 25%。</div></div>
<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px">
<div style="padding:11px 12px;background:#fff5f4;border:1px solid #f0d6d4;border-radius:10px;color:#202124"><div style="font-size:11px;font-weight:800;color:#626a73">混合盈餘年增率</div><div style="font-size:25px;font-weight:950;color:#c62828;margin:3px 0">+31.4%</div><div style="font-size:11px;line-height:1.45;color:#30343a">前週 30.1%；連續第三季高於 25%</div></div>
<div style="padding:11px 12px;background:#eff8f2;border:1px solid #d3e8da;border-radius:10px;color:#202124"><div style="font-size:11px;font-weight:800;color:#626a73">EPS 優於預期公司比例</div><div style="font-size:25px;font-weight:950;color:#16804a;margin:3px 0">84%</div><div style="font-size:11px;line-height:1.45;color:#30343a">高於 5 年均值 78%／10 年均值 77%</div></div>
<div style="padding:11px 12px;background:#fff7eb;border:1px solid #f0dfc2;border-radius:10px;color:#202124"><div style="font-size:11px;font-weight:800;color:#626a73">EPS 平均超預期幅度</div><div style="font-size:25px;font-weight:950;color:#ad7427;margin:3px 0">+2.7%</div><div style="font-size:11px;line-height:1.45;color:#30343a">低於 5 年均值 7.5%／10 年均值 8.0%</div></div>
<div style="padding:11px 12px;background:#f1f6fb;border:1px solid #d6e3ee;border-radius:10px;color:#202124"><div style="font-size:11px;font-weight:800;color:#626a73">混合營收年增率</div><div style="font-size:25px;font-weight:950;color:#c62828;margin:3px 0">+14.3%</div><div style="font-size:11px;line-height:1.45;color:#30343a">前週 13.6%；連續第三季雙位數成長</div></div>
<div style="padding:11px 12px;background:#eff8f2;border:1px solid #d3e8da;border-radius:10px;color:#202124"><div style="font-size:11px;font-weight:800;color:#626a73">營收優於預期公司比例</div><div style="font-size:25px;font-weight:950;color:#16804a;margin:3px 0">74%</div><div style="font-size:11px;line-height:1.45;color:#30343a">高於 5 年均值 70%／10 年均值 68%</div></div>
<div style="padding:11px 12px;background:#f1f6fb;border:1px solid #d6e3ee;border-radius:10px;color:#202124"><div style="font-size:11px;font-weight:800;color:#626a73">Forward 12M P/E</div><div style="font-size:25px;font-weight:950;color:#202124;margin:3px 0">17.7 倍</div><div style="font-size:11px;line-height:1.45;color:#30343a">低於 5 年均值 19.8 倍／10 年均值 19.1 倍</div></div></div>
<div style="margin-top:10px;padding:12px 14px;border:1px solid #e1e5e9;border-radius:10px;color:#202124"><div style="font-size:13px;font-weight:900;margin-bottom:6px;color:#202124">如何解讀</div><div style="font-size:13px;line-height:1.75;color:#30343a"><b style="color:#16804a">正面：</b>獲利年增 31.4%，11 個產業全數呈現獲利年增；營收年增 14.3%，11 個產業營收亦全數年增。<br><b style="color:#ad7427">保留：</b>EPS 優於預期比例雖達 84%，但平均超預期幅度僅 2.7%，若此數字成為最終值，將是 2022 年 Q4 以來最低。<br><b style="color:#202124">估值：</b>Forward P/E 17.7 倍，低於五年與十年均值，亦低於 Q3 季底的 19.0 倍。</div></div>
<div style="margin-top:9px;padding:10px 12px;background:#fff8ed;border:1px solid #efdfc7;border-radius:9px;font-size:12px;line-height:1.65;color:#30343a"><b style="color:#202124">接下來看三件事：</b>EPS 超預期幅度能否回升、Q3 財報季收官後獲利增速是否維持 30% 以上、Q4 分析師預估獲利成長 28.4% 是否開始下修。</div>
<details style="margin-top:8px;font-size:11px;color:#626a73"><summary style="cursor:pointer;font-weight:800">資料來源與統計口徑</summary><div style="padding:8px 0;line-height:1.6">FactSet《S&amp;P 500 Earnings Season Update: November 6, 2026》，John Butters，發布日期 2026/11/06。混合盈餘／營收成長率結合已公布實績與尚未公布公司的分析師預估；截至報告日 88% 的標普 500 成份股已公布 Q3 財報。數值為 FactSet 報告當週快照，非即時盤中更新。<br><a href="https://insight.factset.com/sp-500-earnings-season-update-november-6-2026" target="_blank" rel="noopener" style="color:#1d4ed8">FactSet 11/06 官方報告</a></div></details>
""", "html.parser")
        for _node in list(_health_fragment.contents):
            health.append(_node)
    fed = soup.select_one("#fed")
    if fed:
        meeting = fed.select_one(".fc-fomc-meeting b")
        if meeting: set_text(meeting, "2026/12/08–12/09")
        press = fed.select_one(".fc-fomc-press b")
        if press: set_text(press, "2026/12/10 03:30")
        rate = fed.select_one(".fc-fomc-rate b")
        current_target_range = data.get("fedwatch", {}).get("current_target_range", "待核實")
        if rate: set_text(rate, current_target_range.replace("–", "%–") + ("%" if current_target_range != "待核實" and not current_target_range.endswith("%") else ""))
        rate_date = fed.select_one(".fc-fomc-rate small")
        if rate_date: set_text(rate_date, "Fed官方最新資料：2026/10/29")
        # FOMC tab is a weekly, calendar-driven "limited-time updates" feed.
        # Use only verified US inflation releases and scheduled Fed speaker events
        # already present in this report's weekly calendar; never hard-code dates.
        observation = fed.select_one(".fc-fomc-observation")
        if observation:
            from datetime import date
            weekly = data.get("calendar", {})
            report_day = date.fromisoformat(data.get("report_date"))
            week_end = date.fromisoformat(weekly.get("week_end", data.get("report_date")))
            selected = []
            for event in weekly.get("events", []):
                if event.get("region") != "美國":
                    continue
                name = str(event.get("name", ""))
                relevant = any(term in name.lower() for term in ("cpi", "ppi", "聯準會", "federal reserve", "fed "))
                if not relevant:
                    continue
                try:
                    dt = datetime.fromisoformat(str(event.get("date", "")).replace("Z", "+00:00"))
                    event_day = dt.date()
                except (TypeError, ValueError):
                    continue
                if event_day < report_day or event_day > week_end:
                    continue
                selected.append((dt, event))
            selected.sort(key=lambda pair: pair[0])
            observation.clear()
            observation.name = "div"
            observation["class"] = ["fc-fomc-weekly-events"]
            observation["style"] = "grid-column:1 / -1;grid-row:2;display:block;min-width:0;padding:12px 14px;border:1px solid #dce4ec;border-radius:12px;background:#f7f9fc;box-sizing:border-box;"
            title = soup.new_tag("div")
            title.string = "本週聯準會限時動態"
            title["style"] = "font-size:15px;font-weight:850;color:#244b68;margin:0 0 9px;"
            observation.append(title)
            if selected:
                for dt, event in selected[:6]:
                    card = soup.new_tag("div")
                    card["style"] = "display:grid;grid-template-columns:94px minmax(0,1fr);gap:8px;padding:9px 0;border-top:1px solid #e1e7ee;"
                    stamp = soup.new_tag("div")
                    stamp["style"] = "font-size:12px;line-height:1.5;font-weight:850;color:#a92a32;"
                    stamp.string = dt.strftime("%m/%d") + " " + ["一","二","三","四","五","六","日"][dt.weekday()]
                    if event.get("time_known", True):
                        stamp.string += dt.strftime(" %H:%M")
                    else:
                        stamp.string += " 時間待確認"
                    body = soup.new_tag("div")
                    heading = soup.new_tag("div")
                    heading["style"] = "font-size:13px;line-height:1.45;font-weight:800;color:#273746;"
                    heading.string = str(event.get("name", ""))
                    body.append(heading)
                    impact = str(event.get("impact", "")).strip()
                    if impact:
                        desc = soup.new_tag("div")
                        desc["style"] = "font-size:12px;line-height:1.55;color:#687583;margin-top:3px;"
                        desc.string = impact
                        body.append(desc)
                    url = event.get("source_url")
                    if isinstance(url, str) and url.startswith("https://"):
                        link = source_link(url, str(event.get("source_name") or "官方來源"))
                        link["style"] = "display:inline-block;font-size:11px;margin-top:4px;color:#315d7b;text-decoration:underline;"
                        body.append(link)
                    card.append(stamp)
                    card.append(body)
                    observation.append(card)
            else:
                empty = soup.new_tag("div")
                empty["style"] = "font-size:12px;color:#687583;line-height:1.5;"
                empty.string = "本週尚無已核實的美國通膨數據或聯準會官員公開談話排程。"
                observation.append(empty)
            note = soup.new_tag("div")
            note["style"] = "font-size:10px;color:#7b8793;margin-top:8px;"
            note.string = "事件與時間依本週經濟行事曆更新；未確認時刻不推測。"
            observation.append(note)
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
            snapshot_note = f"12/09會議機率資料更新：{data.get('fedwatch',{}).get('updated_at_tw','時間待核實')}；採頁面公布值，非自行估算。"
            fed_source.append(snapshot_note)
        probabilities = data.get("fedwatch", {}).get("probabilities", [])
        watch=fed.select_one(".fed-live-watch")
        if watch:
            bar=watch.select_one(".fc-split-bar")
            if bar and probabilities:
                bar["aria-label"]="；".join(f"{x.get('rate_range')} {float(x.get('probability',0)):.1f}%" for x in probabilities)
                bar.attrs.pop("style", None)
            elif bar:
                bar["aria-label"]="未取得 2026/11/09 05:25 前可核實的 FedWatch 機率快照"
                bar["style"]="display:none"
            note=watch.select_one("details > div")
            if note:
                if probabilities:
                    set_text(note, f"本次報告資料截點為 {report_cutoff}（台灣時間）。Investing.com Fed Rate Monitor 於 {data.get('fedwatch',{}).get('updated_at_tw','時間待核實')} 提供 2026/12/09 會議機率；本版依來源頁面公布值呈現，不以舊截圖或自行估算代替。")
                else:
                    set_text(note, f"本次報告資料截點為 {report_cutoff}（台灣時間）。未取得該截點前可核實的 FedWatch 機率快照，因此不填入推估機率。")
    fg = soup.select_one(".cnn-fg-preview")
    if fg:
        fg_record = data.get("risk", {}).get("fear_greed", {})
        fg_value = fg_record.get("display", "待核實")
        fg_source = fg_record.get("source", {})
        fg_date = fg_record.get("as_of", previous_trade)
        date_node = fg.select_one(".fg6-date")
        if date_node:
            source_label = "CNN官方歷史讀值" if "FGScore" not in str(fg_source.get("name","")) else "FGScore｜CNN Provider Index備援"
            set_text(date_node, f"{source_label}｜{fg_date}")
        score = fg.select_one(".fg6-score")
        if score: set_text(score, fg_value)
        klass = fg.select_one(".fg6-class")
        if klass: set_text(klass, fg_record.get("band", "待核實"))
        explanation = fg_source.get("note") or "未取得可核實的官方歷史讀值，暫不判定市場恐懼或貪婪程度。"
        explain = fg.select_one(".fg6-explain")
        if explain: set_text(explain, explanation)
        source_detail = fg.select_one(".source-details .source")
        if source_detail:
            source_detail.clear()
            source_detail.append(explanation)
    # Refresh regional market tabs using the location registered for each approved mother.
    region_specs = [
        (region_panel_specs[0][0], {"台灣加權指數":"台灣加權指數","香港恆生指數":"香港恆生指數","上海綜合指數":"上海綜合指數","深證成指":"深證成指","日經225":"日經 225","日經 225":"日經 225","韓國KOSPI":"韓國 KOSPI","韓國 KOSPI":"韓國 KOSPI"}, 0, f"亞洲市場｜{previous_trade}各市場當地正式收盤", [
            ("https://apnews.com/article/806f71d95105bc7efbc760b194dd8cad","AP市場報導"),
            ("https://www.investing.com/indices/japan-ni225-historical-data","Nikkei 225"),
            ("https://www.investing.com/indices/kospi-historical-data","KOSPI"),
            ("https://www.investing.com/indices/taiwan-weighted-historical-data","TWSE"),
            ("https://www.investing.com/indices/hang-sen-40-historical-data","Hang Seng"),
            ("https://www.investing.com/indices/shanghai-composite-historical-data","Shanghai"),
            ("https://www.investing.com/indices/shenzhen-composite-historical-data","Shenzhen")
        ]),
        (region_panel_specs[1][0], {"英國FTSE 100":"英國 FTSE 100","英國 FTSE100":"英國 FTSE 100","德國DAX":"德國 DAX","德國 DAX":"德國 DAX","法國CAC 40":"法國 CAC 40","法國 CAC 40":"法國 CAC 40","STOXX Europe 600":"STOXX Europe 600"}, 1, f"歐洲市場｜{previous_trade}各市場當地正式收盤", [
            ("https://www.investing.com/indices/uk-100-historical-data","FTSE 100"),
            ("https://www.investing.com/indices/germany-30-historical-data","DAX"),
            ("https://www.investing.com/indices/france-40-historical-data","CAC 40"),
            ("https://www.investing.com/indices/stoxx-600-historical-data","STOXX Europe 600")
        ])
    ]
    for selector, row_map, comment_index, meta_text, links in region_specs:
        panel = unique(soup, selector, "regional market panel")
        meta = panel.select_one(".tab-panel-meta")
        if meta: set_text(meta, meta_text)
        normalized_map = {"".join(str(label).split()): key for label, key in row_map.items()}
        for row in panel.select(".row"):
            label = row.select_one("a.global-index-link")
            if not label: continue
            normalized_label = "".join(label.get_text(" ", strip=True).split())
            key = normalized_map.get(normalized_label)
            record = data.get("global_markets", {}).get(key) if key else None
            spans = row.select("span.r")
            if record and len(spans) >= 2:
                set_text(spans[0], record.get("display","待核實"))
                change = record.get("change_display","待核實")
                set_text(spans[1], change)
                state = "up" if "+" in str(change) else "down" if ("−" in str(change) or "-" in str(change)) else "flat"
                spans[1]["class"] = ["r", state] if change != "待核實" else ["r", "warn"]
        reason = panel.select_one(".market-reason")
        comments = data.get("market_comments", {}).get("global_markets", [])
        if reason and comment_index < len(comments): set_text(reason, comments[comment_index])
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
        set_market_observation(panel.select_one(".key") or panel, "市場觀點", data["observation"])

    # Populate all three existing Today Focus tabs; never leave stale mother-template text.
    if data.get("key_levels"):
        levels_panel = unique(view, ".focus-panel.focus-levels", "key levels tab")
        levels_box = unique(levels_panel, ".key", "key levels content")
        disclosure = levels_box.select_one("details.compact-disclosure")
        if disclosure is None:
            raise ValueError("key levels source/method disclosure missing from approved mother template")
        disclosure.extract()
        levels_box.clear()
        for item in data["key_levels"].get("items", []):
            line = soup.new_tag("div")
            label = soup.new_tag("b")
            label.string = item["name"] + "："
            line.append(label)
            line.append(f"支撐 S1：{item['s1']}｜中樞 P：{item['p']}｜壓力 R1：{item['r1']}")
            levels_box.append(line)
            levels_box.append(soup.new_tag("br"))
        levels_box.append(disclosure)
        detail_body = disclosure.select_one("div")
        if detail_body is None:
            raise ValueError("key levels disclosure body missing")
        detail_body.clear()
        detail_body.append(f"基準交易日：{data['key_levels']['baseline_date']}（美國當地正式收盤）。{data['key_levels']['formula']} ")
        for item in data["key_levels"].get("items", []):
            detail_body.append(soup.new_tag("br"))
            detail_body.append(f"{item['name']}｜{item['ohlc']}｜")
            detail_body.append(source_link(item["url"], "Yahoo Finance OHLC"))
            detail_body.append("。")
    else:
        raise ValueError("key_levels data missing; refusing to retain stale mother-template key levels")
    if data.get("core_observation"):
        core_panel = unique(view, ".focus-panel.focus-core", "core observation tab")
        callout = unique(core_panel, ".callout", "core observation content")
        disclosure = callout.select_one("details.compact-disclosure")
        if disclosure is None:
            raise ValueError("core observation disclosure missing from approved mother template")
        disclosure.extract()
        callout.clear()
        title = soup.new_tag("b")
        title.string = data["core_observation"].get("heading", "今日核心觀察") + "："
        callout.append(title)
        callout.append(data["core_observation"]["text"])
        callout.append(soup.new_tag("br"))
        callout.append(disclosure)
        detail_nodes = disclosure.select("div")
        if not detail_nodes:
            raise ValueError("core observation disclosure detail body missing")
        detail_nodes[0].clear()
        detail_nodes[0].append(data["core_observation"].get("details", ""))
        for stale_detail in detail_nodes[1:]:
            stale_detail.decompose()
    else:
        raise ValueError("core_observation data missing; refusing to retain stale mother-template core text")
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
    # Fail closed if any Today Focus tab is stale, missing, or only partially assembled.
    focus_tabs = {
        "market": unique(view, ".focus-panel.focus-market", "market tab"),
        "levels": unique(view, ".focus-panel.focus-levels", "levels tab"),
        "core": unique(view, ".focus-panel.focus-core", "core tab"),
    }
    if len(view.select(".focus-tab-labels label")) != 3 or len(view.select(".focus-panels > .focus-panel")) != 3:
        raise ValueError("Today Focus must retain exactly three approved tabs and panels")
    if data["observation"] not in focus_tabs["market"].get_text(" ", strip=True):
        raise ValueError("market observation text did not assemble")
    levels_text = focus_tabs["levels"].get_text(" ", strip=True)
    if len(data["key_levels"].get("items", [])) != 5 or any(item["s1"] not in levels_text or item["p"] not in levels_text or item["r1"] not in levels_text for item in data["key_levels"]["items"]):
        raise ValueError("one or more key levels did not assemble")
    if data["core_observation"]["text"] not in focus_tabs["core"].get_text(" ", strip=True):
        raise ValueError("core observation text did not assemble")
    focus_text = view.get_text(" ", strip=True)
    if "10/23" in focus_text or "2026/10/23" in focus_text:
        raise ValueError("stale 10/23 mother-template text remains in Today Focus")
    if data.get("bonds", {}).get("2年期美債殖利率", {}).get("change_display") == "待核實":
        raise ValueError("2-year Treasury daily change remains unresolved")
    for item in data["key_levels"]["items"]:
        if not any(a.get("href") == item["url"] for a in focus_tabs["levels"].select("a")):
            raise ValueError("key level OHLC source link missing for " + item.get("name", "unknown index"))
    # Enforce the selected template's weekday-specific section contract.
    monday_only_ids = ("#last-week-calendar", "#last-week-earnings")
    if monday:
        for selector in monday_only_ids:
            unique(soup, selector, "Monday-only section")
    elif any(soup.select(selector) for selector in monday_only_ids):
        raise ValueError("weekday mother/output must not contain Monday-only previous-week sections")
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(str(soup),encoding="utf-8")
    print(json.dumps({"output":str(out),"master_sha":actual,"report_date":report_iso,"template":"monday" if monday else "weekdays","sections_updated":["title","summary","sentiment","news","global_markets","sectors","bonds","fx","energy","metals","risk","fedwatch","calendar headings"],"review_ready":False},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
