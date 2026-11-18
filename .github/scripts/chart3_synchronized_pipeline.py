#!/usr/bin/env python3
"""One-command, explicit-CSV entry point for the isolated Chart 3 research release.

This script never downloads data. The CSV must be supplied by the operator.
Import outputs are staging inputs; the active manifest advances only if all
five native series pass the synchronized release runner's validation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from prepare_sp500_research_import import convert, DEFAULT_COMPACT_PATH, DEFAULT_PROVENANCE_PATH
from run_tac_chart3_synchronized_release import run as run_release

def run_pipeline(csv_path: Path, source_url: str, retrieved_at: str,
                 fred_dataset: Path, compact_path: Path, provenance_path: Path,
                 release_dir: Path, status_path: Path,
                 date_column: str = "Date", close_column: str = "Price") -> dict:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Supplied Investing.com CSV does not exist: {csv_path}")
    if not fred_dataset.is_file():
        status = {"status": "BLOCKED_MISSING_INPUT", "missing_inputs": [str(fred_dataset)],
                  "published": False, "last_good_preserved": True}
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        return {"import": None, "release_exit_code": 2, "status": status}
    imported = convert(csv_path, compact_path, provenance_path, source_url, retrieved_at,
                       date_column=date_column, close_column=close_column)
    rc = run_release(fred_dataset, compact_path, provenance_path, release_dir, status_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    return {"import": imported, "release_exit_code": rc, "status": status,
            "release_manifest": str(release_dir / "active_manifest.json")}

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument("--retrieved-at", required=True)
    p.add_argument("--fred-dataset", type=Path, default=Path("data/tac-chart3/chart3_market_stress.json"))
    p.add_argument("--compact", type=Path, default=DEFAULT_COMPACT_PATH)
    p.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE_PATH)
    p.add_argument("--release-dir", type=Path, default=Path("data/tac-chart3/synchronized"))
    p.add_argument("--status", type=Path, default=Path("data/tac-chart3/synchronized_status.json"))
    p.add_argument("--date-column", default="Date")
    p.add_argument("--close-column", default="Price")
    a = p.parse_args()
    result = run_pipeline(a.csv, a.source_url, a.retrieved_at, a.fred_dataset,
                          a.compact, a.provenance, a.release_dir, a.status,
                          a.date_column, a.close_column)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result["release_exit_code"])

if __name__ == "__main__":
    main()

# QA-triggering no-op: keep this entry point covered by the research workflow.
