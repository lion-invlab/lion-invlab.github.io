import json
import math
import os
import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

OUTPUT_FILE = "data/tac_watchlist_volatility.json"
MIN_REQUIRED_DAYS = 95
DOWNLOAD_PERIOD = "1y"
BATCH_SIZE = 50

WATCHLIST = [
    {"ticker": "TSM", "company": "Taiwan Semiconductor Manufacturing", "sector": "Information Technology"},
    {"ticker": "SKHY", "company": "SK hynix", "sector": "Information Technology"},
    {"ticker": "SPCX", "company": "ConvexityShares 1x SPIKES Futures ETF", "sector": "Other"},
    {"ticker": "AAOI", "company": "Applied Optoelectronics", "sector": "Information Technology"},
]

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
    return float(end / start - 1) if start > 0 else None

def max_drawdown(prices):
    if len(prices) < 2:
        return None
    p = pd.Series(prices).dropna()
    if len(p) < 2:
        return None
    return float((p / p.cummax() - 1).min())

def download_prices(tickers):
    all_data = {}
    for start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[start:start + BATCH_SIZE]
        print(f"Downloading {batch}")
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
                        close = pd.to_numeric(df["Close"], errors="coerce").dropna()
                        if len(close) >= MIN_REQUIRED_DAYS:
                            all_data[ticker] = close.tolist()
                    except Exception as exc:
                        print(f"  {ticker}: {exc}")
            else:
                ticker = batch[0]
                if "Close" in data.columns:
                    close = pd.to_numeric(data["Close"], errors="coerce").dropna()
                    if len(close) >= MIN_REQUIRED_DAYS:
                        all_data[ticker] = close.tolist()
        except Exception as exc:
            print(f"  Batch error: {exc}")
        time.sleep(2)
    return all_data

def main():
    tickers = [x["ticker"] for x in WATCHLIST]
    prices = download_prices(tickers)
    results = []
    for item in WATCHLIST:
        ticker = item["ticker"]
        p = prices.get(ticker)
        record = {
            "ticker": ticker,
            "yahoo_ticker": ticker,
            "company": item["company"],
            "sector": item["sector"],
            "source_group": "TAC Watchlist",
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
        if p is None:
            results.append(record)
            continue
        p = [float(x) for x in p if x is not None and float(x) > 0]
        record["price_days"] = len(p)
        if len(p) < MIN_REQUIRED_DAYS:
            results.append(record)
            continue
        record["price"] = p[-1]
        record["vol_90d"] = annualized_volatility(p, 90)
        record["vol_60d"] = annualized_volatility(p, 60)
        record["vol_30d"] = annualized_volatility(p, 30)
        record["vol_20d"] = annualized_volatility(p, 20)
        record["return_90d"] = period_return(p, 90)
        record["max_drawdown_90d"] = max_drawdown(p[-91:])
        if record["vol_20d"] is not None and record["vol_90d"] not in (None, 0):
            record["vol_ratio_20d_90d"] = record["vol_20d"] / record["vol_90d"]
        record["valid"] = record["vol_90d"] is not None
        results.append(record)

    valid = [x for x in results if x["valid"]]
    vols = [x["vol_90d"] for x in valid]
    output = {
        "meta": {
            "title": "TAC Custom Watchlist Historical Volatility",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "calculation": "std(log(Pt/Pt-1)) * sqrt(252)",
            "windows": [90, 60, 30, 20],
            "price_source": "Yahoo Finance historical daily data",
            "constituent_source": "TAC custom watchlist",
            "data_type": "actual",
            "demo_data": False,
        },
        "summary": {
            "constituents": len(results),
            "valid": len(valid),
            "average_vol_90d": float(sum(vols) / len(vols)) if vols else None,
            "median_vol_90d": float(pd.Series(vols).median()) if vols else None,
            "max_vol_90d": max(vols) if vols else None,
            "min_vol_90d": min(vols) if vols else None,
        },
        "data_quality": {
            "constituent_count": len(results),
            "valid_count": len(valid),
            "missing_count": len(results) - len(valid),
            "coverage": len(valid) / len(results) if results else 0,
        },
        "stocks": results,
    }
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {OUTPUT_FILE}: {len(valid)}/{len(results)} valid")

if __name__ == "__main__":
    main()
