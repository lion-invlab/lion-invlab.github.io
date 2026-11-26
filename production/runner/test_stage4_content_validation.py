#!/usr/bin/env python3
import unittest
from run_stage4 import validate_content, market_snapshot_digest

DOMAINS=["us_policy","us_china","geopolitics","trade_sanctions","major_economies","energy_resources"]
LAYERS=("political","policy_industry","macro","markets","strategy")

def sample():
    def news(i):
        return {"id":f"n{i}","title":f"測試新聞標題{i}","summary":"這是一段足夠長的測試摘要，用來驗證新聞內容欄位、時間窗口與來源網址均可正確通過。","url":f"https://example.com/news/{i}","published_at_tw":"2026-11-25 13:00","published_at_source":"Nov 25 2026 1:00 PM","source_timezone":"Asia/Taipei","publisher":"Test publisher","updated_at_source":"原文未標示","updated_at_source":"Nov 25 2026 1:10 PM"}
    return {
      "run_id":"TAC-2026-11-26-test-1","market_snapshot_sha256":"PLACEHOLDER","report_date":"2026-11-26","trading_date":"2026-11-25","news_cutoff_taipei":"2026-11-26 05:25",
      "summary_title":"市場測試主題與風險觀察","summary_points":[{"label":f"重點{i}","text":"這是一段長度足夠的測試總結文字，用來驗證三段摘要格式。"} for i in range(3)],
      "focus_news":[news(i) for i in range(5)],"headlines":[news(i+10) for i in range(10)],
      "sentiment":"市場情緒測試文字長度足夠。Fear & Greed 待核實，不沿用舊值。",
      "market_analysis":{k:{"paragraphs":["這是一段足夠長的市場分析文字，說明傳導機制與觀察條件。"+(" Fear & Greed 待核實。" if k=="markets" else "")],"sources":[{"label":f"{k} source","url":f"https://example.com/{k}","status":"VERIFIED","checked_at":"2026-11-26T05:00:00+08:00"}]} for k in LAYERS},
      "political_scan":{"checked_at":"2026-11-26T05:00:00+08:00","domains_checked":DOMAINS,"findings":[],"no_material_change_note":"六個政治領域均已掃描，沒有新增重大且可核實的政策變化。"},
      "core_observation":{"heading":"今日核心觀察","text":"主要市場焦點仍須等待收盤數據與政策傳導進一步確認。","points":[{"label":f"焦點{i}","text":"這是一段足夠長的觀察內容。"} for i in range(4)]},
      "observation":{"text":"今日先觀察市場廣度、殖利率及風險偏好是否同步改善。"},
      "key_levels":{"items":[]},"market_comments":{"global_markets":["美國市場測試評論內容足夠長，並描述當日市場方向與主要推動因素。","亞洲市場測試評論內容足夠長，並描述當日市場方向與主要推動因素。","歐洲市場測試評論內容足夠長，並描述當日市場方向與主要推動因素。"],"sectors":"","bonds":"","fx":"","energy":"","metals":"","risk":""}
    }

class Stage4ContentTests(unittest.TestCase):
    def setUp(self):
        self.context={"run_id":"TAC-2026-11-26-test-1","report_date":"2026-11-26","trading_date":"2026-11-25"}
        self.data={"global_markets":{},"bonds":{},"fx":{},"energy":{},"metals":{},"risk":{"fear_greed":{"display":"待核實","source":{"verification_status":"PENDING"}}}}
    def test_valid_three_summary_five_ten_and_five_layers(self):
        x=sample();x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        result=validate_content(x,self.context,self.data)
        self.assertEqual(result["news_counts"],{"focus_news":5,"headlines":10})
    def test_rejects_news_outside_shared_window(self):
        x=sample();x["market_snapshot_sha256"]=market_snapshot_digest(self.data);x["focus_news"][0]["published_at_tw"]="2026-11-25 11:59"
        with self.assertRaisesRegex(ValueError,"outside the report window"):validate_content(x,self.context,self.data)
    def test_rejects_analysis_using_unverified_market_row(self):
        x=sample();self.data["global_markets"]={"SP500":{"source":{"verification_status":"PENDING"}}};x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        x["market_analysis"]["markets"]["supporting_market_rows"]=[{"group":"global_markets","name":"SP500"}]
        with self.assertRaisesRegex(ValueError,"non-verified market row"):validate_content(x,self.context,self.data)

if __name__=="__main__":unittest.main()
