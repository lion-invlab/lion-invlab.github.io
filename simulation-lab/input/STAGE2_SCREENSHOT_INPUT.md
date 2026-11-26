# Stage 2 使用者截圖輸入規格

本目錄是 TAC Stage 2 44 項行情的截圖優先輸入區。正式擷取器會自動尋找：

`simulation-lab/input/market-screenshot-observations-YYYY-MM-DD.json`

其中 YYYY-MM-DD 是報告日期。圖片與 sidecar 必須一併提交至 Simulation 分支；工作流程不會自動取得聊天附件中的原始圖片，也不會自行 OCR 或猜測畫面數值。請將實際圖片放在 Repository 內，例如：

`simulation-lab/input/screenshots/YYYY-MM-DD/market-name.png`

sidecar 的每筆 observation 對應 44 項之一，並且必須符合 Fixture 的交易日期與來源 URL。每個欄位可分別來自截圖或 Investing.com 歷史頁；截圖已提供的欄位不會再由歷史頁覆蓋。

## JSON 範例

```json
{
  "report_date": "2026-11-26",
  "trading_date": "2026-11-25",
  "observations": [
    {
      "group": "global_markets",
      "name": "標普500指數",
      "data_date": "2026-11-25",
      "source_url": "https://www.investing.com/indices/us-spx-500-historical-data",
      "instrument_identity": "S&P 500 (SPX)",
      "evidence_path": "simulation-lab/input/screenshots/2026-11-26/sp500.png",
      "evidence_sha256": "填入圖片檔案實際 SHA-256",
      "captured_at": "2026-11-26T06:45:00+08:00",
      "quote_timestamp": "2026-11-25 16:17 GMT-5",
      "fields": {
        "close": {
          "value": "6,812.34",
          "field_name": "Close"
        },
        "change": {
          "value": "-0.42%",
          "field_name": "Change %"
        },
        "open": {
          "value": "6,830.10",
          "field_name": "Open"
        },
        "high": {
          "value": "6,845.20",
          "field_name": "High"
        },
        "low": {
          "value": "6,790.50",
          "field_name": "Low"
        }
      }
    }
  ]
}
```

## 欄位規則

- 一般指數、ETF、債券殖利率、外匯、能源、金屬及 VIX／MOVE：使用 `close`、`change`；可選 `open`、`high`、`low`。
- CNN Fear & Greed：使用 `score`、`band`。
- 欄位名稱須與畫面表頭相符；數值只填欄位值，不要把商品名稱、日期或漲跌說明混進數值。
- `evidence_sha256` 必須是圖片檔案實際 SHA-256。擷取器會重新計算並比對，不接受只有格式正確但雜湊不符的資料。
- 同一商品若不同欄位來自不同截圖，可在各欄位物件內分別填寫 `evidence_path`、`evidence_sha256`、`captured_at`、`quote_timestamp`；欄位層級設定優先於列層級設定。若整列欄位來自同一張圖，可沿用列層級證據設定。每張圖都會各自核對實際 SHA。
- `data_date` 必須等於該報告 Fixture 的 `trading_date`；不允許沿用前一交易日截圖。
- `source_url` 必須等於 Fixture 中該商品的正式來源 URL。截圖只決定欄位值優先權，不改寫正式來源契約。
- `instrument_identity` 必須清楚指出商品／代號；若無法確認身分，該列不會 VERIFIED。
- 只提供部分欄位時，擷取器只以 Investing.com 歷史數據頁補足缺少的必要 Close／Change 欄位；截圖已提供欄位保留原值與 SHA 證據。
- 若截圖已提供 Close 與 Change（或 Fear & Greed 的 Score 與 Band），該商品不會再開啟歷史頁。
- Cloudflare／讀取阻擋仍記錄 `TOOL_READ_FAILURE`，不繞過存取控制，也不改用未核准來源。

## 產物與驗收

擷取器會先以截圖值更新當輪 Fixture 的對應欄位，再建立 44 項 observation。每個欄位都會記錄 `source_type`、證據檔案路徑、SHA-256、畫面欄位名稱與擷取時間。Manifest 重新讀取證據檔並核對 SHA；缺檔、日期錯誤、來源 URL 不符、標的身分不符或 SHA 不符均不得 VERIFIED。

每日關鍵價位的獨立 Yahoo Finance OHLC 流程不在此輸入規格內，也不會被 Stage 2 截圖規則改寫。
