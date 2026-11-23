#!/usr/bin/env python3
"""Regression: HTTP access failures must never be reported as missing market dates."""
from browser_verify_market_history import classify_http_response, classify_rendered_page


def main():
    assert classify_http_response(None) == "TOOL_READ_FAILURE"
    for status in (400, 401, 403, 404, 429, 500, 503):
        assert classify_http_response(status) == "TOOL_READ_FAILURE", status
    for status in (200, 201, 204, 301, 302):
        assert classify_http_response(status) == "PAGE_READ_OK", status
    assert classify_rendered_page("Access Denied by Cloudflare", 0) == "TOOL_READ_FAILURE"
    assert classify_rendered_page("No historical rows for selected date", 0) == "TARGET_DATE_NOT_FOUND"
    assert classify_rendered_page("Historical prices\nNov 20, 2026 100.00 +1.00%", 1) == "PAGE_READ_OK"
    print("PASS: HTTP failures/challenges, genuine date absence, and successful page reads are distinct")


if __name__ == "__main__":
    main()
