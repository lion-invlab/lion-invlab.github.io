#!/usr/bin/env python3
import json, unittest
from pathlib import Path
from run_stage4 import validate_content

ROOT=Path(__file__).resolve().parents[2]

class Stage4SimCompatibilityTests(unittest.TestCase):
    def test_current_sim14_editorial_fixture_matches_main_stage4_contract(self):
        path=ROOT/"production/testdata/report-content-2026-11-26.json"
        content=json.loads(path.read_text(encoding="utf-8"))
        context={"report_date":"2026-11-26","trading_date":"2026-11-25"}
        data={"global_markets":{},"bonds":{},"fx":{},"energy":{},"metals":{},"risk":{},"sectors":{},"sector_sources":{}}
        result=validate_content(content,context,data)
        self.assertEqual(result["news_counts"],{"focus_news":5,"headlines":10})
        self.assertEqual(len(content["political_scan"]["findings"]),6)
        self.assertEqual(len(content["market_analysis"]),5)
        self.assertEqual(content["core_observation"]["points"].__len__(),4)

if __name__=="__main__":unittest.main()
