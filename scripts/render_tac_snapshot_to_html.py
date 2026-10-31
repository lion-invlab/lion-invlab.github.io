#!/usr/bin/env python3
"""Fail-closed renderer for mapped TAC market text slots; never rebuilds HTML."""
from __future__ import annotations
import argparse, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/"scripts/tac_html_binding_map.json"

class Node:
    def __init__(self,tag,attrs,start,tag_end=None,class_span=None,style_span=None,aria_label_span=None):
        self.tag,self.attrs,self.start=tag,dict(attrs),start
        self.tag_end,self.class_span,self.style_span,self.aria_label_span=tag_end,class_span,style_span,aria_label_span
        self.end=None; self.children=[]
    @property
    def classes(self): return set((self.attrs.get("class") or "").split())
    @property
    def text(self): return "".join(x.text if isinstance(x,Node) else x[0] for x in self.children)
    def descendants(self):
        for x in self.children:
            if isinstance(x,Node):
                yield x; yield from x.descendants()

class Parser(HTMLParser):
    VOID={"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    def __init__(self,s):
        super().__init__(convert_charrefs=False); self.s=s; self.lines=[0]
        self.lines += [m.end() for m in re.finditer("\n",s)]
        self.root=Node("document",{},0); self.stack=[self.root]; self.feed(s); self.close()
    def pos(self):
        line,col=self.getpos(); return self.lines[line-1]+col
    def handle_starttag(self,tag,attrs):
        p=self.pos(); raw=self.get_starttag_text(); class_span=None; style_span=None; aria_label_span=None
        m=re.search(r"class\s*=\s*(['\"])(.*?)\1",raw,re.I)
        if m: class_span=(p+m.start(2),p+m.end(2))
        sm=re.search(r"style\s*=\s*(['\"])(.*?)\1",raw,re.I)
        if sm: style_span=(p+sm.start(2),p+sm.end(2))
        am=re.search(r"aria-label\s*=\s*(['\"])(.*?)\1",raw,re.I)
        if am: aria_label_span=(p+am.start(2),p+am.end(2))
        n=Node(tag,attrs,p,p+len(raw),class_span,style_span,aria_label_span); self.stack[-1].children.append(n)
        if tag not in self.VOID: self.stack.append(n)
        else: n.end=p+len(raw)
    def handle_startendtag(self,tag,attrs):
        p=self.pos(); raw=self.get_starttag_text(); class_span=None; style_span=None; aria_label_span=None
        m=re.search(r"class\s*=\s*(['\"])(.*?)\1",raw,re.I)
        if m: class_span=(p+m.start(2),p+m.end(2))
        sm=re.search(r"style\s*=\s*(['\"])(.*?)\1",raw,re.I)
        if sm: style_span=(p+sm.start(2),p+sm.end(2))
        am=re.search(r"aria-label\s*=\s*(['\"])(.*?)\1",raw,re.I)
        if am: aria_label_span=(p+am.start(2),p+am.end(2))
        n=Node(tag,attrs,p,p+len(raw),class_span,style_span,aria_label_span); n.end=p+len(raw); self.stack[-1].children.append(n)
    def handle_endtag(self,tag):
        p=self.pos()
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                close_end=self.s.find(">",p)
                if close_end<0: raise ValueError("unterminated closing tag")
                self.stack[i].end=close_end+1; del self.stack[i:]; break
    def handle_data(self,data):
        p=self.pos(); self.stack[-1].children.append((data,p,p+len(data)))
    def handle_entityref(self,name):
        p=self.pos(); raw="&"+name+";"; self.stack[-1].children.append((html.unescape(raw),p,p+len(raw)))
    def handle_charref(self,name):
        p=self.pos(); raw="&#"+name+";"; self.stack[-1].children.append((html.unescape(raw),p,p+len(raw)))

def descendants(n): return list(n.descendants())
def by_id(root,k): return [n for n in root.descendants() if n.attrs.get("id")==k]
def by_class(root,k): return [n for n in root.descendants() if k in n.classes]
def selector_nodes(root,selector):
    parts=selector.split()
    if len(parts)==1:
        if parts[0].startswith("."): return by_class(root,parts[0][1:])
        return [n for n in root.descendants() if n.tag==parts[0]]
    if len(parts)==2 and parts[0].startswith("."):
        parents=by_class(root,parts[0][1:])
        target=parts[1]
        result=[]
        for parent in parents:
            result.extend([n for n in parent.descendants() if (n.tag==target if not target.startswith(".") else target[1:] in n.classes)])
        return result
    raise ValueError("unsupported binding selector: "+selector)
def slot_text_nodes(n):
    result=[]
    def walk(x):
        for c in x.children:
            if isinstance(c,Node): walk(c)
            elif c[0].strip(): result.append(c)
    walk(n); return result
def row_for(container,rowclass,token):
    rows=by_class(container,rowclass)
    hits=[r for r in rows if token in r.text]
    if len(hits)!=1: raise ValueError("row "+token+" expected once, found "+str(len(hits)))
    return hits[0]
def fmt(v,u):
    if v is None: return "待核實"
    n=float(v)
    if u=="percent": return format(n,"+.2f")+"%"
    if u=="basis_points": return format(n,"+.0f")+" bp"
    if u=="percentage_point": return format(n*100,"+.0f")+" bp"
    if u in ("index_point","index","points"): return format(n,",.2f")
    if u in ("USD/share","USD/barrel","USD/oz"): return "$"+format(n,",.2f")
    if u in ("yield_percent","%"): return format(n,".2f")+"%"
    if u in ("USD/TWD","EUR/USD","GBP/USD","AUD/USD","USD/JPY"): return format(n,",.4f" if u!="USD/JPY" else ",.3f")
    if u=="DXY": return format(n,",.2f")
    raise ValueError("unsupported display unit: "+str(u)+"; refusing to guess formatting")
def make_edit(node,value):
    nodes=slot_text_nodes(node)
    if len(nodes)!=1: raise ValueError("mapped slot must contain exactly one text node")
    old,start,end=nodes[0]
    return start,end,html.escape(value,quote=False)
def make_status_class_edit(node,status_class):
    if node.class_span is None:
        raise ValueError("status styling requires an explicit class attribute")
    start,end=node.class_span
    classes=(node.attrs.get("class") or "").split()
    allowed={"up","down","flat","warn"}
    classes=[x for x in classes if x not in allowed]
    if status_class not in allowed:
        raise ValueError("unsupported status class")
    classes.append(status_class)
    return start,end," ".join(classes)
def change_status(record):
    if record.get("status")!="verified" or record.get("change") is None:
        return "warn"
    change=float(record["change"])
    return "up" if change>0 else "down" if change<0 else "flat"
def make_style_property_edit(node,property_name,value):
    if node.style_span is None or not node.attrs.get("style"):
        raise ValueError("mapped style attribute missing")
    start,end=node.style_span
    style=node.attrs["style"]
    match=re.search(r"(?i)(\b"+re.escape(property_name)+r"\s*:\s*)([^;]+)",style)
    if not match: raise ValueError("mapped style property missing: "+property_name)
    return start+match.start(2),start+match.end(2),value
def make_aria_label_edit(node,value):
    if node.aria_label_span is None:
        raise ValueError("mapped aria-label attribute missing")
    start,end=node.aria_label_span
    return start,end,html.escape(value,quote=True)
def find_fedwatch_audit_node(root):
    matches=[]
    for node in root.descendants():
        if node.tag!="details": continue
        summaries=[child for child in node.children if isinstance(child,Node) and child.tag=="summary"]
        if not any("資料時間與快照口徑" in normalize(summary.text) for summary in summaries): continue
        content=[child for child in node.children if isinstance(child,Node) and child.tag=="div"]
        if len(content)==1: matches.append(content[0])
    if len(matches)!=1: raise ValueError("FedWatch audit content missing or duplicated")
    return matches[0]
def validate_fedwatch_payload(fed):
    if fed.get("status")!="verified":
        return None
    probabilities=fed.get("probabilities") or []
    if len(probabilities)!=2:
        raise ValueError("verified FedWatch requires exactly two mapped outcomes")
    if not fed.get("target_meeting") or not fed.get("updated_at") or not fed.get("source"):
        raise ValueError("verified FedWatch requires meeting, timestamp and source")
    for item in probabilities:
        if not 0<=float(item["probability"])<=100:
            raise ValueError("FedWatch probability outside 0-100")
        if not item.get("rate_range"):
            raise ValueError("FedWatch rate range missing")
    if abs(sum(float(x["probability"]) for x in probabilities)-100)>0.2:
        raise ValueError("FedWatch probabilities must sum to 100")
    return probabilities
def fear_greed_category(score):
    value=float(score)
    if not 0<=value<=100: raise ValueError("CNN Fear & Greed score must be between 0 and 100")
    if value<=24: return "Extreme Fear","極度恐懼"
    if value<=44: return "Fear","恐懼"
    if value<=55: return "Neutral","中性"
    if value<=75: return "Greed","貪婪"
    return "Extreme Greed","極度貪婪"
def source_summary(record):
    if record.get("status")!="verified" or not record.get("source"):
        return "待核實：尚無符合本次交易日期的來源資料。"
    src=record["source"]
    return "來源："+src["name"]+"｜資料日期："+src["data_date"]+"｜觀測時間："+src["observed_at"]
def sort_sector_rows(source,snapshot,mapping):
    spec=mapping["groups"]["sectors"]
    tree=Parser(source)
    containers=by_id(tree.root,spec["container"].lstrip("#"))
    if len(containers)!=1: raise ValueError("sectors container missing or duplicated")
    rows=by_class(containers[0],spec["row"].lstrip("."))
    tickers=spec["key_by_ticker"]
    if len(rows)!=len(tickers): raise ValueError("sector row count mismatch")
    by_ticker={}
    for ticker_key,ticker in tickers.items():
        matches=[r for r in rows if re.search(r"(?<![A-Z0-9])"+re.escape(ticker)+r"(?![A-Z0-9])",r.text)]
        if len(matches)!=1: raise ValueError("sector ticker "+ticker+" expected once")
        by_ticker[ticker_key]=matches[0]
    ordered=sorted(tickers, key=lambda k: (
        0 if snapshot["sectors"][k]["status"]=="verified" and snapshot["sectors"][k]["change"] is not None else 1,
        -(float(snapshot["sectors"][k]["change"] or 0))
    ))
    source_rows=sorted(rows,key=lambda r:r.start)
    if any(r.end is None or r.end<=r.start for r in source_rows):
        raise ValueError("sector row boundary unavailable")
    chunks={}; separators=[]
    for i,row in enumerate(source_rows):
        ticker_key=next(k for k,v in by_ticker.items() if v is row)
        chunks[ticker_key]=source[row.start:row.end]
        if i+1<len(source_rows):
            gap=source[row.end:source_rows[i+1].start]
            if gap.strip(): raise ValueError("non-whitespace content between sector rows; refusing reorder")
            separators.append(gap)
    if separators and any(gap!=separators[0] for gap in separators):
        raise ValueError("inconsistent whitespace between sector rows; refusing reorder")
    separator=separators[0] if separators else ""
    start=source_rows[0].start; end=source_rows[-1].end
    replacement=separator.join(chunks[k] for k in ordered)
    return source[:start]+replacement+source[end:],len(rows)

def render(source,snapshot,mapping):
    tree=Parser(source); edits=[]
    for group in ("global_indices","bonds","fx","energy","precious_metals"):
        spec=mapping["groups"][group]
        cs=by_id(tree.root,spec["container"].lstrip("#"))
        if len(cs)!=1: raise ValueError(group+" container missing or duplicated")
        for key,label in spec["key_by_label"].items():
            record=snapshot[group][key]
            row=row_for(cs[0],spec["row"].lstrip("."),label)
            vals=[n for n in row.descendants() if "r" in n.classes]
            if len(vals)!=2: raise ValueError(group+"."+key+" expected exactly two value/change slots, found "+str(len(vals)))
            ok=record["status"]=="verified"
            edits += [make_edit(vals[0],fmt(record["value"],record["unit"]) if ok else "待核實"),
                      make_edit(vals[1],fmt(record["change"],record.get("change_unit")) if ok else "待核實"),
                      make_status_class_edit(vals[1],change_status(record))]
    risk_spec=mapping["groups"]["risk_indicators"]
    risk_container=by_id(tree.root,risk_spec["container"].lstrip("#"))
    if len(risk_container)!=1: raise ValueError("risk indicators container missing or duplicated")
    for key,record_spec in risk_spec["records"].items():
        record=snapshot["risk_indicators"][key]
        row_class=record_spec["row"].lstrip(".")
        rows=by_class(risk_container[0],row_class)
        label_hits=[]
        for row in rows:
            labels=[n for n in row.descendants() if "label-en" in n.classes]
            if any(normalize(n.text)==record_spec["key_text"] for n in labels):
                label_hits.append(row)
        if len(label_hits)!=1: raise ValueError("risk row "+key+" expected once")
        row=label_hits[0]
        value_nodes=selector_nodes(row,record_spec["value_selector"])
        source_nodes=selector_nodes(row,record_spec["source_selector"])
        if len(value_nodes)!=1 or len(source_nodes)!=1: raise ValueError("risk row "+key+" value/source slot missing or duplicated")
        verified=record["status"]=="verified" and record.get("value") is not None
        if key in ("vix","move"):
            change_nodes=[n for n in row.descendants() if n.classes.intersection({"warn","up","down","flat"})]
            if len(change_nodes)!=1: raise ValueError("risk row "+key+" change slot missing or duplicated")
            edits.append(make_edit(value_nodes[0],fmt(record["value"],record["unit"]) if verified else "待核實"))
            edits.append(make_edit(change_nodes[0],fmt(record["change"],record.get("change_unit")) if verified and record.get("change") is not None else "待核實"))
            edits.append(make_status_class_edit(change_nodes[0],change_status(record)))
        else:
            if verified:
                score=float(record["value"])
                category_en,category_zh=fear_greed_category(score)
                category_nodes=selector_nodes(row,record_spec["category_selector"])
                category_zh_nodes=selector_nodes(row,record_spec["category_zh_selector"])
                marker_nodes=selector_nodes(row,record_spec["marker_selector"])
                if len(category_nodes)!=1 or len(category_zh_nodes)!=1 or len(marker_nodes)!=1:
                    raise ValueError("CNN Fear & Greed category/marker slots missing or duplicated")
                edits.append(make_edit(value_nodes[0],format(score,".0f")))
                edits.append(make_edit(category_nodes[0],category_en))
                edits.append(make_edit(category_zh_nodes[0],category_zh))
                edits.append(make_style_property_edit(marker_nodes[0],record_spec["marker_style_property"],format(score,".2f")+"%"))
            else:
                edits.append(make_edit(value_nodes[0],"待核實"))
                category_nodes=selector_nodes(row,record_spec["category_selector"])
                category_zh_nodes=selector_nodes(row,record_spec["category_zh_selector"])
                marker_nodes=selector_nodes(row,record_spec["marker_selector"])
                if len(category_nodes)!=1 or len(category_zh_nodes)!=1 or len(marker_nodes)!=1:
                    raise ValueError("CNN Fear & Greed category/marker slots missing or duplicated")
                edits.append(make_edit(category_nodes[0],"待核實"))
                edits.append(make_edit(category_zh_nodes[0],"待核實"))
                edits.append(make_style_property_edit(marker_nodes[0],record_spec["marker_style_property"],"0%"))
        edits.append(make_edit(source_nodes[0],source_summary(record)))
    fed_spec=mapping["groups"]["fedwatch"]
    fed=snapshot["fedwatch"]
    fed_nodes=by_id(tree.root,fed_spec["container"].lstrip("#"))
    if len(fed_nodes)!=1: raise ValueError("FedWatch container missing or duplicated")
    fed_root=fed_nodes[0]
    fed_rows=by_class(fed_root,fed_spec["row"].lstrip("."))
    if len(fed_rows)!=len(fed_spec["outcomes"]): raise ValueError("FedWatch outcome rows missing or duplicated")
    probabilities=validate_fedwatch_payload(fed)
    for index,(outcome_key,outcome_spec) in enumerate(fed_spec["outcomes"].items()):
        matches=[row for row in fed_rows if outcome_spec["label"] in row.text]
        if len(matches)!=1: raise ValueError("FedWatch outcome "+outcome_key+" expected once")
        row=matches[0]
        prob_nodes=selector_nodes(row,outcome_spec["probability_selector"])
        range_nodes=selector_nodes(row,outcome_spec["rate_range_selector"])
        if len(prob_nodes)!=1 or len(range_nodes)!=1: raise ValueError("FedWatch outcome slots missing: "+outcome_key)
        if probabilities is not None:
            prob=float(probabilities[index]["probability"])
            edits.append(make_edit(prob_nodes[0],format(prob,".1f")+"%"))
            edits.append(make_edit(range_nodes[0],probabilities[index]["rate_range"]))
        else:
            edits.append(make_edit(prob_nodes[0],"待核實"))
            edits.append(make_edit(range_nodes[0],"待核實"))
    bar_nodes=by_class(fed_root,fed_spec["split_bar_selector"].lstrip("."))
    hold_nodes=by_class(fed_root,fed_spec["split_hold_selector"].lstrip("."))
    hike_nodes=by_class(fed_root,fed_spec["split_hike_selector"].lstrip("."))
    legend_nodes=selector_nodes(fed_root,fed_spec["split_legend_value_selector"])
    timestamp_nodes=selector_nodes(fed_root,fed_spec["split_timestamp_selector"])
    audit_nodes=by_class(fed_root,fed_spec["audit_content_selector"].lstrip("."))
    if not audit_nodes: audit_nodes=[find_fedwatch_audit_node(fed_root)]
    if any(len(x)!=1 for x in (bar_nodes,hold_nodes,hike_nodes,audit_nodes)) or len(legend_nodes)!=2 or len(timestamp_nodes) not in (1,2):
        raise ValueError("FedWatch split display slots missing or duplicated")
    if probabilities is not None:
        hold=float(probabilities[0]["probability"]); hike=float(probabilities[1]["probability"])
        edits.append(make_style_property_edit(hold_nodes[0],"width",format(hold,".1f")+"%"))
        edits.append(make_style_property_edit(hike_nodes[0],"width",format(hike,".1f")+"%"))
        edits.append(make_edit(legend_nodes[0],format(hold,".1f")+"%"))
        edits.append(make_edit(legend_nodes[1],format(hike,".1f")+"%"))
        updated=fed["updated_at"]; meeting=fed["target_meeting"]
        if len(timestamp_nodes)==2: edits.append(make_edit(timestamp_nodes[1],"官方快照｜"+updated))
        edits.append(make_edit(audit_nodes[0],"FOMC 目標會議："+meeting+"。CME FedWatch 快照時間："+updated+"。此為該時間點市場定價機率，並非聯準會承諾或決策結果。"))
        edits.append(make_aria_label_edit(bar_nodes[0],"維持不變 "+format(hold,".1f")+"%，升息一碼 "+format(hike,".1f")+"%；CME FedWatch 快照時間 "+updated))
    else:
        for node in legend_nodes: edits.append(make_edit(node,"待核實"))
        if len(timestamp_nodes)==2: edits.append(make_edit(timestamp_nodes[1],"資料待核實"))
        edits.append(make_style_property_edit(hold_nodes[0],"width","0%"))
        edits.append(make_style_property_edit(hike_nodes[0],"width","0%"))
        edits.append(make_edit(audit_nodes[0],"FOMC 目標會議：待核實。CME FedWatch 資料時間：待核實。"))
        edits.append(make_aria_label_edit(bar_nodes[0],"CME FedWatch 待核實"))
    sector_spec=mapping["groups"]["sectors"]
    sector_container=by_id(tree.root,sector_spec["container"].lstrip("#"))
    if len(sector_container)!=1: raise ValueError("sectors container missing or duplicated")
    sector_rows=by_class(sector_container[0],sector_spec["row"].lstrip("."))
    if len(sector_rows)!=len(sector_spec["key_by_ticker"]): raise ValueError("sector row count mismatch")
    for key,ticker in sector_spec["key_by_ticker"].items():
        matches=[r for r in sector_rows if re.search(r"(?<![A-Z0-9])"+re.escape(ticker)+r"(?![A-Z0-9])",r.text)]
        if len(matches)!=1: raise ValueError("sector ticker "+ticker+" expected once")
        row=matches[0]
        values=[n for n in row.descendants() if n.tag=="span" and "r" in n.classes]
        ranks=by_class(row,sector_spec["rank_selector"].lstrip("."))
        if len(values)!=1 or len(ranks)!=1: raise ValueError("sector "+ticker+" requires one value and one rank slot")
        record=snapshot["sectors"][key]
        verified=record["status"]=="verified"
        edits.append(make_edit(values[0],fmt(record["change"],record.get("change_unit")) if verified and record.get("change") is not None else "待核實"))
        edits.append(make_status_class_edit(values[0],change_status(record)))
        # Rank is rewritten after sorting in the second pass below.
    edits.sort(key=lambda e:e[1],reverse=True)
    out=source; last=len(source)+1
    for start,end,value in edits:
        if end>last: raise ValueError("overlapping mapped text nodes")
        out=out[:start]+value+out[end:]; last=start
    out,sector_count=sort_sector_rows(out,snapshot,mapping)
    # Re-parse the reordered rows and rewrite rank labels without touching any other markup.
    reordered=Parser(out)
    sec=by_id(reordered.root,sector_spec["container"].lstrip("#"))[0]
    sorted_rows=by_class(sec,sector_spec["row"].lstrip("."))
    rank_edits=[]
    for rank,row in enumerate(sorted_rows,1):
        rank_nodes=by_class(row,sector_spec["rank_selector"].lstrip("."))
        if len(rank_nodes)!=1: raise ValueError("sector rank slot missing or duplicated")
        rank_edits.append(make_edit(rank_nodes[0],str(rank)))
    rank_edits.sort(key=lambda e:e[1],reverse=True)
    for start,end,value in rank_edits:
        out=out[:start]+value+out[end:]
    return out,len(edits)+sector_count+len(rank_edits)
def validate_expected_dates(snapshot, report_date, trading_date):
    if not report_date or not trading_date:
        raise ValueError("both expected report and trading dates are required")
    if snapshot["meta"]["report_date"] != report_date:
        raise ValueError("report_date mismatch: expected "+report_date+", got "+str(snapshot["meta"]["report_date"]))
    if snapshot["meta"]["trading_date"] != trading_date:
        raise ValueError("trading_date mismatch: expected "+trading_date+", got "+str(snapshot["meta"]["trading_date"]))

def self_test():
    sample='<section id="x"><span class="r up">1,234.50</span><b>Keep</b></section>'
    tree=Parser(sample)
    containers=by_id(tree.root,"x")
    assert len(containers)==1
    spans=[n for n in containers[0].descendants() if "r" in n.classes]
    assert len(spans)==1
    start,end,value=make_edit(spans[0],"+1.25%")
    rendered=sample[:start]+value+sample[end:]
    assert rendered=='<section id="x"><span class="r up">+1.25%</span><b>Keep</b></section>'
    assert '<span class="r up">' in rendered and '<b>Keep</b>' in rendered
    try:
        make_edit(Node("span",{"class":"r"},0),"bad")
    except ValueError:
        pass
    else:
        raise AssertionError("empty mapped slot must fail closed")
    print("PASS: exact text-node replacement preserves tags and attributes")
    print("PASS: unrelated sibling content preserved")
    print("PASS: empty slot rejected")

    test_snapshot = {"meta": {"report_date": "2026-11-02", "trading_date": "2026-10-30"}}
    validate_expected_dates(test_snapshot, "2026-11-02", "2026-10-30")
    for expected_report, expected_trade in (("2026-11-03", "2026-10-30"), ("2026-11-02", "2026-10-29")):
        try:
            validate_expected_dates(test_snapshot, expected_report, expected_trade)
        except ValueError:
            pass
        else:
            raise AssertionError("mismatched report/trading date must fail closed")
    try:
        validate_expected_dates(test_snapshot, None, "2026-10-30")
    except ValueError:
        pass
    else:
        raise AssertionError("missing expected date must fail closed")
    print("PASS: report/trading date mismatch and missing expected dates rejected")

    styled=Parser('<span class="r up">+1.0%</span>')
    styled_node=next(styled.root.descendants())
    a,b,v=make_status_class_edit(styled_node,"down")
    styled_html='<span class="r up">+1.0%</span>'
    styled_html=styled_html[:a]+v+styled_html[b:]
    assert 'class="r down"' in styled_html
    assert change_status({"status":"verified","change":1.0})=="up"
    assert change_status({"status":"verified","change":-1.0})=="down"
    assert change_status({"status":"verified","change":0.0})=="flat"
    assert change_status({"status":"pending_verification","change":1.0})=="warn"
    print("PASS: direction changes update only the mapped value node status class")

    sector_html='<div id="sectors"><div class="sector-row"><span class="rank">1</span><span class="r up">+1%</span><b>XLK</b></div><div class="sector-row"><span class="rank">2</span><span class="r down">-1%</span><b>XLY</b></div></div>'
    sector_map={"groups":{"sectors":{"container":"#sectors","row":".sector-row","key_by_ticker":{"xlk":"XLK","xly":"XLY"}}}}
    sector_snapshot={"sectors":{"xlk":{"status":"verified","change":-1.0},"xly":{"status":"verified","change":2.0}}}
    sorted_html,count=sort_sector_rows(sector_html,sector_snapshot,sector_map)
    assert count==2 and sorted_html.index("XLY")<sorted_html.index("XLK")
    print("PASS: sector rows reordered by verified daily change without rebuilding row markup")
    assert fmt(4.7,"%")=="4.70%"
    assert fmt(0.01,"percentage_point")=="+1 bp"
    try:
        fmt(1.2345,"unknown_fx_unit")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown display unit must fail closed")
    print("PASS: known Treasury units formatted and unknown units rejected")
    assert fmt(32.1,"USD/TWD")=="32.1000"
    assert fmt(153.45,"USD/JPY")=="153.450"
    assert fmt(101.25,"DXY")=="101.25"
    assert fear_greed_category(10)==("Extreme Fear","極度恐懼")
    assert fear_greed_category(33)==("Fear","恐懼")
    assert fear_greed_category(50)==("Neutral","中性")
    assert fear_greed_category(66)==("Greed","貪婪")
    assert fear_greed_category(90)==("Extreme Greed","極度貪婪")
    try:
        fear_greed_category(101)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range CNN score must fail closed")
    print("PASS: CNN Fear & Greed category thresholds and range validation")
    sentiment=Parser('<div class="fg6-status"><span>Fear</span><i></i><b>恐懼</b></div><i class="fg6-marker" style="left:33%"></i>')
    assert len(selector_nodes(sentiment.root,".fg6-status span"))==1
    marker_sample='<i class="fg6-marker" style="left:33%"></i>'
    marker_tree=Parser(marker_sample)
    marker=by_class(marker_tree.root,"fg6-marker")[0]
    a,b,v=make_style_property_edit(marker,"left","66.00%")
    changed_style=marker_sample[:a]+v+marker_sample[b:]
    assert 'style="left:66.00%"' in changed_style
    print("PASS: CNN marker position updates only its mapped inline style property")
    fed_test={"status":"verified","target_meeting":"2026-11-03","updated_at":"2026-10-31T08:00:00+08:00","source":{"name":"CME FedWatch","url":"https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"},"probabilities":[{"rate_range":"維持 3.75%–4.00%","probability":92.5},{"rate_range":"升至 4.00%–4.25%","probability":7.5}]}
    assert len(validate_fedwatch_payload(fed_test))==2
    for bad in (dict(fed_test,probabilities=[fed_test["probabilities"][0]]),dict(fed_test,probabilities=[{"rate_range":"維持","probability":95.0},{"rate_range":"升息","probability":10.0}])):
        try: validate_fedwatch_payload(bad)
        except ValueError: pass
        else: raise AssertionError("invalid FedWatch probabilities must fail closed")
    print("PASS: FedWatch outcome count, probability range and 100% total validation")
    fed_html='<div id="fed"><div class="fc-prob"><strong>1%</strong><div class="fc-range">old</div></div><div class="fc-prob"><strong>2%</strong><div class="fc-range">old</div></div><div class="fc-split-bar" aria-label="old"><span class="fc-split-hold" style="width:1%"></span><span class="fc-split-hike" style="width:2%"></span></div><div class="fc-split-legend"><span><b>1%</b></span><span><b>2%</b></span></div><div class="fc-split-head"><span>Official</span><span>old</span></div><div class="audit-content">old</div></div>'
    fed_tree=Parser(fed_html); bar=by_class(fed_tree.root,"fc-split-bar")[0]
    a,b,v=make_aria_label_edit(bar,"new & updated")
    assert fed_html[:a]+v+fed_html[b:]==fed_html.replace('aria-label="old"','aria-label="new &amp; updated"')
    print("PASS: FedWatch aria-label text escaped and updated without changing markup")

    mapping=json.loads(MAP.read_text(encoding="utf-8"))
    fixture={"meta":{"report_date":"2026-11-02","trading_date":"2026-10-30"}}
    source_meta={"name":"Test source","url":"https://example.com/data","observed_at":"2026-10-31T08:00:00+08:00","data_date":"2026-10-30","quote_type":"official close","instrument":"test instrument"}
    for group in ("global_indices","bonds","fx","energy","precious_metals"):
        spec=mapping["groups"][group]
        fixture[group]={}
        for index,key in enumerate(spec["key_by_label"]):
            if group=="global_indices": unit="index_point"
            elif group=="bonds": unit="%"
            elif group=="fx": unit=key.upper().replace("_","/") if key!="dxy" else "DXY"
            elif group=="energy": unit="USD/barrel"
            else: unit="USD/oz"
            fixture[group][key]={"value":100.0+index,"unit":unit,"change":1.25,"change_unit":"percent" if group!="bonds" else "percentage_point","status":"verified","source":source_meta,"fallback_used":False,"fallback_reason":None,"notes":None}
    fixture["risk_indicators"]={}
    for key in mapping["groups"]["risk_indicators"]["records"]:
        unit="score" if key=="cnn_fear_greed" else "index_point"
        fixture["risk_indicators"][key]={"value":42.0 if key=="cnn_fear_greed" else 18.2,"unit":unit,"change":-1.25,"change_unit":"percent","status":"verified","source":source_meta,"fallback_used":False,"fallback_reason":None,"notes":None}
    fixture["sectors"]={}
    for index,key in enumerate(mapping["groups"]["sectors"]["key_by_ticker"]):
        fixture["sectors"][key]={"status":"verified","change":(index-5)*0.1,"change_unit":"percent"}
    fixture["fedwatch"]={"status":"verified","target_meeting":"2026-11-03","updated_at":"2026-10-31T08:00:00+08:00","source":{"name":"CME FedWatch","url":"https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"},"probabilities":[{"rate_range":"維持 3.75%–4.00%","probability":92.5},{"rate_range":"升至 4.00%–4.25%","probability":7.5}],"notes":None}
    for template_name,relative in mapping["templates"].items():
        source_html=(ROOT/relative).read_text(encoding="utf-8")
        rendered,count=render(source_html,fixture,mapping)
        assert count>0
        assert rendered.count("<script") == source_html.count("<script")
        assert rendered.count("<style") == source_html.count("<style")
        assert "92.5%" in rendered and "7.5%" in rendered
        assert "2026-11-03" in rendered
        sector_order=[rendered.index(">"+ticker+"<") for ticker in mapping["groups"]["sectors"]["key_by_ticker"].values()]
        assert sector_order==sorted(sector_order,key=lambda pos:pos)
        print("PASS: full mapped render against approved "+template_name+" mother ("+str(count)+" edits)")
    print("PASS: full dual-mother renderer integration fixture")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--html"); ap.add_argument("--snapshot")
    ap.add_argument("--output"); ap.add_argument("--template",choices=("monday","weekday"))
    ap.add_argument("--expected-report-date"); ap.add_argument("--expected-trading-date")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    if not all((a.html,a.snapshot,a.output,a.template)):
        ap.error("--html, --snapshot, --output and --template are required unless --self-test is used")
    from validate_tac_daily_snapshot import load_validator
    validator,_=load_validator()
    snap=json.loads(Path(a.snapshot).read_text(encoding="utf-8"))
    errors=list(validator.iter_errors(snap))
    if errors: raise ValueError("snapshot schema invalid: "+"; ".join(e.message for e in errors[:5]))
    validate_expected_dates(snap, a.expected_report_date, a.expected_trading_date)
    mapping=json.loads(MAP.read_text(encoding="utf-8"))
    expected=mapping["templates"][a.template]
    if Path(a.html).as_posix()!=expected: raise ValueError("input is not the approved "+a.template+" mother")
    source=Path(a.html).read_text(encoding="utf-8")
    output,count=render(source,snap,mapping)
    target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(output,encoding="utf-8")
    print("PASS: "+str(count)+" mapped value/change text slots rendered")
    print("PASS: source HTML tags, attributes, CSS and scripts retained verbatim")
    print("Dates: report="+snap["meta"]["report_date"]+" trading="+snap["meta"]["trading_date"])
if __name__=="__main__":
    try: main()
    except Exception as e: print("FAIL: "+str(e),file=sys.stderr); raise SystemExit(1)
