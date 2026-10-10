"""
Nasdaq-100 historical volatility data updater.

Primary constituent source:
    Nasdaq official API endpoint on api.nasdaq.com
    https://api.nasdaq.com/api/quote/list-type/nasdaq100

Reference:
    Nasdaq Global Indexes - NDX Weighting
    https://indexes.nasdaq.com/Index/Weighting/NDX

Price source:
    Yahoo Finance historical daily data

Calculation:
    HV_N = std(log(Pt / Pt-1)) * sqrt(252)

Output:
    data/nasdaq100_volatility.json

Important:
- This script does NOT modify the existing S&P 500 pipeline.
- If Nasdaq's official constituent page cannot be parsed, the script FAILS
  rather than silently using a stale or guessed constituent list.
- Missing price history is recorded as null / valid=False; no estimates.
"""

import json
import math
import os
import re
import time
from datetime import datetime, timezone
from datetime import date, datetime, timezone

import pandas as pd
import requests
import yfinance as yf


CONSTITUENTS_URL = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
OFFICIAL_WEIGHTING_URL = "https://indexes.nasdaq.com/Index/Weighting/NDX"
OUTPUT_FILE = "data/nasdaq100_volatility.json"

# Canonical 11 GICS sectors. Prefer the already-validated S&P 500 dataset
# for constituents shared by both indexes; use reviewed overrides only for
# Nasdaq-100 constituents outside the S&P 500.
VALID_GICS_SECTORS = {
    "Communication Services", "Consumer Discretionary", "Consumer Staples",
    "Energy", "Financials", "Health Care", "Industrials",
    "Information Technology", "Materials", "Real Estate", "Utilities",
}
NON_SP500_SECTOR_OVERRIDES = {
    "ASML": "Information Technology",
    "MSTR": "Information Technology",
    "ALNY": "Health Care",
    "MELI": "Consumer Discretionary",
    "NBIS": "Information Technology",
    "SHOP": "Information Technology",
    "CCEP": "Consumer Staples",
    "PDD": "Consumer Discretionary",
    "RKLB": "Industrials",
    "ARM": "Information Technology",
    "TRI": "Industrials",
    "FER": "Industrials",
    "ALAB": "Information Technology",
    "CRWV": "Information Technology",
    "SPCX": "Industrials",
}


def load_sector_map():
    """Load validated S&P 500 GICS classifications and add reviewed exceptions."""
    sectors = {}
    try:
        with open("data/sp500_volatility.json", encoding="utf-8") as f:
            sp = json.load(f)
        for stock in sp.get("stocks", []):
            ticker = str(stock.get("ticker", "")).strip().upper()
            sector = stock.get("sector")
            if ticker and sector in VALID_GICS_SECTORS:
                sectors[ticker] = sector
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Cannot load data/sp500_volatility.json for sector fallback; "
            "refusing to write Nasdaq data with missing sectors."
        ) from exc

    sectors.update(NON_SP500_SECTOR_OVERRIDES)
    return sectors

MIN_REQUIRED_DAYS = 95
DOWNLOAD_PERIOD = "1y"
BATCH_SIZE = 50

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)


def yahoo_symbol(symbol):
    """Yahoo Finance ticker conversion for common share-class notation."""
    return str(symbol).strip().replace(".", "-")


def annualized_volatility(prices, window):
    if len(prices) < window + 1:
        return None

    p = pd.Series(prices).dropna().tail(window + 1)
    if len(p) < window + 1:
        return None

    returns = (p / p.shift(1)).apply(math.log).dropna()
    if len(returns) < window:
        return None

    return float(returns.std(ddof=1) * math.sqrt(252))


def period_return(prices, window):
    if len(prices) < window + 1:
        return None

    p = pd.Series(prices).dropna()
    if len(p) < window + 1:
        return None

    start = float(p.iloc[-window - 1])
    end = float(p.iloc[-1])

    if start <= 0:
        return None

    return float(end / start - 1)


def max_drawdown(prices):
    if len(prices) < 2:
        return None

    p = pd.Series(prices).dropna()
    if len(p) < 2:
        return None

    running_max = p.cummax()
    drawdown = p / running_max - 1
    return float(drawdown.min())


def clean_company_name(value):
    name = str(value).strip()
    # Keep the official Nasdaq name, but remove the generic security suffix
    # so the Dashboard displays a cleaner company name.
    name = re.sub(
        r"\\s+(Common Stock|Class A Common Stock|Class B Common Stock|"
        r"Class C Capital Stock|Ordinary Shares|American Depositary Shares)$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    return name.strip()


def download_official_constituents():
    """
    Retrieve the Nasdaq-100 security list from Nasdaq's own API endpoint.

    The public Nasdaq weighting page is dynamically rendered, so the old
    HTML-table parser could see zero rows inside GitHub Actions. The
    api.nasdaq.com endpoint returns the component list as JSON and is hosted
    on Nasdaq's own domain.

    Nasdaq announced on 2026-10-01 that MRNA will replace WBD effective
    before market open on 2026-10-09. We apply that announced effective-date
    change locally so the pipeline does not wait for a stale API snapshot.
    """
    print("Loading Nasdaq-100 constituents from Nasdaq...")

    response = requests.get(
        CONSTITUENTS_URL,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": OFFICIAL_WEIGHTING_URL,
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    rows = (
        payload.get("data", {})
        .get("data", {})
        .get("rows", [])
    )

    if not rows:
        raise RuntimeError(
            "Nasdaq API returned no constituent rows; "
            "refusing to write potentially incorrect data."
        )

    api_date = payload.get("data", {}).get("date")

    constituents = []
    seen = set()

    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        company = clean_company_name(row.get("companyName", ""))

        if not symbol or not company:
            continue

        yahoo_ticker = yahoo_symbol(symbol)

        if yahoo_ticker in seen:
            continue

        seen.add(yahoo_ticker)
        constituents.append(
            {
                "ticker": symbol,
                "yahoo_ticker": yahoo_ticker,
                "company": company,
            }
        )

    # Nasdaq's API may temporarily lag the live GIW page. The latest
    # announced constituent change is effective 2026-10-09.
    effective_date = date(2026, 10, 9)

    symbols = {x["ticker"] for x in constituents}

    if date.today() >= effective_date:
        constituents = [
            x for x in constituents
            if x["ticker"] != "WBD"
        ]

        if "MRNA" not in symbols:
            constituents.append(
                {
                    "ticker": "MRNA",
                    "yahoo_ticker": "MRNA",
                    "company": "Moderna, Inc.",
                }
            )

    # The Nasdaq-100 can have more than 100 securities because multiple
    # share classes can be represented. Nasdaq's current fact sheet reports
    # 101 securities. Refuse obviously broken responses.
    if not (95 <= len(constituents) <= 110):
        raise RuntimeError(
            f"Unexpected Nasdaq-100 constituent count: {len(constituents)}. "
            "Refusing to write potentially incorrect data."
        )

    print(
        f"Nasdaq API snapshot date: {api_date}; "
        f"constituent securities after announced changes: {len(constituents)}"
    )

    if date.today() < effective_date:
        print("Scheduled change: MRNA replaces WBD effective 2026-10-09.")

    return constituents

def download_prices(tickers):
    print(f"Downloading {len(tickers)} tickers from Yahoo Finance...")

    all_data = {}

    for start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[start:start + BATCH_SIZE]

        print(
            f"Batch {start + 1}-"
            f"{min(start + BATCH_SIZE, len(tickers))}"
        )

        try:
            data = yf.download(
                tickers=batch,
                period=DOWNLOAD_PERIOD,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
                group_by="ticker",
                timeout=30,
            )

            if data is None or data.empty:
                print("  No data returned")
                continue

            if isinstance(data.columns, pd.MultiIndex):
                for ticker in batch:
                    try:
                        if ticker not in data.columns.get_level_values(0):
                            continue

                        df = data[ticker]

                        if "Close" not in df.columns:
                            continue

                        close = (
                            pd.to_numeric(
                                df["Close"],
                                errors="coerce",
                            )
                            .dropna()
                        )

                        if len(close) >= MIN_REQUIRED_DAYS:
                            all_data[ticker] = close.tolist()

                    except Exception as exc:
                        print(f"  {ticker}: {exc}")

            else:
                ticker = batch[0]

                if "Close" in data.columns:
                    close = (
                        pd.to_numeric(
                            data["Close"],
                            errors="coerce",
                        )
                        .dropna()
                    )

                    if len(close) >= MIN_REQUIRED_DAYS:
                        all_data[ticker] = close.tolist()

        except Exception as exc:
            print(f"  Batch error: {exc}")

        time.sleep(2)

    return all_data


def main():
    print("=" * 60)
    print("Nasdaq-100 90D Volatility Update")
    print("=" * 60)

    constituents = download_official_constituents()
    sector_map = load_sector_map()

    # Fail before downloading/writing if any newly added constituent lacks a
    # reviewed sector mapping. Never publish null/unknown sector values.
    missing_sector = [
        row["ticker"] for row in constituents
        if sector_map.get(row["ticker"]) not in VALID_GICS_SECTORS
    ]
    if missing_sector:
        raise RuntimeError(
            "Missing GICS sector mapping for: "
            + ", ".join(missing_sector)
            + ". Update NON_SP500_SECTOR_OVERRIDES before publishing."
        )

    tickers = [row["yahoo_ticker"] for row in constituents]

    price_data = download_prices(tickers)

    print(f"Successful price series: {len(price_data)}")

    results = []

    for row in constituents:
        original_symbol = str(row["ticker"])
        ticker = str(row["yahoo_ticker"])
        prices = price_data.get(ticker)

        record = {
            "ticker": original_symbol,
            "yahoo_ticker": ticker,
            "company": str(row["company"]),
            "sector": sector_map[original_symbol],
            "price": None,
            "vol_90d": None,
            "vol_60d": None,
            "vol_30d": None,
            "vol_20d": None,
            "return_90d": None,
            "max_drawdown_90d": None,
            "vol_ratio_20d_90d": None,
            "valid": False,
            "price_days": 0,
        }

        if prices is None:
            results.append(record)
            continue

        prices = [
            float(x)
            for x in prices
            if x is not None and float(x) > 0
        ]

        record["price_days"] = len(prices)

        if len(prices) < MIN_REQUIRED_DAYS:
            results.append(record)
            continue

        record["price"] = prices[-1]

        record["vol_90d"] = annualized_volatility(prices, 90)
        record["vol_60d"] = annualized_volatility(prices, 60)
        record["vol_30d"] = annualized_volatility(prices, 30)
        record["vol_20d"] = annualized_volatility(prices, 20)

        record["return_90d"] = period_return(prices, 90)

        recent_90 = prices[-91:]
        record["max_drawdown_90d"] = max_drawdown(recent_90)

        if (
            record["vol_20d"] is not None
            and record["vol_90d"] is not None
            and record["vol_90d"] > 0
        ):
            record["vol_ratio_20d_90d"] = (
                record["vol_20d"] / record["vol_90d"]
            )

        if record["vol_90d"] is not None:
            record["valid"] = True

        results.append(record)

    invalid_sectors = [
        r["ticker"] for r in results
        if r.get("sector") not in VALID_GICS_SECTORS
    ]
    if invalid_sectors:
        raise RuntimeError(
            "Invalid GICS sector values remain: " + ", ".join(invalid_sectors)
        )

    valid_records = [r for r in results if r["valid"]]

    vols = [
        r["vol_90d"]
        for r in valid_records
        if r["vol_90d"] is not None
    ]

    returns = [
        r["return_90d"]
        for r in valid_records
        if r["return_90d"] is not None
    ]

    if vols:
        average_vol = float(sum(vols) / len(vols))
        median_vol = float(pd.Series(vols).median())
        max_vol = float(max(vols))
        min_vol = float(min(vols))
    else:
        average_vol = None
        median_vol = None
        max_vol = None
        min_vol = None

    if returns:
        median_return = float(pd.Series(returns).median())
        positive = sum(1 for x in returns if x > 0)
        negative = sum(1 for x in returns if x < 0)
    else:
        median_return = None
        positive = 0
        negative = 0

    valid_count = len(valid_records)

    data_quality = {
        "constituent_count": len(results),
        "valid_count": valid_count,
        "missing_count": len(results) - valid_count,
        "coverage": (
            valid_count / len(results)
            if results
            else 0
        ),
    }

    output = {
        "meta": {
            "title": "Nasdaq-100 90D Historical Volatility",
            "index": "NDX",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "calculation": "std(log(Pt/Pt-1)) * sqrt(252)",
            "windows": [90, 60, 30, 20],
            "price_source": "Yahoo Finance historical daily data",
            "constituent_source": (
                "Nasdaq Global Indexes - NDX Weighting"
            ),
            "constituent_url": CONSTITUENTS_URL,
            "official_weighting_page": OFFICIAL_WEIGHTING_URL,
            "data_type": "actual",
            "demo_data": False,
        },
        "summary": {
            "constituents": len(results),
            "valid": valid_count,
            "average_vol_90d": average_vol,
            "median_vol_90d": median_vol,
            "max_vol_90d": max_vol,
            "min_vol_90d": min_vol,
            "median_return_90d": median_return,
            "positive_90d": positive,
            "negative_90d": negative,
        },
        "data_quality": data_quality,
        "stocks": results,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 60)
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Valid stocks: {valid_count}/{len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
