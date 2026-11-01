#!/usr/bin/env python3
"""Build deterministic visual-regression HTML from approved TAC templates.

All market values are explicitly synthetic and used only to exercise the renderer.
Calendar cards come from the checked-in weekly JSON and the approved adapter.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from assemble_tac_calendar_snapshot import build_calendar_snapshot
from render_tac_market_safe import render_market_html
from validate_tac_daily_snapshot import load_validator, sample_snapshot

BINDING_PATH = ROOT / "scripts/tac_html_binding_map.json"
SCHEMA_PATH = ROOT / "schemas/tac-daily-market-snapshot.schema.json"
CURRENT_PATH = ROOT / "data/calendar/weeks/2026-W45.json"
PREVIOUS_PATH = ROOT / "data/calendar/weeks/2026-W44.json"
TEMPLATES = {
    "monday": ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "weekday": ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
}
OUT = ROOT / "artifacts/tac-visual-regression"

def build():
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    _validator, _ = load_validator()
    current = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))
    previous = json.loads(PREVIOUS_PATH.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    for kind, template_path in TEMPLATES.items():
        template = template_path.read_text(encoding="utf-8")
        snapshot = sample_snapshot(schema)
        snapshot["meta"].update({
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "generated_at": "2026-11-02T05:00:00+08:00",
        })
        # Synthetic display-only figures: no synthetic figure is represented as
        # a real market observation or used in the actual daily report.
        for group_name, records in snapshot.items():
            if group_name not in {"global_indices", "sectors", "bonds", "fx", "energy", "precious_metals"}:
                continue
            for index, record in enumerate(records.values()):
                record["value"] = f"{42000 + index * 137.25:,.2f}"
                record["change"] = f"{'+' if index % 2 == 0 else '-'}{0.12 + index * 0.03:.2f}%"
        snapshot["risk_indicators"] = {
            "vix": {"value": "18.42", "change": "+1.25%"},
            "move": {"value": "96.80", "change": "-0.72%"},
            "cnn_fear_greed": {"value": "54.0"},
        }
        snapshot["fedwatch"] = {
            "probabilities": {
                "hold": {"probability": 80.0, "rate_range": "3.50%–3.75%"},
                "hike_one": {"probability": 20.0, "rate_range": "3.75%–4.00%"},
            },
            "target_meeting": "2026-12-09",
            "updated_at": "2026-11-02 05:00（合成視覺測試）",
            "target_rate_range": "3.50%–3.75%",
            "audit_text": "此處為合成視覺回歸資料，非 CME 即時機率。",
            "aria_label": "合成測試：維持不變 80%，升息一碼 20%",
        }
        report_date = "2026-11-02" if kind == "monday" else "2026-11-03"
        calendar = build_calendar_snapshot(
            current, previous if kind == "monday" else None,
            report_date, template, binding
        )
        snapshot.update(calendar)
        rendered = render_market_html(template, snapshot, binding)
        path = OUT / f"{kind}.html"
        path.write_text(rendered, encoding="utf-8")
        print(f"PASS: {kind} rendered to {path.relative_to(ROOT)}")
    print("NOTE: Market values are synthetic visual-test fixtures only.")

if __name__ == "__main__":
    build()
