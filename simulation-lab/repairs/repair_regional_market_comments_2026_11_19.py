#!/usr/bin/env python3
"""DOM-only repair for the 2026-11-19 regional market commentary panels.

Reads the report's own fixture, maps the fixture's semantic comment entries to
the three visible regional tabs, edits only the existing .market-reason nodes,
and writes a separate, auditable QA record.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "preview/2026-11-19-simulation.html"
FIXTURE_PATH = ROOT / "simulation-lab/fixtures/report-data-2026-11-19.json"
QA_PATH = ROOT / "preview/2026-11-19-regional-commentary-repair.qa.json"

def body_without_label(value: str) -> str:
    text = str(value).strip()
    if "｜" in text:
        text = text.split("｜", 1)[1].strip()
    return text

def set_observation(soup: BeautifulSoup, panel_id: str, heading: str, body: str) -> dict:
    panels = soup.select(f"#global-markets #{panel_id}")
    if len(panels) != 1:
        raise ValueError(f"{panel_id}: expected exactly one regional tab panel, found {len(panels)}")
    panel = panels[0]
    notes = panel.select(".market-reason")
    if len(notes) != 1:
        raise ValueError(f"{panel_id}: expected exactly one .market-reason node, found {len(notes)}")
    note = notes[0]
    note.clear()
    title = soup.new_tag("b")
    title.string = heading
    note.append(title)
    note.append(soup.new_tag("br"))
    note.append(NavigableString(body))
    text = note.get_text(" ", strip=True)
    if not text.startswith(heading) or len(text) <= len(heading) + 10:
        raise ValueError(f"{panel_id}: DOM write verification failed")
    indexes = [
        a.get_text(" ", strip=True)
        for a in panel.select("a.global-index-link")
    ]
    return {
        "panel_id": panel_id,
        "heading": heading,
        "commentary": body,
        "index_names": indexes,
        "dom_node_count": len(notes),
        "verified": True,
    }

def main() -> None:
    if not HTML_PATH.is_file() or not FIXTURE_PATH.is_file():
        raise FileNotFoundError("Expected 2026-11-19 preview and matching report fixture")
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if data.get("report_date") != "2026-11-19":
        raise ValueError("Fixture report_date does not match target preview")
    comments = data.get("market_comments", {}).get("global_markets", [])
    if len(comments) < 4:
        raise ValueError("Expected fixture comment indexes 0 (US), 1+2 (Asia/China), 3 (Europe)")
    us = body_without_label(comments[0])
    asia = (
        body_without_label(comments[1]).replace("亞洲市場", "亞洲市場", 1)
        + " "
        + body_without_label(comments[2])
    )
    europe = body_without_label(comments[3])

    html = HTML_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    report_date = soup.select_one('meta[name="report-date"]')
    if report_date is None or report_date.get("content") != "2026-11-19":
        raise ValueError("Preview meta report-date mismatch")
    records = [
        set_observation(soup, "tac-global-panel-0", "📌 美股觀察", us),
        set_observation(soup, "tac-global-panel-1", "📌 亞股觀察", asia),
        set_observation(soup, "tac-global-panel-2", "📌 歐股觀察", europe),
    ]

    # Semantic cross-region leakage checks: only permit the expected market
    # universe in each observation. Asia intentionally includes China.
    checks = [
        ("tac-global-panel-0", ("上證", "深證", "恆生", "FTSE", "DAX", "CAC 40", "STOXX")),
        ("tac-global-panel-1", ("FTSE 100", "DAX", "CAC 40", "STOXX Europe")),
        ("tac-global-panel-2", ("上證", "深證", "恆生", "日經", "KOSPI", "台灣加權", "STI", "ASX 200")),
    ]
    for panel_id, forbidden in checks:
        text = soup.select_one(f"#global-markets #{panel_id} .market-reason").get_text(" ", strip=True)
        hits = [term for term in forbidden if term in text]
        if hits:
            raise ValueError(f"{panel_id}: cross-region references detected: {hits}")

    # Re-read all three nodes from the parsed DOM after the mutations.
    for record in records:
        panel = soup.select_one(f"#global-markets #{record['panel_id']}")
        node = panel.select_one(".market-reason")
        if node is None or node.select_one("b") is None:
            raise ValueError(f"{record['panel_id']}: final DOM read-back failed")
        if node.select_one("b").get_text(" ", strip=True) != record["heading"]:
            raise ValueError(f"{record['panel_id']}: heading read-back mismatch")
        if node.get_text(" ", strip=True) != record["heading"] + " " + record["commentary"]:
            raise ValueError(f"{record['panel_id']}: commentary read-back mismatch")

    output = str(soup)
    HTML_PATH.write_text(output, encoding="utf-8")
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    evidence = {
        "report_date": "2026-11-19",
        "repair_type": "BeautifulSoup DOM node update",
        "source_fixture": str(FIXTURE_PATH.relative_to(ROOT)),
        "source_comment_mapping": {"US": 0, "Asia_including_China": [1, 2], "Europe": 3},
        "panels": records,
        "all_three_regions_passed": True,
        "html_sha256_after_repair": digest,
    }
    QA_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
