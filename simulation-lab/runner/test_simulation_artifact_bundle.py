#!/usr/bin/env python3
"""Regression tests for the post-upload Simulation artifact audit."""
import json
import struct
import tempfile
import zlib
from pathlib import Path

from audit_simulation_artifact_bundle import audit_bundle, git_blob_sha, sha256


def png_1x1() -> bytes:
    signature = b"\\x89PNG\\r\\n\\x1a\\n"
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return signature + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\\x00\\x00\\x00\\x00")) + chunk(b"IEND", b"")


def make_bundle(root: Path) -> None:
    files = {
        "preview/2026-11-23-simulation.html": b"<html>ok</html>",
        "simulation-lab/output/runner-metadata.txt": (
            "branch=simulation/test\ncommit=abc123\nrun_id=12345\nrun_attempt=1\nreport_date=2026-11-23\n"
        ).encode(),
        "simulation-lab/output/prebuild-stage-input-receipt.json": json.dumps({"status":"PASS","workflow_run_id":"12345"}).encode(),
        "simulation-lab/output/market-snapshot-audit.json": json.dumps({"status":"PASS","indicator_count":44}).encode(),
        "simulation-lab/output/market-source-verification-manifest.json": json.dumps({"status":"PASS","row_count":44}).encode(),
        "simulation-lab/output/visual/visual-regression.json": json.dumps({"failures":[]}).encode(),
        "simulation-lab/output/interaction-smoke.json": json.dumps({"status":"PASS","page_errors":[]}).encode(),
        "simulation-lab/output/monday-mother-transfer-evidence.json": b"{}",
        "simulation-lab/output/weekdays-mother-transfer-evidence.json": b"{}",
        "simulation-lab/output/visual/test.png": png_1x1(),
    }
    for rel, raw in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    html = files["preview/2026-11-23-simulation.html"]
    sidecar = {
        "status":"QA_PASSED","review_ready":True,"review_ready_blockers":[],
        "report_path":"preview/2026-11-23-simulation.html","report_sha256":sha256(html),
        "report_git_blob_sha":git_blob_sha(html),"workflow_run_id":"12345",
        "branch":"simulation/test","build_commit_sha":"abc123",
        "prebuild_input_receipt_sha256":sha256(files["simulation-lab/output/prebuild-stage-input-receipt.json"]),
        "market_snapshot_audit_sha256":sha256(files["simulation-lab/output/market-snapshot-audit.json"]),
        "market_source_verification_manifest_sha256":sha256(files["simulation-lab/output/market-source-verification-manifest.json"]),
        "visual_evidence_sha256":sha256(files["simulation-lab/output/visual/visual-regression.json"]),
        "interaction_evidence_sha256":sha256(files["simulation-lab/output/interaction-smoke.json"]),
    }
    p = root / "preview/2026-11-23-simulation.qa.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sidecar), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_bundle(root)
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test")
        assert result["status"] == "PASS", result["errors"]
        assert result["png_validated_count"] == 1
        (root / "simulation-lab/output/bad.json").write_text("{broken", encoding="utf-8")
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test")
        assert result["status"] == "FAIL"
        assert any("invalid JSON" in error for error in result["errors"])
    print("PASS: post-upload artifact audit accepts a SHA-bound bundle and rejects corrupt JSON.")


if __name__ == "__main__":
    main()
