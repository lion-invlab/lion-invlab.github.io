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

def main():
    print("SOX 公開來源穩定性探測｜僅診斷，不輸出正式行情")
    sessions = requests.Session()
    sessions.headers.update({"User-Agent": "Mozilla/5.0 (compatible; TACSourceProbe/1.0)"})
    for name, url in URLS.items():
        print(f"\nSOURCE｜{name}\nURL｜{url}")
        try:
            response = sessions.get(url, timeout=(3, 6))
            print(f"HTTP｜{response.status_code}｜bytes={len(response.content)}")
            response.raise_for_status()
            html = response.text
            if "fred.stlouisfed.org/data/NASDAQSOX" in url:
                rows = re.findall(r"(?m)^\s*(\d{4}-\d{2}-\d{2})\s+([0-9.]+|\.)\s*$", html)
                print("FRED 最近日期與收盤列｜" + (str(rows[-5:]) if rows else "未解析到純文字日期列"))
            else:
                date_matches = re.findall(r"DATA AS OF\\s*([^<]+)", html, flags=re.I)
                stat_matches = re.findall(r"(?:Last|Day High|Day Low|Previous Close)\\s*</?[^>]*>\\s*([^<]+)", html, flags=re.I)
                print("DATA AS OF 原始匹配｜" + (str(date_matches[:3]) if date_matches else "頁面 HTML 未匹配到"))
                print("頁面包含 SOX｜" + str("PHLX Semiconductor" in html or "SOX" in html))
                # Print short context only; deliberately do not parse a tradable quote from an unstable page.
                for pattern in (r"DATA AS OF", r"Day High", r"Day Low", r"Previous Close"):
                    pos = html.lower().find(pattern.lower())
                    print(f"HTML context {pattern}｜" + (re.sub(r"\\s+", " ", html[max(0,pos-100):pos+240]) if pos >= 0 else "not found"))
        except Exception as exc:
            print(f"ERROR｜{type(exc).__name__}: {exc}")
    print("\n判讀｜此工具只比較公開頁面是否可連線及呈現內容；不會把任何結果自動寫入早報或 JSON。")

if __name__ == "__main__":
    main()
