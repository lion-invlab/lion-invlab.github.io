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
    add_class_to_id(section_id, "tac-ds-panel tac-ds-panel--calendar")
add_class_to_id("sp500-earnings-health", "tac-ds-panel tac-ds-panel--earnings-health")
add_class_to_id("fed", "tac-ds-panel tac-ds-panel--fed")
add_class_to_id("view", "tac-ds-panel tac-ds-panel--focus")

# Keep prior-week disclosures on proven legacy geometry for this pass.
# Shared disclosure minimum-height and padding changed wrapping at mobile widths;
# leave these two legacy components unmigrated until parity can be proven.

# Apply the shared radio-tab component without changing radio IDs, labels, names, or panel IDs.
tab_nav_variants = [
    "tac-ds-tabs--scroll",
    "tac-ds-tabs--scroll",
    "tac-ds-tabs--industry",
]
tab_nav_index = 0
def add_tac_tab_nav(match):
    global tab_nav_index
    variant = tab_nav_variants[tab_nav_index]
    tab_nav_index += 1
    tag = match.group(0)
    class_match = re.search(r'\bclass="([^"]*)"', tag, re.I)
    names = class_match.group(1).split()
    for name in ("tac-ds-tabs", variant):
        if name not in names:
            names.append(name)
    return tag[:class_match.start(1)] + " ".join(names) + tag[class_match.end(1):]

html = re.sub(r'<div\b[^>]*\bclass="tac-tab-nav"[^>]*>', add_tac_tab_nav, html, flags=re.I)
if tab_nav_index != 3:
    raise SystemExit(f"Refusing build: expected 3 primary tab navigations, found {tab_nav_index}.")

tab_wrapper_variants = {
    "week-econ-tab-labels": "tac-ds-tabs--equal-3",
    "week-earnings-tab-labels": "tac-ds-tabs--equal-3",
    "fed-live-tab-labels": "tac-ds-tabs--equal-2",
    "focus-tab-labels": "tac-ds-tabs--equal-3",
}
for original_class, variant in tab_wrapper_variants.items():
    pattern = re.compile(r'(<div\b[^>]*\bclass="[^"]*\b' + re.escape(original_class) + r'\b[^"]*"[^>]*>)', re.I)
    matches = list(pattern.finditer(html))
    if len(matches) != 1:
        raise SystemExit(f"Refusing build: expected one {original_class} wrapper, found {len(matches)}.")
    tag = matches[0].group(1)
    class_match = re.search(r'\bclass="([^"]*)"', tag, re.I)
    names = class_match.group(1).split()
    for name in ("tac-ds-tabs", variant):
        if name not in names:
            names.append(name)
    updated_tag = tag[:class_match.start(1)] + " ".join(names) + tag[class_match.end(1):]
    html = html[:matches[0].start(1)] + updated_tag + html[matches[0].end(1):]

tab_label_for_ids = {
    "tac-news-0", "tac-news-1",
    "tac-region-0", "tac-region-1", "tac-region-2",
    "tac-assets-0", "tac-assets-1", "tac-assets-2", "tac-assets-3", "tac-assets-4",
    "week-econ-today", "week-econ-upcoming", "week-econ-published",
    "week-earnings-today", "week-earnings-upcoming", "week-earnings-published",
    "fed-live-tab-watch", "fed-live-tab-fomc",
    "focus-tab-market", "focus-tab-levels", "focus-tab-core",
}
def add_tac_tab_label(match):
    tag = match.group(0)
    for_match = re.search(r"\bfor=[\"']([^\"']+)[\"']", tag, re.I)
    if not for_match or for_match.group(1) not in tab_label_for_ids:
        return tag
    class_match = re.search(r"\bclass=[\"']([^\"']*)[\"']", tag, re.I)
    if class_match:
        names = class_match.group(1).split()
        if "tac-ds-tabs__tab" not in names:
            names.append("tac-ds-tabs__tab")
        return tag[:class_match.start(1)] + " ".join(names) + tag[class_match.end(1):]
    return tag[:-1] + ' class="tac-ds-tabs__tab">'

html = re.sub(r'<label\b[^>]*>', add_tac_tab_label, html, flags=re.I)
migrated_tab_labels = re.findall(r'<label\b[^>]*class="[^"]*\btac-ds-tabs__tab\b[^"]*"[^>]*>', html, flags=re.I)
if len(migrated_tab_labels) != 21:
    raise SystemExit(f"Refusing build: expected 21 shared tab labels, found {len(migrated_tab_labels)}.")


def add_classes_to_tag(tag, class_names):
    class_match = re.search(r'\bclass="([^"]*)"', tag, re.I)
    if not class_match:
        return tag[:-1] + f' class="{class_names}">'
    names = class_match.group(1).split()
    for name in class_names.split():
        if name not in names:
            names.append(name)
    return tag[:class_match.start(1)] + " ".join(names) + tag[class_match.end(1):]

def add_classes_to_tags(fragment, pattern, class_names):
    return re.sub(pattern, lambda m: add_classes_to_tag(m.group(0), class_names), fragment, flags=re.I)

source_details_pattern = r'<details\b(?=[^>]*\bclass="[^"]*\bsource-details\b[^"]*")[^>]*>'
method_details_pattern = r'<details\b(?=[^>]*\bclass="[^"]*\bcompact-disclosure\b[^"]*")[^>]*>'
empty_state_pattern = r'<div\b(?=[^>]*\bclass="[^"]*\bcalendar-status-empty\b[^"]*")[^>]*>'

# Standardize source/method disclosures without changing their content or open state.
html = add_classes_to_tags(html, source_details_pattern, "tac-ds-disclosure tac-ds-disclosure--source")
html = add_classes_to_tags(html, method_details_pattern, "tac-ds-disclosure tac-ds-disclosure--method")
html = add_classes_to_tags(html, empty_state_pattern, "tac-ds-empty")

# News cards share a visual shell while their headlines, body text and source links remain untouched.
news_item_pattern = r'<div\b(?=[^>]*\bclass="[^"]*\bnewsitem\b[^"]*")[^>]*>'
html = add_classes_to_tags(html, news_item_pattern, "tac-ds-card tac-ds-card--news")
news_card_count = len(re.findall(r'<div\b[^>]*class="[^"]*\btac-ds-card--news\b[^"]*"', html, flags=re.I))
if news_card_count != 15:
    raise SystemExit(f"Refusing build: expected 15 shared news cards, found {news_card_count}.")

event_pattern = r'<details\b(?=[^>]*\bclass="[^"]*\becon-event\b[^"]*")[^>]*>'
html = add_classes_to_tags(html, event_pattern, "tac-ds-event")
event_card_count = len(re.findall(r'<details\b[^>]*class="[^"]*\btac-ds-event\b[^"]*"', html, flags=re.I))
if event_card_count != 12:
    raise SystemExit(f"Refusing build: expected 12 shared economic event cards, found {event_card_count}.")

earnings_card_pattern = r'<details\b(?=[^>]*\bclass="[^"]*\bearnings-accordion\b[^"]*")[^>]*>'
html = add_classes_to_tags(html, earnings_card_pattern, "tac-ds-earnings-card")
earnings_card_count = len(re.findall(r'<details\b[^>]*class="[^"]*\btac-ds-earnings-card\b[^"]*"', html, flags=re.I))
if earnings_card_count != 22:
    raise SystemExit(f"Refusing build: expected 22 shared earnings accordion cards, found {earnings_card_count}.")

sector_row_pattern = r'<div\b(?=[^>]*\bclass="[^"]*\bsector-row\b[^"]*")[^>]*>'
html = add_classes_to_tags(html, sector_row_pattern, "tac-ds-data-row tac-ds-data-row--sector")
sector_row_count = len(re.findall(r'<div\b[^>]*class="[^"]*\btac-ds-data-row--sector\b[^"]*"', html, flags=re.I))
if sector_row_count != 11:
    raise SystemExit(f"Refusing build: expected 11 shared sector rows, found {sector_row_count}.")

# Standardize the 14 actual-result cards inside the prior-week earnings disclosure.
actual_earnings_pattern = r'<div\b(?=[^>]*\bclass="[^"]*\bearnings-actual-card(?:\s|")[^"]*")[^>]*>'
html = add_classes_to_tags(html, actual_earnings_pattern, "tac-ds-earnings-actual-card")
actual_earnings_count = len(re.findall(r'<div\b[^>]*class="[^"]*\btac-ds-earnings-actual-card(?:\s|")[^"]*"', html, flags=re.I))
if actual_earnings_count != 14:
    raise SystemExit(f"Refusing build: expected 14 shared actual earnings result cards, found {actual_earnings_count}.")

# Preserve the dark sentiment cards with a dedicated disclosure variant.
sentiment_id_pos = html.find('id="sentiment"')
if sentiment_id_pos < 0:
    raise SystemExit("Refusing build: sentiment panel not found.")
sentiment_start = html.rfind("<article", 0, sentiment_id_pos)
sentiment_end = html.find("</article>", sentiment_id_pos)
if sentiment_start < 0 or sentiment_end < 0:
    raise SystemExit("Refusing build: sentiment article bounds not found.")
sentiment_fragment = html[sentiment_start:sentiment_end]
sentiment_fragment = add_classes_to_tags(sentiment_fragment, source_details_pattern, "tac-ds-disclosure--dark")
html = html[:sentiment_start] + sentiment_fragment + html[sentiment_end:]

source_disclosure_count = len(re.findall(r'<details\b[^>]*class="[^"]*\btac-ds-disclosure\b[^"]*"', html, flags=re.I))
empty_state_count = len(re.findall(r'<div\b[^>]*class="[^"]*\btac-ds-empty\b[^"]*"', html, flags=re.I))
if source_disclosure_count < 13:
    raise SystemExit(f"Refusing build: expected at least 13 shared source/method disclosures, found {source_disclosure_count}.")
if empty_state_count != 4:
    raise SystemExit(f"Refusing build: expected 4 calendar empty states, found {empty_state_count}.")

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
