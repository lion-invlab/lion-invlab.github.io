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
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()

def validate(key: str) -> dict:
    record = MANIFEST["templates"][key]
    # Simulation manifest paths must resolve to the isolated baseline copies.
    isolated_path = BASE / ("monday-mother-template.html" if key == "monday" else "weekday-mother-template.html")
    raw = isolated_path.read_text(encoding="utf-8")
    actual = blob_sha(raw)
    if actual != record["simulation_blob_sha"]:
        raise SystemExit(
            f"{key}: simulation baseline SHA mismatch actual={actual} "
            f"expected={record['simulation_blob_sha']}"
        )

    soup = BeautifulSoup(raw, "html.parser")
    scopes = [("#calendar", "current"), ("#last-week-calendar", "last-week")]
    cards = []
    for selector, scope in scopes:
        container = soup.select_one(selector)
        if container:
            cards.extend((card, scope) for card in container.select("details.econ-event"))
    if not cards:
        raise SystemExit(f"{key}: no economic event cards")

    for i, (card, scope) in enumerate(cards, 1):
        # The approved DOM contract is: details > .econ-details > .econ-primary-grid
        # followed by full-width impact and source fields. Do not impose an
        # additional direct-child-div assumption on the details node.
        details_nodes = card.select(":scope > .econ-details")
        if len(details_nodes) != 1:
            # BeautifulSoup's :scope support varies; use a direct-child walk.
            details_nodes = [
                child for child in card.children
                if getattr(child, "name", None) == "div"
                and "econ-details" in child.get("class", [])
            ]
        if len(details_nodes) != 1:
            raise SystemExit(f"{key} card {i}: expected one direct .econ-details container")
        details = details_nodes[0]
        direct_divs = [
            node for node in details.find_all("div", recursive=False)
        ]
        if len(direct_divs) != 3:
            raise SystemExit(f"{key} card {i}: expected exactly three direct field zones, got {len(direct_divs)}")
        grid, impact, source = direct_divs
        if "econ-primary-grid" not in grid.get("class", []):
            raise SystemExit(f"{key} card {i}: first zone is not .econ-primary-grid")
        for cls in ("econ-prev", "econ-forecast", "econ-actual"):
            matches = [node for node in grid.find_all("div", recursive=False) if cls in node.get("class", [])]
            if len(matches) != 1:
                raise SystemExit(f"{key} card {i}: expected exactly one {cls}")
        for node, cls in ((impact, "econ-impact"), (source, "econ-source")):
            if "econ-field" not in node.get("class", []) or cls not in node.get("class", []):
                raise SystemExit(f"{key} card {i}: expected full-width {cls} as zone {direct_divs.index(node)+1}")

        # Validate the card's matching expand control without normalizing the
        # existing distinction between current-week and Monday retrospective cards.
        toggles = card.select("summary > span.econ-toggle, summary > span.econ-event-toggle")
        if len(toggles) != 1:
            raise SystemExit(f"{key} card {i}: expected exactly one native expand control")
        toggle_classes = toggles[0].get("class", [])
        expected_toggle = "econ-event-toggle" if scope == "last-week" else "econ-toggle"
        if expected_toggle not in toggle_classes:
            raise SystemExit(f"{key} card {i}: {scope} card requires {expected_toggle}")

    style = soup.select_one("#simulation-economic-five-zone-layout")
    if not style:
        raise SystemExit(f"{key}: simulation five-zone CSS missing")
    ids = [node.get("id") for node in soup.select("[id]")]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"{key}: duplicate IDs detected")

    return {
        "template": key,
        "path": str(isolated_path.relative_to(ROOT)),
        "sha": actual,
        "economic_cards": len(cards),
        "last_week_cards": sum(1 for _, scope in cards if scope == "last-week"),
        "status": "PASS",
    }

if __name__ == "__main__":
    results = [validate("monday"), validate("weekdays")]
    print(json.dumps({"dual_mother_validation": results}, ensure_ascii=False, indent=2))
