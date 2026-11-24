#!/usr/bin/env python3
"""Regression tests for the post-upload Simulation artifact audit."""
import json
import struct
import tempfile
import zlib
from pathlib import Path

from audit_simulation_artifact_bundle import audit_bundle, git_blob_sha, sha256


def png_1x1() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return signature + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) + chunk(b"IEND", b"")


def make_bundle(root: Path) -> None:
    files = {
        "preview/2026-11-23-simulation.html": b"<html>ok</html>",
        "simulation-lab/output/runner-metadata.txt": (
            "branch=simulation/test\ncommit=final789\nbuild_commit=abc123\ncheckout_commit=abc123\nrun_id=12345\ntrigger_commit=trigger456\nrun_attempt=1\nreport_date=2026-11-23\n"
        ).encode(),
        "simulation-lab/output/prebuild-stage-input-receipt.json": json.dumps({"status":"PASS","workflow_run_id":"12345"}).encode(),
        "simulation-lab/output/market-snapshot-audit.json": json.dumps({"status":"PASS","indicator_count":44}).encode(),
        "simulation-lab/output/market-source-verification-manifest.json": json.dumps({
            "status":"PARTIAL","row_count":44,"verified_count":42,"pending_count":2,
            "rows":[
                {"verification_status":"VERIFIED"} for _ in range(42)
            ] + [
                {"verification_status":"CLOSED"},
                {"verification_status":"PENDING_CURRENT_RUN_BROWSER_OBSERVATION"}
            ]
        }).encode(),
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
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test", "trigger456")
        assert result["status"] == "PASS", result["errors"]
        assert result["png_validated_count"] == 1
        # A complete 44-row register with zero live observations is valid for a
        # review draft only when every unresolved row remains explicitly pending.
        manifest_path = root / "simulation-lab/output/market-source-verification-manifest.json"
        pending_manifest = {
            "status": "PENDING", "row_count": 44, "verified_count": 0, "pending_count": 44,
            "rows": [{"verification_status": "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"} for _ in range(44)]
        }
        pending_bytes = json.dumps(pending_manifest).encode("utf-8")
        manifest_path.write_bytes(pending_bytes)
        sidecar_path = root / "preview/2026-11-23-simulation.qa.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["market_source_verification_manifest_sha256"] = sha256(pending_bytes)
        sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test", "trigger456")
        assert result["status"] == "PASS", result["errors"]
        # Restore the partial fixture for the remaining capture-evidence checks.
        make_bundle(root)
        capture_rows = [
            {"page_readable": False, "verification_status": "TOOL_READ_FAILURE",
             "capture": {"http_status": 403, "raw_response_sha256": "a" * 64}}
            for _ in range(44)
        ]
        capture_path = root / "simulation-lab/output/market-source-page-captures.json"
        capture_path.write_text(json.dumps({
            "status": "CAPTURE_FAILED", "row_count": 44, "page_readable_count": 0,
            "tool_read_failure_count": 44, "http_capture_success_count": 0,
            "displayed_values_independently_reconciled": False, "rows": capture_rows
        }), encoding="utf-8")
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test", "trigger456")
        assert result["status"] == "PASS", result["errors"]
        assert any("readable: 0/44" in warning for warning in result["warnings"])
        capture_path.unlink()
        metadata_path = root / "simulation-lab/output/runner-metadata.txt"
        metadata = metadata_path.read_text(encoding="utf-8")
        metadata_path.write_text(metadata.replace("commit=abc123", "commit=wrong"), encoding="utf-8")
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test", "trigger456")
        assert result["status"] == "FAIL"
        assert any("build_commit_sha does not match runner metadata build_commit" in error for error in result["errors"])
        metadata_path.write_text(metadata, encoding="utf-8")
        metadata_path.write_text(metadata.replace("trigger_commit=trigger456", "trigger_commit=wrong"), encoding="utf-8")
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test", "trigger456")
        assert result["status"] == "FAIL"
        assert any("trigger_commit mismatch" in error for error in result["errors"])
        metadata_path.write_text(metadata, encoding="utf-8")
        (root / "simulation-lab/output/bad.json").write_text("{broken", encoding="utf-8")
        result = audit_bundle(root, "preview/2026-11-23-simulation.html", "12345", "simulation/test")
        assert result["status"] == "FAIL"
        assert any("invalid JSON" in error for error in result["errors"])
    print("PASS: post-upload artifact audit accepts a SHA-bound bundle and rejects corrupt JSON.")

    workflow = Path(".github/workflows/tac-simulation-lab.yml").read_text(encoding="utf-8")
    names = [
        "Upload simulation evidence",
        "Download uploaded simulation evidence for independent verification",
        "Verify downloaded simulation evidence bundle",
        "Upload post-upload artifact audit report",
    ]
    positions = [workflow.index(f"- name: {name}") for name in names]
    assert positions == sorted(positions), "post-upload artifact audit steps are out of order"
    for name in names[1:]:
        block = workflow.split(f"- name: {name}", 1)[1].split("\n      - name:", 1)[0]
        assert "if: always()" in block, f"{name} must run after earlier failures"
    assert "uses: actions/download-artifact@v4" in workflow
    assert "audit_simulation_artifact_bundle.py" in workflow
    assert "tac-simulation-postupload-audit-" in workflow
    assert 'echo "SIM_CHECKOUT_COMMIT=$(git rev-parse HEAD)"' in workflow
    assert 'echo "SIM_TRIGGER_COMMIT=$GITHUB_SHA"' in workflow
    assert 'echo "commit=$(git rev-parse HEAD)"' in workflow
    assert 'echo "checkout_commit=${SIM_CHECKOUT_COMMIT:-unavailable}"' in workflow
    assert 'echo "trigger_commit=$GITHUB_SHA"' in workflow
    assert "--expected-trigger-commit" in workflow
    print("PASS: workflow uploads, downloads, verifies, and separately archives the post-upload audit.")


if __name__ == "__main__":
    main()
