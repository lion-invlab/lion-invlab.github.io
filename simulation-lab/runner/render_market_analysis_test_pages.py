#!/usr/bin/env python3
"""Render synthetic, non-production five-layer pages for responsive browser smoke tests."""
from __future__ import annotations
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
import build_review_html as builder
from test_market_analysis_slots import sample_data

OUT = ROOT / "simulation-lab" / "output" / "market-analysis-browser"
OUT.mkdir(parents=True, exist_ok=True)
manifest = __import__("json").loads(
    (ROOT / "simulation-lab" / "baseline" / "mother-template-manifest.json").read_text(encoding="utf-8")
)
for key, filename in (
    ("monday", "monday-mother-template.html"),
    ("weekdays", "weekday-mother-template.html"),
):
    soup = BeautifulSoup(
        (ROOT / "simulation-lab" / "baseline" / filename).read_text(encoding="utf-8"),
        "html.parser",
    )
    receipt = builder.populate_market_analysis_preserving_dom(soup, sample_data(), manifest)
    out = OUT / f"{key}.html"
    out.write_text(str(soup), encoding="utf-8")
    print(f"PASS: rendered isolated {key} five-layer browser fixture: {out} ({len(receipt['layers'])} layers)")
