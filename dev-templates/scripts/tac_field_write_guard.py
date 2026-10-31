"""Test-only allowlist guard for leaf-node data writes.

This module is not a production updater. It provides a narrow reference guard
used by tests to prove that only registered content leaves can be changed.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit

import cssselect2
import html5lib


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "dev-templates/selector-registry-v1.json"


def load_registry(path=REGISTRY_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_html(source):
    parser = html5lib.HTMLParser(
        tree=html5lib.getTreeBuilder("etree"),
        namespaceHTMLElements=False,
        strict=False,
    )
    return parser.parse(source)


def select_wrappers(root, selector):
    compiled = cssselect2.compile_selector_list(selector)
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [
        item for item in wrapped.iter_subtree()
        if any(s.pseudo_element is None and s.test(item) for s in compiled)
    ]


def update_registered_source_links(root, selector, links, registry=None):
    """Update href and label on individually registered anchor leaves only."""
    registry = registry or load_registry()
    item = next((x for x in registry["selectors"] if x["selector"] == selector), None)
    if item is None:
        raise PermissionError(f"selector is not registered: {selector}")
    if item["kind"] != "source_link_leaf":
        raise PermissionError(f"selector kind is not a source-link leaf: {item['kind']}")

    matches = select_wrappers(root, selector)
    if not matches:
        raise LookupError(f"registered source-link selector matched no nodes: {selector}")
    if len(matches) != len(links):
        raise ValueError(f"source-link update count mismatch: {len(matches)} != {len(links)}")

    prepared = []
    for match, link in zip(matches, links):
        node = match.etree_element
        if node.tag.lower() != "a" or len(list(node)):
            raise PermissionError("source-link target must be a leaf anchor")
        href = link.get("href")
        label = link.get("label")
        if not isinstance(href, str) or not isinstance(label, str) or not label.strip():
            raise ValueError("each source link requires a non-empty href and label")
        parsed = urlsplit(href)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("source links must use absolute http(s) URLs")
        if parsed.username or parsed.password or any(ord(ch) < 32 for ch in href):
            raise ValueError("unsafe source URL")
        prepared.append((node, href, label))

    for node, href, label in prepared:
        node.attrib["href"] = href
        node.text = label
    return len(prepared)


def update_registered_text_segments(root, selector, values, registry=None):
    """Update only explicitly indexed child-tail text segments; never replace markup."""
    registry = registry or load_registry()
    candidates = [x for x in registry["selectors"] if x["selector"] == selector and x.get("kind") == "text_segments"]
    if len(candidates) != 1:
        raise PermissionError(f"selector must have exactly one text-segments registration: {len(candidates)}")
    item = candidates[0]
    segments = item.get("segments", [])
    if len(values) != len(segments):
        raise ValueError(f"text-segment update count mismatch: {len(values)} != {len(segments)}")
    matches = select_wrappers(root, selector)
    if len(matches) != 1:
        raise ValueError(f"text-segment parent must match exactly once: {len(matches)}")

    parent = matches[0].etree_element
    children = list(parent)
    prepared = []
    used_indexes = set()
    for segment, value in zip(segments, values):
        index = segment.get("child_index")
        if not isinstance(index, int) or index < 0 or index >= len(children):
            raise PermissionError("registered text-segment child index is outside the parent")
        if index in used_indexes:
            raise PermissionError("duplicate text-segment child index")
        used_indexes.add(index)
        child = children[index]
        if child.tag.lower() != segment.get("expected_tag", "").lower():
            raise PermissionError("text-segment child tag does not match the registered structure")
        if segment.get("target") != "tail":
            raise PermissionError("only registered child-tail text segments are supported")
        if not isinstance(value, str):
            raise ValueError("text-segment values must be strings")
        prepared.append((child, value))

    for child, value in prepared:
        child.tail = value
    return len(prepared)



def update_registered_labeled_leaf_fields(root, card_selector, card_values, registry=None):
    """Update explicitly allowlisted detail labels inside registered repeat cards.

    The field label is immutable. Only its adjacent value element may change,
    and only when that value is a plain-text leaf. All cards are validated
    before any text is written.
    """
    registry = registry or load_registry()
    candidates = [
        item for item in registry["selectors"]
        if item["selector"] == card_selector
        and item.get("kind") in {"repeat", "monday_only"}
    ]
    if len(candidates) != 1:
        raise PermissionError(
            f"card selector must have exactly one repeat registration: {len(candidates)}"
        )
    item = candidates[0]
    allowed = set(item.get("writable_detail_labels", []))
    field_class = item.get("detail_field_class")
    value_class = item.get("detail_value_class")
    if not allowed or not field_class or not value_class:
        raise PermissionError("repeat card has no explicit detail-field write allowlist")

    cards = select_wrappers(root, card_selector)
    if len(cards) != len(card_values):
        raise ValueError(
            f"card update count mismatch: {len(card_values)} != {len(cards)}"
        )

    prepared = []
    for card_index, (wrapper, values) in enumerate(zip(cards, card_values)):
        if not isinstance(values, dict):
            raise ValueError(f"card {card_index} update must be a label/value mapping")
        if not set(values).issubset(allowed):
            raise PermissionError(
                f"card {card_index} contains non-allowlisted labels: {sorted(set(values) - allowed)}"
            )
        card = wrapper.etree_element
        for label_text, value in values.items():
            if not isinstance(value, str):
                raise ValueError("labeled detail values must be strings")
            matching_fields = []
            for field in card.iter():
                classes = set(field.attrib.get("class", "").split())
                if field.tag.lower() not in {"div", "section"} or field_class not in classes:
                    continue
                labels = [
                    child for child in list(field)
                    if child.tag.lower() == "label" and (child.text or "").strip() == label_text
                ]
                if labels:
                    matching_fields.append((field, labels))
            if len(matching_fields) != 1:
                raise PermissionError(
                    f"card {card_index} label {label_text!r} must match exactly one detail field"
                )
            field, labels = matching_fields[0]
            values_nodes = [
                child for child in list(field)
                if value_class in set(child.attrib.get("class", "").split())
            ]
            if len(values_nodes) != 1:
                raise PermissionError(
                    f"card {card_index} label {label_text!r} has no unique adjacent value node"
                )
            target = values_nodes[0]
            if len(list(target)):
                raise PermissionError(
                    f"card {card_index} label {label_text!r} value is not a plain-text leaf"
                )
            prepared.append((target, value))

    for target, value in prepared:
        target.text = value
    return len(prepared)

def update_registered_leaf_text(root, selector, value, registry=None):
    """Update text only when selector is explicitly registered as content and targets leaves."""
    registry = registry or load_registry()
    item = next((x for x in registry["selectors"] if x["selector"] == selector), None)
    if item is None:
        raise PermissionError(f"selector is not registered: {selector}")
    if item["kind"] != "content":
        raise PermissionError(f"selector kind is protected: {item['kind']}")

    matches = select_wrappers(root, selector)
    if not matches:
        raise LookupError(f"registered selector matched no nodes: {selector}")

    for match in matches:
        node = match.etree_element
        if len(list(node)):
            raise PermissionError(f"target is not a leaf node: {selector}")
    for match in matches:
        match.etree_element.text = str(value)
    return len(matches)
