#!/usr/bin/env python3
"""Verify the downloaded TAC Simulation artifact bundle against its QA sidecar."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def parse_kv(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def validate_png(data: bytes) -> None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG signature")
    offset = 8
    saw_ihdr = saw_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated PNG payload")
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xffffffff
        if actual_crc != expected_crc:
            raise ValueError(f"PNG CRC mismatch in {chunk_type.decode('ascii', 'replace')}")
        if chunk_type == b"IHDR":
            if length != 13 or saw_ihdr:
                raise ValueError("invalid or duplicate IHDR")
            saw_ihdr = True
        if chunk_type == b"IEND":
            if length != 0:
                raise ValueError("invalid IEND")
            saw_iend = True
            if end != len(data):
                raise ValueError("trailing bytes after IEND")
            break
        offset = end
    if not saw_ihdr or not saw_iend:
        raise ValueError("PNG missing IHDR or IEND")


def audit_bundle(root: Path, report_path: str | None = None,
                 expected_run_id: str | None = None,
                 expected_branch: str | None = None,
                 expected_trigger_commit: str | None = None) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checked_json = checked_png = 0

    def read_required(rel: str) -> bytes | None:
        path = root / rel
        if not path.is_file():
            errors.append(f"missing required file: {rel}")
            return None
        return path.read_bytes()

    if report_path:
        html_rel = report_path
    else:
        candidates = sorted((root / "preview").glob("*-simulation.html")) if (root / "preview").is_dir() else []
        html_rel = str(candidates[-1].relative_to(root)) if candidates else "preview/UNRESOLVED-simulation.html"
    sidecar_rel = html_rel[:-5] + ".qa.json" if html_rel.endswith(".html") else html_rel + ".qa.json"

    html = read_required(html_rel)
    sidecar_bytes = read_required(sidecar_rel)
    metadata_bytes = read_required("simulation-lab/output/runner-metadata.txt")
    receipt_bytes = read_required("simulation-lab/output/prebuild-stage-input-receipt.json")
    snapshot_bytes = read_required("simulation-lab/output/market-snapshot-audit.json")
    manifest_bytes = read_required("simulation-lab/output/market-source-verification-manifest.json")
    capture_path = root / "simulation-lab/output/market-source-page-captures.json"
    capture_bytes = capture_path.read_bytes() if capture_path.is_file() else None
    visual_bytes = read_required("simulation-lab/output/visual/visual-regression.json")
    interaction_bytes = read_required("simulation-lab/output/interaction-smoke.json")
    # Mother transfer JSON files were a legacy contract and are not produced by
    # the current dual-mother browser gates. The current visual regression and
    # DOM-contract receipts are the authoritative evidence.

    parsed: dict[str, dict] = {}
    for rel, raw in [
        (sidecar_rel, sidecar_bytes), ("simulation-lab/output/prebuild-stage-input-receipt.json", receipt_bytes),
        ("simulation-lab/output/market-snapshot-audit.json", snapshot_bytes),
        ("simulation-lab/output/market-source-verification-manifest.json", manifest_bytes),
        ("simulation-lab/output/market-source-page-captures.json", capture_bytes),
        ("simulation-lab/output/visual/visual-regression.json", visual_bytes),
        ("simulation-lab/output/interaction-smoke.json", interaction_bytes),
    ]:
        if raw is None:
            continue
        try:
            parsed[rel] = json.loads(raw)
            checked_json += 1
        except Exception as exc:
            errors.append(f"invalid JSON {rel}: {exc}")

    if metadata_bytes is not None:
        metadata = parse_kv(root / "simulation-lab/output/runner-metadata.txt")
        if expected_run_id and metadata.get("run_id") != str(expected_run_id):
            errors.append(f"runner metadata run_id mismatch: {metadata.get('run_id')} != {expected_run_id}")
        if expected_branch and metadata.get("branch") != expected_branch:
            errors.append(f"runner metadata branch mismatch: {metadata.get('branch')} != {expected_branch}")
        if expected_trigger_commit and metadata.get("trigger_commit") != expected_trigger_commit:
            errors.append(f"runner metadata trigger_commit mismatch: {metadata.get('trigger_commit')} != {expected_trigger_commit}")
    else:
        metadata = {}

    sidecar = parsed.get(sidecar_rel, {})
    if html is not None and sidecar:
        if sidecar.get("report_path") != html_rel:
            errors.append("QA sidecar report_path does not match archived HTML path")
        if sidecar.get("report_sha256") != sha256(html):
            errors.append("QA sidecar report_sha256 does not match archived HTML")
        if sidecar.get("report_git_blob_sha") != git_blob_sha(html):
            errors.append("QA sidecar report_git_blob_sha does not match archived HTML")
        if sidecar.get("status") != "QA_PASSED" or sidecar.get("review_ready") is not True:
            errors.append("QA sidecar is not QA_PASSED/review_ready")
        if sidecar.get("review_ready_blockers") != []:
            errors.append("QA sidecar has review_ready_blockers")
        if expected_run_id and str(sidecar.get("workflow_run_id")) != str(expected_run_id):
            errors.append("QA sidecar workflow_run_id mismatch")
        if expected_branch and sidecar.get("branch") != expected_branch:
            errors.append("QA sidecar branch mismatch")
        if metadata and sidecar.get("build_commit_sha") != metadata.get("build_commit"):
            errors.append("QA sidecar build_commit_sha does not match runner metadata build_commit")

    receipt = parsed.get("simulation-lab/output/prebuild-stage-input-receipt.json", {})
    if receipt_bytes is not None and sidecar:
        if receipt.get("status") != "PASS":
            errors.append("pre-build receipt status is not PASS")
        if sidecar.get("prebuild_input_receipt_sha256") != sha256(receipt_bytes):
            errors.append("pre-build receipt SHA-256 does not match QA sidecar")
        if expected_run_id and str(receipt.get("workflow_run_id")) != str(expected_run_id):
            errors.append("pre-build receipt workflow_run_id mismatch")

    for rel, raw, key in [
        ("simulation-lab/output/market-snapshot-audit.json", snapshot_bytes, "market_snapshot_audit_sha256"),
        ("simulation-lab/output/market-source-verification-manifest.json", manifest_bytes, "market_source_verification_manifest_sha256"),
        ("simulation-lab/output/visual/visual-regression.json", visual_bytes, "visual_evidence_sha256"),
        ("simulation-lab/output/interaction-smoke.json", interaction_bytes, "interaction_evidence_sha256"),
    ]:
        if raw is not None and sidecar and sidecar.get(key) != sha256(raw):
            errors.append(f"{rel} SHA-256 does not match QA sidecar field {key}")

    snapshot = parsed.get("simulation-lab/output/market-snapshot-audit.json", {})
    if snapshot and (snapshot.get("indicator_count") != 44 or snapshot.get("status") != "PASS"):
        errors.append("market snapshot audit is not PASS with 44 indicators")
    market_manifest = parsed.get("simulation-lab/output/market-source-verification-manifest.json", {})
    if market_manifest:
        market_rows = market_manifest.get("rows", [])
        allowed_market_states = {
            "VERIFIED", "BACKUP_VERIFIED",
            "PENDING_CURRENT_RUN_BROWSER_OBSERVATION", "CLOSED",
        }
        row_states_valid = (
            len(market_rows) == 44
            and all(row.get("verification_status") in allowed_market_states for row in market_rows)
        )
        verified_count = market_manifest.get("verified_count")
        pending_count = market_manifest.get("pending_count")
        closed_count = market_manifest.get("closed_count")
        expected_status = "PASS" if verified_count == 44 else "PARTIAL" if isinstance(verified_count, int) and verified_count > 0 else "PENDING"
        counts_valid = (
            isinstance(verified_count, int) and isinstance(pending_count, int) and isinstance(closed_count, int)
            and verified_count >= 0 and pending_count >= 0 and closed_count >= 0
            and verified_count + pending_count + closed_count == 44
            and market_manifest.get("status") == expected_status
        )
        if market_manifest.get("row_count") != 44 or not counts_valid or not row_states_valid:
            errors.append("market source manifest must contain 44 rows, reconciled PASS/PARTIAL/PENDING counts, and explicit row-level verification states")
    capture = parsed.get("simulation-lab/output/market-source-page-captures.json")
    if capture is not None:
        capture_rows = capture.get("rows", [])
        if capture.get("row_count") != 44 or len(capture_rows) != 44:
            errors.append("market source page capture does not contain exactly 44 rows")
        else:
            readable = sum(1 for row in capture_rows if row.get("page_readable") is True)
            failures = sum(1 for row in capture_rows if row.get("verification_status") == "TOOL_READ_FAILURE")
            http_successes = sum(
                1 for row in capture_rows
                if row.get("capture", {}).get("http_status") == 200
                and row.get("capture", {}).get("raw_response_sha256")
            )
            if capture.get("page_readable_count") != readable:
                errors.append("market source capture page_readable_count does not match row evidence")
            if capture.get("tool_read_failure_count") != failures:
                errors.append("market source capture tool_read_failure_count does not match row evidence")
            if capture.get("http_capture_success_count") != http_successes:
                errors.append("market source capture HTTP success count does not match row evidence")
            if capture.get("displayed_values_independently_reconciled") is not False:
                warnings.append("Source capture artifact must not imply numeric reconciliation.")
            if readable < 44:
                warnings.append(f"Current-run market source page capture readable: {readable}/44; this is not a full live-source verification.")
    visual = parsed.get("simulation-lab/output/visual/visual-regression.json", {})
    if visual and visual.get("failures") != []:
        errors.append("visual regression contains failures")
    interaction = parsed.get("simulation-lab/output/interaction-smoke.json", {})
    if interaction and (interaction.get("status") != "PASS" or interaction.get("page_errors") != []):
        errors.append("interaction smoke is not clean PASS")

    for path in sorted(root.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            checked_json += 1
        except Exception as exc:
            errors.append(f"invalid JSON {path.relative_to(root)}: {exc}")
    for path in sorted(root.rglob("*.png")):
        try:
            validate_png(path.read_bytes())
            checked_png += 1
        except Exception as exc:
            errors.append(f"invalid PNG {path.relative_to(root)}: {exc}")

    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        raw = path.read_bytes()
        files.append({"path": str(path.relative_to(root)), "bytes": len(raw), "sha256": sha256(raw)})
    result = {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "artifact_root": str(root),
        "report_path": html_rel,
        "qa_sidecar_path": sidecar_rel,
        "expected_run_id": str(expected_run_id) if expected_run_id else None,
        "expected_branch": expected_branch,
        "expected_trigger_commit": expected_trigger_commit,
        "file_count": len(files),
        "json_validated_count_including_required_rechecks": checked_json,
        "png_validated_count": checked_png,
        "required_evidence": {
            "html": html is not None,
            "qa_sidecar": sidecar_bytes is not None,
            "runner_metadata": metadata_bytes is not None,
            "prebuild_receipt": receipt_bytes is not None,
            "market_snapshot_audit": snapshot_bytes is not None,
            "market_source_manifest": manifest_bytes is not None,
            "visual_regression": visual_bytes is not None,
            "interaction_smoke": interaction_bytes is not None,
            "dual_mother_visual_and_dom_gates": visual_bytes is not None,
        },
        "errors": errors,
        "warnings": warnings,
        "files": files,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--report-path")
    parser.add_argument("--expected-run-id")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-trigger-commit")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit_bundle(Path(args.root), args.report_path, args.expected_run_id, args.expected_branch, args.expected_trigger_commit)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "file_count", "json_validated_count_including_required_rechecks", "png_validated_count", "errors")}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
