import json
import math
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
import requests


# ============================================================
# S&P 500 Volatility Data Updater
# 不使用 Nasdaq Data Link
# 使用：
# 1. GitHub S&P 500 constituent list
# 2. Yahoo Finance historical daily prices
#
# Historical Volatility:
# HV = std(log(Pt / Pt-1)) × sqrt(252)
# ============================================================

CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/"
    "chinobing/historical_sp500_constituents/main/"
    "sp500_constituents.csv"
)

OUTPUT_FILE = "data/sp500_volatility.json"

LOOKBACK_DAYS = 180
MIN_REQUIRED_DAYS = 95

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)


def yahoo_symbol(symbol):
    """
    Yahoo Finance ticker conversion.
    BRK.B -> BRK-B
    BF.B  -> BF-B
    """
    return symbol.strip().replace(".", "-")


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


def download_prices(tickers):
    """
    Download daily adjusted prices in batches.
    yfinance uses Yahoo Finance historical data.
    """

    print(f"Downloading {len(tickers)} tickers...")

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    all_data = {}

    batch_size = 50

    for start in range(0, len(tickers), batch_size):

        batch = tickers[start:start + batch_size]

        print(
            f"Batch {start + 1}-"
            f"{min(start + batch_size, len(tickers))}"
        )

        try:
            data = yf.download(
                tickers=batch,
                period="1y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
                group_by="ticker",
                timeout=30
            )

            if data is None or data.empty:
                print("  No data returned")
                continue

            # Multiple ticker download
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
                                errors="coerce"
                            )
                            .dropna()
                        )

                        if len(close) >= MIN_REQUIRED_DAYS:
                            all_data[ticker] = close.tolist()

                    except Exception as e:
                        print(f"  {ticker}: {e}")

            else:
                # Single ticker fallback
                ticker = batch[0]

                if "Close" in data.columns:

                    close = (
                        pd.to_numeric(
                            data["Close"],
                            errors="coerce"
                        )
                        .dropna()
                    )

                    if len(close) >= MIN_REQUIRED_DAYS:
                        all_data[ticker] = close.tolist()

        except Exception as e:
            print(f"Batch error: {e}")

        # Avoid Yahoo rate limiting
        time.sleep(2)

    return all_data


def main():

    print("=" * 60)
    print("S&P 500 90D Volatility Update")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Download current S&P 500 constituents
    # --------------------------------------------------------

    print("Loading S&P 500 constituents...")

    response = requests.get(
        CONSTITUENTS_URL,
        headers={"User-Agent": UA},
        timeout=30
    )

    response.raise_for_status()

    from io import StringIO

    constituents = pd.read_csv(
        StringIO(response.text)
    )

    constituents.columns = [
        c.strip().lower().replace(" ", "_")
        for c in constituents.columns
    ]

    required_columns = [
        "symbol",
        "security",
        "gics_sector"
    ]

    for column in required_columns:
        if column not in constituents.columns:
            raise RuntimeError(
                f"Missing required column: {column}"
            )

    constituents = constituents.dropna(
        subset=["symbol"]
    )

    constituents = constituents.drop_duplicates(
        subset=["symbol"]
    )

    print(
        f"S&P 500 constituents: "
        f"{len(constituents)}"
    )

    # --------------------------------------------------------
    # 2. Convert tickers for Yahoo Finance
    # --------------------------------------------------------

    constituents["yahoo_symbol"] = (
        constituents["symbol"]
        .astype(str)
        .map(yahoo_symbol)
    )

    tickers = (
        constituents["yahoo_symbol"]
        .tolist()
    )

    # --------------------------------------------------------
    # 3. Download historical prices
    # --------------------------------------------------------

    price_data = download_prices(tickers)

    print(
        f"Successful price series: "
        f"{len(price_data)}"
    )

    # --------------------------------------------------------
    # 4. Calculate volatility
    # --------------------------------------------------------

    results = []

    cutoff_date = None

    for _, row in constituents.iterrows():

        original_symbol = str(row["symbol"])
        ticker = str(row["yahoo_symbol"])

        prices = price_data.get(ticker)

        record = {
            "ticker": original_symbol,
            "yahoo_ticker": ticker,
            "company": str(row["security"]),
            "sector": str(row["gics_sector"]),
            "price": None,
            "vol_90d": None,
            "vol_60d": None,
            "vol_30d": None,
            "vol_20d": None,
            "return_90d": None,
            "max_drawdown_90d": None,
            "vol_ratio_20d_90d": None,
            "valid": False,
            "price_days": 0
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

        record["vol_90d"] = annualized_volatility(
            prices, 90
        )

        record["vol_60d"] = annualized_volatility(
            prices, 60
        )

        record["vol_30d"] = annualized_volatility(
            prices, 30
        )

        record["vol_20d"] = annualized_volatility(
            prices, 20
        )

        record["return_90d"] = period_return(
            prices, 90
        )

        recent_90 = prices[-91:]

        record["max_drawdown_90d"] = max_drawdown(
            recent_90
        )

        if (
            record["vol_20d"] is not None
            and record["vol_90d"] is not None
            and record["vol_90d"] > 0
        ):
            record["vol_ratio_20d_90d"] = (
                record["vol_20d"]
                / record["vol_90d"]
            )

        if record["vol_90d"] is not None:
            record["valid"] = True

        results.append(record)

    # --------------------------------------------------------
    # 5. Summary
    # --------------------------------------------------------

    valid_records = [
        r for r in results
        if r["valid"]
    ]

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
        average_vol = float(
            sum(vols) / len(vols)
        )

        median_vol = float(
            pd.Series(vols).median()
        )

        max_vol = float(max(vols))
        min_vol = float(min(vols))

    else:
        average_vol = None
        median_vol = None
        max_vol = None
        min_vol = None

    if returns:
        median_return = float(
            pd.Series(returns).median()
        )

        positive = sum(
            1 for x in returns
            if x > 0
        )

        negative = sum(
            1 for x in returns
            if x < 0
        )

    else:
        median_return = None
        positive = 0
        negative = 0

    # --------------------------------------------------------
    # 6. Data quality
    # --------------------------------------------------------

    valid_count = len(valid_records)

    data_quality = {
        "constituent_count": len(results),
        "valid_count": valid_count,
        "missing_count": (
            len(results) - valid_count
        ),
        "coverage": (
            valid_count / len(results)
            if results
            else 0
        )
    }

    # --------------------------------------------------------
    # 7. Final JSON
    # --------------------------------------------------------

    output = {
        "meta": {
            "title": "S&P 500 90D Historical Volatility",
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "calculation": (
                "std(log(Pt/Pt-1)) * sqrt(252)"
            ),
            "windows": [
                90,
                60,
                30,
                20
            ],
            "price_source": (
                "Yahoo Finance historical daily data"
            ),
            "constituent_source": (
                "GitHub historical_sp500_constituents"
            ),
            "data_type": "actual",
            "demo_data": False
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
            "negative_90d": negative
        },

        "data_quality": data_quality,

        "stocks": results
    }

    # --------------------------------------------------------
    # 8. Write output
    # --------------------------------------------------------

    import os

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("=" * 60)
    print(
        f"Saved: {OUTPUT_FILE}"
    )

    print(
        f"Valid stocks: "
        f"{valid_count}/{len(results)}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
