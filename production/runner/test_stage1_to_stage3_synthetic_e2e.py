#!/usr/bin/env python3
"""Synthetic integration test: one Run through Stage 5 and Stage 6 pre-delivery handoff."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "production" / "runner"
sys.path.insert(0, str(RUNNER))

from create_run_fixture import build, stable_run_id, write_run_files
from stage_wr_preflight import stage_wr_preflight
from accept_stage_submission import accept_stage_submission
import run_stage2
import run_stage3
import prepare_stage4_research_bundle
import run_stage4
import run_stage5
import run_stage6
from test_stage4_content_validation import sample as sample_stage4_content
from test_validate_chatgpt_web_observations import make_bundle

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Stage1To3SyntheticE2ETests(unittest.TestCase):
    def _run_full_synthetic_e2e(self, report_date: date, trading_date: date, sample_date: date, expected_current_week: str, expected_previous_week: str | None):
        token = os.environ.get("GITHUB_RUN_ID") or str(900000000 + os.getpid())
        run_id = stable_run_id(report_date, token)
        run_dir = ROOT / "production" / "runs" / run_id
        if run_dir.exists():
            self.fail(f"Refusing to reuse existing synthetic Run directory: {run_dir}")
        original_ref = os.environ.get("GITHUB_REF")
        original_run_id = os.environ.get("GITHUB_RUN_ID")
        os.environ["GITHUB_REF"] = "refs/heads/main"
        os.environ["GITHUB_RUN_ID"] = token
        try:
            result = build(report_date, run_id, trading_date)
            stage1 = write_run_files(run_dir, run_id, result, ROOT)
            context = json.loads((run_dir / "run-context.json").read_text(encoding="utf-8"))
            self.assertEqual(stage1["status"], "PASS")
            self.assertEqual(context["run_id"], run_id)
            self.assertEqual(context["report_date"], report_date.isoformat())
            self.assertEqual(context["trading_date"], trading_date.isoformat())
            if report_date.weekday() == 0:
                self.assertEqual(context["production_date"], "2026-11-28")
                self.assertEqual(context["mother"]["key"], "monday")
            else:
                self.assertEqual(context["mother"]["key"], "weekdays")

            wr = stage_wr_preflight("STAGE_2", context)
            sample_data = json.loads((ROOT / f"production/testdata/report-data-{sample_date.isoformat()}.json").read_text(encoding="utf-8"))
            synthetic_seed = copy.deepcopy(json.loads((run_dir / "stage1-fixture.json").read_text(encoding="utf-8")))
            # Keep current Main source policy/URLs from the blank-first Stage 1 fixture;
            # import only synthetic numeric values from the historical test fixture.
            for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
                for name, item in synthetic_seed[group].items():
                    old_source = (sample_data.get(group, {}).get(name) or {}).get("source") or {}
                    source = item.setdefault("source", {})
                    for field in ("close_value", "history_close", "score_value", "backup_source_score_value",
                                  "daily_change_percent", "history_change", "band"):
                        if old_source.get(field) is not None:
                            source[field] = old_source[field]
            for name, source in synthetic_seed["sector_sources"].items():
                old_source = (sample_data.get("sector_sources") or {}).get(name) or {}
                for field in ("history_close", "history_change"):
                    if old_source.get(field) is not None:
                        source[field] = old_source[field]
            bundle = make_bundle(synthetic_seed)
            # The helper retains a legacy sample report date. Bind the envelope
            # and each observation to this Run before Stage 2 acceptance.
            bundle["report_date"] = context["report_date"]
            bundle["trading_date"] = context["trading_date"]
            for row in bundle["observations"]:
                row["report_date"] = context["report_date"]
                row["trading_date"] = context["trading_date"]
                if row.get("data_date") is not None:
                    row["data_date"] = context["trading_date"]
                if row.get("group") in ("energy", "metals"):
                    row["contract_label"] = sample_data[row["group"]][row["name"]].get("contract_label")
            bundle.update({
                "schema_version": "1.1",
                "run_id": run_id,
                "stage1_receipt_sha256": digest(run_dir / "stage1-receipt.json"),
                "run_context_sha256": digest(run_dir / "run-context.json"),
                "stage1_fixture_sha256": digest(run_dir / "stage1-fixture.json"),
                "stage2_wr_sha256": wr["wr_sha256"],
            })
            bundle["fedwatch"] = {
                "status": "SOURCE_NO_DATA",
                "source_name": "Investing.com Fed Rate Monitor",
                "source_url": "https://www.investing.com/central-banks/fed-rate-monitor",
                "report_date": context["report_date"],
                "trading_date": context["trading_date"],
                "captured_at_utc": bundle["captured_at_utc"],
                "target_meeting": None,
                "current_target_range": None,
                "updated_at_tw": None,
                "probabilities": [],
                "web_reader_ref": None,
                "web_line_start": None,
                "web_line_end": None,
                "reason": "Synthetic E2E fixture; no live FedWatch read was performed.",
                "stage2_wr_sha256": wr["wr_sha256"],
            }
            observation_path = run_dir / "market-history-web-observations.json"
            observation_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            submitted = accept_stage_submission(run_dir, "STAGE_2")
            self.assertEqual(submitted["status"], "SUBMITTED")
            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")

            with patch.object(run_stage2, "append_chart3_sp500_increment", return_value={"status": "SKIPPED_SYNTHETIC_E2E"}):
                with patch.object(sys, "argv", ["run_stage2.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                    run_stage2.main()

            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_2"]["status"], "PASS")
            stage2_receipt = json.loads((run_dir / "stage2-market-snapshot-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(stage2_receipt["run_id"], run_id)
            self.assertEqual(stage2_receipt["row_count"], 44)
            self.assertEqual(stage2_receipt["pending_count"], 0)

            with patch.object(sys, "argv", ["run_stage3.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                run_stage3.main()

            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_3"]["status"], "PASS")
            stage3_receipt = json.loads((run_dir / "stage3-calendar-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(stage3_receipt["run_id"], run_id)
            self.assertEqual(stage3_receipt["current_week"]["week_id"], expected_current_week)
            self.assertEqual(stage3_receipt["current_week"]["week_id"], "2026-W49" if report_date.weekday() == 0 else "2026-W48")
            self.assertEqual(stage3_receipt["current_week"]["path"], f"data/calendar/weeks/{expected_current_week}.json")
            if expected_previous_week:
                self.assertEqual(stage3_receipt["previous_week"]["week_id"], "2026-W48")
                self.assertEqual(stage3_receipt["previous_week"]["path"], "data/calendar/weeks/2026-W48.json")
            else:
                self.assertIsNone(stage3_receipt["previous_week"])
            if expected_previous_week is None:
                self.assertIsNone(stage3_receipt["previous_week"])
            else:
                self.assertEqual(stage3_receipt["previous_week"]["week_id"], expected_previous_week)
            self.assertEqual(state["last_passed_stage"], "STAGE_3")

            with patch.object(sys, "argv", ["prepare_stage4_research_bundle.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                prepare_stage4_research_bundle.main()
            bundle_receipt = json.loads((run_dir / "stage4-research-bundle-receipt.json").read_text(encoding="utf-8"))
            stage4_wr = stage_wr_preflight("STAGE_4", context)
            wr_path = ROOT / "production" / "stages" / "STAGE_4_NEWS_ANALYSIS.md"
            wr_text = wr_path.read_bytes().decode("utf-8")
            capture = {
                "schema_version": "1.0",
                "status": "AWAITING_EDITORIAL_INPUT",
                "stage4_work_instructions": {
                    "path": "production/stages/STAGE_4_NEWS_ANALYSIS.md",
                    "sha256": stage4_wr["wr_sha256"],
                    "git_blob_sha": stage4_wr["wr_git_blob_sha"],
                    "full_text": wr_text,
                },
                "run_id": run_id,
                "report_date": context["report_date"],
                "trading_date": context["trading_date"],
                "market_snapshot_sha256": bundle_receipt["market_snapshot_sha256"],
                "stage3_receipt_sha256": digest(run_dir / "stage3-calendar-receipt.json"),
                "stage2_status": stage2_receipt["status"],
                "stage2_pending_rows": stage2_receipt.get("pending_rows", []),
                "capture_trigger": {"event_name": "synthetic_e2e", "dispatch_mode": "synthetic", "workflow_run_id": token},
            }
            (run_dir / "capture-stage-receipt.json").write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            editorial = sample_stage4_content()
            for key in ("summary_title", "summary_points", "focus_news", "headlines", "sentiment",
                        "market_analysis", "political_scan", "core_observation", "observation",
                        "key_levels", "market_comments", "warning_note", "quality_note"):
                editorial[key] = copy.deepcopy(sample_data[key])
            editorial.update({
                "run_id": run_id,
                "report_date": context["report_date"],
                "trading_date": context["trading_date"],
                "market_snapshot_sha256": bundle_receipt["market_snapshot_sha256"],
                "research_bundle_sha256": bundle_receipt["bundle_sha256"],
                "stage3_receipt_sha256": digest(run_dir / "stage3-calendar-receipt.json"),
                "stage4_wr_sha256": stage4_wr["wr_sha256"],
                "news_cutoff_taipei": f"{report_date.isoformat()} 05:25",
            })
            editorial["core_observation"] = {
                "heading": "本週三大觀察焦點",
                "text": "以下三點為合成資料，僅驗證今日核心觀察模組的三個固定項目。",
                "points": [
                    {"label": "① 市場廣度", "text": "觀察指數反彈是否擴散至更多產業與成分股。"},
                    {"label": "② 利率定價", "text": "追蹤公債殖利率與風險資產估值的互動。"},
                    {"label": "③ 風險控制", "text": "依波動度與信用條件調整部位及槓桿。"},
                    {"label": "④ 跨市場訊號", "text": "比較美元、商品與亞洲市場走勢是否一致。"},
                ],
            }
            editorial["observation"] = {
                "heading": "盤面觀察重點",
                "text": "合成測試觀察：市場反彈、產業輪動與風險指標僅用於驗證五個固定觀察槽位的完整交接。",
                "points": [
                    {"label": "市場廣度", "text": "觀察主要指數反彈是否擴散至更多產業與成分股。"},
                    {"label": "利率定價", "text": "追蹤美債殖利率變化是否支持風險資產估值。"},
                    {"label": "產業輪動", "text": "確認大型科技股以外的產業是否跟進。"},
                    {"label": "跨市場訊號", "text": "比較美元、商品與亞洲市場走勢是否一致。"},
                    {"label": "風險控制", "text": "以波動度與信用壓力決定部位調整節奏。"},
                ],
            }
            for item in editorial["focus_news"] + editorial["headlines"]:
                item["published_at_tw"] = f"{trading_date.isoformat()} 13:00"
                item["published_at_source"] = trading_date.strftime("%b %d, %Y 1:00 PM")
                item["updated_at_source"] = trading_date.strftime("%b %d, %Y 1:10 PM")
                item["publisher"] = item.get("publisher") or "Synthetic E2E source"
            editorial["market_comments"]["global_markets"] = editorial["market_comments"]["global_markets"][:3]
            # Synthetic same-day cash-index OHLC used only to exercise the pivot-level schema;
            # values are deterministic transformations of the synthetic closes, not market observations.
            key_level_specs = [
                ("dow", "道瓊工業指數", "道瓊工業指數"),
                ("sp500", "標普500指數", "S&P 500"),
                ("nasdaq", "那斯達克綜合指數", "Nasdaq Composite"),
                ("sox", "費城半導體指數", "費城半導體指數（SOX）"),
                ("russell2000", "羅素2000指數", "Russell 2000"),
            ]
            synthetic_levels = []
            q = Decimal("0.01")
            for key, market_name, display_name in key_level_specs:
                close = Decimal(sample_data["global_markets"][market_name]["source"]["close_value"].replace(",", ""))
                open_value = (close * Decimal("0.999")).quantize(q, rounding=ROUND_HALF_UP)
                high = (close * Decimal("1.002")).quantize(q, rounding=ROUND_HALF_UP)
                low = (close * Decimal("0.998")).quantize(q, rounding=ROUND_HALF_UP)
                pivot = (high + low + close) / Decimal(3)
                s1 = Decimal(2) * pivot - high
                s2 = pivot - (high - low)
                r1 = Decimal(2) * pivot - low
                r2 = pivot + (high - low)
                source_url = synthetic_seed["global_markets"][market_name]["source"]["url"]
                synthetic_levels.append({
                    "key": key, "name": display_name, "trading_date": context["trading_date"],
                    "quote_type": "cash_index",
                    "ohlc": f"O {open_value}｜H {high}｜L {low}｜C {close}",
                    "s2": str(s2.quantize(q, rounding=ROUND_HALF_UP)),
                    "s1": str(s1.quantize(q, rounding=ROUND_HALF_UP)),
                    "p": str(pivot.quantize(q, rounding=ROUND_HALF_UP)),
                    "r1": str(r1.quantize(q, rounding=ROUND_HALF_UP)),
                    "r2": str(r2.quantize(q, rounding=ROUND_HALF_UP)),
                    "source_name": "Investing.com｜合成測試資料，非實際行情",
                    "url": source_url,
                })
            editorial["key_levels"] = {
                "baseline_date": context["trading_date"],
                "trading_date": context["trading_date"],
                "captured_at_taipei": f"{report_date.isoformat()} 05:00:00",
                "formula": "Synthetic test fixture: pivot levels calculated from deterministic OHLC derived from synthetic close values.",
                "items": synthetic_levels,
            }
            editorial["market_analysis"]["markets"]["paragraphs"].append("Fear & Greed 指數採 FGScore 備援來源，讀值 17；此為合成測試資料的來源揭露。")
            editorial["market_analysis"]["strategy"]["paragraphs"].extend([
                "基準情境：維持核心持倉並觀察市場廣度、現金流與信用條件。",
                "風險情境：若波動率及信用利差同步上升，降低高Beta與槓桿曝險。",
                "嚴重情境：若政策與流動性風險擴大，優先保留現金並分散單一市場風險。",
            ])
            editorial["political_scan"]["checked_at"] = f"{report_date.isoformat()}T05:00:00+08:00"
            for finding in editorial["political_scan"]["findings"]:
                finding["checked_at"] = "2026-11-24T05:00:00+08:00"
                if isinstance(finding.get("transmission"), dict):
                    finding["transmission"] = "；".join(str(value) for value in finding["transmission"].values())
            for layer in editorial["market_analysis"].values():
                for source in layer["sources"]:
                    source["checked_at"] = "2026-11-24T05:00:00+08:00"
            editorial_path = run_dir / "stage4-editorial-content.json"
            editorial_path.write_text(json.dumps(editorial, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            submitted4 = accept_stage_submission(run_dir, "STAGE_4")
            self.assertEqual(submitted4["status"], "SUBMITTED")

            with patch.object(sys, "argv", ["run_stage4.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                run_stage4.main()
            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_4"]["status"], "PASS")
            self.assertEqual(state["last_passed_stage"], "STAGE_4")
            stage4_receipt = json.loads((run_dir / "stage4-analysis-receipt.json").read_text(encoding="utf-8"))
            self.assertTrue(stage4_receipt["market_snapshot_unchanged"])
            self.assertEqual(stage4_receipt["editorial_run_binding"]["run_id"], run_id)

            try:
                with patch.object(sys, "argv", ["run_stage5.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                    run_stage5.main()
            except Exception as exc:
                diagnostics = []
                for log_path in run_dir.glob("qa-*.log"):
                    diagnostics.append(f"\n--- {log_path.name} ---\n{log_path.read_text(encoding='utf-8', errors='replace')}")
                raise AssertionError(f"Stage 5 synthetic E2E failed: {exc}" + "".join(diagnostics)) from exc
            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_5"]["status"], "PASS")
            self.assertEqual(state["last_passed_stage"], "STAGE_5")
            stage5_receipt = json.loads((run_dir / "stage5-render-qa-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(stage5_receipt["status"], "REVIEW_READY")
            self.assertTrue((run_dir / "review.html").is_file())
            self.assertTrue((run_dir / "qa-sidecar.json").is_file())

            # Stage 6 pre-delivery integration: validate its own pinned WR and
            # the exact Stage 5 HTML/QA/render/Stage 4 receipt bindings without
            # creating a Git worktree, publishing Pages, or mutating Run state.
            stage6_wr = stage_wr_preflight("STAGE_6", context)
            self.assertEqual(stage6_wr["status"], "PASS")
            from stage_wr_preflight import require_stage_wr_receipt
            require_stage_wr_receipt(stage5_receipt, "STAGE_5", context)
            qa_doc = json.loads((run_dir / "qa-sidecar.json").read_text(encoding="utf-8"))
            render_doc = json.loads((run_dir / "render-manifest.json").read_text(encoding="utf-8"))
            run_stage6.validate_stage5_handoff(
                stage5_receipt, qa_doc, render_doc, context,
                digest(run_dir / "review.html"), digest(run_dir / "render-manifest.json"),
                stage4_receipt, digest(run_dir / "stage4-analysis-receipt.json")
            )
            self.assertEqual(
                run_stage6.allowed_paths(context["report_date"], context),
                [
                    f"preview/main/{context['report_date']}-review.html",
                    f"preview/main/{context['report_date']}-review.qa.json",
                    f"preview/main/{context['report_date']}-review.delivery.json",
                ]
            )
            state_after_stage6_preflight = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state_after_stage6_preflight["stages"]["STAGE_6"]["status"], "READY")
            self.assertFalse((run_dir / "stage6-delivery-receipt.json").exists())
        finally:
            import shutil
            shutil.rmtree(run_dir, ignore_errors=True)
            if original_ref is None:
                os.environ.pop("GITHUB_REF", None)
            else:
                os.environ["GITHUB_REF"] = original_ref
            if original_run_id is None:
                os.environ.pop("GITHUB_RUN_ID", None)
            else:
                os.environ["GITHUB_RUN_ID"] = original_run_id

    def test_weekday_run_stage1_to_stage6_pre_delivery(self):
        self._run_full_synthetic_e2e(
            report_date=date(2026, 11, 24), trading_date=date(2026, 11, 23),
            sample_date=date(2026, 11, 24), expected_current_week="2026-W48",
            expected_previous_week=None
        )

    def test_saturday_to_monday_run_stage1_to_stage6_pre_delivery(self):
        self._run_full_synthetic_e2e(
            report_date=date(2026, 11, 30), trading_date=date(2026, 11, 27),
            sample_date=date(2026, 11, 24), expected_current_week="2026-W49",
            expected_previous_week="2026-W48"
        )

if __name__ == "__main__":
    unittest.main()
