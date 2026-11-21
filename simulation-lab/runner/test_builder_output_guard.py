#!/usr/bin/env python3
"""Negative tests for the Builder's simulation-preview-only write boundary."""
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup

import build_review_html as builder


class BuilderOutputGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "preview").mkdir()
        self.original_root = builder.ROOT
        builder.ROOT = self.root

    def tearDown(self):
        builder.ROOT = self.original_root
        self.temp.cleanup()

    def test_key_levels_update_preserves_mother_dom_and_disclosure(self):
        fixtures = (
            '<div class="key"><b>道瓊工業指數：</b>old values<br/>'
            '<b>S&amp;P 500：</b>old values<br/><b>Nasdaq：</b>old values<br/>'
            '<b>SOX：</b>old values<br/><b>Russell：</b>old values<br/>'
            '<details class="compact-disclosure"><summary>來源</summary><div><b>方法</b>舊說明</div></details></div>',
            '<div class="key"><b>道瓊工業指數｜</b>old values<br/>'
            '<b>S&amp;P 500｜</b>old values<br/><b>Nasdaq｜</b>old values<br/>'
            '<b>Russell｜</b>old values<br/><b>SOX｜</b>old values<br/>'
            '<details class="source-details"><summary>來源</summary><div class="source">舊說明</div></details></div>',
        )
        items = [
            {"name": f"指數{i}", "s2": "1", "s1": "2", "p": "3", "r1": "4", "r2": "5"}
            for i in range(5)
        ]
        for markup in fixtures:
            with self.subTest(markup=markup[:45]):
                soup = BeautifulSoup(markup, "html.parser")
                box = soup.select_one(".key")
                disclosure = box.find("details", recursive=False)
                before_shape = [
                    (getattr(child, "name", None), tuple(child.get("class", [])) if getattr(child, "name", None) else None)
                    for child in box.contents
                ]
                before_disclosure = str(disclosure)
                builder.populate_key_levels_preserving_dom(box, items, disclosure)
                after_shape = [
                    (getattr(child, "name", None), tuple(child.get("class", [])) if getattr(child, "name", None) else None)
                    for child in box.contents
                ]
                self.assertEqual(after_shape, before_shape)
                self.assertEqual(str(box.find("details", recursive=False)), before_disclosure)
                self.assertEqual(len(box.find_all("b", recursive=False)), 5)
                self.assertIn("第二支撐：1", box.get_text(" ", strip=True))
                self.assertIn("第二壓力：5", box.get_text(" ", strip=True))

    def test_accepts_only_canonical_dated_preview(self):
        expected = (self.root / "preview/2026-11-23-simulation.html").resolve()
        self.assertEqual(
            builder.resolve_allowed_output_path("2026-11-23", "preview/2026-11-23-simulation.html"),
            expected,
        )
        self.assertEqual(
            builder.resolve_allowed_output_path("2026-11-23", str(expected)),
            expected,
        )

    def test_rejects_homepage_and_protected_paths(self):
        for target in ("index.html", "母版專區/master.html", "data/calendar/weeks/2026-W48.json", "simulation-lab/baseline/mother-template-manifest.json"):
            with self.subTest(target=target), self.assertRaises(SystemExit):
                builder.resolve_allowed_output_path("2026-11-23", target)

    def test_rejects_preview_path_traversal_and_wrong_filename(self):
        for target in ("preview/../index.html", "preview/other.html", "preview/2026-11-24-simulation.html"):
            with self.subTest(target=target), self.assertRaises(SystemExit):
                builder.resolve_allowed_output_path("2026-11-23", target)

    def test_rejects_preview_directory_symlink_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "preview").rmdir()
        (self.root / "preview").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(SystemExit):
            builder.resolve_allowed_output_path("2026-11-23", "preview/2026-11-23-simulation.html")

    def test_rejects_output_file_symlink_escape(self):
        outside = self.root / "outside.html"
        outside.write_text("do not overwrite", encoding="utf-8")
        target = self.root / "preview/2026-11-23-simulation.html"
        target.symlink_to(outside)
        with self.assertRaises(SystemExit):
            builder.resolve_allowed_output_path("2026-11-23", "preview/2026-11-23-simulation.html")


if __name__ == "__main__":
    unittest.main(verbosity=2)