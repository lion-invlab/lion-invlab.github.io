#!/usr/bin/env python3
"""Fail-closed orchestration for the isolated five-series Chart 3 release."""
from __future__ import annotations
import argparse, datetime as dt, json, sys
from pathlib import Path
from build_tac_chart3_synchronized_release import build_candidate, atomic_write

def write_status(path: Path, status: str, **details):
    obj={"status":status,"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),**details}
    atomic_write(path,obj)
    return obj

def run(fred_dataset: Path, sp500_compact: Path, sp500_provenance: Path,
        release_dir: Path, status_path: Path):
    missing=[str(p) for p in (fred_dataset,sp500_compact,sp500_provenance) if not p.is_file()]
    if missing:
        write_status(status_path,"BLOCKED_MISSING_INPUT",missing_inputs=missing,
                     published=False,last_good_preserved=True)
        return 2

    manifest_path=release_dir/"active_manifest.json"
    previous_snapshot=None
    previous_manifest=None
    if manifest_path.exists():
        previous_manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        previous_snapshot=release_dir/previous_manifest.get("snapshot_file","")
        if not previous_snapshot.is_file():
            write_status(status_path,"BLOCKED_BROKEN_LAST_GOOD_MANIFEST",
                         manifest=str(manifest_path),snapshot_file=str(previous_snapshot),
                         published=False,last_good_preserved=True)
            return 2

    try:
        candidate=build_candidate(
            json.loads(fred_dataset.read_text(encoding="utf-8")),
            json.loads(sp500_compact.read_text(encoding="utf-8")),
            json.loads(sp500_provenance.read_text(encoding="utf-8")))
    except Exception as exc:
        write_status(status_path,"BLOCKED_VALIDATION_FAILURE",reason=str(exc),
                     published=False,last_good_preserved=True)
        return 2

    common=candidate["common_observation_date"]
    if previous_manifest:
        old_date=previous_manifest.get("common_observation_date")
        if old_date and common<=old_date:
            write_status(status_path,"NO_NEW_COMMON_DATE",common_observation_date=common,
                         previous_common_observation_date=old_date,published=False,
                         last_good_preserved=True)
            return 0

    # Immutable snapshot first; the active manifest is the sole atomic pointer.
    snapshots=release_dir/"snapshots"
    snapshot_name=f'{candidate["snapshot_id"]}.json'
    snapshot_path=snapshots/snapshot_name
    if not snapshot_path.exists():
        atomic_write(snapshot_path,candidate)
    manifest={
        "schema_version":"1.0",
        "status":"PASS",
        "snapshot_id":candidate["snapshot_id"],
        "snapshot_file":f"snapshots/{snapshot_name}",
        "common_observation_date":common,
        "published_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "previous_snapshot_id":previous_manifest.get("snapshot_id") if previous_manifest else None,
        "series_latest_observation_dates":{
            item["series_id"]:item["latest_observation_date"] for item in candidate["series"]},
        "snapshot_sha256":__import__("hashlib").sha256(snapshot_path.read_bytes()).hexdigest()
    }
    atomic_write(manifest_path,manifest)
    write_status(status_path,"PUBLISHED",snapshot_id=candidate["snapshot_id"],
                 common_observation_date=common,manifest=str(manifest_path),
                 published=True,last_good_preserved=True)
    return 0

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fred-dataset",type=Path,default=Path("data/tac-chart3/chart3_market_stress.json"))
    p.add_argument("--sp500-compact",type=Path,default=Path("data/tac-chart3/sp500_investing_com_daily.compact.json"))
    p.add_argument("--sp500-provenance",type=Path,default=Path("data/tac-chart3/sp500_investing_com_daily.provenance.json"))
    p.add_argument("--release-dir",type=Path,default=Path("data/tac-chart3/synchronized"))
    p.add_argument("--status",type=Path,default=Path("data/tac-chart3/synchronized_status.json"))
    a=p.parse_args()
    raise SystemExit(run(a.fred_dataset,a.sp500_compact,a.sp500_provenance,a.release_dir,a.status))

if __name__=="__main__": main()
