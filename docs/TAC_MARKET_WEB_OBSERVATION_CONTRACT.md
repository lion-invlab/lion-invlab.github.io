# TAC 行情資料擷取契約｜ChatGPT 直接讀取網頁

## 正式採集方式
- 行情主要由 ChatGPT 直接開啟並閱讀 Investing.com 香港站的對應商品／歷史資料頁，核對商品身份、報價值、漲跌、資料日期與報價口徑。
- 每筆觀察都必須保留來源名稱、原始網址、資料日期、實際讀取時間、商品識別、單位／幣別及報價口徑。
- Investing.com 優先來源若無最新且可核實資料，才依正式 WR 啟用備援；必須記錄備援原因。優先與備援均無法核實時，標示待核實，不沿用舊值、不推算補值。
- ChatGPT 將核實結果寫成符合 `schemas/tac-investing-com-web-observations.schema.json` 的 JSON，再交由 GitHub 驗證與後續組裝。

## 不得混淆的兩種工作
- `scripts/fetch_tac_global_indices.py` 等自動擷取程式不是本契約的主要報價來源，不得在早報正式流程中取代 ChatGPT 直接讀取網頁。
- 自動擷取器若保留，只能作為獨立的研究／比對工具；不得覆蓋 ChatGPT 已核實的觀察值，也不得因擷取器成功就將報價標成 verified。
- GitHub Actions 不會自行執行 ChatGPT 的網頁閱讀或分析能力。沒有 ChatGPT 產生並提交的核實 JSON，不得宣稱已完成行情採集。

## 資料欄位與驗證
- `asset_id` 必須使用 schema 的固定清單；同一資料集不得重複。
- `value` 是該資產的主報價；`change` 與 `change_unit` 必須遵守該商品頁顯示口徑。
- 11 檔產業 ETF 的 `value_type` 使用 `percent_change`，只呈現漲跌幅，不將 ETF 價格混入早報欄位。
- 美債殖利率使用 `yield_percent`，並在 `quote_basis` 明確標示日度殖利率曲線；不得與個別債券即時殖利率混用。
- VIX、MOVE、CNN Fear & Greed 與 CME FedWatch 各自保留正確指標口徑；FedWatch 必須在 notes 記錄會議及機率快照時間，不能把不同會議機率混成同一筆。
- `verified` 必須有數值、資料日期與來源；否則應標為 `pending_verification` 或 `missing`。
- `fallback_used=true` 時必須填寫 `fallback_reason`。
- 完整性由驗證器另行檢查：缺少任一預期資產、重複 asset_id、日期不一致或未核實值，均不得宣告行情資料完整。

## 固定資產範圍
17 項全球主要指數、11 檔 S&P 產業 ETF、3 個美債期限、DXY 與 5 組外匯、WTI／Brent、黃金／白銀、VIX／MOVE／CNN Fear & Greed、CME FedWatch。

## 安全邊界
本契約僅建立 PR #226 原型分支的資料輸入與驗證基礎；不修改正式首頁、正式 WR、雙母版、母版 manifest 或排程，也不授權合併／發布。
