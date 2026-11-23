#!/usr/bin/env python3
"""Regression: HTTP access failures must never be reported as missing market dates."""
from browser_verify_market_history import classify_http_response, classify_rendered_page, header_indexes, split_cells


def main():
    assert classify_http_response(None) == "TOOL_READ_FAILURE"
    for status in (400, 401, 403, 404, 429, 500, 503):
        assert classify_http_response(status) == "TOOL_READ_FAILURE", status
    for status in (200, 201, 204, 301, 302):
        assert classify_http_response(status) == "PAGE_READ_OK", status
    assert classify_rendered_page("Access Denied by Cloudflare", 0) == "TOOL_READ_FAILURE"
    assert classify_rendered_page("No historical rows for selected date", 0) == "TARGET_DATE_NOT_FOUND"
    assert classify_rendered_page("Historical prices\nNov 20, 2026 100.00 +1.00%", 1) == "PAGE_READ_OK"
    headers, date_i, value_i, change_i = header_indexes(["日期\t收市\t開市\t高\t低\t成交量\t升跌（%）"])
    assert (date_i, value_i, change_i) == (0, 1, 6)
    cells = split_cells("2026年11月20日\t48,147.33\t49,071.82\t49,594.90\t47,998.86\t1.17B\t-1.93%")
    assert cells[value_i] == "48,147.33" and cells[change_i] == "-1.93%"
    print("PASS: HTTP failures/challenges, genuine date absence, and successful page reads are distinct")
    print("PASS: localized historical-table headers map Date / Close / Change % to the correct cells")


if __name__ == "__main__":
    main()
