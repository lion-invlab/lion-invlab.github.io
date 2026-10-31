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
