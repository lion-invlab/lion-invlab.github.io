"""
Validate data/company_profiles.json before GitHub Actions commits it.

The validator is intentionally conservative:
- required top-level structure must exist
- constituent coverage must be >= 90%
- no demo flag
- every company must have ticker/company/sector fields
- malformed numeric fields are rejected
- missing financial/valuation values are allowed and remain null
"""

import json
import math
import sys
from pathlib import Path

FILE = Path("data/company_profiles.json")
MIN_COVERAGE = 0.90


def is_number_or_none(value):
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def fail(message):
    print(f"VALIDATION FAILED: {message}")
    sys.exit(1)


def main():
    if not FILE.exists():
        fail(f"{FILE} does not exist")

    try:
        with FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        fail(f"invalid JSON: {exc}")

    if not isinstance(data, dict):
        fail("root must be an object")

    for key in ("meta", "data_quality", "companies"):
        if key not in data:
            fail(f"missing top-level key: {key}")

    meta = data["meta"]
    quality = data["data_quality"]
    companies = data["companies"]

    if meta.get("demo_data") is True:
        fail("demo_data is true")

    if not isinstance(companies, dict) or not companies:
        fail("companies is empty")

    constituent_count = quality.get("constituent_count")
    coverage = quality.get("coverage")

    if not isinstance(constituent_count, int) or constituent_count <= 0:
        fail("invalid constituent_count")

    if not is_number_or_none(coverage):
        fail("invalid coverage")

    if float(coverage) < MIN_COVERAGE:
        fail(
            f"coverage {float(coverage):.2%} is below "
            f"required {MIN_COVERAGE:.0%}"
        )

    required_company_fields = ("ticker", "company", "sector")

    numeric_paths = (
        ("financials", "revenue"),
        ("financials", "revenue_growth_yoy"),
        ("financials", "gross_margin"),
        ("financials", "operating_margin"),
        ("financials", "net_margin"),
        ("financials", "eps_diluted"),
        ("financials", "roe"),
        ("financials", "roa"),
        ("financials", "operating_cash_flow"),
        ("financials", "free_cash_flow"),
        ("financials", "cash"),
        ("financials", "total_debt"),
        ("financials", "debt_to_equity"),
        ("financials", "current_ratio"),
        ("valuation", "market_cap"),
        ("valuation", "trailing_pe"),
        ("valuation", "forward_pe"),
        ("valuation", "price_to_book"),
        ("valuation", "price_to_sales"),
        ("valuation", "peg_ratio"),
        ("valuation", "ev_to_ebitda"),
        ("valuation", "price_to_fcf"),
        ("valuation", "dividend_yield"),
        ("market", "current_price"),
    )

    checked = 0

    for ticker, record in companies.items():
        if not isinstance(record, dict):
            fail(f"{ticker}: record is not an object")

        for field in required_company_fields:
            if not record.get(field):
                fail(f"{ticker}: missing {field}")

        for group, field in numeric_paths:
            group_data = record.get(group, {})
            if not isinstance(group_data, dict):
                fail(f"{ticker}: {group} is not an object")
            if not is_number_or_none(group_data.get(field)):
                fail(f"{ticker}: {group}.{field} is not numeric/null")

        checked += 1

    print("VALIDATION PASSED")
    print(f"Constituents: {constituent_count}")
    print(f"Company records: {checked}")
    print(f"Coverage: {float(coverage):.2%}")
    print("Missing individual metrics are allowed and remain null.")


if __name__ == "__main__":
    main()
