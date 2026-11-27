# Stage 2｜44 項行情及獨立 FedWatch

## 開工前強制 WR Preflight
- Stage Runner 必須在任何本階段資料處理、分析、組裝或交付動作前，呼叫 `stage_wr_preflight` 完整讀取本階段 WR。
- Stage 1 以當前 main HEAD 的本階段 WR 為基準；Stage 2–6 必須同時核對 Stage 1 `governance.blob_shas`、鎖定 commit 與當前 WR Git blob SHA。
- 缺檔、空檔、無法完整 UTF-8 讀取、Run 未鎖定該 WR、SHA 不一致，均立即 FAIL-CLOSED；不得跳過、fallback 或繼續工作。
- 本階段輸出收據必須包含 `wr_preflight`，至少記錄 `wr_path`、`wr_loaded`、`wr_sha256`、`wr_git_blob_sha`、`stage1_pinned_git_blob_sha`、讀取位元組數及 PASS 狀態。沒有該證據不得宣告本階段完成。
 
Stage 2 必須先完整讀取本文件及完成 WR Preflight，才可建立／修改行情 fixture 或讀取行情。

## Stage 2 ChatGPT 擷取工作者開工前必讀
- 在讀取任何使用者截圖、Investing.com Historical Data 頁或建立 observation 前，必須先完整讀取 Main 的 `production/stages/STAGE_2_MARKET.md`；不得只看摘要。
- `production/input/market-history-web-observations-YYYY-MM-DD.json` 根層必須包含 `stage2_wr_sha256`，值為本文件完整 UTF-8 bytes 的 SHA-256。
- Stage 2 Runner 會將該值與本次 Run 的 Stage 1 pinned WR 版本及自身 preflight SHA 比對；缺漏或不符即拒絕 44 項觀察輸入，不進入行情合併。

## 輸入
Stage 1 run-context、`production/MASTER_WR.md`、`production/contracts/SOURCE_POLICY.md`、選定母版欄位、當日使用者截圖 sidecar（若存在）。

## 執行順序
1. 建立本輪 blank-first market fixture：清除所有舊 close/change/score/OHLC、舊 Observation、截圖紀錄、evidence hash/time 與含舊數字的備註；保留欄位身分、來源 URL、quote_type、日期及非行情內容。不得沿用舊 fixture 數值。
2. 當日截圖 sidecar 固定路徑為 `production/input/market-screenshot-observations-YYYY-MM-DD.json`；原始圖片須封存在 `production/input/screenshots/YYYY-MM-DD/`。先讀取 sidecar 並驗證 report_date、trading_date、商品身分、正式 Investing.com URL、欄位標籤、圖片路徑與 SHA-256。使用者提供且可辨識商品、日期及數值的截圖優先於全部 44 項行情，不限 MOVE。已提供欄位直接採用，不重抓、不覆蓋；缺欄才補讀。
3. 對仍需讀取的項目，瀏覽器直接開啟 Investing.com 對應商品 Historical Data 頁，讀取實際歷史數據表格及指定交易日列。不得以搜尋摘要、第三方 API、Yahoo Finance 或其他未核准來源取代；不得繞過 Cloudflare。
4. 同時最多開啟 4 個不同歷史資料頁（concurrency=4）。每頁獨立記錄商品／合約、日期、Close／Price、Change／Change %、必要 OHLC、URL、查核時間、讀取方法與狀態。不得縮短 timeout 或提高並行數規避限制。已完整由截圖提供欄位的頁面不開啟。
5. 第一輪完整掃描 44 項；符合標的、交易日、欄位、口徑及證據者立即鎖定。後續只刷新 PENDING／缺欄／有具體疑義項目；不重抓已鎖定值。頁面表格可讀但無目標日期列為 SOURCE_NO_DATA；工具無法讀取頁面／表格列為 TOOL_READ_FAILURE。只有同時附上指定交易日、官方交易日曆來源 URL、官方來源類型及可回查證據，才可標記 MARKET_CLOSED；單憑歷史表格沒有該日期列，或只回傳 MARKET_CLOSED 字串，不得推定休市。正式休市列的數值欄顯示「-」，變動欄顯示「休市」；不得兩欄都顯示休市。
6. 建立 44 列 Observation、source manifest、metadata audit、fixture 及 Stage 2 receipt，綁定 workflow_run_id、attempt、report/trading date、batch_id 與 SHA-256。各列狀態計數必須完整覆蓋 44 項且總數等於 44；不得把 PENDING、MISSING、CLOSED、TOOL_READ_FAILURE 或 SOURCE_NO_DATA 併記成 VERIFIED。Observation SHA 是標準化觀察紀錄 SHA，不得冒充原始 HTTP response SHA。
7. FedWatch 獨立讀取 Investing.com Fed Rate Monitor，記錄當下時間、會議日期、現行利率區間、各目標區間機率及來源；CME 僅作方法／交叉核對。
8. 將本輪已核實 S&P 500 現貨正式收盤交接至既有 `data/tac-chart3/sp500_daily_increment.jsonl`。沿用既有 append 程式、SHA、防重、日期遞增及衝突停止規則；不得另抓第二份報價、不得重建歷史底稿。
9. 截圖純輸入、截圖與歷史頁混合、純歷史頁及官方觀察均逐欄記錄來源。截圖來源仍依商品契約標示 Investing.com 對應商品頁；不得在報告正文寫「依使用者截圖」。

## 輸出
market fixture、44-row Observation bundle、source manifest、metadata audit、Stage 2 snapshot receipt、FedWatch object、Chart 3 S&P500 increment handoff、未結項目清單及耗時統計。

## 驗收與交接
44 項逐項有值或明確狀態；未核實值不得進入分析當成事實；PENDING 不得讓 Runner crash；Stage 3–6 對行情快照唯讀。首次 concurrency=4 真實早報測試須記錄起訖、總耗時、實際網頁讀取數及各狀態數。

## 截圖 sidecar 必要欄位
固定路徑：`production/input/market-screenshot-observations-YYYY-MM-DD.json`；原始圖片封存於 `production/input/screenshots/YYYY-MM-DD/`。JSON 根層欄位為 `report_date`、`trading_date`、`observations`。每筆 observation 含 `group`、`name`、`data_date`、`source_url`、`instrument_identity`、`fields`。fields 是欄位名稱對應物件，key 限 `close`、`change`、`open`、`high`、`low`、`score`、`band`；每個欄位物件必含 `value`、`field_name`、`evidence_path`、`evidence_sha256`、`captured_at`，可含 `quote_timestamp`。source_url 必須與該 fixture 指標來源 URL 完全一致；data_date 必須等於 trading_date。圖片 SHA-256 由 Runner 重新計算；不得只填看似有效的 SHA 字串。聊天附件不會自動出現在 GitHub Runner checkout，必須先封存原圖與 sidecar 才能由排程讀取。


## 官方休市 Observation 證據契約（Main）
- 44 項行情的 `target_date` 統一等於本次 Run 的 `trading_date`；例如 2026-11-27 早報全部查 2026-11-26。不得按市場分別退回最近有資料日期。
- 歷史頁沒有目標日期列時，先記錄 `SOURCE_NO_DATA`；只有進一步取得官方市場行事曆證據才可改為 `MARKET_CLOSED`。
- `MARKET_CLOSED` Observation 必須使用同一組可回查欄位：`source_page_fetched=true`、`source_url`、`target_date`、`instrument_identity_status=VERIFIED`、`field_mapping_status=VERIFIED`、`closure_evidence_url`、`closure_evidence_reader_ref`、`closure_evidence_line_start/end`、`provenance=CURRENT_CHATGPT_WEB_OPEN_OBSERVATION`、`read_method=CHATGPT_WEB_OPEN_HISTORICAL_PAGE`、`prior_observation_reused=false`、`finished_at_utc`。
- `closure_evidence_url` 必須為官方交易所／官方市場營運機構網域；頁面缺列、任意 HTTPS、非官方內容或沒有當次瀏覽器 reader 行號，均不得標 CLOSED。
- Fixture bootstrap 與 Source Verification Manifest 必須採用同一套 `closure_evidence_*` 欄位，不得一端要求 `market_calendar_*` 別名而另一端只產生 `closure_evidence_*`。
- Schema 已列明上述欄位；測試需涵蓋無證據、非官方網域及完整官方證據三種情境。
