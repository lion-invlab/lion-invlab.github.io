#!/usr/bin/env python3
"""Render a validated TAC market snapshot into its SHA-pinned approved mother.

Only existing text slots and explicitly whitelisted state classes may change.
No sections, nodes, links, styles, scripts, or layout attributes are created.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "母版專區" / "mother-template-manifest.json"
BINDING_MAP = ROOT / "scripts" / "tac_html_binding_map.json"
PROTECTED = {
    "index.html",
    "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
    "母版專區/mother-template-manifest.json",
    "TAC_WORK_RULES.md",
}
STATUS_CLASSES = {"up", "down", "flat", "warn"}


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def choose_template(snapshot: dict, manifest: dict) -> tuple[str, dict]:
    report_day = date.fromisoformat(snapshot["meta"]["report_date"])
    if report_day.weekday() > 4:
        raise ValueError("weekend report dates are not eligible for automatic production")
    key = "monday" if report_day.weekday() == 0 else "weekdays"
    item = manifest["templates"][key]
    path = ROOT / item["path"]
    if not path.is_file():
        raise ValueError(f"approved mother template missing: {item['path']}")
    if path.as_posix().startswith("../"):
        raise ValueError("template path escapes repository root")
    import hashlib
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    if digest != item["blob_sha"]:
        raise ValueError(
            f"mother SHA mismatch for {key}: expected {item['blob_sha']}, got {digest}; stop without fallback"
        )
    return key, item


def record_text(record: dict, field: str) -> str:
    value = record.get(field)
    if value is None:
        return "待核實"
    unit = record.get("unit") if field == "value" else record.get("change_unit")
    if field == "change" and unit == "percent":
        return f"{value:+.2f}%"
    if field == "change" and unit == "basis_point":
        return f"{value:+.1f} bp"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def state_class(record: dict) -> str:
    if record.get("status") in {"missing", "pending_verification"}:
        return "warn"
    change = record.get("change")
    if change is None:
        return "flat"
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def replace_text(tag, value: str, label: str) -> None:
    if tag is None:
        raise ValueError(f"binding target missing: {label}")
    if len(tag.contents) != 1 or not isinstance(tag.contents[0], NavigableString):
        raise ValueError(f"binding target must contain exactly one text node: {label}")
    tag.contents[0].replace_with(value)


def set_state_class(tag, state: str, allowed: set[str]) -> None:
    if state not in allowed:
        raise ValueError(f"state class not whitelisted: {state}")
    classes = list(tag.get("class", []))
    old = [item for item in classes if item in allowed]
    if len(old) > 1:
        raise ValueError("binding target contains multiple status classes")
    if old:
        classes[classes.index(old[0])] = state
    else:
        classes.append(state)
    tag["class"] = classes


def unique_row(container, selector: str, predicate, label: str):
    matches = [node for node in container.select(selector) if predicate(node)]
    if len(matches) != 1:
        raise ValueError(f"{label}: expected exactly one row, found {len(matches)}")
    return matches[0]


def apply_group(group, soup, snapshot, spec, allowed):
    container = soup.select_one(spec["container"])
    if container is None:
        raise ValueError(f"{group}: container {spec['container']} missing")

    if "key_by_label" in spec:
        rows = container.select(spec["row"])
        if len(rows) != len(spec["key_by_label"]):
            raise ValueError(f"{group}: expected {len(spec['key_by_label'])} rows, found {len(rows)}")
        for key, label in spec["key_by_label"].items():
            row = unique_row(container, spec["row"], lambda n: label in normalized(n.get_text(" ", strip=True)), f"{group}.{key}")
            slots = row.select(spec["value_selector"])
            if len(slots) < 2:
                raise ValueError(f"{group}.{key}: expected value and change slots, found {len(slots)}")
            record = snapshot[group][key]
            replace_text(slots[spec.get("value_index", 0)], record_text(record, "value"), f"{group}.{key}.value")
            change_slot = slots[spec.get("change_index", 1)]
            replace_text(change_slot, record_text(record, "change"), f"{group}.{key}.change")
            set_state_class(change_slot, state_class(record), allowed)

    if "key_by_ticker" in spec:
        rows = container.select(spec["row"])
        if len(rows) != len(spec["key_by_ticker"]):
            raise ValueError(f"{group}: expected {len(spec['key_by_ticker'])} sector rows, found {len(rows)}")
        for key, ticker in spec["key_by_ticker"].items():
            row = unique_row(container, spec["row"], lambda n: re.search(r"(?<![A-Z0-9])" + re.escape(ticker) + r"(?![A-Z0-9])", normalized(n.get_text(" ", strip=True))) is not None, f"{group}.{key}")
            slots = row.select(spec["value_selector"])
            if len(slots) != 1:
                raise ValueError(f"{group}.{key}: expected one sector return slot, found {len(slots)}")
            record = snapshot[group][key]
            replace_text(slots[0], record_text(record, "change"), f"{group}.{key}.change")
            set_state_class(slots[0], state_class(record), allowed)

    if "records" in spec:
        for key, item in spec["records"].items():
            row = unique_row(container, item["row"], lambda n: any(normalized(x.get_text()) == item["key_text"] for x in n.select(".label-en")), f"{group}.{key}")
            value_target = row.select_one(item["value_selector"])
            record = snapshot[group][key]
            replace_text(value_target, record_text(record, "value"), f"{group}.{key}.value")
            if item.get("change_selector"):
                candidates = row.select(item["change_selector"])
                if len(candidates) != 1:
                    raise ValueError(f"{group}.{key}: expected one change/status target, found {len(candidates)}")
                replace_text(candidates[0], record_text(record, "change"), f"{group}.{key}.change")
                set_state_class(candidates[0], state_class(record), allowed)

    if "outcomes" in spec:
        rows = container.select(spec["row"])
        if len(rows) != len(spec["outcomes"]):
            raise ValueError(f"{group}: expected {len(spec['outcomes'])} FedWatch outcomes, found {len(rows)}")
        probabilities = snapshot["fedwatch"]["probabilities"]
        for key, outcome in spec["outcomes"].items():
            row = unique_row(container, spec["row"], lambda n: outcome["label"] in normalized(n.get_text(" ", strip=True)), f"{group}.{key}")
            range_target = row.select_one(outcome["rate_range_selector"])
            current_range = normalized(range_target.get_text(" ", strip=True))
            if snapshot["fedwatch"]["status"] != "verified":
                replace_text(row.select_one(outcome["probability_selector"]), "待核實", f"fedwatch.{key}.probability")
                replace_text(range_target, "待核實", f"fedwatch.{key}.rate_range")
                continue
            candidates = [p for p in probabilities if normalized(p["rate_range"]) in current_range or current_range in normalized(p["rate_range"])]
            if len(candidates) != 1:
                raise ValueError(f"fedwatch.{key}: cannot uniquely match rate range '{current_range}' to snapshot")
            probability = candidates[0]["probability"]
            replace_text(row.select_one(outcome["probability_selector"]), f"{probability:.1f}%", f"fedwatch.{key}.probability")
            replace_text(range_target, candidates[0]["rate_range"], f"fedwatch.{key}.rate_range")


def tree_signature(soup):
    """Compare DOM shape and all non-state attributes; text content is intentionally ignored."""
    def walk(node):
        if isinstance(node, NavigableString):
            return ("#text",)
        if not getattr(node, "name", None):
            return ("#other",)
        attrs = []
        for key, value in sorted(node.attrs.items()):
            if key == "class":
                stable = tuple(x for x in value if x not in STATUS_CLASSES)
                attrs.append((key, stable))
            elif key == "content" and node.name == "meta" and node.get("name") == "report-date":
                attrs.append((key, "<REPORT_DATE>"))
            else:
                attrs.append((key, str(value)))
        return (node.name, tuple(attrs), tuple(walk(child) for child in node.children))
    return tuple(walk(child) for child in soup.contents)


def render(snapshot_path: Path, output_path: Path) -> dict:
    snapshot = read_json(snapshot_path)
    from validate_tac_daily_snapshot import load_validator
    validator, _ = load_validator()
    errors = list(validator.iter_errors(snapshot))
    if errors:
        raise ValueError("snapshot schema invalid: " + "; ".join(e.message for e in errors[:8]))

    manifest = read_json(MANIFEST)
    binding = read_json(BINDING_MAP)
    template_key, template = choose_template(snapshot, manifest)
    source_path = ROOT / template["path"]
    original = source_path.read_text(encoding="utf-8")
    before = BeautifulSoup(original, "html.parser")
    after = copy.deepcopy(before)
    before_signature = tree_signature(before)

    for group, spec in binding["groups"].items():
        apply_group(group, after, snapshot, spec, set(binding["rules"].get("mutable_status_classes", [])))

    # Update only the existing report-date metadata value; do not alter its attributes.
    report_meta = after.select('meta[name="report-date"]')
    if len(report_meta) != 1:
        raise ValueError(f"expected one report-date meta tag, found {len(report_meta)}")
    report_meta[0]["content"] = snapshot["meta"]["report_date"]

    if tree_signature(after) != before_signature:
        raise ValueError("DOM structure or non-whitelisted attributes changed; refusing output")
    if output_path.resolve() in {(ROOT / p).resolve() for p in PROTECTED}:
        raise ValueError("refusing to write a protected path")
    if output_path.resolve() == source_path.resolve():
        raise ValueError("refusing to overwrite approved mother template")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(after), encoding="utf-8")
    return {
        "template": template_key,
        "template_path": template["path"],
        "template_sha": template["blob_sha"],
        "report_date": snapshot["meta"]["report_date"],
        "trading_date": snapshot["meta"]["trading_date"],
        "output": str(output_path),
        "verified_records": sum(
            1 for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators")
            for item in snapshot[group].values() if item["status"] == "verified"
        ),
        "pending_records": sum(
            1 for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators")
            for item in snapshot[group].values() if item["status"] == "pending_verification"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = render(Path(args.snapshot), Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("PASS: snapshot rendered using SHA-pinned approved mother")
    print("PASS: DOM tree and non-state attributes preserved")
    print("PASS: protected files were not modified")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
