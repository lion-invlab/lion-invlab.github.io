#!/usr/bin/env python3
"""Integration checks for the rendered TAC report's 今日關鍵價位 panel."""
from pathlib import Path
import re
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")
START = '<div class="focus-panel focus-levels">'
END = '<div class="focus-panel focus-core">'

def levels_panel():
    start = HTML.find(START)
    end = HTML.find(END, start + len(START))
    if start < 0 or end < 0:
        raise AssertionError("找不到今日關鍵價位面板或面板邊界")
    return HTML[start:end]

class KeyLevelsIntegrationTests(unittest.TestCase):
    def test_final_levels_are_rendered(self):
        panel = levels_panel()
        for value in (
            "支撐 S1：52,608.28", "中樞 P：52,768.08", "壓力 R1：53,027.78",
            "支撐 S1：7,632.88", "中樞 P：7,667.91", "壓力 R1：7,698.46",
            "支撐 S1：25,831.50", "中樞 P：26,095.45", "壓力 R1：26,272.82",
            "支撐 S1：10,552.15", "中樞 P：10,846.24", "壓力 R1：11,026.07",
        ):
            self.assertIn(value, panel, f"面板缺少已核實價位：{value}")

    def test_no_pending_placeholders(self):
        self.assertNotIn("待完成技術價位核算", levels_panel())

    def test_methodology_is_collapsed_and_ohlc_not_displayed(self):
        panel = levels_panel()
        self.assertRegex(panel, r"<details class=\"source-details\">\s*<summary>關鍵價位計算方式與資料來源</summary>")
        self.assertNotRegex(panel, r"(?i)\bOHLC\s*[:=]")

    def test_unverified_russell_is_not_fabricated(self):
        panel = levels_panel()
        self.assertIn("Russell 2000 未完成同日來源驗證", panel)
        self.assertIn("暫不發布推算值", panel)

if __name__ == "__main__":
    unittest.main(verbosity=2)
