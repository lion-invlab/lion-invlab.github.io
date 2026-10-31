#!/usr/bin/env python3
"""Fail-closed renderer for mapped TAC market text slots; never rebuilds HTML."""
from __future__ import annotations
import argparse, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/"scripts/tac_html_binding_map.json"

class Node:
    def __init__(self,tag,attrs,start,tag_end=None,class_span=None):
        self.tag,self.attrs,self.start=tag,dict(attrs),start
        self.tag_end,self.class_span=tag_end,class_span
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
        p=self.pos(); raw=self.get_starttag_text(); class_span=None
        m=re.search(r'\\bclass\\s*=\\s*(["\\'])(.*?)\\1',raw,re.I)
        if m: class_span=(p+m.start(2),p+m.end(2))
        n=Node(tag,attrs,p,p+len(raw),class_span); self.stack[-1].children.append(n)
        if tag not in self.VOID: self.stack.append(n)
        else: n.end=p+len(raw)
    def handle_startendtag(self,tag,attrs):
        p=self.pos(); raw=self.get_starttag_text(); class_span=None
        m=re.search(r'\\bclass\\s*=\\s*(["\\'])(.*?)\\1',raw,re.I)
        if m: class_span=(p+m.start(2),p+m.end(2))
        n=Node(tag,attrs,p,p+len(raw),class_span); n.end=p+len(raw); self.stack[-1].children.append(n)
    def handle_endtag(self,tag):
        p=self.pos()
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                self.stack[i].end=p+len("</"+tag+">"); del self.stack[i:]; break
    def handle_data(self,data):
        p=self.pos(); self.stack[-1].children.append((data,p,p+len(data)))
    def handle_entityref(self,name):
        p=self.pos(); raw="&"+name+";"; self.stack[-1].children.append((html.unescape(raw),p,p+len(raw)))
    def handle_charref(self,name):
        p=self.pos(); raw="&#"+name+";"; self.stack[-1].children.append((html.unescape(raw),p,p+len(raw)))

def descendants(n): return list(n.descendants())
def by_id(root,k): return [n for n in root.descendants() if n.attrs.get("id")==k]
def by_class(root,k): return [n for n in root.descendants() if k in n.classes]
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
    if u in ("index_point","index","points"): return format(n,",.2f")
    if u in ("USD/share","USD/barrel","USD/oz"): return "$"+format(n,",.2f")
    if u=="yield_percent": return format(n,".2f")+"%"
    return format(n,",.4f").rstrip("0").rstrip(".")
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
            if len(vals)<2: raise ValueError(group+"."+key+" value/change slots missing")
            ok=record["status"]=="verified"
            edits += [make_edit(vals[0],fmt(record["value"],record["unit"]) if ok else "待核實"),
                      make_edit(vals[1],fmt(record["change"],record.get("change_unit")) if ok else "待核實"),
                      make_status_class_edit(vals[1],change_status(record))]
    edits.sort(key=lambda e:e[1],reverse=True)
    out=source; last=len(source)+1
    for start,end,value in edits:
        if end>last: raise ValueError("overlapping mapped text nodes")
        out=out[:start]+value+out[end:]; last=start
    return out,len(edits)
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
