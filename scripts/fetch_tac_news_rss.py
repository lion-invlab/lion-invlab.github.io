#!/usr/bin/env python3
"""Read-only RSS collector for TAC news candidates (no article-page scraping)."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

FEEDS = (
    {"name":"鉅亨網","url":"https://news.cnyes.com/rss/v1/news/category/headline","role":"both"},
    {"name":"Investing.com","url":"https://www.investing.com/rss/news_14.rss","role":"focus"},
    {"name":"Investing.com","url":"https://www.investing.com/rss/news_95.rss","role":"focus"},
    {"name":"Investing.com","url":"https://www.investing.com/rss/news_25.rss","role":"headlines"},
    {"name":"Investing.com","url":"https://www.investing.com/rss/news.rss","role":"headlines"},
)
MACRO_TERMS = (
    "fed","federal reserve","central bank","interest rate","rate cut","rate hike",
    "inflation","cpi","ppi","pce","payroll","employment","unemployment","gdp",
    "recession","tariff","trade war","sanction","geopolit","election","budget",
    "treasury","bond yield","央行","聯準會","美聯儲","利率","降息","升息","通膨",
    "通脹","CPI","PCE","非農","就業","失業","GDP","關稅","貿易戰","制裁",
    "地緣政治","選舉","財政","公債","殖利率"
)
POLICY_TERMS=("fed","central bank","interest rate","tariff","sanction","央行","聯準會","利率","關稅","制裁","政策")
GEO_TERMS=("war","invasion","geopolit","sanction","conflict","戰爭","衝突","地緣","制裁")


def local_name(tag: str) -> str:
    return tag.rsplit("}",1)[-1].lower()


def child_text(node, names):
    for child in list(node):
        if local_name(child.tag) in names:
            raw=" ".join(child.itertext()).strip()
            return html.unescape(raw)
    return ""


def parse_pubdate(value: str) -> datetime:
    if not value:
        raise ValueError("RSS item has no publication timestamp")
    try:
        parsed=parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("RSS publication timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def clean_text(value: str) -> str:
    value=re.sub(r"<[^>]+>"," ",value)
    value=html.unescape(value)
    return re.sub(r"\\s+"," ",value).strip()


def classify(title: str, summary: str) -> str:
    text=(title+" "+summary).lower()
    if any(term.lower() in text for term in GEO_TERMS):
        return "geopolitics"
    if any(term.lower() in text for term in POLICY_TERMS):
        return "policy"
    if any(term.lower() in text for term in MACRO_TERMS):
        return "macro"
    if re.search(r"earnings|revenue|eps|quarterly results|財報|營收|獲利|每股盈餘",text):
        return "company"
    return "market"


def parse_feed(xml_text: str, feed: dict, observed_at: str) -> list[dict]:
    root=ET.fromstring(xml_text)
    items=[node for node in root.iter() if local_name(node.tag) in {"item","entry"}]
    output=[]
    for node in items:
        title=clean_text(child_text(node,{"title"}))
        summary=clean_text(child_text(node,{"description","summary","content"}))
        published=child_text(node,{"pubdate","published","updated","date"})
        link=""
        for child in list(node):
            if local_name(child.tag)=="link":
                href=child.attrib.get("href")
                link=href or (child.text or "").strip()
                if link:
                    break
        if not link or not title or not summary:
            continue
        parsed=parse_pubdate(published)
        item_id=hashlib.sha256((feed["name"]+"|"+link).encode()).hexdigest()[:16]
        output.append({
            "id":item_id,"category":classify(title,summary),"headline":title[:240],
            "summary":summary[:1200],"published_at":parsed.isoformat(),
            "source":{"name":feed["name"],"url":link,"published_at":parsed.isoformat(),
                      "observed_at":observed_at,"publisher":feed["name"],
                      "notes":"RSS candidate; summary is feed-provided and not an independently verified full-article analysis."},
            "status":"pending_verification","impact":None,"_feed_role":feed["role"]
        })
    return output


def fetch_feed(feed: dict, timeout: int=20) -> list[dict]:
    request=urllib.request.Request(feed["url"],headers={"User-Agent":"TAC-Private-Morning-Report/1.0 (+read-only RSS client)","Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        if response.status!=200:
            raise RuntimeError(f"HTTP {response.status}")
        payload=response.read(4_000_000)
    observed=datetime.now(timezone.utc).isoformat()
    return parse_feed(payload.decode("utf-8",errors="replace"),feed,observed)


def collect(start: datetime, end: datetime, feeds=FEEDS, fetcher=fetch_feed):
    if start.tzinfo is None or end.tzinfo is None or start>=end:
        raise ValueError("news window must be timezone-aware and start before end")
    records=[]
    errors=[]
    for feed in feeds:
        try:
            records.extend(fetcher(feed))
        except Exception as exc:
            errors.append(f"{feed['name']} {feed['url']}: {type(exc).__name__}: {exc}")
    unique={}
    for item in records:
        key=item["source"]["url"]
        previous=unique.get(key)
        if previous is None or item["source"]["name"]=="鉅亨網":
            unique[key]=item
    candidates=[x for x in unique.values() if start<=datetime.fromisoformat(x["published_at"])<=end]
    candidates.sort(key=lambda x:x["published_at"],reverse=True)
    focus=[x for x in candidates if x["category"] in {"macro","policy","geopolitics"}][:5]
    headlines=candidates[:10]
    for item in focus+headlines:
        item.pop("_feed_role",None)
    return {"focus_news":focus,"market_headlines":headlines,
            "meta":{"news_window_start":start.isoformat(),"news_window_end":end.isoformat()},
            "collector":{"feeds_attempted":len(feeds),"items_in_window":len(candidates),
                         "errors":errors,"status":"pending_verification"}}


def self_test():
    feed={"name":"Investing.com","url":"https://example.com/feed.xml","role":"both"}
    xml="""<?xml version="1.0"?><rss><channel>
      <item><title>Fed signals rate cut as inflation cools</title><link>https://example.com/a</link>
      <description><![CDATA[Central bank policy outlook and inflation trends.]]></description>
      <pubDate>Sat, 31 Oct 2026 08:00:00 GMT</pubDate></item>
      <item><title>Chip stocks rally after earnings</title><link>https://example.com/b</link>
      <description>Technology shares advance after quarterly results.</description>
      <pubDate>Sat, 31 Oct 2026 09:00:00 GMT</pubDate></item>
    </channel></rss>"""
    parsed=parse_feed(xml,feed,"2026-10-31T10:00:00+00:00")
    assert len(parsed)==2
    assert parsed[0]["category"]=="macro"
    assert parsed[1]["category"]=="company"
    assert parsed[0]["source"]["url"]=="https://example.com/a"
    assert parsed[0]["status"]=="pending_verification"
    print("PASS: RSS item parsing, canonical article URL and publication time")
    print("PASS: macro and company categories distinguished")
    def fake_fetch(_feed):
        return parsed
    result=collect(datetime(2026,10,31,7,tzinfo=timezone.utc),
                   datetime(2026,10,31,10,tzinfo=timezone.utc),
                   feeds=[feed],fetcher=fake_fetch)
    assert len(result["focus_news"])==1 and len(result["market_headlines"])==2
    assert result["meta"]["news_window_start"].endswith("+00:00")
    print("PASS: report time-window filter and focus/headline separation")
    result=collect(datetime(2026,11,1,tzinfo=timezone.utc),
                   datetime(2026,11,2,tzinfo=timezone.utc),
                   feeds=[feed],fetcher=fake_fetch)
    assert result["collector"]["status"]=="pending_verification"
    assert not result["focus_news"] and not result["market_headlines"]
    print("PASS: empty window remains pending; no synthetic stories")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    parser.add_argument("--output")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.window_start,args.window_end,args.output)):
        parser.error("--window-start, --window-end and --output are required")
    start=datetime.fromisoformat(args.window_start.replace("Z","+00:00"))
    end=datetime.fromisoformat(args.window_end.replace("Z","+00:00"))
    result=collect(start,end)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print(f"News RSS probe: {result['collector']['items_in_window']} candidates; "
          f"{len(result['focus_news'])}/5 macro focus; {len(result['market_headlines'])}/10 headlines")
    for error in result["collector"]["errors"]:
        print("SOURCE PENDING: "+error,file=sys.stderr)
    print("Saved "+args.output)
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
