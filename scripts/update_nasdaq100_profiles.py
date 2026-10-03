import json, math, os, time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

PROFILE_OUTPUT = Path("data/company_profiles.json")
NDX_DATA = Path("data/nasdaq100_volatility.json")
TEMP = Path("data/company_profiles.tmp.json")

SLEEP_SECONDS = 0.75
RETRIES = 3

# Confirmed Nasdaq-100 securities currently absent from the volatility JSON.
# These are included for company profiles only; this script does not change
# Nasdaq-100 volatility data.
EXTRA_NDX = {
    "TSM": {
        "company": "Taiwan Semiconductor Manufacturing Company Ltd.",
        "sector": "Technology",
    },
    "SKHY": {
        "company": "SK hynix Inc.",
        "sector": "Technology",
    },
}


def now():
    return datetime.now(timezone.utc).isoformat()


def num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def txt(x):
    if x is None:
        return None
    x = str(x).strip()
    return x or None


def yahoo_symbol(s):
    return str(s).strip().replace(".", "-")


def load_json(path, default):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save(data):
    PROFILE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with TEMP.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(TEMP, PROFILE_OUTPUT)


def stmt_value(df, names):
    if df is None or getattr(df, "empty", True):
        return None, None
    for name in names:
        if name not in df.index:
            continue
        row = df.loc[name]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        for period in row.index:
            value = num(row.loc[period])
            if value is not None:
                return value, str(period)
    return None, None


def yoy(df, names):
    if df is None or getattr(df, "empty", True):
        return None, None
    for name in names:
        if name not in df.index:
            continue
        row = df.loc[name]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        values = []
        for period in row.index:
            value = num(row.loc[period])
            if value is not None:
                values.append((str(period), value))
        if len(values) >= 2 and values[1][1] != 0:
            return values[0][1] / values[1][1] - 1, f"{values[0][0]} vs {values[1][0]}"
    return None, None


def fetch_one(yahoo_ticker, original, fallback_company, fallback_sector):
    last_error = None

    for attempt in range(1, RETRIES + 1):
        try:
            t = yf.Ticker(yahoo_ticker)
            info = t.get_info()
            income = t.get_income_stmt(freq="yearly")
            balance = t.get_balance_sheet(freq="yearly")
            cashflow = t.get_cash_flow(freq="yearly")

            revenue, rev_period = stmt_value(
                income, ["TotalRevenue", "OperatingRevenue"]
            )
            growth, growth_period = yoy(
                income, ["TotalRevenue", "OperatingRevenue"]
            )
            gross, gross_period = stmt_value(income, ["GrossProfit"])
            op_income, op_period = stmt_value(
                income, ["OperatingIncome", "OperatingIncomeLoss"]
            )
            net_income, net_period = stmt_value(
                income, ["NetIncome", "NetIncomeCommonStockholders"]
            )
            eps, eps_period = stmt_value(
                income, ["DilutedEPS", "BasicEPS"]
            )
            ocf, ocf_period = stmt_value(
                cashflow,
                ["OperatingCashFlow", "TotalCashFromOperatingActivities"],
            )
            capex, capex_period = stmt_value(
                cashflow, ["CapitalExpenditure", "CapitalExpenditureReported"]
            )
            cash, cash_period = stmt_value(
                balance,
                ["CashCashEquivalentsAndShortTermInvestments",
                 "CashAndCashEquivalents"],
            )
            debt, debt_period = stmt_value(balance, ["TotalDebt"])
            ca, ca_period = stmt_value(balance, ["CurrentAssets"])
            cl, cl_period = stmt_value(balance, ["CurrentLiabilities"])

            trailing_pe = num(info.get("trailingPE"))
            if trailing_pe is not None and trailing_pe <= 0:
                trailing_pe = None

            forward_pe = num(info.get("forwardPE"))
            if forward_pe is not None and forward_pe <= 0:
                forward_pe = None

            return {
                "ticker": original,
                "yahoo_ticker": yahoo_ticker,
                "company": txt(info.get("longName") or info.get("shortName")
                               or fallback_company),
                "sector": txt(info.get("sector") or fallback_sector),
                "industry": txt(info.get("industry")),
                "industry_key": txt(info.get("industryKey")),
                "location": {
                    "city": txt(info.get("city")),
                    "state": txt(info.get("state")),
                    "country": txt(info.get("country")),
                },
                "website": txt(info.get("website")),
                "business": {
                    "summary": txt(info.get("longBusinessSummary")),
                    "employees": info.get("fullTimeEmployees"),
                },
                "competitive_advantages": None,
                "competitive_advantages_source": None,
                "competitive_advantages_status":
                    "待以最新10-K／公司IR公開資料整理；目前不做推論",
                "financials": {
                    "revenue": revenue,
                    "revenue_growth_yoy": growth,
                    "gross_margin": gross / revenue
                    if revenue and gross is not None else None,
                    "operating_margin": op_income / revenue
                    if revenue and op_income is not None else None,
                    "net_margin": net_income / revenue
                    if revenue and net_income is not None else None,
                    "eps_diluted": eps,
                    "roe": num(info.get("returnOnEquity")),
                    "roa": num(info.get("returnOnAssets")),
                    "operating_cash_flow": ocf,
                    "free_cash_flow": ocf + capex
                    if ocf is not None and capex is not None else None,
                    "cash": cash,
                    "total_debt": debt,
                    "debt_to_equity": num(info.get("debtToEquity")),
                    "current_ratio": ca / cl
                    if ca is not None and cl not in (None, 0) else None,
                },
                "valuation": {
                    "market_cap": num(info.get("marketCap")),
                    "trailing_pe": trailing_pe,
                    "forward_pe": forward_pe,
                    "price_to_book": num(info.get("priceToBook")),
                    "price_to_sales": num(
                        info.get("priceToSalesTrailing12Months")
                    ),
                    "peg_ratio": num(info.get("pegRatio")),
                    "ev_to_ebitda": num(info.get("enterpriseToEbitda")),
                    "price_to_fcf": None,
                    "dividend_yield": num(info.get("dividendYield")),
                },
                "market": {
                    "current_price": num(
                        info.get("currentPrice")
                        or info.get("regularMarketPrice")
                    ),
                    "currency": txt(info.get("currency")),
                },
                "periods": {
                    "revenue": rev_period,
                    "revenue_growth": growth_period,
                    "gross_profit": gross_period,
                    "operating_income": op_period,
                    "net_income": net_period,
                    "eps": eps_period,
                    "operating_cash_flow": ocf_period,
                    "capex": capex_period,
                    "cash": cash_period,
                    "total_debt": debt_period,
                    "current_assets": ca_period,
                    "current_liabilities": cl_period,
                },
                "indexes": ["Nasdaq-100"],
                "source": {
                    "profile_and_market": "Yahoo Finance via yfinance",
                    "financial_statements": "Yahoo Finance via yfinance",
                    "constituent_source": "Nasdaq-100",
                    "fetched_at_utc": now(),
                },
            }
        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(attempt * 2)

    raise last_error


def load_ndx_universe():
    data = load_json(NDX_DATA, {})
    stocks = data.get("stocks", [])
    universe = {}

    for row in stocks:
        ticker = txt(row.get("ticker"))
        if not ticker:
            continue
        universe[ticker.upper()] = {
            "company": txt(row.get("company")) or ticker.upper(),
            "sector": txt(row.get("sector")),
        }

    universe.update(EXTRA_NDX)
    return universe


def main():
    print("Nasdaq-100 Company Profiles Supplement")

    profiles = load_json(
        PROFILE_OUTPUT,
        {"meta": {}, "data_quality": {}, "companies": {}},
    )
    companies = profiles.setdefault("companies", {})
    universe = load_ndx_universe()

    total = len(universe)
    existing = 0
    added = 0
    failed = 0

    for i, (ticker, meta) in enumerate(sorted(universe.items()), 1):
        if ticker in companies:
            companies[ticker].setdefault("indexes", [])
            if "Nasdaq-100" not in companies[ticker]["indexes"]:
                companies[ticker]["indexes"].append("Nasdaq-100")
            existing += 1
            print(f"[{i}/{total}] EXISTS {ticker}")
            continue

        try:
            companies[ticker] = fetch_one(
                yahoo_symbol(ticker),
                ticker,
                meta["company"],
                meta.get("sector"),
            )
            added += 1
            print(f"[{i}/{total}] ADDED {ticker}")
        except Exception as exc:
            failed += 1
            print(f"[{i}/{total}] FAILED {ticker}: {exc}")

        if i % 10 == 0:
            profiles["meta"] = {
                "title": "S&P 500 + Nasdaq-100 Company Profiles",
                "updated_at_utc": now(),
                "data_type": "actual",
                "demo_data": False,
                "profile_source": "Yahoo Finance via yfinance",
                "constituent_source": "S&P 500 existing cache + Nasdaq-100",
            }
            profiles["data_quality"] = {
                "nasdaq100_universe": total,
                "already_existing": existing,
                "newly_added_this_run": added,
                "failed_this_run": failed,
                "nasdaq100_profile_coverage":
                    (existing + added) / total if total else 0,
            }
            save(profiles)

        time.sleep(SLEEP_SECONDS)

    profiles["meta"] = {
        "title": "S&P 500 + Nasdaq-100 Company Profiles",
        "updated_at_utc": now(),
        "data_type": "actual",
        "demo_data": False,
        "profile_source": "Yahoo Finance via yfinance",
        "constituent_source": "S&P 500 existing cache + Nasdaq-100",
    }
    profiles["data_quality"] = {
        "nasdaq100_universe": total,
        "already_existing": existing,
        "newly_added_this_run": added,
        "failed_this_run": failed,
        "nasdaq100_profile_coverage":
            (existing + added) / total if total else 0,
    }
    save(profiles)

    print(
        f"Completed: NDX universe={total}, existing={existing}, "
        f"added={added}, failed={failed}"
    )

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
