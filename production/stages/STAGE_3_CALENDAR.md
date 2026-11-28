# Stage 3｜行事曆與財報事件
版本：Main E2E v1.2（2026-11-28）

## 開工前讀取本階段 WR
- 開始本階段工作前，完整讀取本文件（UTF-8）；確認內容可讀即可。
- 這是工作指令，不是額外驗收關卡。不得要求 Stage 1–4 提交 WR SHA、Git blob SHA、Preflight receipt 或跨階段 WR 證明。
- 讀取本階段 WR 後，直接依下列工作內容執行；完成即交付下一階段。

 
Stage 3 必須先完整讀取本文件及完成 WR Preflight，才可讀取或投影行事曆／財報資料。

## 輸入
Stage 1 當週 JSON commit 與 blob SHA；僅週一另含上週 JSON commit 與 blob SHA；Stage 2 凍結行情快照、`production/MASTER_WR.md`、`production/contracts/DATA_SCHEMA.md` 與 `production/contracts/SOURCE_POLICY.md`。SIM-1.4 僅為技術規範來源，不是 main 執行期依賴。

## 執行
1. 僅讀取 main `data/calendar/weeks/YYYY-Www.json`。工作日 04:35 行事曆排程是唯一 writer；Stage 3 嚴格唯讀，不修補、不 merge、不 upsert、不覆寫。
2. 每日只讀取本週 JSON；只有週一需要「上週」回顧時，才額外讀取前一週 JSON。讀取的檔案均須來自 Stage 1 鎖定的同一 main commit。週二至週五不得為了產生空白區塊而讀取前一週 JSON。
3. 逐事件核對 event ID、日期／時區、公司／國家、事件狀態、實際值、預期值、來源、星等及所屬分頁。已公布經濟事件須呈現實際值及市場影響判斷。
4. 財報共識：Yahoo Finance Average Estimate 第一順位；該指標缺值、不可讀或期間不符，依序 Investing.com、LSEG I/B/E/S、FactSet Estimates。EPS 與 Revenue 各自獨立選源；取得第一個有效平均預期後停止該指標搜尋。
5. 已公布財報須呈現實際 EPS／Revenue、各自共識、優於／符合／低於預期判斷及股價反應。若共識不可得，明確標示待核實，不可虛構。
6. 跨幣別營收比較須明確標示換算匯率、日期及計算方式；不可直接比較不同幣別數字。
7. 05:25 後發現的事件修正只記錄於當次 run 與審核版，不回寫週 JSON，交由下一次 04:35 唯一 writer 處理。

## 輸出
calendar-data.json、earnings-data.json、event/source references、未核實項目及唯讀 SHA receipt。

## 驗收與交接
事件 ID 唯一、日期／時區正確、JSON SHA 一致、已公布值有來源、EPS／Revenue 獨立判讀。交給 Stage 4 與 Stage 5；不改動來源 JSON。


## Main Run state contract v1.2
- Stage 3 必須讀取同一 Run 的 run-state.json；Stage 2 必須已由 GitHub validator 標記 PASS 或 PARTIAL，Stage 2 receipt 的 run_id 必須等於 run-context.run_id。Stage 2 SUBMITTED 尚未驗證時，不得開始 Stage 3。
- Stage 3 只可在 Stage 3=READY 時，以 compare-and-swap 將狀態改為 RUNNING，記錄 lease、Stage 2 receipt SHA 與 calendar input SHA。
- Stage 3 完成並寫出 stage3-calendar-receipt.json 後，將 Stage 3 改為 PASS，記錄 receipt SHA，並將 Stage 4 設為 READY。Receipt 與 state 必須在同一 Run 證據提交中保存。
- Stage 3 不建立 Run、不重抓行情、不改寫週 JSON、不以日期共用檔作輸入；任何前置狀態或 Run ID 不符均 FAIL-CLOSED。
