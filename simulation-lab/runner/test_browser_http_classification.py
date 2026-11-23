#!/usr/bin/env python3
"""Regression: HTTP access failures must never be reported as missing market dates."""
from browser_verify_market_history import classify_http_response


def main():
    assert classify_http_response(None) == "TOOL_READ_FAILURE"
    for status in (400, 401, 403, 404, 429, 500, 503):
        assert classify_http_response(status) == "TOOL_READ_FAILURE", status
    for status in (200, 201, 204, 301, 302):
        assert classify_http_response(status) == "PAGE_READ_OK", status
    print("PASS: HTTP 403/429/server errors are TOOL_READ_FAILURE, never target-date missing")


if __name__ == "__main__":
    main()
