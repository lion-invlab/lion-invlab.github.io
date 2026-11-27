# Stage 3｜行事曆與財報事件

## 開工前強制 WR Preflight
- Stage Runner 必須在任何本階段資料處理、分析、組裝或交付動作前，呼叫 `stage_wr_preflight` 完整讀取本階段 WR。
- Stage 1 以當前 main HEAD 的本階段 WR 為基準；Stage 2–6 必須同時核對 Stage 1 `governance.blob_shas`、鎖定 commit 與當前 WR Git blob SHA。
- 缺檔、空檔、無法完整 UTF-8 讀取、Run 未鎖定該 WR、SHA 不一致，均立即 FAIL-CLOSED；不得跳過、fallback 或繼續工作。
- 本階段輸出收據必須包含 `wr_preflight`，至少記錄 `wr_path`、`wr_loaded`、`wr_sha256`、`wr_git_blob_sha`、`stage1_pinned_git_blob_sha`、讀取位元組數及 PASS 狀態。沒有該證據不得宣告本階段完成。
 
Stage 3 必須先完整讀取本文件及完成 WR Preflight，才可讀取或投影行事曆／財報資料。

## 輸入
Stage 1 當週／上週 JSON commit 與 blob SHA、Stage 2 凍結行情快照、`production/MASTER_WR.md`、`production/contracts/DATA_SCHEMA.md` 與 `production/contracts/SOURCE_POLICY.md`。SIM-1.4 僅為技術規範來源，不是 main 執行期依賴。

## 執行
1. 僅讀取 main `data/calendar/weeks/YYYY-Www.json`。工作日 04:35 行事曆排程是唯一 writer；Stage 3 嚴格唯讀，不修補、不 merge、不 upsert、不覆寫。
2. 讀取本週及前一週 JSON，兩者必須來自 Stage 1 鎖定的同一 main commit，作為跨週來源收據。只有週一將前一週事件投影至可見回顧區塊；週二至週五的前一週投影保持空白且不得顯示。
3. 逐事件核對 event ID、日期／時區、公司／國家、事件狀態、實際值、預期值、來源、星等及所屬分頁。已公布經濟事件須呈現實際值及市場影響判斷。
4. 財報共識：Yahoo Finance Average Estimate 第一順位；該指標缺值、不可讀或期間不符，依序 Investing.com、LSEG I/B/E/S、FactSet Estimates。EPS 與 Revenue 各自獨立選源；取得第一個有效平均預期後停止該指標搜尋。
5. 已公布財報須呈現實際 EPS／Revenue、各自共識、優於／符合／低於預期判斷及股價反應。若共識不可得，明確標示待核實，不可虛構。
6. 跨幣別營收比較須明確標示換算匯率、日期及計算方式；不可直接比較不同幣別數字。
7. 05:25 後發現的事件修正只記錄於當次 run 與審核版，不回寫週 JSON，交由下一次 04:35 唯一 writer 處理。

## 輸出
calendar-data.json、earnings-data.json、event/source references、未核實項目及唯讀 SHA receipt。

## 驗收與交接
事件 ID 唯一、日期／時區正確、JSON SHA 一致、已公布值有來源、EPS／Revenue 獨立判讀。交給 Stage 4 與 Stage 5；不改動來源 JSON。
