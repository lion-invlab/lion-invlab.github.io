#!/usr/bin/env python3
"""One-command TAC report/D4 -> S&P 500 append -> history merge -> five-series release.

This pipeline consumes an existing machine-readable TAC capture. It does not
fetch Yahoo Finance or any other market data itself.
"""
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
from import_sp500_from_d4_capture import build_record, append_record
from merge_sp500_existing_history_with_d4_incremental import merge
from run_tac_chart3_synchronized_release import run as run_release

def write_status(path: Path, status: str, **details):
    obj = {
        "status": status,
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "published": False,
        "last_good_preserved": True,
        **details
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return obj

def run_pipeline(capture_path: Path,
                 fred_dataset: Path = Path("data/tac-chart3/chart3_market_stress.json"),
                 baseline: Path = Path("data/tac-chart3/sp500_daily_close_1927-2026.compact.json"),
                 append_jsonl: Path = Path("data/tac-chart3/sp500_tac_d4_close.jsonl"),
                 compact: Path = Path("data/tac-chart3/sp500_tac_d4_merged.compact.json"),
                 provenance: Path = Path("data/tac-chart3/sp500_tac_d4_merged.provenance.json"),
                 release_dir: Path = Path("data/tac-chart3/synchronized"),
                 status_path: Path = Path("data/tac-chart3/synchronized_status.json")) -> dict:
    missing = [str(p) for p in (capture_path, fred_dataset, baseline) if not p.is_file()]
    if missing:
        status = write_status(status_path, "BLOCKED_MISSING_INPUT", missing_inputs=missing)
        return {"status": status, "exit_code": 2, "import_status": None}

    try:
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        record = build_record(capture)
        import_status = append_record(append_jsonl, record)
        merged = merge(baseline, append_jsonl, compact, provenance)
    except Exception as exc:
        status = write_status(status_path, "BLOCKED_VALIDATION_FAILURE", reason=str(exc),
                              observation_date=(record.get("observation_date") if "record" in locals() else None))
        return {"status": status, "exit_code": 2, "import_status": None}

    rc = run_release(fred_dataset, compact, provenance, release_dir, status_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    return {
        "status": status,
        "exit_code": rc,
        "import_status": import_status,
        "merged_history": merged,
        "release_manifest": str(release_dir / "active_manifest.json")
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", type=Path, required=True,
                   help="TAC D4 capture or report-data JSON with an explicit retrieval/capture timestamp")
    p.add_argument("--fred-dataset", type=Path, default=Path("data/tac-chart3/chart3_market_stress.json"))
    p.add_argument("--baseline", type=Path, default=Path("data/tac-chart3/sp500_daily_close_1927-2026.compact.json"))
    p.add_argument("--append-jsonl", type=Path, default=Path("data/tac-chart3/sp500_tac_d4_close.jsonl"))
    p.add_argument("--compact", type=Path, default=Path("data/tac-chart3/sp500_tac_d4_merged.compact.json"))
    p.add_argument("--provenance", type=Path, default=Path("data/tac-chart3/sp500_tac_d4_merged.provenance.json"))
    p.add_argument("--release-dir", type=Path, default=Path("data/tac-chart3/synchronized"))
    p.add_argument("--status", type=Path, default=Path("data/tac-chart3/synchronized_status.json"))
    a = p.parse_args()
    result = run_pipeline(a.capture, a.fred_dataset, a.baseline, a.append_jsonl,
                          a.compact, a.provenance, a.release_dir, a.status)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result["exit_code"])

if __name__ == "__main__":
    main()
