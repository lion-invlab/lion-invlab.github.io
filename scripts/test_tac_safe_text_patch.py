#!/usr/bin/env python3
"""Tests for the experimental byte-preserving TAC text patcher."""
import unittest
from pathlib import Path

from tac_safe_text_patch import _SpanParser, replace_unique_text_nodes


class SafeTextPatchTests(unittest.TestCase):
    def test_only_target_text_changes(self):
        original = (
            '<!doctype html><html><head><style>.card{color:red}</style>'
            '<script>window.keep = true;</script></head><body>'
            '<main id="market" class="card up" data-x="1">'
            '<span class="quote">舊收盤</span></main></body></html>'
        )
        expected = original.replace("舊收盤", "新收盤 &amp; 價格")
        actual = replace_unique_text_nodes(original, {"舊收盤": "新收盤 & 價格"})
        self.assertEqual(actual, expected)
        self.assertIn('<style>.card{color:red}</style>', actual)
        self.assertIn('<script>window.keep = true;</script>', actual)
        self.assertIn('id="market" class="card up" data-x="1"', actual)

    def test_missing_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "matched 0 times"):
            replace_unique_text_nodes("<p>現值</p>", {"不存在": "新值"})

    def test_duplicate_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "matched 2 times"):
            replace_unique_text_nodes("<p>現值</p><p>現值</p>", {"現值": "新值"})

    def test_script_and_style_are_not_editable(self):
        source = "<style>safe-token</style><script>safe-token</script>"
        with self.assertRaisesRegex(ValueError, "matched 0 times"):
            replace_unique_text_nodes(source, {"safe-token": "changed"})

    def test_nested_text_node_is_updated_without_markup_rebuild(self):
        source = '<div><strong><span>舊值</span></strong><i>固定</i></div>'
        self.assertEqual(
            replace_unique_text_nodes(source, {"舊值": "新值"}),
            '<div><strong><span>新值</span></strong><i>固定</i></div>',
        )

    def test_multiple_updates_keep_original_offsets(self):
        source = "<p>第一</p><p>第二</p>"
        self.assertEqual(
            replace_unique_text_nodes(source, {"第一": "甲", "第二": "乙"}),
            "<p>甲</p><p>乙</p>",
        )

    def test_real_mother_templates_are_byte_local(self):
        root = Path(__file__).resolve().parents[1]
        paths = [
            root / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
            root / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
        ]
        for path in paths:
            with self.subTest(template=path.name):
                source = path.read_text(encoding="utf-8")
                parser = _SpanParser(source)
                parser.feed(source)
                parser.close()
                anchor = next(
                    span.text for span in parser.spans
                    if span.text.strip()
                    and sum(other.text == span.text for other in parser.spans) == 1
                )
                actual = replace_unique_text_nodes(source, {anchor: anchor + "（試作）"})
                self.assertEqual(actual.replace(anchor + "（試作）", anchor, 1), source)
                self.assertEqual(actual.count("（試作）"), 1)


if __name__ == "__main__":
    unittest.main()
