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
