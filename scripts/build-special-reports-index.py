#!/usr/bin/env python3
"""Generate the TAC special-reports index from published research HTML metadata."""
from html.parser import HTMLParser
from pathlib import Path
from html import escape
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "special-reports.html"
RESEARCH = ROOT / "research"
START = "<!-- TAC_AUTO_ARTICLES_START -->"
END = "<!-- TAC_AUTO_ARTICLES_END -->"

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.title = ""
        self.in_title = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "meta" and attrs.get("name", "").startswith("tac:"):
            self.meta[attrs["name"][4:]] = attrs.get("content", "").strip()
        if tag.lower() == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.title += data

def load_articles():
    items = []
    for path in sorted(RESEARCH.rglob("*.html")):
        parser = MetaParser()
        parser.feed(path.read_text(encoding="utf-8"))
        meta = parser.meta
        if meta.get("publish", "").lower() not in {"true", "yes", "1"}:
            continue
        title = meta.get("title") or parser.title.strip()
        date = meta.get("date", "")
        category = meta.get("category", "其他")
        summary = meta.get("summary", "")
        tags = [tag.strip() for tag in meta.get("tags", "").split("|") if tag.strip()]
        if not title or not date or not summary:
            raise SystemExit(f"Published article missing title/date/summary metadata: {path}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise SystemExit(f"Invalid tac:date in {path}: {date}")
        href = "/" + path.relative_to(ROOT).as_posix()
        search = " ".join([title, category, summary, *tags])
        items.append((date, title, category, summary, tags, href, search))
    return sorted(items, key=lambda item: (item[0], item[1]), reverse=True)

def render(item):
    date, title, category, summary, tags, href, search = item
    tag_html = "".join(f'<span class="tag">{escape(tag)}</span>' for tag in tags)
    return f'''<article class="featured article" data-category="{escape(category, quote=True)}" data-search="{escape(search, quote=True)}">
 <div class="feature-art"><span class="art-label">TAC SPECIAL REPORT</span><span class="art-line"></span><span class="art-mark">MARKET<br>INSIGHT</span></div>
 <div class="feature-copy"><div class="feature-kicker">{escape(category)}　/　TAC 深度專題</div><h2>{escape(title)}</h2><p>{escape(summary)}</p>
 <div class="tags">{tag_html}</div><div class="feature-bottom"><span class="date-meta">發布日期　{date.replace("-", ".")}</span>
 <a class="read-link" href="{escape(href, quote=True)}" target="_blank" rel="noopener">閱讀完整專題 <span>↗</span></a></div></div></article>'''

def main():
    html = INDEX.read_text(encoding="utf-8")
    if html.count(START) != 1 or html.count(END) != 1:
        raise SystemExit("Index generation markers missing or duplicated.")
    articles = load_articles()
    cards = "\n".join(render(item) for item in articles)
    # Replace the complete marker region, tolerating indentation/whitespace
    # around either marker. The previous exact-string replacement silently
    # missed the indented markers in special-reports.html.
    marker_pattern = re.compile(re.escape(START) + r"[\\s\\S]*?" + re.escape(END))
    html, replacements = marker_pattern.subn(
        lambda _: START + "\\n" + cards + "\\n " + END, html, count=1
    )
    if replacements != 1:
        raise SystemExit(f"Expected to replace one article region; replaced {replacements}.")
    generated_region = html.split(START, 1)[1].split(END, 1)[0]
    generated_count = len(re.findall(r'<article class="featured article"', generated_region))
    if generated_count != len(articles):
        raise SystemExit(f"Generated card count mismatch: expected {len(articles)}, found {generated_count}.")
    if '<b id="archive-total">' not in html:
        raise SystemExit("Archive total target missing.")
    html = re.sub(r'<b id="archive-total">\d+</b>',
                  f'<b id="archive-total">{len(articles):02d}</b>', html)
    INDEX.write_text(html, encoding="utf-8")
    print(f"Generated {len(articles)} published TAC research article(s).")

if __name__ == "__main__":
    main()
