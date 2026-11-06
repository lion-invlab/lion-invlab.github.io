#!/usr/bin/env python3
"""Validate the simulation-only Monday and weekday mother templates."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "simulation-lab/baseline"
MANIFEST = json.loads((BASE / "mother-template-manifest.json").read_text(encoding="utf-8"))

def blob_sha(text: str) -> str:
    raw = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def validate(key: str) -> dict:
    record = MANIFEST["templates"][key]
    path = ROOT / record["path"]
    raw = path.read_text(encoding="utf-8")
    actual = blob_sha(raw)
    if actual != record["blob_sha"]:
        raise SystemExit(f"{key}: manifest SHA mismatch actual={actual} expected={record['blob_sha']}")
    soup = BeautifulSoup(raw, "html.parser")
    cards = soup.select("#calendar details.econ-event, #last-week-calendar details.econ-event")
    if not cards:
        raise SystemExit(f"{key}: no economic event cards")
    for i, card in enumerate(cards, 1):
        direct_divs = [node for node in card.find_all("div", recursive=False)]
        details = next((node for node in direct_divs if "econ-details" in node.get("class", [])), None)
        detail_divs = [node for node in details.find_all("div", recursive=False)] if details else []
        grid = next((node for node in detail_divs if "econ-primary-grid" in node.get("class", [])), None)
        if not grid:
            raise SystemExit(f"{key} card {i}: primary comparison grid missing")
        for cls in ("econ-prev", "econ-forecast", "econ-actual"):
            if sum(cls in node.get("class", []) for node in grid.find_all("div", recursive=False)) != 1:
                raise SystemExit(f"{key} card {i}: expected exactly one {cls}")
        for cls in ("econ-impact", "econ-source"):
            if sum(cls in node.get("class", []) for node in detail_divs) != 1:
                raise SystemExit(f"{key} card {i}: expected exactly one full-width {cls}")
        direct = [x.get("class", []) for x in detail_divs]
        expected = [["econ-primary-grid"], ["econ-field", "econ-impact"], ["econ-field", "econ-source"]]
        if direct != expected:
            raise SystemExit(f"{key} card {i}: five-zone field order mismatch: {direct}")
    css = soup.select_one("#simulation-economic-five-zone-layout")
    if not css:
        raise SystemExit(f"{key}: simulation five-zone CSS missing")
    ids = [x.get("id") for x in soup.select("[id]")]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{key}: duplicate IDs detected")
    return {"template": key, "path": record["path"], "sha": actual, "economic_cards": len(cards), "status": "PASS"}

if __name__ == "__main__":
    results = [validate("monday"), validate("weekdays")]
    print(json.dumps({"dual_mother_validation": results}, ensure_ascii=False, indent=2))
