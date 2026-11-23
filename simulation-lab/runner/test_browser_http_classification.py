#!/usr/bin/env python3
"""Regression: HTTP access failures must never be reported as missing market dates."""
from browser_verify_market_history import classify_http_response, classify_rendered_page, header_indexes, split_cells, parse_cnn_history, cnn_score_matches_display, cnn_band_for_score


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
    noisy_headers, date_i, value_i, change_i = header_indexes(["代號交易所貨幣\t日期\t收市\t開市\t高\t低\t成交量\t升跌（%）"], 7)
    assert (date_i, value_i, change_i) == (0, 1, 6)
    empty_volume = split_cells("Nov 20, 2026\t6,910.39\t7,150.39\t7,198.67\t6,882.66\t\t-3.70%")
    assert len(empty_volume) == 7 and empty_volume[5] == "" and empty_volume[6] == "-3.70%"
    print("PASS: localized historical-table headers map Date / Close / Change % to the correct cells")
    import datetime
    target = "2026-11-20"
    stamp = int(datetime.datetime(2026, 11, 20, 0, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)
    cnn = parse_cnn_history({"fear_and_greed_historical":{"data":[{"x":stamp,"y":18.5873840445269,"rating":"extreme fear"}]}}, target)
    assert cnn["status"] == "PAGE_READ_OK" and cnn["date"] == target and cnn["score"] == 18.5873840445269 and cnn["rating"] == "extreme fear"
    assert cnn["timestamp_utc"].startswith(target) and len(cnn["target_date_points"]) == 1
    later = stamp + 23 * 60 * 60 * 1000
    multi = parse_cnn_history({"fear_and_greed_historical":{"data":[
        {"x":stamp,"y":18.5,"rating":"extreme fear"},
        {"x":later,"y":19.0,"rating":"extreme fear"},
    ]}}, target)
    assert multi["score"] == 19.0 and len(multi["target_date_points"]) == 2
    assert cnn_score_matches_display(18.5873840445269, "19") is True
    assert cnn_score_matches_display(9.67368421052632, "10") is True
    assert cnn_band_for_score(9.67368421052632) == "extreme fear"
    assert cnn_band_for_score(30) == "fear"
    assert cnn_band_for_score(50) == "neutral"
    assert cnn_band_for_score(65) == "greed"
    assert cnn_band_for_score(80) == "extreme greed"
    assert cnn_score_matches_display(19.5873840445269, "19") is False
    missing = parse_cnn_history({"fear_and_greed_historical":{"data":[{"x":stamp,"y":18.5,"rating":"extreme fear"}]}}, "2026-11-19")
    assert missing["status"] == "TARGET_DATE_NOT_FOUND" and missing["recent_points"]
    print("PASS: leading page headings and empty volume cells do not shift field mapping")
    print("PASS: CNN composite historical score/rating is matched by UTC date and latest same-day observation")


if __name__ == "__main__":
    main()
