import json
from pathlib import Path
import tempfile
import unittest

from scripts.tac_calendar_html_renderer import render


ROOT = Path(__file__).resolve().parents[1]
MONDAY = ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html"
WEEKDAY = ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html"


def econ(event_id, event_date, status="upcoming", name="測試經濟事件"):
    return {
        "id": event_id, "event_date": event_date, "region": "美國",
        "event_name": name, "importance_stars": 5,
        "previous": 1.0, "forecast": 1.2,
        "actual": 1.3 if status == "released" else None,
        "status": status, "time_known": True,
        "impact_judgment": "測試用市場影響判讀",
        "source": {"name": "官方來源", "url": "https://example.com/official"}
    }


def earnings(event_id, event_date, status="upcoming", company="測試公司"):
    return {
        "id": event_id, "event_date": event_date, "company": company,
        "ticker": "TST", "session": "after_market", "status": status,
        "importance_stars": 4, "time_known": True,
        "eps_estimate": 1.2, "eps_actual": 1.3 if status == "released" else None,
        "revenue_estimate": 2.0, "revenue_actual": 2.1 if status == "released" else None,
        "eps_currency": "USD", "revenue_currency": "USD", "revenue_unit": "B",
        "eps_comparison_status": "beat" if status == "released" else None,
        "revenue_comparison_status": "beat" if status == "released" else None,
        "industry": "測試產業", "financial_judgment": "測試財報判讀",
        "stock_price_reaction": "首個交易日收盤上漲",
        "source": {"name": "公司 IR", "url": "https://example.com/ir"},
        "consensus_source": {"name": "市場共識", "url": "https://example.com/consensus"}
    }


class TacCalendarHtmlRendererTests(unittest.TestCase):
    def snapshot(self):
        return {
            "meta": {"report_date": "2026-11-02", "week_id": "2026-W45",
                     "approval_status": "draft", "previous_week_id": "2026-W44"},
            "economic_calendar": [
                econ("today-e", "2026-11-02T23:00:00+08:00", name="當日經濟事件"),
                econ("future-e", "2026-11-03T23:00:00+08:00", name="未來經濟事件"),
                econ("past-e", "2026-10-30T20:30:00+08:00", "released", "已公布經濟事件")
            ],
            "earnings_calendar": [
                earnings("today-r", "2026-11-02T06:00:00+08:00", company="當日財報公司"),
                earnings("future-r", "2026-11-03T06:00:00+08:00", company="未來財報公司")
            ],
            "previous_economic_calendar": [
                econ("archive-e", "2026-10-29T20:30:00+08:00", "released", "上週五星經濟事件")
            ],
            "previous_earnings_calendar": [
                earnings("archive-r", "2026-10-29T06:00:00+08:00", "released", "上週財報公司")
            ]
        }

    def test_monday_render_injects_all_four_sections_and_preserves_other_content(self):
        original = MONDAY.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            snap = Path(td) / "snapshot.json"
            out = Path(td) / "monday-review.html"
            snap.write_text(json.dumps(self.snapshot(), ensure_ascii=False), encoding="utf-8")
            render(str(MONDAY), str(snap), str(out), "monday")
            result = out.read_text(encoding="utf-8")
        self.assertIn('id="last-week-calendar"', result)
        self.assertIn('id="last-week-earnings"', result)
        for phrase in ("當日經濟事件", "未來經濟事件", "已公布經濟事件",
                       "當日財報公司", "未來財報公司", "上週五星經濟事件", "上週財報公司"):
            self.assertIn(phrase, result)
        self.assertIn('id="sp500-earnings-health"', result)
        self.assertEqual(MONDAY.read_text(encoding="utf-8"), original)

    def test_weekday_render_has_no_monday_archive_and_keeps_other_content(self):
        original = WEEKDAY.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            snap = Path(td) / "snapshot.json"
            out = Path(td) / "weekday-review.html"
            snap.write_text(json.dumps(self.snapshot(), ensure_ascii=False), encoding="utf-8")
            render(str(WEEKDAY), str(snap), str(out), "weekday")
            result = out.read_text(encoding="utf-8")
        self.assertNotIn('id="last-week-calendar"', result)
        self.assertNotIn('id="last-week-earnings"', result)
        self.assertIn("當日經濟事件", result)
        self.assertIn("當日財報公司", result)
        self.assertIn('id="sp500-earnings-health"', result)
        self.assertEqual(WEEKDAY.read_text(encoding="utf-8"), original)

    def test_renderer_escapes_untrusted_text(self):
        row = econ("unsafe", "2026-11-02T10:00:00+08:00", name='<script>alert("x")</script>')
        from scripts.tac_calendar_html_renderer import econ_card
        html = econ_card(row)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
