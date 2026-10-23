#!/usr/bin/env python3
"""Test-only validator for TAC key-level inputs. Does not write files or touch JSON."""
from datetime import date
import sys
import pandas as pd
import yfinance as yf

EXPECTED_SESSION = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
TICKERS = {
    "道瓊工業指數": "^DJI",
    "S&P 500": "^GSPC",
    "Nasdaq Composite": "^IXIC",
    "費城半導體指數（SOX）": "^SOX",
    "Russell 2000": "^RUT",
}

def main():
    print(f"TAC 關鍵價位資料源測試｜預期交易日：{EXPECTED_SESSION.isoformat()}")
    print("資料來源：Yahoo Finance chart data via yfinance；所有指數一律要求指定交易日即時取數，不使用固定快照代替。")
    errors = []
    live_passes = 0
    for name, ticker in TICKERS.items():
        try:
            df = yf.download(ticker, period="10d", interval="1d", auto_adjust=False,
                             progress=False, threads=False, group_by="column")
            if df is None or df.empty:
                raise ValueError("來源回傳空資料")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index).date
            if EXPECTED_SESSION not in df.index:
                newest = max(df.index)
                raise ValueError(f"缺少指定交易日；來源最新資料日期={newest}")
            row = df.loc[EXPECTED_SESSION]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
            vals = {k: float(row[k]) for k in ("High", "Low", "Close")}
            if not all(pd.notna(v) and v > 0 for v in vals.values()):
                raise ValueError(f"OHLC 欄位缺漏或非正值：{vals}")
            if vals["High"] < vals["Low"] or not (vals["Low"] <= vals["Close"] <= vals["High"]):
                raise ValueError(f"OHLC 邏輯驗證失敗：{vals}")
            p = (vals["High"] + vals["Low"] + vals["Close"]) / 3
            r1 = 2 * p - vals["Low"]
            s1 = 2 * p - vals["High"]
            print(f"PASS｜{name}｜{EXPECTED_SESSION}｜來源 Yahoo Finance chart data via yfinance｜收盤 {vals['Close']:,.2f}｜支撐 S1 {s1:,.2f}｜中樞 P {p:,.2f}｜壓力 R1 {r1:,.2f}")
            live_passes += 1
        except Exception as exc:
            errors.append(f"{name} ({ticker}): {exc}")
            print(f"FAIL｜{name}｜待核實｜{exc}")
    print(f"即時來源取數通過：{live_passes}/{len(TICKERS)}")
    if live_passes != len(TICKERS):
        print("整體來源驗收未完成：不可用固定快照或單純計算通過取代即時取數。")
    if errors:
        print("未通過項目：")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
