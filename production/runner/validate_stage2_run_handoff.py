#!/usr/bin/env python3
"""Confirm Stage 1 -> Stage 2 handoff by Run identity, dates and deliverables."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from run_state import validate_state

ROOT = Path(__file__).resolve().parents[2]
WEB = "market-history-web-observations.json"

def read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or symlinked Run bundle: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))

def validate_stage2_run_handoff(run_dir: Path, root: Path = ROOT) -> dict:
    run_dir=Path(run_dir)
    if not run_dir.is_absolute(): run_dir=root/run_dir
    run_dir=run_dir.resolve()
    if run_dir.parent != (root/"production/runs").resolve():
        raise ValueError("Stage 2 Run must be a direct child of production/runs")
    context=read(run_dir/"run-context.json")
    fixture=read(run_dir/"stage1-fixture.json")
    working=read(run_dir/"report-data.json")
    stage1=read(run_dir/"stage1-receipt.json")
    state=read(run_dir/"run-state.json")
    bundle=read(run_dir/WEB)
    run_id=str(context.get("run_id") or "")
    report=str(context.get("report_date") or "")
    trading=str(context.get("trading_date") or "")
    if run_id != run_dir.name or not run_id.startswith(f"TAC-{report}-"):
        raise ValueError("run_id does not match Stage 1 Run directory/report date")
    for label,item in (("Stage 1 receipt",stage1),("Stage 1 fixture",fixture),
                       ("working fixture",working),("Stage 2 observation",bundle)):
        item_run=item.get("run_id",(item.get("run_metadata") or {}).get("run_id"))
        if item_run != run_id:
            raise ValueError(f"{label} run_id does not match this Run")
        if item.get("report_date") != report or item.get("trading_date") != trading:
            raise ValueError(f"{label} dates do not match this Run")
    if stage1.get("status") != "PASS":
        raise ValueError("Stage 1 has not completed")
    validate_state(state,expected_run_id=run_id)
    if state["stages"]["STAGE_2"]["status"] != "SUBMITTED":
        raise ValueError("Stage 2 observation must be submitted before capture processing")
    observations=bundle.get("observations")
    expected=set()
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        expected.update((group,str(name)) for name in (fixture.get(group) or {}))
    expected.update(("sectors",str(name)) for name in (fixture.get("sectors") or {}))
    keys={(row.get("group"),str(row.get("name"))) for row in observations or [] if isinstance(row,dict)}
    if len(observations or []) != 44 or len(keys) != 44 or keys != expected:
        raise ValueError("Stage 2 observations do not match the exact 44-row Stage 1 universe")
    return {"status":"PASS","run_id":run_id,"report_date":report,"trading_date":trading,
            "stage1_fixture_path":str((run_dir/"stage1-fixture.json").relative_to(root)),
            "working_fixture_path":str((run_dir/"report-data.json").relative_to(root)),
            "observation_count":len(observations)}

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    args=ap.parse_args()
    print(json.dumps(validate_stage2_run_handoff(Path(args.run_dir)),ensure_ascii=False,indent=2))

if __name__=="__main__": main()
