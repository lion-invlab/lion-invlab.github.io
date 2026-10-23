#!/usr/bin/env python3
"""Diagnostic-only probe of public SOX pages. Never supplies production quote values."""
import re
import requests

URLS = {
    "Nasdaq official overview (omx)": "https://indexes.nasdaqomx.com/Index/Overview/SOX",
    "Nasdaq official overview (indexes)": "https://indexes.nasdaq.com/index/overview/SOX",
    "Nasdaq official history": "https://indexes.nasdaq.com/Index/History/SOX",
    "FRED daily close (Nasdaq source)": "https://fred.stlouisfed.org/data/NASDAQSOX",
}

def clean(value):
    return re.sub(r"\s+", " ", value).strip()

def show_context(html, label, before=120, after=420):
    pos = html.lower().find(label.lower())
    if pos < 0:
        print(f"HTML context {label}｜not found")
        return
    print(f"HTML context {label}｜{clean(html[max(0, pos-before):pos+after])}")

def main():
    print("SOX 公開來源穩定性探測｜僅診斷，不輸出正式行情")
    sessions = requests.Session()
    sessions.headers.update({"User-Agent": "Mozilla/5.0 (compatible; TACSourceProbe/1.1)"})
    for name, url in URLS.items():
        print(f"\nSOURCE｜{name}\nURL｜{url}")
        try:
            response = sessions.get(url, timeout=(5, 15))
            print(f"HTTP｜{response.status_code}｜bytes={len(response.content)}")
            response.raise_for_status()
            html = response.text
            if "fred.stlouisfed.org/data/NASDAQSOX" in url:
                rows = re.findall(r"(?m)^\s*(\d{4}-\d{2}-\d{2})\s+([0-9.]+|\.)\s*$", html)
                print("FRED 最近日期與收盤列｜" + (str(rows[-5:]) if rows else "未解析到純文字日期列"))
            else:
                date_matches = re.findall(r"DATA AS OF\s*([^<]+)", html, flags=re.I)
                print("DATA AS OF 原始匹配｜" + (str([clean(x) for x in date_matches[:3]]) if date_matches else "未匹配"))
                print("頁面包含 SOX｜" + str("PHLX Semiconductor" in html or "SOX" in html))
                for label in ("trend-data", "data-previous-close", "data-todays-high", "data-todays-low", "Day High", "Day Low", "Previous Close"):
                    show_context(html, label, 100, 360)
        except Exception as exc:
            print(f"ERROR｜{type(exc).__name__}: {exc}")
    print("\n判讀｜本工具僅診斷公開來源欄位及連線狀態，不把結果寫入早報或 JSON。正式採用前仍需確認日期、收盤、高低價欄位及跨來源一致性。")

if __name__ == "__main__":
    main()
