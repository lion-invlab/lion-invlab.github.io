"""
Nasdaq-100 historical volatility data updater.

Primary constituent source:
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
from html.parser import HTMLParser

import pandas as pd
import requests
import yfinance as yf


CONSTITUENTS_URL = "https://indexes.nasdaq.com/Index/Weighting/NDX"
OUTPUT_FILE = "data/nasdaq100_volatility.json"

MIN_REQUIRED_DAYS = 95
DOWNLOAD_PERIOD = "1y"
BATCH_SIZE = 50

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)


class TableParser(HTMLParser):
    """Small stdlib-only HTML table parser."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = []
        self.tables = []
        self._table_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self.in_table = True
            self._table_depth += 1
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_table and tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("td", "th") and self.in_cell:
            value = " ".join("".join(self.current_cell).split())
            self.current_row.append(value)
            self.current_cell = []
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.current_row:
                self.tables.append(self.current_row)
            self.current_row = []
            self.in_row = False
        elif tag == "table":
            self._table_depth = max(0, self._table_depth - 1)
            if self._table_depth == 0:
                self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


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


def normalize_header(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def extract_nasdaq_rows(html):
    """
    Extract rows containing a company name and security symbol from Nasdaq's
    official NDX weighting page.

    The page is allowed to change its HTML layout. We therefore search all
    parsed table rows rather than depending on a fixed table number.
    """
    parser = TableParser()
    parser.feed(html)

    candidates = []

    for row in parser.tables:
        if len(row) < 2:
            continue

        normalized = [normalize_header(x) for x in row]

        # Typical official Nasdaq table:
        # Number | Company Name | Security Symbol
        symbol_index = None
        company_index = None

        for i, value in enumerate(normalized):
            if value in ("security symbol", "symbol", "ticker"):
                symbol_index = i
            if value in ("company name", "company"):
                company_index = i

        if symbol_index is not None and company_index is not None:
            continue  # header row

        # For data rows, infer the last short uppercase token as ticker.
        ticker = None
        ticker_index = None
        for i in range(len(row) - 1, -1, -1):
            token = str(row[i]).strip().upper()
            if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", token):
                if token not in {
                    "NDX", "NASDAQ", "NUMBER", "COMPANY", "NAME",
                    "SECURITY", "SYMBOL", "DATE", "FILTER"
                }:
                    ticker = token
                    ticker_index = i
                    break

        if not ticker or ticker_index is None:
            continue

        # Company name is normally immediately before the symbol.
        company = ""
        for i in range(ticker_index - 1, -1, -1):
            text = str(row[i]).strip()
            if text and not text.isdigit():
                company = text
                break

        if not company:
            continue

        candidates.append(
            {
                "ticker": ticker,
                "company": company,
            }
        )

    # Deduplicate while preserving order.
    seen = set()
    result = []
    for item in candidates:
        ticker = yahoo_symbol(item["ticker"])
        if ticker in seen:
            continue
        seen.add(ticker)
        result.append(
            {
                "ticker": item["ticker"],
                "yahoo_ticker": ticker,
                "company": item["company"],
            }
        )

    # The NDX represents 100 companies, but may contain slightly more
    # securities because multiple eligible share classes can be included.
    if not (95 <= len(result) <= 110):
        raise RuntimeError(
            f"Unexpected Nasdaq-100 constituent count: {len(result)}. "
            "Official Nasdaq page layout/content may have changed; "
            "refusing to write potentially incorrect data."
        )

    return result


def download_official_constituents():
    print("Loading Nasdaq-100 constituents from official Nasdaq...")
    response = requests.get(
        CONSTITUENTS_URL,
        headers={"User-Agent": UA},
        timeout=30,
    )
    response.raise_for_status()

    rows = extract_nasdaq_rows(response.text)

    print(f"Official Nasdaq constituent securities found: {len(rows)}")

    return rows


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
            "sector": None,
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
