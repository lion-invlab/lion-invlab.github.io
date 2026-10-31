#!/usr/bin/env python3
"""Compare TAC mother-template and development-template fixed DOM structure.

Text nodes and href values are intentionally excluded because they contain daily data.
Tag hierarchy, IDs, classes, selected interaction attributes, and inline CSS/JS
content hashes are compared. This is a conservative first version: repeat-card
count changes are treated as structural differences until an explicit repeat rule
is approved and added.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

VOID = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
}
STABLE_ATTRS = {
    'type', 'name', 'role', 'for', 'aria-controls', 'aria-expanded',
    'aria-label', 'aria-hidden', 'data-template-note',
}

class Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.raw_text = ''

class TACParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#document')
        self.stack = [self.root]
        self.parse_errors = []

    def handle_starttag(self, tag, attrs):
        node = Node(tag.lower(), attrs)
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag.lower(), attrs))

    def handle_endtag(self, tag):
        tag = tag.lower()
        for idx in range(len(self.stack) - 1, 0, -1):
            if self.stack[idx].tag == tag:
                del self.stack[idx:]
                return
        self.parse_errors.append(f'unmatched closing tag: {tag}')

    def handle_data(self, data):
        if self.stack[-1].tag in {'style', 'script'}:
            self.stack[-1].raw_text += data

def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)

def node_signature(node):
    attrs = node.attrs
    classes = sorted((attrs.get('class') or '').split())
    stable = sorted((key, attrs[key]) for key in STABLE_ATTRS if key in attrs)
    return {
        'tag': node.tag,
        'id': attrs.get('id', ''),
        'classes': classes,
        'stable_attrs': stable,
        'children': [node_signature(child) for child in node.children],
    }

def inspect(path):
    source = Path(path).read_text(encoding='utf-8')
    parser = TACParser()
    parser.feed(source)
    parser.close()
    nodes = list(walk(parser.root))
    ids = [n.attrs['id'] for n in nodes if n.attrs.get('id')]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    inline_assets = []
    for n in nodes:
        if n.tag in {'style', 'script'}:
            digest = hashlib.sha256(n.raw_text.encode('utf-8')).hexdigest()
            inline_assets.append({
                'tag': n.tag, 'id': n.attrs.get('id', ''), 'sha256': digest
            })
    return {
        'path': str(path),
        'node_count': sum(1 for n in nodes if n.tag != '#document'),
        'duplicate_ids': duplicates,
        'parse_warnings': parser.parse_errors,
        'inline_assets': inline_assets,
        'structure': node_signature(parser.root),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True, help='Approved mother-template HTML')
    ap.add_argument('--candidate', required=True, help='Development-template HTML')
    ap.add_argument('--report', help='Optional JSON report path')
    args = ap.parse_args()
    base = inspect(args.baseline)
    candidate = inspect(args.candidate)
    structure_equal = base['structure'] == candidate['structure']
    assets_equal = base['inline_assets'] == candidate['inline_assets']
    ids_equal = base['duplicate_ids'] == candidate['duplicate_ids']
    result = {
        'baseline': {k: v for k, v in base.items() if k != 'structure'},
        'candidate': {k: v for k, v in candidate.items() if k != 'structure'},
        'checks': {
            'fixed_dom_structure_equal': structure_equal,
            'inline_css_js_equal': assets_equal,
            'duplicate_id_set_equal': ids_equal,
        },
        'pass': structure_equal and assets_equal and ids_equal
            and not base['parse_warnings'] and not candidate['parse_warnings'],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
    raise SystemExit(0 if result['pass'] else 1)

if __name__ == '__main__':
    main()

## 使用方式
```bash
python scripts/tac_template_structure_fingerprint.py \
  --baseline path/to/approved-mother.html \
  --candidate path/to/development-template.html \
  --report structure-audit.json
```

第一版採保守策略：任何 DOM 層級、ID、class、互動屬性或 inline CSS/JS 差異都會失敗；每日資料重複卡片張數若需變動，必須先定義受控 repeat-group 規則，不能直接放寬整體結構比對。

注意：此腳本目前只提供結構層驗收，不取代瀏覽器視覺、手機響應式、tab、details/summary 與紅圓加號互動測試。