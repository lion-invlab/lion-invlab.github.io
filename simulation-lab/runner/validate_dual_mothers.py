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
        # Five-zone contract: three comparison fields live inside the primary
        # grid; impact and source are two following full-width sibling fields.
        primary_grids = [
            node for node in details.find_all("div", recursive=False)
            if "econ-primary-grid" in node.get("class", [])
        ]
        if len(primary_grids) != 1:
            raise SystemExit(f"{key} card {i}: expected exactly one direct .econ-primary-grid")
        primary = primary_grids[0]
        primary_fields = [
            node for node in primary.find_all("div", recursive=False)
            if "econ-field" in node.get("class", [])
        ]
        if len(primary_fields) != 3:
            raise SystemExit(
                f"{key} card {i}: primary grid must contain exactly 3 comparison fields, got {len(primary_fields)}"
            )
        expected_classes = ["econ-prev", "econ-forecast", "econ-actual"]
        expected_labels = ["前值", "市場預估", "實際"]
        for field, required_class, required_label in zip(primary_fields, expected_classes, expected_labels):
            if required_class not in field.get("class", []):
                raise SystemExit(f"{key} card {i}: comparison field class mismatch, expected {required_class}")
            label = field.find("label", recursive=False)
            value = field.find("div", class_="econ-value", recursive=False)
            if not label or label.get_text(strip=True) != required_label or not value:
                raise SystemExit(f"{key} card {i}: {required_label} field label/value structure incomplete")

        wide_fields = [
            node for node in details.find_all("div", recursive=False)
            if "econ-field" in node.get("class", []) and "wide" in node.get("class", [])
        ]
        if len(wide_fields) != 2:
            raise SystemExit(
                f"{key} card {i}: expected exactly 2 direct full-width fields (impact/source), got {len(wide_fields)}"
            )
        if "econ-impact" not in wide_fields[0].get("class", []) or "econ-source" not in wide_fields[1].get("class", []):
            raise SystemExit(f"{key} card {i}: full-width impact/source order or classes mismatch")
        impact_label = wide_fields[0].find("label", recursive=False)
        source_label = wide_fields[1].find("label", recursive=False)
        impact_value = wide_fields[0].find("div", class_="econ-value", recursive=False)
        source_value = wide_fields[1].find("div", class_="econ-value", recursive=False)
        if not impact_label or impact_label.get_text(strip=True) != "市場影響" or not impact_value:
            raise SystemExit(f"{key} card {i}: market impact field incomplete")
        if not source_label or source_label.get_text(strip=True) != "資料來源" or not source_value:
            raise SystemExit(f"{key} card {i}: source field incomplete")
        source_links = source_value.select("a[href^='https://']")
        if not source_links:
            raise SystemExit(f"{key} card {i}: source field must contain an HTTPS source link")

        # Validate the card's matching expand control without normalizing the
        # existing distinction between current-week and Monday retrospective cards.
        toggles = card.select("summary > span.econ-toggle, summary > span.econ-event-toggle")
        if len(toggles) != 1:
            raise SystemExit(f"{key} card {i}: expected exactly one native expand control")
        toggle_classes = toggles[0].get("class", [])
        expected_toggle = "econ-event-toggle" if scope == "last-week" else "econ-toggle"
        if expected_toggle not in toggle_classes:
            raise SystemExit(f"{key} card {i}: {scope} card requires {expected_toggle}")

    # Validate the persistent QUICK ACCESS toolbar and interactive charts link.
    toolbar = soup.select("aside#tac-side-tools")
    if len(toolbar) != 1:
        raise SystemExit(f"{key}: expected exactly one TAC toolbar")
    links = toolbar[0].select("a.tac-side-link")
    labels = [link.get_text(" ", strip=True) for link in links]
    expected = ["美股個股波動率", "Q4 精選基金", "專題報導", "互動式圖表", "歷史早報"]
    positions = [labels.index(label) if label in labels else -1 for label in expected]
    if any(p < 0 for p in positions) or positions != sorted(positions):
        raise SystemExit(f"{key}: toolbar link order/content mismatch: {labels}")
    chart_links = [link for link in links if link.get_text(" ", strip=True) == "互動式圖表"]
    if len(chart_links) != 1 or chart_links[0].get("href") != "https://lion-invlab.github.io/interactive-charts/":
        raise SystemExit(f"{key}: interactive charts link missing, duplicated, or incorrect")

    # Baselines are byte-for-byte copies of the approved main mothers; no simulation-only CSS is required.
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
