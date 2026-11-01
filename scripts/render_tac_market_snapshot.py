#!/usr/bin/env python3
"""Apply a validated TAC market snapshot to existing approved HTML value slots only."""
from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = ROOT / "scripts" / "tac_html_binding_map.json"
SNAPSHOT_VALIDATOR = ROOT / "scripts" / "validate_tac_daily_snapshot.py"


class Node:
    def __init__(self, tag, attrs, start, open_end, parent=None, self_closing=False):
        self.tag = tag.lower()
        self.attrs = dict(attrs)
        self.start = start
        self.open_end = open_end
        self.close_start = open_end if self_closing else None
        self.end = open_end if self_closing else None
        self.parent = parent
        self.children = []
        self.self_closing = self_closing

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()

    def text(self, source):
        if self.end is None:
            return ""
        inner = source[self.open_end:self.close_start]
        return re.sub(r"<[^>]*>", "", inner).replace("&amp;", "&").replace("&nbsp;", " ").strip()


class SourceParser(HTMLParser):
    VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.nodes = []
        self.stack = []
        self.line_offsets = [0]
        for match in re.finditer("\n", source):
            self.line_offsets.append(match.end())
        self.feed(source)
        self.close()

    def source_offset(self):
        line, col = self.getpos()
        return self.line_offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.source_offset()
        raw = self.get_starttag_text()
        parent = self.stack[-1] if self.stack else None
        node = Node(tag, attrs, start, start + len(raw), parent, tag.lower() in self.VOID)
        if parent:
            parent.children.append(node)
        self.nodes.append(node)
        if not node.self_closing:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag.lower():
            node = self.stack.pop()
            node.close_start = node.open_end
            node.end = node.open_end

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag.lower():
                node = self.stack[index]
                node.close_start = self.source_offset()
                end_tag = re.match(r"</\s*" + re.escape(tag) + r"\s*>", self.source[self.source_offset():], re.I)
                node.end = self.source_offset() + (len(end_tag.group(0)) if end_tag else 0)
                del self.stack[index:]
                break


def simple_match(node, token):
    if not token:
        return False
    tag_match = re.match(r"^[a-zA-Z][\w-]*", token)
    if tag_match and node.tag != tag_match.group(0).lower():
        return False
    ident = re.search(r"#([\w-]+)", token)
    if ident and node.attrs.get("id") != ident.group(1):
        return False
    classes = re.findall(r"\.([\w-]+)", token)
    return all(node.has_class(c) for c in classes)


def selector_tokens(selector):
    return re.findall(r"([^\s>]+)|([>])", selector)


def select(nodes, selector):
    if "," in selector:
        found = []
        for part in selector.split(","):
            found.extend(select(nodes, part.strip()))
        return list(dict.fromkeys(found))
    parts = re.split(r"\s+(?![^\[]*\])", selector.strip())
    if ">" in selector:
        parts = [p.strip() for p in selector.split(">")]
        current = [node for node in nodes if simple_match(node, parts[0])]
        for part in parts[1:]:
            current = [child for node in current for child in node.children if simple_match(child, part.strip())]
        return current
    current = [node for node in nodes if simple_match(node, parts[-1])]
    if len(parts) == 1:
        return current
    result = []
    for node in current:
        parent = node.parent
        ok = True
        for part in reversed(parts[:-1]):
            while parent is not None and not simple_match(parent, part):
                parent = parent.parent
            if parent is None:
                ok = False
                break
            parent = parent.parent
        if ok:
            result.append(node)
    return result


def replace_inner(source, node, value, status=None):
    if node.end is None:
        raise ValueError("unclosed target node")
    raw_open = source[node.start:node.open_end]
    if status is not None:
        classes = (node.attrs.get("class") or "").split()
        allowed = {"up", "down", "flat", "warn"}
        classes = [item for item in classes if item not in allowed]
        if status in allowed:
            classes.append(status)
        class_attr = 'class="' + " ".join(classes) + '"'
        class_pattern = r'class\s*=\s*"[^"]*"'
        if re.search(class_pattern, raw_open, re.I|re.S):
            raw_open = re.sub(class_pattern, class_attr, raw_open, count=1, flags=re.I|re.S)
        elif classes:
            raw_open = raw_open[:-1] + " " + class_attr + ">"
    return source[:node.start] + raw_open + escape(str(value), quote=False) + source[node.close_start:]

def format_number(value, decimals=2, unit=None):
    if value is None:
        return "待核實"
    suffix = "%" if unit == "%" else ""
    return f"{value:,.{decimals}f}{suffix}"


def format_change(value, unit, decimals=2):
    if value is None:
        return "待核實"
    if unit == "%":
        return f"{value:+.{decimals}f}%"
    if unit == "bp":
        return f"{value:+.0f} bp"
    if unit in {"point", "points", "index point"}:
        return f"{value:+,.{decimals}f}"
    return f"{value:+,.{decimals}f}{unit or ''}"


def status_class(row):
    if row["status"] in {"pending_verification", "missing"}:
        return "warn"
    change = row.get("change")
    if change is None or change == 0:
        return "flat"
    return "up" if change > 0 else "down"


def find_row(nodes, selector, label, source):
    rows = select(nodes, selector)
    matches = [row for row in rows if label in row.text(source)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one row for {label!r}, found {len(matches)}")
    return matches[0]





def update_row(source, nodes, selector, label, row_data, decimals=2, has_change=True):
    row = find_row(nodes, selector, label, source)
    value_nodes = select(nodes, "span.r")
    value_nodes = [node for node in value_nodes if is_descendant(node, row)]
    expected = 2 if has_change else 1
    if len(value_nodes) < expected:
        raise ValueError(f"{label}: expected at least {expected} span.r slots, found {len(value_nodes)}")
    if has_change:
        source = replace_inner(source, value_nodes[1],
            format_change(row_data["change"], row_data["change_unit"], 2), status_class(row_data))
    source = replace_inner(source, value_nodes[0], format_number(row_data["value"], decimals, row_data.get("unit")))
    return source


def is_descendant(node, ancestor):
    current = node.parent
    while current is not None:
        if current is ancestor:
            return True
        current = current.parent
    return False


def update_group(source, binding, group_name, snapshot, labels, decimals):
    group = binding["groups"][group_name]
    for key, label in labels.items():
        row = snapshot[group_name][key]
        source = update_row(source, SourceParser(source).nodes, group["container"] + " " + group["row"], label, row,
            decimals.get(key, 2), has_change=True)
    return source


def update_sectors(source, binding, snapshot):
    group = binding["groups"]["sectors"]
    initial_nodes = SourceParser(source).nodes
    row_nodes = select(initial_nodes, group["container"] + " " + group["row"])
    ticker_to_node = {}
    for key, ticker in group["key_by_ticker"].items():
        matches = [node for node in row_nodes if re.search(r"\b" + re.escape(ticker) + r"\b", node.text(source))]
        if len(matches) != 1:
            raise ValueError(f"sector ticker {ticker} must resolve exactly once; got {len(matches)}")
        ticker_to_node[key] = matches[0]

    updated_fragments = {}
    for key, original_node in sorted(ticker_to_node.items(), key=lambda item: item[1].start, reverse=True):
        ticker = group["key_by_ticker"][key]
        current_nodes = SourceParser(source).nodes
        current_rows = [node for node in select(current_nodes, group["container"] + " " + group["row"])
            if re.search(r"\b" + re.escape(ticker) + r"\b", node.text(source))]
        if len(current_rows) != 1:
            raise ValueError(f"sector {key} row changed unexpectedly during update")
        current_row = current_rows[0]
        value_nodes = [node for node in select(current_nodes, "span.r") if is_descendant(node, current_row)]
        if len(value_nodes) != 1:
            raise ValueError(f"sector {key} must have exactly one value slot")
        row_data = snapshot["sectors"][key]
        source = replace_inner(source, value_nodes[0], format_change(row_data["change"], "%", 2), status_class(row_data))

        # Capture this row after update. Processing from bottom to top means later
        # edits cannot invalidate the source offsets of rows still to be updated.
        captured_nodes = SourceParser(source).nodes
        captured_rows = [node for node in select(captured_nodes, group["container"] + " " + group["row"])
            if re.search(r"\b" + re.escape(ticker) + r"\b", node.text(source))]
        if len(captured_rows) != 1:
            raise ValueError(f"sector {key} could not be captured after update")
        captured = captured_rows[0]
        updated_fragments[key] = source[captured.start:captured.end]

    # Sort only the existing intact row fragments; preserve the sector-list container.
    parsed = SourceParser(source)
    sector_lists = select(parsed.nodes, ".sector-list")
    if len(sector_lists) != 1:
        raise ValueError("expected exactly one .sector-list container")
    container = sector_lists[0]
    ordered_keys = sorted(
        group["key_by_ticker"].keys(),
        key=lambda key: snapshot["sectors"][key]["change"]
            if snapshot["sectors"][key]["change"] is not None else float("-inf"),
        reverse=True,
    )
    ordered_html = "".join(updated_fragments[key] for key in ordered_keys)
    source = source[:container.open_end] + ordered_html + source[container.close_start:]
    return source


def ticker_from_text(text, mapping):
    for key, ticker in mapping.items():
        if re.search(r"\b" + re.escape(ticker) + r"\b", text):
            return key
    raise ValueError("sector row ticker could not be identified")


def update_risk(source, binding, snapshot):
    group = binding["groups"]["risk_indicators"]
    for key, config in group["records"].items():
        nodes = SourceParser(source).nodes
        rows = select(nodes, group["container"] + " " + config["row"])
        matches = [node for node in rows if config["key_text"] in node.text(source)]
        if len(matches) != 1:
            raise ValueError(f"risk indicator {key} must resolve exactly once")
        row_node = matches[0]
        value_nodes = select(nodes, config["value_selector"])
        value_nodes = [n for n in value_nodes if n is row_node or is_descendant(n, row_node)]
        if len(value_nodes) != 1:
            raise ValueError(f"risk indicator {key} value slot mismatch")
        row = snapshot["risk_indicators"][key]
        source = replace_inner(source, value_nodes[0], format_number(row["value"], group["value_decimals"][key]))
        if config["change_selector"]:
            nodes = SourceParser(source).nodes
            current_rows = [n for n in select(nodes, group["container"] + " " + config["row"]) if config["key_text"] in n.text(source)]
            row_node = current_rows[0]
            change_nodes = [n for n in select(nodes, config["change_selector"]) if n is row_node or is_descendant(n, row_node)]
            if len(change_nodes) != 1:
                raise ValueError(f"risk indicator {key} change slot mismatch")
            source = replace_inner(source, change_nodes[0], format_change(row["change"], row["change_unit"], 2), status_class(row))
    return source


def render(template_path, snapshot_path, binding_path, output_path, mode):
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    subprocess_args = [sys.executable, str(SNAPSHOT_VALIDATOR), "--file", str(snapshot_path)]
    import subprocess
    subprocess.run(subprocess_args, cwd=ROOT, check=True)
    binding = json.loads(Path(binding_path).read_text(encoding="utf-8"))
    expected_template = binding["templates"][mode]
    template_path = Path(template_path)
    if template_path.resolve() != (ROOT / expected_template).resolve():
        raise ValueError("template path does not match approved binding-map template")
    source = template_path.read_text(encoding="utf-8")
    original = source
    global_group = binding["groups"]["global_indices"]
    for key, label in global_group["key_by_label"].items():
        source = update_row(source, SourceParser(source).nodes, global_group["container"] + " " + global_group["row"], label,
            snapshot["global_indices"][key], global_group["value_decimals"].get(key, 2), True)
    for group_name in ("bonds", "fx", "energy", "precious_metals"):
        group = binding["groups"][group_name]
        for key, label in group["key_by_label"].items():
            source = update_row(source, SourceParser(source).nodes, group["container"] + " " + group["row"], label,
                snapshot[group_name][key], group.get("value_decimals", {}).get(key, 2), True)
    source = update_sectors(source, binding, snapshot)
    source = update_risk(source, binding, snapshot)
    # Refresh existing market-panel date labels only; no layout or structure changes.
    trading_date = snapshot["meta"]["trading_date"]
    date_label = f"{trading_date[:4]}/{trading_date[5:7]}/{trading_date[8:10]}"
    parsed = SourceParser(source)
    meta_nodes = [node for node in parsed.nodes if node.has_class("tab-panel-meta")]
    for node in reversed(meta_nodes):
        old_text = source[node.open_end:node.close_start]
        if re.search(r"20\d{2}/\d{1,2}/\d{1,2}", re.sub(r"<[^>]*>", "", old_text)):
            new_text = re.sub(r"20\d{2}/\d{1,2}/\d{1,2}", date_label, old_text, count=1)
            source = source[:node.open_end] + new_text + source[node.close_start:]
    if source == original:
        raise ValueError("renderer made no changes")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")
    print(json.dumps({"output":str(output),"template_mode":mode,"trading_date":trading_date,
        "market_sections_updated":["global_indices","sectors","bonds","fx","energy","precious_metals","risk_indicators"],
        "source_master_unchanged":True,"publish_allowed":False},ensure_ascii=False,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--binding-map", default=str(BINDING_PATH))
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("monday","weekday"), required=True)
    args = parser.parse_args()
    render(args.template,args.snapshot,args.binding_map,args.output,args.mode)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("TAC MARKET RENDER FAIL-SAFE: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
