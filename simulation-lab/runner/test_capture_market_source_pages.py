#!/usr/bin/env python3
"""Offline tests for raw source page capture status handling."""
import hashlib
from pathlib import Path
from capture_market_source_pages import capture_manifest

def fake_manifest():
    return {"row_count": 44, "rows": [
        {"name": "row-" + str(i), "source_url": "https://example.com/" + str(i),
         "display": "1.0", "verification_status": "PENDING_SOURCE_PAGE_CAPTURE",
         "source_page_fetched": False, "display_value_reconciled": False}
        for i in range(44)
    ]}

def main():
    import capture_market_source_pages as module
    original = module.capture_one
    module.capture_one = lambda url, timeout=25: {
        "http_status": 200, "final_url": url, "content_type": "text/html",
        "content_length_bytes": 3, "raw_response_sha256": hashlib.sha256(b"abc").hexdigest(),
        "raw_body_base64": "YWJj", "captured_at_utc": "2026-11-22T00:00:00+00:00", "error": None
    }
    try:
        import tempfile, json
        with tempfile.TemporaryDirectory() as temp:
            result = capture_manifest(fake_manifest(), Path(temp), 0)
            assert result["capture_success_count"] == 44
            assert result["capture_status"] == "CAPTURED_PENDING_VALUE_RECONCILIATION"
            assert result["status"] == "CAPTURED_PENDING_VALUE_RECONCILIATION"
            assert result["source_value_verification_status"] == "PENDING"
            assert result["page_readable_count"] == 44
            assert result["displayed_values_independently_reconciled"] is False
            assert all(r["verification_status"] == "CAPTURED_PENDING_VALUE_RECONCILIATION" for r in result["rows"])
            assert all(r["display_value_reconciled"] is False for r in result["rows"])
            assert len(list(Path(temp).glob("*.bin"))) == 44
        module.capture_one = lambda url, timeout=25: {
            "http_status": 403, "final_url": url, "content_type": "text/html",
            "content_length_bytes": 128, "raw_response_sha256": hashlib.sha256(b"challenge").hexdigest(),
            "raw_body_base64": "Y2hhbGxlbmdl", "captured_at_utc": "2026-11-22T00:00:00+00:00", "error": "HTTP_ERROR"
        }
        with tempfile.TemporaryDirectory() as temp:
            result = capture_manifest(fake_manifest(), Path(temp), 0)
            assert result["capture_failure_count"] == 44
            assert result["capture_status"] == "CAPTURE_FAILED"
            assert result["status"] == "CAPTURE_FAILED"
            assert result["page_readable_count"] == 0
            assert result["tool_read_failure_count"] == 44
            assert result["raw_response_sha256_saved_count"] == 44
            assert all(r["verification_status"] == "TOOL_READ_FAILURE" for r in result["rows"])
            assert all(r["display_value_reconciled"] is False for r in result["rows"])
        module.capture_one = lambda url, timeout=25: {
            "http_status": 200, "final_url": url, "content_type": "text/html",
            "content_length_bytes": 64, "raw_response_sha256": hashlib.sha256(b"Just a moment... Cloudflare").hexdigest(),
            "raw_body_base64": "SnVzdCBhIG1vbWVudC4uLiBDbG91ZGZsYXJl", "captured_at_utc": "2026-11-22T00:00:00+00:00", "error": None
        }
        with tempfile.TemporaryDirectory() as temp:
            result = capture_manifest(fake_manifest(), Path(temp), 0)
            assert result["capture_success_count"] == 44
            assert result["capture_status"] == "CAPTURE_FAILED"
            assert result["page_readable_count"] == 0
            assert result["tool_read_failure_count"] == 44
            assert all(r["source_page_fetched"] is True for r in result["rows"])
            assert all(r["page_readable"] is False for r in result["rows"])
            assert all(r["verification_status"] == "TOOL_READ_FAILURE" for r in result["rows"])
        verified_manifest = fake_manifest()
        verified_manifest["rows"][0]["verification_status"] = "VERIFIED"
        verified_manifest["rows"][0]["display_value_reconciled"] = True
        verified_manifest["rows"][1]["verification_status"] = "BACKUP_VERIFIED"
        verified_manifest["rows"][1]["display_value_reconciled"] = True
        with tempfile.TemporaryDirectory() as temp:
            result = capture_manifest(verified_manifest, Path(temp), 0)
            assert result["already_verified_skip_count"] == 2
            assert result["capture_attempted_count"] == 42
            assert result["rows"][0]["capture"]["status"] == "SKIPPED_ALREADY_VERIFIED"
    finally:
        module.capture_one = original
    print("PASS: raw capture never implies numeric reconciliation")

if __name__ == "__main__":
    main()
