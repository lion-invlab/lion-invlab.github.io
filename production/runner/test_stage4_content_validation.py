#!/usr/bin/env python3
import unittest
from run_stage4 import validate_content, market_snapshot_digest, validate_research_bundle_binding, validate_stage4_wr_handoff, normalize_news_publication_times
import json, tempfile
from pathlib import Path

DOMAINS=["us_policy","us_china","geopolitics","trade_sanctions","major_economies","energy_resources"]
LAYERS=("political","policy_industry","macro","markets","strategy")

def sample():
    def news(i):
        return {"id":f"n{i}","title":f"測試新聞標題{i}","summary":"這是一段足夠長的測試摘要，用來驗證新聞內容欄位、時間窗口與來源網址均可正確通過。","url":f"https://example.com/news/{i}","published_at_tw":"2026-11-25 13:00","published_at_source":"Nov 25 2026 1:00 PM","source_timezone":"Asia/Taipei","publisher":"Test publisher","updated_at_source":"原文未標示","updated_at_source":"Nov 25 2026 1:10 PM"}
    return {
      "run_id":"TAC-2026-11-26-test-1","market_snapshot_sha256":"PLACEHOLDER","research_bundle_sha256":"a"*64,"stage3_receipt_sha256":"b"*64,"stage4_wr_sha256":"f"*64,"report_date":"2026-11-26","trading_date":"2026-11-25","news_cutoff_taipei":"2026-11-26 05:25",
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
    def test_source_timezone_is_authoritative_for_taipei_publication_time(self):
        content={"focus_news":[{"published_at_source":"2026-11-27 07:24 PM AEDT",
                                "source_timezone":"Australia/Sydney",
                                "published_at_tw":"2026-11-28 16:24"}],"headlines":[]}
        repairs=normalize_news_publication_times(content)
        self.assertEqual(content["focus_news"][0]["published_at_tw"],"2026-11-27 16:24")
        self.assertEqual(len(repairs),1)
    def setUp(self):
        self.context={"run_id":"TAC-2026-11-26-test-1","report_date":"2026-11-26","trading_date":"2026-11-25"}
        self.data={"global_markets":{},"bonds":{},"fx":{},"energy":{},"metals":{},"risk":{"fear_greed":{"display":"待核實","source":{"verification_status":"PENDING"}}}}
    def test_stage4_wr_handoff_requires_full_exact_text(self):
        import hashlib
        text = "# Stage 4\nFull rules\n"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        blob = "a" * 40
        capture = {"status":"AWAITING_EDITORIAL_INPUT","stage4_work_instructions":{
            "path":"production/stages/STAGE_4_NEWS_ANALYSIS.md","full_text":text,
            "sha256":digest,"git_blob_sha":blob}}
        editorial = {"stage4_wr_sha256":digest}
        preflight = {"wr_sha256":digest,"wr_git_blob_sha":blob}
        attestation = validate_stage4_wr_handoff(capture,editorial,preflight)
        self.assertEqual(attestation["status"],"PASS")
        self.assertEqual(attestation["stage4_wr_sha256"],digest)
        editorial["stage4_wr_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError,"attestation"):
            validate_stage4_wr_handoff(capture,editorial,preflight)

    def test_valid_three_summary_five_ten_and_five_layers(self):
        x=sample();x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        result=validate_content(x,self.context,self.data)
        self.assertEqual(result["news_counts"],{"focus_news":5,"headlines":10})

    def test_monday_report_uses_saturday_production_news_window_and_exact_bundle_cutoff(self):
        x=sample()
        ctx={"run_id":"TAC-2026-11-30-saturday-run","report_date":"2026-11-30","trading_date":"2026-11-27"}
        x["run_id"]=ctx["run_id"];x["report_date"]=ctx["report_date"];x["trading_date"]=ctx["trading_date"]
        x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        x["news_cutoff_taipei"]="2026-11-28 05:12"
        x["core_observation"]["details"]="週末市場回顧與本週觀察補充段落。"
        for item in x["focus_news"]+x["headlines"]:
            item["published_at_tw"]="2026-11-27 13:00"
        bundle={"news_window":{"target_cutoff_taipei":"2026-11-28 05:12"}}
        result=validate_content(x,ctx,self.data,bundle)
        self.assertEqual(result["cutoff"].strftime("%Y-%m-%d %H:%M"),"2026-11-28 05:12")
        x["news_cutoff_taipei"]="2026-11-28 05:15"
        with self.assertRaisesRegex(ValueError,"exactly match the Saturday Stage 4 bundle cutoff"):
            validate_content(x,ctx,self.data,bundle)

    def test_rejects_news_outside_shared_window(self):
        x=sample();x["market_snapshot_sha256"]=market_snapshot_digest(self.data);x["focus_news"][0]["published_at_tw"]="2026-11-25 11:59"
        with self.assertRaisesRegex(ValueError,"outside the report window"):validate_content(x,self.context,self.data)
    def test_research_bundle_binding_requires_exact_run_snapshot_and_bytes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as td:
            path=Path(td)/"bundle.json"
            bundle={"run_id":self.context["run_id"],"report_date":self.context["report_date"],"trading_date":self.context["trading_date"],"market_snapshot_sha256":market_snapshot_digest(self.data)}
            path.write_text(json.dumps(bundle),encoding="utf-8")
            digest=__import__("hashlib").sha256(path.read_bytes()).hexdigest()
            content={"research_bundle_sha256":digest,"market_snapshot_sha256":bundle["market_snapshot_sha256"]}
            receipt={"status":"PASS","run_id":self.context["run_id"],"report_date":self.context["report_date"],
                     "market_snapshot_sha256":bundle["market_snapshot_sha256"],"trading_date":self.context["trading_date"],"bundle_sha256":digest}
            result=validate_research_bundle_binding(content,self.context,receipt,path)
            self.assertEqual(result["sha256"],digest)
            content["research_bundle_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"differs from capture receipt"):
                validate_research_bundle_binding(content,self.context,receipt,path)
    def test_rejects_http_source_in_political_scan(self):
        x=sample();x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        x["political_scan"]["findings"]=[{"title":"政策測試","domain":"us_policy","classification":"political_statement","source_url":"http://example.com/policy","published_at":"2026-11-25T12:00:00+08:00","checked_at":"2026-11-26T05:00:00+08:00","transmission":"政策表態尚未生效，暫不視為正式政策衝擊。"}]
        with self.assertRaisesRegex(ValueError,"HTTPS source"): validate_content(x,self.context,self.data)

    def test_rejects_political_finding_outside_six_domains(self):
        x=sample();x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        x["political_scan"]["findings"]=[{"title":"政策測試","domain":"unknown_domain","classification":"political_statement","source_url":"https://example.com/policy","published_at":"2026-11-25T12:00:00+08:00","checked_at":"2026-11-26T05:00:00+08:00","transmission":"政策表態尚未生效，暫不視為正式政策衝擊。"}]
        with self.assertRaisesRegex(ValueError,"recognized domain"): validate_content(x,self.context,self.data)

    def test_research_bundle_binding_rejects_cross_run_receipt(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as td:
            path=Path(td)/"bundle.json"
            bundle={"run_id":self.context["run_id"],"report_date":self.context["report_date"],"trading_date":self.context["trading_date"],"market_snapshot_sha256":market_snapshot_digest(self.data)}
            path.write_text(json.dumps(bundle),encoding="utf-8")
            digest=__import__("hashlib").sha256(path.read_bytes()).hexdigest()
            content={"research_bundle_sha256":digest,"market_snapshot_sha256":bundle["market_snapshot_sha256"]}
            receipt={"status":"PASS","run_id":"TAC-OTHER-RUN","report_date":self.context["report_date"],"market_snapshot_sha256":bundle["market_snapshot_sha256"],"trading_date":self.context["trading_date"],"bundle_sha256":digest}
            with self.assertRaisesRegex(ValueError,"not bound to this Run"): validate_research_bundle_binding(content,self.context,receipt,path)

    def test_research_bundle_binding_rejects_bundle_snapshot_mismatch(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]) as td:
            path=Path(td)/"bundle.json"
            bundle={"run_id":self.context["run_id"],"report_date":self.context["report_date"],"trading_date":self.context["trading_date"],"market_snapshot_sha256":"f"*64}
            path.write_text(json.dumps(bundle),encoding="utf-8")
            digest=__import__("hashlib").sha256(path.read_bytes()).hexdigest()
            content={"research_bundle_sha256":digest,"market_snapshot_sha256":market_snapshot_digest(self.data)}
            receipt={"status":"PASS","run_id":self.context["run_id"],"report_date":self.context["report_date"],"market_snapshot_sha256":content["market_snapshot_sha256"],"trading_date":self.context["trading_date"],"bundle_sha256":digest}
            with self.assertRaisesRegex(ValueError,"not bound to the exact Run"): validate_research_bundle_binding(content,self.context,receipt,path)

    def test_rejects_analysis_using_unverified_market_row(self):
        x=sample();self.data["global_markets"]={"SP500":{"source":{"verification_status":"PENDING"}}};x["market_snapshot_sha256"]=market_snapshot_digest(self.data)
        x["market_analysis"]["markets"]["supporting_market_rows"]=[{"group":"global_markets","name":"SP500"}]
        with self.assertRaisesRegex(ValueError,"non-verified market row"):validate_content(x,self.context,self.data)

if __name__=="__main__":unittest.main()
