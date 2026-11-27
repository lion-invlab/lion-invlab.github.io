#!/usr/bin/env python3
"""Fail-closed Run-scoped Stage 2 handoff validation."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

WEB = "market-history-web-observations.json"
OPTIONAL = ("cnn-fear-greed-observation.json", "market-screenshot-observations.json")
FIELDS = ("run_id", "report_date", "trading_date", "stage1_receipt_sha256",
          "run_context_sha256", "stage1_fixture_sha256")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def need(ok: bool, message: str) -> None:
    if not ok: raise ValueError(message)

def read(path: Path) -> dict:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise ValueError(f"{path.name}: {exc}") from exc
    need(isinstance(value,dict),f"{path.name} must be a JSON object")
    return value

def universe(fixture: dict) -> set[tuple[str,str]]:
    keys=set()
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        keys.update((group,str(name)) for name in (fixture.get(group) or {}))
    keys.update(("sectors",str(name)) for name in (fixture.get("sectors") or {}))
    need(len(keys)==44,"Stage 1 fixture must define exactly 44 unique market rows")
    return keys

def validate_stage2_run_handoff(run_dir: str|Path, repo_root: str|Path|None=None) -> dict:
    root=Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    runs=root/"production"/"runs"
    need(not runs.is_symlink() and runs.resolve()==runs.absolute(),"production/runs must be canonical and not a symlink")
    supplied=Path(run_dir)
    if not supplied.is_absolute(): supplied=root/supplied
    need(not supplied.is_symlink(),"Run directory must not be a symlink")
    run=supplied.resolve()
    need(run.parent==runs.resolve(),"Run directory must be a direct child of production/runs")
    context_path=run/"run-context.json"; stage1_fixture_path=run/"stage1-fixture.json"
    working_fixture_path=run/"report-data.json"; receipt_path=run/"stage1-receipt.json"
    for p in (context_path,stage1_fixture_path,working_fixture_path,receipt_path):
        need(p.is_file() and not p.is_symlink(),f"Missing Stage 1/working file: {p.name}")
    context=read(context_path); fixture=read(stage1_fixture_path)
    working_fixture=read(working_fixture_path); receipt=read(receipt_path)
    run_id=str(context.get("run_id") or ""); report=str(context.get("report_date") or ""); trading=str(context.get("trading_date") or "")
    need(run_id==run.name and run_id.startswith(f"TAC-{report}-"),"run-context Run ID does not match directory/report date")
    need(receipt.get("status")=="PASS" and receipt.get("run_id")==run_id,"Stage 1 receipt status/Run ID mismatch")
    need(receipt.get("report_date")==report and receipt.get("trading_date")==trading,"Stage 1 receipt date mismatch")
    need(fixture.get("report_date")==report and fixture.get("trading_date")==trading,"Stage 1 fixture date mismatch")
    need((fixture.get("run_metadata") or {}).get("run_id")==run_id,"Stage 1 fixture Run ID mismatch")
    need(working_fixture.get("report_date")==report and working_fixture.get("trading_date")==trading,
         "Working report-data fixture date mismatch")
    need((working_fixture.get("run_metadata") or {}).get("run_id")==run_id,
         "Working report-data fixture Run ID mismatch")
    context_hash=sha(context_path); fixture_hash=sha(stage1_fixture_path); receipt_hash=sha(receipt_path)
    need(receipt.get("run_context_sha256")==context_hash,"Stage 1 run-context SHA mismatch")
    need(receipt.get("fixture_sha256")==fixture_hash,"Stage 1 fixture SHA mismatch")
    binding={"run_id":run_id,"report_date":report,"trading_date":trading,
             "stage1_receipt_sha256":receipt_hash,"run_context_sha256":context_hash,
             "stage1_fixture_sha256":fixture_hash}
    expected=universe(fixture); files={WEB:run/WEB}
    for name in OPTIONAL:
        if (run/name).exists(): files[name]=run/name
    hashes={}
    screenshot={"row_count":0,"field_count":0}
    for name,path in files.items():
        need(path.is_file() and not path.is_symlink(),f"Missing or symlinked Run bundle: {name}")
        payload=read(path)
        need(bool(payload.get("schema_version")),f"{name} schema_version missing")
        for field in FIELDS: need(payload.get(field)==binding[field],f"{name} {field} does not match Stage 1")
        need(bool(payload.get("captured_at_utc")),f"{name} captured_at_utc missing")
        rows=payload.get("observations")
        need(isinstance(rows,list),f"{name} observations must be a list")
        if name==WEB:
            keys=[(x.get("group"),x.get("name")) for x in rows if isinstance(x,dict)]
            need(len(rows)==44 and len(keys)==44 and len(set(keys))==44 and set(keys)==expected,
                 "Run-scoped web bundle must contain the exact 44-row Stage 1 universe")
        elif name=="cnn-fear-greed-observation.json":
            need(len(rows)<=1 and all((x.get("group"),x.get("name"))==("risk","fear_greed") for x in rows),
                 "CNN bundle may contain at most the Fear & Greed row")
        else:
            keys={(x.get("group"),x.get("name")) for x in rows}
            need(keys.issubset(expected),"Screenshot sidecar contains a row outside this Run")
            from stage2_screenshot_inputs import load_screenshot_bundle
            loaded=load_screenshot_bundle(path,fixture,run)
            screenshot={"row_count":len(loaded),"field_count":sum(len(x.get("fields") or {}) for x in loaded.values())}
        hashes[name]=sha(path)
    return {"status":"PASS",**binding,"stage1_fixture_path":str(stage1_fixture_path.relative_to(root)),
            "working_fixture_path":str(working_fixture_path.relative_to(root)),"bundle_sha256":hashes[WEB],
            "optional_bundle_sha256":{k:v for k,v in hashes.items() if k!=WEB},
            "screenshot":screenshot}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--run-dir",required=True); a=p.parse_args()
    print(json.dumps(validate_stage2_run_handoff(a.run_dir),ensure_ascii=False,indent=2))

if __name__=="__main__": main()
