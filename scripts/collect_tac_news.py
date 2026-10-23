#!/usr/bin/env python3
"""Collect Taiwan-readable TAC finance headlines, including Cnyes RSS, for review branch."""
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OUT = Path("data/tac_news_snapshot.json")
NOW = datetime.now(timezone.utc)
WINDOW_HOURS = 72
FEEDS = [
    {"name": "鉅亨網｜即時頭條", "url": "https://news.cnyes.com/rss/v1/news/category/headline"},
    {"name": "鉅亨網｜台股相關", "url": "https://news.cnyes.com/rss/v1/news/category/wd_stock"},
]
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; TACNewsCollector/1.0)"})
retry = Retry(total=3, connect=3, read=3, status=3, backoff_factor=1.0,
              status_forcelist=(429, 500, 502, 503, 504),
              allowed_methods=frozenset(["GET"]), raise_on_status=False)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

def clean(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()

def parse_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def collect_feed(feed):
    errors = []
    for attempt in range(1, 4):
        try:
            response = session.get(feed["url"], timeout=(8, 20))
            response.raise_for_status()
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            if not items:
                # Atom-compatible fallback
                ns = {"a": "http://www.w3.org/2005/Atom"}
                items = root.findall(".//a:entry", ns)
            out = []
            for item in items:
                def child_text(names):
                    for name in names:
                        found = item.find(name)
                        if found is not None and found.text:
                            return found.text.strip()
                    return ""
                title = clean(child_text(["title", "{http://www.w3.org/2005/Atom}title"]))
                link = child_text(["link"])
                if not link:
                    link_node = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_node is not None:
                        link = link_node.attrib.get("href", "")
                pub_raw = child_text(["pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"])
                published = parse_date(pub_raw)
                if not title or not link:
                    continue
                age_hours = (NOW - published).total_seconds() / 3600 if published else None
                # Keep undated entries marked for review, but don't present them as fresh by assumption.
                if age_hours is not None and (age_hours < -2 or age_hours > WINDOW_HOURS):
                    continue
                summary = clean(child_text(["description", "summary", "{http://www.w3.org/2005/Atom}summary"]))
                out.append({
                    "title": title, "url": link, "published_utc": published.isoformat() if published else None,
                    "age_hours": round(age_hours, 1) if age_hours is not None else None,
                    "summary": summary[:500], "source": feed["name"], "source_url": feed["url"],
                    "date_status": "dated" if published else "publish_time_unverified"
                })
            if not out:
                raise RuntimeError("feed returned no eligible entries in 72-hour window")
            return out, None
        except Exception as exc:
            errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
            time.sleep(attempt)
    return [], " | ".join(errors)

def main():
    collected, errors = [], []
    for feed in FEEDS:
        entries, error = collect_feed(feed)
        collected.extend(entries)
        if error:
            errors.append({"source": feed["name"], "url": feed["url"], "error": error})
    seen, unique = set(), []
    for item in sorted(collected, key=lambda x: x.get("published_utc") or "", reverse=True):
        key = "".join(ch for ch in item["title"].lower() if ch.isalnum())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    result = {
        "schema_version": 1, "fetched_at_utc": NOW.isoformat(),
        "fetched_at_taipei": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "window_hours": WINDOW_HOURS, "sources_attempted": [f["name"] for f in FEEDS],
        "sources_failed": errors, "article_count": len(unique), "articles": unique,
        "status": "ok" if unique and not errors else ("partial" if unique else "missing"),
        "note": "Candidate news only. Before publishing, apply TAC's balanced global-market, materiality, freshness and duplicate checks."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "status": result["status"], "article_count": len(unique),
                      "sources_failed": errors}, ensure_ascii=False, indent=2))
    if not unique:
        sys.exit(1)

if __name__ == "__main__":
    main()
