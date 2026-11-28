#!/usr/bin/env python3
"""Confirm the Stage 1 to Stage 2 Run handoff using identity, dates and deliverables."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from run_state import validate_state

ROOT = Path(__file__).resolve().parents[2]
WEB = "market-history-web-observations.json"

def read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"Required Run handoff file is missing: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    args=ap.parse_args()
    run=Path(args.run_dir)
    if not run.is_absolute(): run=ROOT/run
    run=run.resolve()
    if run.parent != (ROOT/"production/runs").resolve():
        raise SystemExit("Stage 2 Run must be a direct child of production/runs")
    context=read(run/"run-context.json")
    fixture=read(run/"stage1-fixture.json")
    working=read(run/"report-data.json")
    stage1=read(run/"stage1-receipt.json")
    state=read(run/"run-state.json")
    bundle=read(run/WEB)
    run_id=str(context.get("run_id") or "")
    report=str(context.get("report_date") or "")
    trading=str(context.get("trading_date") or "")
    if run_id != run.name or not run_id.startswith(f"TAC-{report}-"):
        raise SystemExit("Stage 1 Run ID does not match its Run directory/report date")
    for label,item in (("Stage 1 receipt",stage1),("Stage 1 fixture",fixture),("working fixture",working),("Stage 2 observation",bundle)):
        if item.get("run_id", (item.get("run_metadata") or {}).get("run_id")) != run_id:
            raise SystemExit(f"{label} belongs to a different Run")
        if item.get("report_date") != report or item.get("trading_date") != trading:
            raise SystemExit(f"{label} dates do not match the current Run")
    if stage1.get("status") != "PASS":
        raise SystemExit("Stage 1 has not completed")
    validate_state(state,expected_run_id=run_id)
    if state["stages"]["STAGE_2"]["status"] != "SUBMITTED":
        raise SystemExit("Stage 2 observation must be submitted before capture processing")
    observations=bundle.get("observations")
    expected=set()
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        expected.update((group,str(name)) for name in (fixture.get(group) or {}))
    expected.update(("sectors",str(name)) for name in (fixture.get("sectors") or {}))
    keys={(row.get("group"),str(row.get("name"))) for row in observations or [] if isinstance(row,dict)}
    if len(observations or []) != 44 or len(keys) != 44 or keys != expected:
        raise SystemExit("Stage 2 observations do not match the 44-item Stage 1 instrument list")
    import hashlib
    bundle_sha=hashlib.sha256((run/WEB).read_bytes()).hexdigest()
    if state["stages"]["STAGE_2"].get("output_sha256") != bundle_sha:
        raise SystemExit("Stage 2 submitted artifact does not match its Run-state output")
    print(json.dumps({
        "status":"PASS","run_id":run_id,"report_date":report,"trading_date":trading,
        "stage1_fixture_path":str((run/"stage1-fixture.json").relative_to(ROOT)),
        "working_fixture_path":str((run/"report-data.json").relative_to(ROOT)),
        "bundle_sha256":bundle_sha
    },ensure_ascii=False,indent=2))

if __name__=="__main__": main()
