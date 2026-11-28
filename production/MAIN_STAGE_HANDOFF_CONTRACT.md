# TAC Main Stage 1–6｜簡化後交接契約

版本：1.0（2026-11-28）
適用分支：main
設計基礎：使用者 2026-11-28 Main 生產流程重新設計計劃、SIM-1.4
Simulation：只讀，不修改

## 核心流程

Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Stage 6

Stage 1–4 開工前只完整讀取自己的 WR，完成工作後直接交付下一階段。不得以跨階段 WR SHA、Preflight receipt、worker attestation 或重複的上游 receipt hash 作為交接門檻。Stage 5 是唯一完整 QA 關卡；Stage 6 只接收 Stage 5 通過的成果並產出 Main Preview。

## Run 與交接

- 同一份 production/runs/<run_id>/ 是本次生產的工作目錄。
- Run ID、report_date、trading_date 是階段交接的基本識別。
- 每階段交付實際工作檔案，下一階段直接讀取；不得為了交接重建一套證明文件。
- 必要的檔案完整性摘要可留在執行紀錄，但不得形成重複阻塞 Gate。
- 不得沿用其他 Run 的行情、截圖、FedWatch、新聞或分析內容。
- Stage 2 仍必須交付完整 44 項觀察及獨立 FedWatch；每項保留真實來源、商品身分、資料日期與狀態。
- Stage 3 交付行事曆、財報及已公布結果；不得捏造市場共識。
- Stage 4 交付新聞、三段式總結、五層市場分析、盤面觀察重點與市場情緒。
- Stage 5 直接檢查 Stage 1–4 實際成果、必要來源及完整 HTML，不要求上游重複提交 WR 證明。
- Stage 6 只產出 preview/main/YYYY-MM-DD-review.html 及必要 QA／delivery sidecar；不修改正式首頁。

## 各 Stage 的直接交付

| Stage | 主要交付 |
|---|---|
| 1 | run-context.json、stage1-fixture.json、初始 report-data.json、Run 狀態 |
| 2 | 44 項行情觀察、行情快照、FedWatch、各項來源及缺漏狀態 |
| 3 | calendar-data.json、earnings-data.json、已公布結果及來源 |
| 4 | stage4-editorial-content.json、新聞及市場分析內容 |
| 5 | review.html、完整 QA sidecar、QA 結果 |
| 6 | Main Preview HTML、交付資訊 |

## 保留的必要資料品質要求

- Investing.com Historical Data 實際表格仍是指定行情首選；不得以搜尋摘要代替。
- 不得繞過 Cloudflare；MOVE 僅依核准規則使用 TradingView 備援。
- 截圖僅限當次 Run；已提供欄位不重抓、不覆蓋。
- 休市、PENDING、TOOL_READ_FAILURE、SOURCE_NO_DATA 等狀態必須語意正確。
- 缺漏不得填 0、沿用舊值或偽裝 VERIFIED。
- Stage 5 QA 必須檢查資料日期、來源、商品身分、數值、內容、DOM、響應式、互動與視覺。
- 上漲紅色、下跌綠色。
- Stage 6 不得更新 index.html；正式發布另需使用者核准。

## 本輪程式改造已涵蓋

- Stage 1–4 的 WR 載入改為完整讀取，不做跨階段 WR SHA pinning。
- 上游 WR receipt 不再要求 worker attestation。
- Stage 2 Observation 不再要求 Stage 1 receipt／context／fixture 三組 SHA。
- Stage 2 handoff 以 Run ID、日期及 44 項商品身分確認。
- Stage 3 不再把 Stage 2 receipt SHA 作為 Stage 3 輸入 Gate。
- Stage 4 不再要求 Stage 3 receipt SHA 或 Stage 4 WR SHA。
- Stage 5／6 的 QA 與交付規則保留。

## 尚待完成

1. 完成六份 WR 與 Runner 的全量一致性清理。
2. 對照 Stage 3／4 的真實交付檔，確保 Builder 不依賴已移除的欄位。
3. 更新所有受影響的單元測試與 Workflow 結構測試。
4. 執行完整 CI。
5. 以全新 Run 執行 2026-11-30 Stage 1–6 E2E。
