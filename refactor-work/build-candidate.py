#!/usr/bin/env python3
"""Build a self-contained TAC HTML candidate from the frozen source and CSS work files.

Usage:
  python build-candidate.py [output.html]

The script intentionally preserves all source scripts and content. It removes the
source's embedded style tags and inserts one consolidated style block made from
legacy-cascade.css followed by design-system.css. Do not use this as a production
release until browser regression tests pass.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source-baseline-2026-10-26.html"
LEGACY = ROOT / "legacy-cascade.css"
DESIGN = ROOT / "design-system.css"
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "candidate-build.html"

html = SOURCE.read_text(encoding="utf-8")
legacy_css = LEGACY.read_text(encoding="utf-8")
design_css = DESIGN.read_text(encoding="utf-8")

# Apply the first shared panel-shell migration to the frozen DOM.
def add_class_to_id(element_id, class_names):
    global html
    pattern = re.compile(r'<(section|article)\b[^>]*\bid="' + re.escape(element_id) + r'"[^>]*>', re.I)
    match = pattern.search(html)
    if not match:
        raise SystemExit(f"Refusing build: panel element not found: {element_id}")
    tag = match.group(0)
    class_match = re.search(r'\bclass="([^"]*)"', tag, re.I)
    if class_match:
        names = class_match.group(1).split()
        for name in class_names.split():
            if name not in names:
                names.append(name)
        updated_tag = tag[:class_match.start(1)] + " ".join(names) + tag[class_match.end(1):]
    else:
        updated_tag = tag[:-1] + f' class="{class_names}">'
    html = html[:match.start()] + updated_tag + html[match.end():]

def add_class_to_calendar_article(section_id, class_names):
    global html
    section_pattern = re.compile(r'<section\b[^>]*\bid="' + re.escape(section_id) + r'"[^>]*>[\s\S]*?</section>', re.I)
    match = section_pattern.search(html)
    if not match:
        raise SystemExit(f"Refusing build: calendar section not found: {section_id}")
    fragment = match.group(0)
    article_pattern = re.compile(r'<article\b[^>]*\bclass="([^"]*\bcalendar-card\b[^"]*)"[^>]*>', re.I)
    article = article_pattern.search(fragment)
    if not article:
        raise SystemExit(f"Refusing build: calendar article not found in: {section_id}")
    names = article.group(1).split()
    for name in class_names.split():
        if name not in names:
            names.append(name)
    updated_tag = article.group(0)[:article.start(1)-article.start()] + " ".join(names) + article.group(0)[article.end(1)-article.start():]
    fragment = fragment[:article.start()] + updated_tag + fragment[article.end():]
    html = html[:match.start()] + fragment + html[match.end():]

# BLUF and sentiment retain their unique visual identities.
bluf_pattern = re.compile(r'<article\b[^>]*\bclass="([^"]*\bbluf\b[^"]*)"[^>]*>', re.I)
bluf_match = bluf_pattern.search(html)
if not bluf_match:
    raise SystemExit("Refusing build: BLUF article not found.")
bluf_names = bluf_match.group(1).split()
for name in ("tac-ds-panel", "tac-ds-panel--bluf"):
    if name not in bluf_names:
        bluf_names.append(name)
bluf_tag = bluf_match.group(0)
bluf_tag_new = bluf_tag[:bluf_match.start(1)-bluf_match.start()] + " ".join(bluf_names) + bluf_tag[bluf_match.end(1)-bluf_match.start():]
html = html[:bluf_match.start()] + bluf_tag_new + html[bluf_match.end():]

add_class_to_id("sentiment", "tac-ds-panel--sentiment")
for element_id in ("news-scan", "global-markets", "industry-bonds-fx-commodities"):
    add_class_to_id(element_id, "tac-ds-panel tac-ds-panel--tabbed")
for section_id in ("last-week-calendar", "last-week-earnings", "calendar", "earnings"):
    add_class_to_calendar_article(section_id, "tac-ds-panel tac-ds-panel--calendar")
add_class_to_id("sp500-earnings-health", "tac-ds-panel tac-ds-panel--earnings-health")
add_class_to_id("fed", "tac-ds-panel tac-ds-panel--fed")
add_class_to_id("view", "tac-ds-panel tac-ds-panel--focus")

source_scripts = re.findall(r"<script\b[^>]*>[\s\S]*?</script>", html, flags=re.I)
source_style_tags = re.findall(r"<style\b[^>]*>[\s\S]*?</style>", html, flags=re.I)
if not source_style_tags:
    raise SystemExit("Refusing build: no source style blocks found.")
if not re.search(r"</head\s*>", html, flags=re.I):
    raise SystemExit("Refusing build: </head> not found.")

# Preserve the source DOM and script order; only relocate CSS into one style block.
html = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", "", html, flags=re.I)
combined_css = (
    "/* Built from legacy-cascade.css in original order, then design-system.css. */\n"
    + legacy_css + "\n\n/* --- TAC Design System --- */\n" + design_css
)
style_block = '<style data-tac-consolidated="build">\n' + combined_css + "\n</style>\n"
html = re.sub(r"</head\s*>", lambda m: style_block + m.group(0), html, count=1, flags=re.I)

built_scripts = re.findall(r"<script\b[^>]*>[\s\S]*?</script>", html, flags=re.I)
if source_scripts != built_scripts:
    raise SystemExit("Refusing build: script blocks or their order changed.")
if re.search(r"<style\b", html[html.lower().find("<body"):], flags=re.I):
    raise SystemExit("Refusing build: a style block remains in the body.")
if len(re.findall(r"<style\b", html, flags=re.I)) != 1:
    raise SystemExit("Refusing build: expected exactly one consolidated style block.")
ids = re.findall(r'\bid=["\']([^"\']+)["\']', html, flags=re.I)
if len(ids) != len(set(ids)):
    raise SystemExit("Refusing build: duplicate IDs found.")

OUTPUT.write_text(html, encoding="utf-8")
print(f"Built: {OUTPUT}")
print(f"HTML bytes: {OUTPUT.stat().st_size}")
print(f"Source script blocks preserved: {len(source_scripts)}")
print("Note: this validates structure only, not browser visual parity.")
