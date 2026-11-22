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
    for row in manifest["rows"]:
        item = dict(row)
        host = urlparse(item["source_url"]).netloc.lower()
        if last_host == host:
            time.sleep(sleep_seconds)
        result = capture_one(item["source_url"])
        body64 = result.pop("raw_body_base64", None)
        item["capture"] = result
        item["source_page_fetched"] = bool(result.get("http_status") == 200 and result.get("raw_response_sha256"))
        item["display_value_reconciled"] = False
        item["verification_status"] = "CAPTURED_PENDING_VALUE_RECONCILIATION" if item["source_page_fetched"] else "SOURCE_PAGE_CAPTURE_FAILED"
        if body64 is not None:
            import base64
            body = base64.b64decode(body64)
            safe_name = str(len(rows) + 1).zfill(2) + "-" + hashlib.sha256(item["source_url"].encode()).hexdigest()[:12] + ".bin"
            (output_dir / safe_name).write_bytes(body)
            item["capture"]["raw_file"] = safe_name
        rows.append(item)
        last_host = host
    captured = sum(1 for r in rows if r["source_page_fetched"])
    result = dict(manifest)
    result.update({
        "verification_scope": "RAW_SOURCE_PAGE_CAPTURE_ONLY",
        "source_pages_fetched": captured == len(rows),
        "displayed_values_independently_reconciled": False,
        "capture_success_count": captured,
        "capture_failure_count": len(rows) - captured,
        "rows": rows,
        "warning": "HTTP 200/raw-body capture is not numeric verification; each displayed value remains pending independent reconciliation.",
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
    print(json.dumps({"rows": 44, "captured": result["capture_success_count"], "failed": result["capture_failure_count"], "value_reconciled": False, "output": str(target)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
