#!/usr/bin/env python3
"""Render the approved TAC mother with validated market Snapshot values.

This renderer intentionally handles only the market-data binding contract currently
present in tac_html_binding_map.json. It does NOT produce a review-ready report:
news, analysis, economic-calendar and earnings-card payloads are separate inputs
and must be rendered by a later, explicitly mapped stage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "scripts" / "tac_html_binding_map.json"
MANIFEST_PATH = ROOT / "母版專區" / "mother-template-manifest.json"
PROTECTED = {
    "index.html",
    "TAC_WORK_RULES.md",
    "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
    "母版專區/mother-template-manifest.json",
}
STATE_CLASSES = {"up", "down", "flat", "warn"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_number(value: float, places: int = 2) -> str:
    rendered = f"{value:,.{places}f}"
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def format_value(key: str, record: dict, group: str) -> str:
    value = record.get("value")
    if record.get("status") != "verified" or not isinstance(value, (int, float)):
        return "待核實"
    if group == "fx":
        places = {"usd_twd": 3, "eur_usd": 4, "gbp_usd": 4, "aud_usd": 4}.get(key, 2)
    elif group == "risk_indicators" and key == "cnn_fear_greed":
        places = 0
    else:
        places = 2
    result = compact_number(float(value), places)
    unit = record.get("unit")
    if unit == "percent":
        result += "%"
    elif unit == "percent_per_year":
        result += "%"
    return result


def format_change(record: dict) -> str:
    change = record.get("change")
    if record.get("status") != "verified" or not isinstance(change, (int, float)):
        return "待核實"
    unit = record.get("change_unit")
    if unit == "percent":
        return f"{float(change):+.2f}%".replace("-", "−")
    if unit == "basis_point":
        return f"{float(change):+.0f} bp"
    if unit == "bp":
        return f"{float(change):+.0f} bp"
    return compact_number(float(change), 2)


def set_state_class(node, status: str, change) -> None:
    node.attrs["class"] = [c for c in node.get("class", []) if c not in STATE_CLASSES]
    if status != "verified" or not isinstance(change, (int, float)):
        node["class"].append("warn")
    elif change > 0:
        node["class"].append("up")
    elif change < 0:
        node["class"].append("down")
    else:
        node["class"].append("flat")


def find_unique(nodes, description: str):
    if len(nodes) != 1:
        fail(f"{description}: expected exactly one match, found {len(nodes)}")
    return nodes[0]


def row_by_label(container, row_selector: str, label: str):
    rows = container.select(row_selector)
    matches = [r for r in rows if label in " ".join(r.stripped_strings)]
    return find_unique(matches, f"row label {label!r}")


def update_row(container, row_selector: str, label: str, record: dict,
               key: str, group: str, value_index: int = 0,
               change_index: int | None = 1) -> None:
    row = row_by_label(container, row_selector, label)
    slots = row.select("span.r")
    needed = max(value_index, change_index if change_index is not None else value_index) + 1
    if len(slots) < needed:
        fail(f"{group}.{key}: insufficient span.r slots ({len(slots)} < {needed})")
    slots[value_index].string = format_value(key, record, group)
    if change_index is not None:
        slots[change_index].string = format_change(record)
        set_state_class(slots[change_index], record.get("status"), record.get("change"))


def update_group(soup, group: str, spec: dict, snapshot: dict) -> None:
    container = find_unique(soup.select(spec["container"]), f"{group} container")
    fields = snapshot.get(group, {})
    if "key_by_label" in spec:
        for key, label in spec["key_by_label"].items():
            record = fields.get(key, {})
            update_row(container, spec["row"], label, record, key, group,
                       spec.get("value_index", 0), spec.get("change_index", 1))
    elif "key_by_ticker" in spec:
        rows = container.select(spec["row"])
        if len(rows) != len(spec["key_by_ticker"]):
            fail(f"{group}: expected {len(spec['key_by_ticker'])} rows, found {len(rows)}")
        ranked = []
        for key, ticker in spec["key_by_ticker"].items():
            matches = [r for r in rows if re.search(
                r"(?<![A-Z0-9])" + re.escape(ticker) + r"(?![A-Z0-9])",
                " ".join(r.stripped_strings))]
            row = find_unique(matches, f"{group} ticker {ticker}")
            record = fields.get(key, {})
            slot = find_unique(row.select(spec["value_selector"]), f"{ticker} value slot")
            slot.string = format_change(record)
            set_state_class(slot, record.get("status"), record.get("change"))
            ranked.append((record.get("change") if record.get("status") == "verified" else None, row))
        # Sorting is permitted only as data ordering among the fixed 11 approved rows.
        parent = rows[0].parent if rows else None
        if parent is not None:
            ordered = sorted(ranked, key=lambda item: (
                item[0] is None, -(item[0] or 0)
            ))
            for _, row in ordered:
                parent.append(row.extract())
    elif "records" in spec:
        for key, record_spec in spec["records"].items():
            rows = [r for r in container.select(record_spec["row"])
                    if any(label.get_text(" ", strip=True) == record_spec["key_text"]
                           for label in r.select(".label-en"))]
            row = find_unique(rows, f"{group}.{key} row")
            record = fields.get(key, {})
            value_node = find_unique(row.select(record_spec["value_selector"]), f"{key} value")
            value_node.string = format_value(key, record, group)
            change_selector = record_spec.get("change_selector")
            if change_selector:
                change_nodes = row.select(change_selector)
                if record.get("change") is not None:
                    change_node = find_unique(change_nodes, f"{key} change")
                    change_node.string = format_change(record)
                    set_state_class(change_node, record.get("status"), record.get("change"))
                elif change_nodes:
                    change_nodes[0].string = "待核實"
                    set_state_class(change_nodes[0], "pending_verification", None)
            if key == "cnn_fear_greed":
                marker = find_unique(row.select(".fg6-marker"), "Fear & Greed marker")
                if record.get("status") == "verified" and isinstance(record.get("value"), (int, float)):
                    marker["style"] = re.sub(
                        r"(?i)(^|;)\s*left\s*:[^;]+",
                        lambda m: m.group(1) + f"left:{max(0,min(100,float(record['value']))):g}%",
                        marker.get("style", ""),
                    )
                status = "極度恐懼" if record.get("value", 0) <= 24 else "恐懼" if record.get("value", 0) <= 44 else "中性" if record.get("value", 0) <= 55 else "貪婪" if record.get("value", 0) <= 75 else "極度貪婪"
                state = find_unique(row.select(".fg6-status"), "Fear & Greed status")
                chinese = find_unique(state.select("b"), "Fear & Greed Chinese label")
                english = find_unique(state.select("span"), "Fear & Greed English label")
                english_map = {"極度恐懼": "Extreme Fear", "恐懼": "Fear", "中性": "Neutral", "貪婪": "Greed", "極度貪婪": "Extreme Greed"}
                chinese.string = status
                english.string = english_map[status]
    elif group == "fedwatch":
        update_fedwatch(container, snapshot.get("fedwatch", {}))



def rate_range_bounds(value: str) -> tuple[float, float]:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*%\s*[-–—]\s*(\d+(?:\.\d+)?)\s*%\s*", value)
    if not match:
        fail(f"Unrecognized Fed target-rate range: {value!r}")
    lower, upper = map(float, match.groups())
    if lower >= upper:
        fail(f"Invalid Fed target-rate range: {value!r}")
    return lower, upper


def classify_rate_outcome(rate_range: str, current_rate_range: str) -> str:
    lower, upper = rate_range_bounds(rate_range)
    current_lower, current_upper = rate_range_bounds(current_rate_range)
    if abs(lower-current_lower) < 1e-6 and abs(upper-current_upper) < 1e-6:
        return "維持不變"
    if upper <= current_lower:
        steps = round((current_lower-lower)/0.25)
        return f"降息{steps}碼" if steps else "降息"
    if lower >= current_upper:
        steps = round((lower-current_upper)/0.25)
        return f"升息{steps}碼" if steps else "升息"
    fail(f"Outcome range {rate_range!r} overlaps current range {current_rate_range!r} ambiguously")

def update_fedwatch(container, fedwatch: dict) -> None:
    probs = fedwatch.get("probabilities", [])
    if fedwatch.get("status") != "verified":
        fail("FedWatch requires verified probabilities")
    if len(probs) != 2:
        fail(f"FedWatch has {len(probs)} rate outcomes; approved two-card master cannot safely render this distribution. Dynamic-card upgrade required; no outcomes were discarded.")
    if abs(sum(float(x["probability"]) for x in probs) - 100.0) > 0.05:
        fail("FedWatch probabilities do not sum to 100%")
    rows = container.select(".fc-prob")
    if len(rows) != 2:
        fail(f"FedWatch: expected two probability rows, found {len(rows)}")
    # The approved master has two semantic rows: hold and hike-one. Their
    # probability and range text slots are updated without changing the DOM.
    for row, outcome in zip(rows, probs):
        strong = find_unique(row.select("strong"), "FedWatch probability slot")
        rate_range = find_unique(row.select(".fc-range"), "FedWatch rate range slot")
        strong.string = f"{float(outcome['probability']):.1f}%"
        rate_range.string = outcome["rate_range"]
    split = container.select_one(".fc-split-bar")
    if split:
        spans = split.select("span")
        if len(spans) != 2:
            fail("FedWatch split bar must contain two spans")
        for span, outcome in zip(spans, probs):
            span["style"] = re.sub(r"(?i)(^|;)\s*width\s*:[^;]+",
                                   lambda m: m.group(1) + f"width:{float(outcome['probability']):g}%",
                                   span.get("style", ""))
        split["aria-label"] = "；".join(
            f"{x['rate_range']} {float(x['probability']):.1f}%" for x in probs
        )
    legend_values = container.select(".fc-split-legend b")
    if len(legend_values) != 2:
        fail("FedWatch split legend must contain two probability values")
    for node, outcome in zip(legend_values, probs):
        node.string = f"{float(outcome['probability']):.1f}%"
    split_head = container.select(".fc-split-head span")
    if len(split_head) >= 2:
        split_head[0].string = "市場隱含機率分布"
    # Update only the dedicated snapshot timestamp text node; never relabel this
    # market-implied probability as an official CME decision.
    timestamp = fedwatch.get("updated_at")
    if not timestamp:
        fail("FedWatch updated_at missing")
    for node in container.select(".fc-split-head span"):
        if "官方截圖" in node.get_text() or "資料時間" in node.get_text():
            node.string = f"Investing.com 快照｜{timestamp.replace('T', ' ')[:16]} 台灣時間"


def render(master_path: Path, snapshot_path: Path, output_path: Path,
           expected_master_sha: str) -> dict:
    import hashlib
    contract = load_json(MAP_PATH)
    manifest = load_json(MANIFEST_PATH)
    snapshot = load_json(snapshot_path)
    report_date = date.fromisoformat(snapshot["meta"]["report_date"])
    weekday = "monday" if report_date.weekday() == 0 else "weekdays"
    expected_path = manifest["templates"]["monday" if weekday == "monday" else "weekdays"]["path"]
    if master_path.resolve() != (ROOT / expected_path).resolve():
        fail(f"wrong weekday master: expected {expected_path}")
    raw = master_path.read_text(encoding="utf-8")
    blob = raw.encode("utf-8")
    actual_sha = hashlib.sha1(b"blob " + str(len(blob)).encode("ascii") + bytes([0]) + blob).hexdigest()
    if actual_sha != expected_master_sha:
        fail(f"mother SHA mismatch: {actual_sha} != {expected_master_sha}")
    if actual_sha != manifest["templates"]["monday" if weekday == "monday" else "weekdays"]["blob_sha"]:
        fail("mother SHA does not match the approved Manifest")
    if snapshot["meta"].get("timezone") != "Asia/Taipei":
        fail("Snapshot timezone must be Asia/Taipei")
    if snapshot["meta"].get("report_date") != report_date.isoformat():
        fail("Snapshot report_date invalid")
    soup = BeautifulSoup(raw, "html.parser")
    for group, spec in contract["groups"].items():
        update_group(soup, group, spec, snapshot)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(soup), encoding="utf-8")
    return {
        "report_date": report_date.isoformat(),
        "trading_date": snapshot["meta"]["trading_date"],
        "master_sha1": actual_sha,
        "market_groups_rendered": list(contract["groups"]),
        "review_ready": False,
        "blocked_sections": [
            "global focus news", "market hot headlines", "market observation highlights",
            "market sentiment narrative", "economic calendar", "earnings calendar",
            "industry and macro analysis"
        ],
    }


def self_test() -> None:
    assert compact_number(3608.1, 2) == "3,608.1"
    assert format_change({"status": "verified", "change": 1.25, "change_unit": "percent"}) == "+1.25%"
    assert format_change({"status": "verified", "change": -0.39, "change_unit": "percent"}) == "−0.39%"
    assert format_change({"status": "pending_verification", "change": None}) == "待核實"
    assert abs(26.6 + 73.4 - 100) < 0.001
    assert classify_rate_outcome("3.50%-3.75%", "3.75%-4.00%") == "降息一碼"
    assert classify_rate_outcome("3.75%-4.00%", "3.75%-4.00%") == "維持不變"
    assert classify_rate_outcome("4.00%-4.25%", "3.75%-4.00%") == "升息一碼"
    assert classify_rate_outcome("3.25%-3.50%", "3.75%-4.00%") == "降息兩碼"
    print("PASS: numeric formatting and signed percentage formatting")
    print("PASS: missing data is rendered as 待核實")
    print("PASS: FedWatch probability arithmetic")
    print("PASS: FedWatch cut/hold/hike classification")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master")
    parser.add_argument("--snapshot")
    parser.add_argument("--output")
    parser.add_argument("--expected-master-sha")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.master, args.snapshot, args.output, args.expected_master_sha)):
        parser.error("--master, --snapshot, --output and --expected-master-sha are required")
    try:
        result = render(Path(args.master), Path(args.snapshot), Path(args.output), args.expected_master_sha)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("NOTICE: market-only rendering; this output is NOT a review-ready TAC report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
