#!/usr/bin/env python3
"""Integration checks for the rendered TAC report's 今日關鍵價位 panel."""
from pathlib import Path
import re
import unittest

HTML = Path("index.html").read_text(encoding="utf-8")
START = '<div class="focus-panel focus-levels">'
END = '<div class="callout">'

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
            "支撐 S1：2,769.43", "中樞 P：2,777.18", "壓力 R1：2,791.77",
        ):
            self.assertIn(value, panel, f"面板缺少已核實價位：{value}")

    def test_no_pending_placeholders(self):
        self.assertNotIn("待完成技術價位核算", levels_panel())

    def test_methodology_is_collapsed_and_ohlc_not_displayed(self):
        panel = levels_panel()
        self.assertRegex(panel, r'<details class="source-details">\s*<summary>關鍵價位計算方式與資料來源</summary>')
        self.assertNotRegex(panel, r"(?i)\\bOHLC\\s*[:=]")

    def test_russell_levels_require_cross_checked_same_session_data(self):
        panel = levels_panel()
        self.assertIn("Russell 2000｜2,784.03（+0.11%）", panel)
        self.assertIn("支撐 S1：2,769.43", panel)
        self.assertIn("中樞 P：2,777.18", panel)
        self.assertIn("壓力 R1：2,791.77", panel)
        self.assertIn("ChartExchange 與 Tallac Options 交叉核對", panel)
        self.assertIn("樞紐點計算只使用高、低、收盤價", panel)
        self.assertNotIn("本輪尚未完成同日 OHLC 驗證，暫不發布推算值", panel)

    def test_both_test_masters_render_verified_2026_10_22_levels(self):
        paths = (
            Path("test-masters/index_母版_修正測試_週一.html"),
            Path("test-masters/index_母版_修正測試_週二至週五.html"),
        )
        expected = (
            "支撐 S1：52,608.28", "中樞 P：52,768.08", "壓力 R1：53,027.78",
            "支撐 S1：7,632.88", "中樞 P：7,667.91", "壓力 R1：7,698.46",
            "支撐 S1：25,831.50", "中樞 P：26,095.45", "壓力 R1：26,272.82",
            "支撐 S1：10,552.15", "中樞 P：10,846.24", "壓力 R1：11,026.07",
            "支撐 S1：2,769.43", "中樞 P：2,777.18", "壓力 R1：2,791.77",
        )
        for path in paths:
            with self.subTest(master=path.name):
                self.assertTrue(path.exists(), f"測試母版不存在：{path}")
                html = path.read_text(encoding="utf-8")
                start = html.find(START)
                end = html.find(END, start + len(START))
                self.assertGreaterEqual(start, 0, f"{path.name} 缺少今日關鍵價位面板")
                self.assertGreater(end, start, f"{path.name} 的關鍵價位面板邊界錯誤")
                panel = html[start:end]
                for value in expected:
                    self.assertIn(value, panel, f"{path.name} 缺少已驗證價位：{value}")
                self.assertNotIn("本輪尚未完成同日 OHLC 驗證，暫不發布推算值", panel)
                self.assertNotIn("待更新｜最新交易日價位尚未完成同日資料核對。", panel)
                self.assertIn("費城半導體指數（SOX）", panel)


    def test_both_test_masters_publish_explicit_taiwan_time_news_windows(self):
        monday = Path("test-masters/index_母版_修正測試_週一.html").read_text(encoding="utf-8")
        weekdays = Path("test-masters/index_母版_修正測試_週二至週五.html").read_text(encoding="utf-8")
        self.assertIn("前一個美股交易日12:00至本次實際截稿時間（台灣時間；週末消息一併納入）", monday)
        self.assertIn("前一日12:00至實際截稿時間（台灣時間）", weekdays)
        for html in (monday, weekdays):
            self.assertIn("核對原始發布時間", html, "新聞規則未要求核對原始發布時間")
            self.assertIn("時區", html, "新聞規則未要求核對時區")
            self.assertIn("重複", html, "新聞規則未要求合併重複事件")

    def test_both_test_masters_suppress_stale_commentary_until_same_session_is_verified(self):
        paths = (
            Path("test-masters/index_母版_修正測試_週一.html"),
            Path("test-masters/index_母版_修正測試_週二至週五.html"),
        )
        for path in paths:
            with self.subTest(master=path.name):
                html = path.read_text(encoding="utf-8")
                self.assertIn("市場定調｜待同步核實", html,
                              f"{path.name} 的總結仍可能呈現未核實的舊行情")
                self.assertIn("美股摘要｜待同步核實", html,
                              f"{path.name} 的美股摘要未標示資料待核實")
                self.assertIn("市場觀點｜待同步核實", html,
                              f"{path.name} 的市場觀點未標示資料待核實")
                self.assertIn("2026/10/22 同日 OHLC", html,
                              f"{path.name} 未標示關鍵價位的交易日基準")
                self.assertIn("2026/10/21", html,
                              f"{path.name} 未說明尚未核實的舊資料日期")
                self.assertNotIn("SpaceX 公布上市後首季獲利", html,
                                 f"{path.name} 仍顯示未完成同日核對的舊催化劑")
                self.assertNotIn("① 反彈能否延續", html,
                                 f"{path.name} 仍顯示未完成同日核對的舊市場觀點")
                self.assertIn("今日核心觀察", html)
                self.assertIn("class=\"data-sync-warning\"", html,
                              f"{path.name} 未提示市場報價日期與關鍵價位日期不一致")
                self.assertIn("市場情緒與多數市場報價仍是 2026/10/21", html,
                              f"{path.name} 未明示舊報價日期")
                self.assertIn("今日關鍵價位基準為 2026/10/22", html,
                              f"{path.name} 未明示關鍵價位日期")
                self.assertIn("請勿直接發布", html,
                              f"{path.name} 未阻止未同步母版直接發布")
                self.assertIn("未完成最新交易日及當日催化劑的交叉核對", html,
                              f"{path.name} 未保留核心觀察的資料時效警示")


if __name__ == "__main__":
    unittest.main(verbosity=2)
