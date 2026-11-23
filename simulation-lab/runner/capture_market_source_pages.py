#!/usr/bin/env python3
"""Capture raw HTTPS source pages for the 44-indicator audit worklist.

A successful HTTP capture is NOT numeric source-value verification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = "TAC-Market-Source-Audit/1.0 (+https://github.com/lion-invlab/lion-invlab.github.io)"
MAX_BYTES = 8 * 1024 * 1024

def capture_one(url: str, timeout: int = 25) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return {"http_status": None, "error": "REJECTED_NON_HTTPS_URL"}
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5"})
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read(MAX_BYTES + 1)
            captured = datetime.now(timezone.utc).isoformat()
            if len(body) > MAX_BYTES:
                return {"http_status": response.status, "error": "RESPONSE_EXCEEDS_8MB", "captured_at_utc": captured}
            return {
                "http_status": response.status,
                "final_url": response.geturl(),
                "content_type": response.headers.get("Content-Type"),
                "content_length_bytes": len(body),
                "raw_response_sha256": hashlib.sha256(body).hexdigest(),
                "raw_body_base64": __import__("base64").b64encode(body).decode("ascii"),
                "captured_at_utc": captured,
                "error": None,
            }
    except HTTPError as exc:
        body = exc.read(MAX_BYTES + 1)
        captured = datetime.now(timezone.utc).isoformat()
        return {
            "http_status": exc.code, "final_url": exc.geturl(),
            "content_type": exc.headers.get("Content-Type"),
            "content_length_bytes": len(body),
            "raw_response_sha256": hashlib.sha256(body).hexdigest() if len(body) <= MAX_BYTES else None,
            "raw_body_base64": __import__("base64").b64encode(body).decode("ascii") if len(body) <= MAX_BYTES else None,
            "captured_at_utc": captured, "error": "HTTP_ERROR",
        }
    except (URLError, TimeoutError, OSError) as exc:
        captured = datetime.now(timezone.utc).isoformat()
        return {"http_status": None, "captured_at_utc": captured, "error": type(exc).__name__ + ": " + str(exc)}

def capture_manifest(manifest: dict, output_dir: Path, sleep_seconds: float = 1.0) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    last_host = None
    attempted = 0
    skipped_verified = 0
    for row in manifest["rows"]:
        item = dict(row)
        if item.get("verification_status") in ("VERIFIED", "BACKUP_VERIFIED") and item.get("display_value_reconciled") is True:
            item["capture"] = {"status": "SKIPPED_ALREADY_VERIFIED", "note": "SIM-1.4：已核實並鎖定的數值不重抓。"}
            rows.append(item)
            skipped_verified += 1
            continue
        attempted += 1
        host = urlparse(item["source_url"]).netloc.lower()
        if last_host == host:
            time.sleep(sleep_seconds)
        result = capture_one(item["source_url"])
        body64 = result.pop("raw_body_base64", None)
        item["capture"] = result
        item["source_page_fetched"] = bool(result.get("http_status") == 200 and result.get("raw_response_sha256"))
        challenge_page = False
        if body64 is not None:
            import base64
            body = base64.b64decode(body64)
            body_text = body[:MAX_BYTES].decode("utf-8", errors="ignore").lower()
            challenge_markers = (
                "just a moment",
                "cf-chl-",
                "challenge-platform",
                "enable javascript and cookies",
                "verify you are human",
                "cloudflare",
            )
            challenge_page = any(marker in body_text for marker in challenge_markers)
            safe_name = str(len(rows) + 1).zfill(2) + "-" + hashlib.sha256(item["source_url"].encode()).hexdigest()[:12] + ".bin"
            (output_dir / safe_name).write_bytes(body)
            item["capture"]["raw_file"] = safe_name
        item["page_readable"] = bool(item["source_page_fetched"] and not challenge_page)
        item["display_value_reconciled"] = False
        if item["page_readable"]:
            item["verification_status"] = "CAPTURED_PENDING_VALUE_RECONCILIATION"
        else:
            # Access denials and anti-bot/challenge HTML are tool failures,
            # not proof that the source has no observation for the requested date.
            item["verification_status"] = "TOOL_READ_FAILURE"
        item["capture"]["challenge_page_detected"] = challenge_page
        rows.append(item)
        last_host = host
    http_capture_successes = sum(
        1 for row in rows
        if row.get("capture", {}).get("http_status") == 200
        and row.get("capture", {}).get("raw_response_sha256")
    )
    page_readable_count = sum(1 for row in rows if row.get("page_readable") is True)
    tool_read_failure_count = sum(1 for row in rows if row.get("verification_status") == "TOOL_READ_FAILURE")
    raw_response_saved_count = sum(
        1 for row in rows if row.get("capture", {}).get("raw_response_sha256")
    )
    reconciled_count = sum(1 for row in rows if row.get("display_value_reconciled") is True)
    result = dict(manifest)
    result.update({
        "source_value_verification_status": manifest.get("status"),
        "source_value_verification_scope": manifest.get("verification_scope"),
        "capture_status": (
            "CAPTURE_FAILED" if page_readable_count == 0
            else "CAPTURE_PARTIAL" if page_readable_count < len(rows)
            else "CAPTURED_PENDING_VALUE_RECONCILIATION"
        ),
        "status": (
            "CAPTURE_FAILED" if page_readable_count == 0
            else "CAPTURE_PARTIAL" if page_readable_count < len(rows)
            else "CAPTURED_PENDING_VALUE_RECONCILIATION"
        ),
        "verification_scope": "CURRENT_RUN_SOURCE_PAGE_CAPTURE_SEPARATE_FROM_PRIOR_OBSERVATIONS",
        "source_pages_fetched": page_readable_count == len(rows),
        "page_readable_count": page_readable_count,
        "http_capture_success_count": http_capture_successes,
        "displayed_values_independently_reconciled": reconciled_count == len(rows),
        "current_run_reconciled_count": reconciled_count,
        "prior_observation_reused_count": skipped_verified,
        "prior_observation_missing_time_count": sum(
            1 for row in rows
            if row.get("observation_provenance") == "MISSING_PER_ITEM_OBSERVATION_TIME"
        ),
        "verified_count": sum(
            1 for row in rows
            if row.get("verification_status") in ("VERIFIED", "BACKUP_VERIFIED")
        ),
        "pending_count": sum(
            1 for row in rows
            if row.get("verification_status") not in ("VERIFIED", "BACKUP_VERIFIED")
        ),
        "row_count": len(rows),
        "capture_attempted_count": attempted,
        "already_verified_skip_count": skipped_verified,
        "capture_success_count": http_capture_successes,
        "capture_failure_count": attempted - http_capture_successes,
        "tool_read_failure_count": tool_read_failure_count,
        "raw_response_sha256_saved_count": raw_response_saved_count,
        "rows": rows,
        "warning": "HTTP 200/raw-body capture is not page readability or numeric verification. Prior observations and current-run capture outcomes are reported separately.",
    })
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--sleep-seconds", type=float, default=1.0)
    args = ap.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("row_count") != 44 or len(manifest.get("rows", [])) != 44:
        raise SystemExit("Expected exactly 44 source worklist rows")
    result = capture_manifest(manifest, Path(args.raw_dir), args.sleep_seconds)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": 44, "captured": result["capture_success_count"], "failed": result["capture_failure_count"], "value_reconciled": result["displayed_values_independently_reconciled"], "output": str(target)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
