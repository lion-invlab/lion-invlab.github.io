#!/usr/bin/env python3
"""Byte-preserving, fail-closed text-slot patcher for TAC HTML experiments.

This module deliberately does not parse and re-serialize a DOM. It locates
unique existing text nodes and replaces only their source spans. All markup,
attributes, classes, CSS, scripts, comments, and surrounding whitespace remain
byte-for-byte unchanged. It is an experimental primitive, not yet a production
replacement for the TAC renderers.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser


VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
NON_CONTENT = {"script", "style", "noscript", "textarea", "template"}


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int
    text: str
    ancestors: tuple[str, ...]


class _SpanParser(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.stack: list[str] = []
        self.spans: list[TextSpan] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        return

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not data or any(tag in NON_CONTENT for tag in self.stack):
            return
        start = self._offset()
        end = start + len(data)
        # Defensive source check: parser offsets must identify the exact raw node.
        if self.source[start:end] != data:
            raise ValueError("HTML parser source offset mismatch; refusing to patch")
        self.spans.append(TextSpan(start, end, data, tuple(self.stack)))


def replace_unique_text_nodes(source: str, replacements: dict[str, str]) -> str:
    """Replace exact, unique existing text nodes; fail closed on missing/duplicate anchors."""
    if not isinstance(source, str) or not isinstance(replacements, dict) or not replacements:
        raise ValueError("source and a non-empty replacement mapping are required")
    if any(not isinstance(k, str) or not k for k in replacements):
        raise ValueError("every source text anchor must be a non-empty string")
    if any(not isinstance(v, str) for v in replacements.values()):
        raise ValueError("replacement values must be strings")

    parser = _SpanParser(source)
    parser.feed(source)
    parser.close()

    edits: list[tuple[int, int, str]] = []
    for anchor, value in replacements.items():
        matches = [span for span in parser.spans if span.text == anchor]
        if len(matches) != 1:
            raise ValueError(
                f"text anchor must match exactly once; {anchor!r} matched {len(matches)} times"
            )
        span = matches[0]
        edits.append((span.start, span.end, escape(value, quote=False)))

    # Apply from right to left so earlier source offsets remain valid.
    result = source
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result
