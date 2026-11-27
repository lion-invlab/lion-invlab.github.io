# Stage 2｜44 項行情及獨立 FedWatch

## 開工前強制 WR Preflight
- Stage Runner 必須在任何本階段資料處理、分析、組裝或交付動作前，呼叫 `stage_wr_preflight` 完整讀取本階段 WR。
- Stage 1 以當前 main HEAD 的本階段 WR 為基準；Stage 2–6 必須同時核對 Stage 1 `governance.blob_shas`、鎖定 commit 與當前 WR Git blob SHA。
- 缺檔、空檔、無法完整 UTF-8 讀取、Run 未鎖定該 WR、SHA 不一致，均立即 FAIL-CLOSED；不得跳過、fallback 或繼續工作。
- 本階段輸出收據必須包含 `wr_preflight`，至少記錄 `wr_path`、`wr_loaded`、`wr_sha256`、`wr_git_blob_sha`、`stage1_pinned_git_blob_sha`、讀取位元組數及 PASS 狀態。沒有該證據不得宣告本階段完成。
 
Stage 2 必須先完整讀取本文件及完成 WR Preflight，才可建立／修改行情 fixture 或讀取行情。

## 美股收盤時點與擷取邊界
- 台灣冬令 04:45（15:45 ET）是 Stage 1 建立 Run 的時間；美股尚未收盤。Stage 1 僅建立 Run／鎖定治理版本／交付 handoff，不代表可開始正式收盤行情擷取。
- Stage 2 worker 排程為台灣冬令 05:00（16:00 ET），即美股正式收盤時點；只有在同一 Run 的 Stage 1 三份 handoff 檔及 SHA 核對通過後，才可開始行情頁讀取。
- `report_cutoff_taipei` 是資料截點而非排程啟動時間：美東 16:25，台灣夏令 04:25／冬令 05:25。各商品仍須依自身市場已完成交易時段、實際歷史表格日期及資料可讀性判定；不得把 04:45 盤中值當收盤，也不得因 05:00 到點就把尚未更新的歷史表格當成已核實收盤。尚未出現收盤列時，只能維持 PENDING 並依本 WR 刷新同一來源，或在交付期限到達時如實標示來源狀態；不得用盤中價、舊值或未核准來源替代。

## Stage 2 ChatGPT 擷取工作者開工前必讀
- 在讀取任何使用者截圖、Investing.com Historical Data 頁或建立 observation 前，必須先完整讀取本 WR；隨後等待同一 report_date 的 Stage 1 Run 已提交 `run-context.json`、`stage1-fixture.json`、`stage1-receipt.json`。讀取三檔並計算 SHA 後，才可開始擷取。Stage 2 worker 於 05:00（夏令 04:00）啟動時，Stage 1 handoff 正常應已在前 15 分鐘完成。只允許最多 5 分鐘短暫交接容錯；若 5 分鐘內仍無唯一且完整的 Stage 1 handoff，立即標記 BLOCKED、附上排程／Run 證據並停止本輪預擷取，不得延長此 5 分鐘容錯，也不得以其他 Run 代替。
- `production/input/market-history-web-observations-YYYY-MM-DD.json` 根層必須包含 `stage2_wr_sha256`，值為本文件完整 UTF-8 bytes 的 SHA-256。
- 同日期 `mode=rerun` 時，必須先移除舊日期 observation bundle，再重新讀取本文件並新建 bundle；不得從舊 Run、舊 observation、舊截圖、舊 FedWatch 或舊網頁讀取紀錄複製欄位。所有 44 列的 `prior_observation_reused` 必須為 false，`captured_at_utc` 必須記錄本輪實際擷取時間；Stage 2 不得使用 `--reuse-observations`。
- 能源與金屬期貨（WTI、Brent、Gold、Silver）必須從 Investing.com 歷史頁標題擷取當前選定合約的完整 `contract_label`（含合約月份與頁面顯示代碼），寫入該 observation 的 `contract_label`；`page_title` 必須保留完整商品標題。不得自行推算月份、只填通用商品名稱，或用前一 Run 的合約標籤。Stage 2 populate fixture 會將本輪 `contract_label` 寫入報告資料，供快照驗證與商品名稱顯示。
- Observation bundle 根層必須包含同一 Run 的 `run_id`、`stage1_receipt_sha256`、`run_context_sha256`、`stage1_fixture_sha256`；另包含獨立的 `fedwatch` 物件（不計入 44 列）：`status`、`source_name`、`source_url`、`report_date`、`trading_date`、`captured_at_utc`、`target_meeting`、`current_target_range`、`updated_at_tw`、`probabilities`、`web_reader_ref`、`web_line_start`、`web_line_end`、`reason`、`stage2_wr_sha256`。主來源固定 Investing.com Fed Rate Monitor；已核實時逐一記錄頁面顯示的 outcome、rate_range、probability，機率總和須為 100%；無法讀取或沒有可用資料時，明確標示 TOOL_READ_FAILURE／SOURCE_NO_DATA，probabilities 留空並寫明原因，不得沿用舊機率或推估。
- Stage 2 Runner 必須將 FedWatch 物件寫入 Run 的 `report-data.json`，並將狀態及 observation SHA 寫入 Stage 2 receipt／summary；不得讓模板中的空 `fedwatch: {}` 靜默流入 Builder。
- Stage 2 Runner 會將該值與本次 Run 的 Stage 1 pinned WR 版本及自身 preflight SHA 比對；缺漏或不符即拒絕 44 項觀察輸入，不進入行情合併。

## 輸入
Stage 1 run-context、`production/MASTER_WR.md`、`production/contracts/SOURCE_POLICY.md`、選定母版欄位、當日使用者截圖 sidecar（若存在）。

## 執行順序
1. 建立本輪 blank-first market fixture：清除所有舊 close/change/score/OHLC、舊 Observation、截圖紀錄、evidence hash/time 與含舊數字的備註；保留欄位身分、來源 URL、quote_type、日期及非行情內容。不得沿用舊 fixture 數值。
2. 當日截圖 sidecar 固定路徑為 `production/input/market-screenshot-observations-YYYY-MM-DD.json`；原始圖片須封存在 `production/input/screenshots/YYYY-MM-DD/`。先讀取 sidecar 並驗證 report_date、trading_date、run_id、Stage 1 三項 SHA、商品身分、正式 Investing.com URL、欄位標籤、圖片路徑與 SHA-256。使用者提供且可辨識商品、日期及數值的截圖優先於全部 44 項行情，不限 MOVE。已提供欄位直接採用，不重抓、不覆蓋；缺欄才補讀。
3. 對仍需讀取的項目，瀏覽器直接開啟 Investing.com 對應商品 Historical Data 頁，讀取實際歷史數據表格及指定交易日列。不得以搜尋摘要、第三方 API、Yahoo Finance 或其他未核准來源取代；不得繞過 Cloudflare。
4. 同時最多開啟 4 個不同歷史資料頁（concurrency=4）。每頁獨立記錄商品／合約、日期、Close／Price、Change／Change %、必要 OHLC、URL、查核時間、讀取方法與狀態。不得縮短 timeout 或提高並行數規避限制。已完整由截圖提供欄位的頁面不開啟。
5. 第一輪完整掃描 44 項；符合標的、交易日、欄位、口徑及證據者立即鎖定。後續只刷新 PENDING／缺欄／有具體疑義項目；不重抓已鎖定值。頁面表格可讀但無目標日期列為 SOURCE_NO_DATA；工具無法讀取頁面／表格列為 TOOL_READ_FAILURE。只有同時附上指定交易日、官方交易日曆來源 URL、官方來源類型及可回查證據，才可標記 MARKET_CLOSED；單憑歷史表格沒有該日期列，或只回傳 MARKET_CLOSED 字串，不得推定休市。正式休市列的數值欄顯示「-」，變動欄顯示「休市」；不得兩欄都顯示休市。
6. 建立 44 列 Observation、source manifest、metadata audit、fixture 及 Stage 2 receipt，綁定 workflow_run_id、attempt、report/trading date、batch_id 與 SHA-256。各列狀態計數必須完整覆蓋 44 項且總數等於 44；不得把 PENDING、MISSING、CLOSED、TOOL_READ_FAILURE 或 SOURCE_NO_DATA 併記成 VERIFIED。Observation SHA 是標準化觀察紀錄 SHA，不得冒充原始 HTTP response SHA。
7. FedWatch 獨立讀取 Investing.com Fed Rate Monitor，記錄當下時間、會議日期、現行利率區間、各目標區間機率及來源；CME 僅作方法／交叉核對。
7a. MOVE 是 ICE BofAML 美國公債市場選擇權波動度指數，且是唯一具有本項專屬備援路徑的行情列。優先序：①本次當日有效且通過 screenshot sidecar 契約的使用者截圖；②固定 Investing.com MOVE Historical Data 主來源；③當 Investing.com 頁面不可讀或目標日期列不存在時，使用 TradingView ICE:MOVE（`https://www.tradingview.com/symbols/ICE-MOVE/`）讀取同一目標交易日的日線收盤及必要變動欄位。TradingView 必須明確識別為 ICE BofAML U.S. Bond Market Option Volatility Estimate Index，且日期、收盤欄位、變動欄位均有當次可回查證據；Observation 的 source_role 記為 BACKUP_1、欄位來源類型記為 TRADINGVIEW_HISTORICAL_PAGE，不得偽裝成 Investing.com。備援 Observation 同時附上本輪 Investing.com 主來源失敗／無目標日期列的證據；不得在主來源尚未判定失敗時提前啟用備援。若 SIFMA 官方美國固定收益市場行事曆確認休市，MOVE 標 MARKET_CLOSED，不啟用 TradingView 備援。若兩來源皆無法核實，保留正確 TOOL_READ_FAILURE／SOURCE_NO_DATA 狀態，不猜值、不沿用舊值。延遲重試及備援只可更新 risk:move，其他 43 列必須逐位元保持不變。此備援規則不得套用到其他 43 項。
8. 將本輪已核實 S&P 500 現貨正式收盤交接至既有 `data/tac-chart3/sp500_daily_increment.jsonl`。沿用既有 append 程式、SHA、防重、日期遞增及衝突停止規則；不得另抓第二份報價、不得重建歷史底稿。Stage 2 只負責追加並提交增量帳，不得自行 dispatch 或等待 Chart 3 合併；Chart 3 merge workflow 僅在 Main 早報 Stage 6 成功、整條 production workflow 完成後觸發，屬非阻塞支線。
9. 截圖純輸入、截圖與歷史頁混合、純歷史頁及官方觀察均逐欄記錄來源。截圖來源仍依商品契約標示 Investing.com 對應商品頁；不得在報告正文寫「依使用者截圖」。

## 輸出
market fixture、44-row Observation bundle、source manifest、metadata audit、Stage 2 snapshot receipt、FedWatch object、Chart 3 S&P500 increment handoff、未結項目清單及耗時統計。

## 驗收與交接
44 項逐項有值或明確狀態；未核實值不得進入分析當成事實；PENDING 不得讓 Runner crash；Stage 3–6 對行情快照唯讀。首次 concurrency=4 真實早報測試須記錄起訖、總耗時、實際網頁讀取數及各狀態數。

## 截圖 sidecar 必要欄位
固定路徑：`production/input/market-screenshot-observations-YYYY-MM-DD.json`；原始圖片封存於 `production/input/screenshots/YYYY-MM-DD/`。JSON 根層欄位為 `schema_version=1.1`、`run_id`、`report_date`、`trading_date`、`captured_at_utc`、`stage1_receipt_sha256`、`run_context_sha256`、`stage1_fixture_sha256`、`observations`。每筆 observation 含 `group`、`name`、`data_date`、`source_url`、`instrument_identity`、`fields`。fields 是欄位名稱對應物件，key 限 `close`、`change`、`open`、`high`、`low`、`score`、`band`；每個欄位物件必含 `value`、`field_name`、`evidence_path`、`evidence_sha256`、`captured_at`，可含 `quote_timestamp`。source_url 必須與該 fixture 指標來源 URL 完全一致；data_date 必須等於該商品 observation 的 target_date；不得要求等於共用 trading_date。圖片 SHA-256 由 Runner 重新計算；不得只填看似有效的 SHA 字串。聊天附件不會自動出現在 GitHub Runner checkout，必須先封存原圖與 sidecar 才能由排程讀取。


## 官方休市 Observation 證據契約（Main）
- `trading_date` 是 Run 共用的日期錨點，不是所有商品的強制報價日期。44 項每一列必須依該商品所屬市場交易日曆及 report cutoff，採用最近一個已完成交易時段的實際資料日期；每列 `target_date` 必須等於該列實際讀取的歷史表格日期，並回填為 Fixture 的 `source.data_date`。不同市場允許不同日期，不得為了統一日期而把 11/25 美股收盤錯標為 11/26，亦不得把舊值標成新日期。
- 歷史頁沒有目標日期列時，先記錄 `SOURCE_NO_DATA`；只有進一步取得官方市場行事曆證據才可改為 `MARKET_CLOSED`。
- `MARKET_CLOSED` Observation 必須使用同一組可回查欄位：`source_page_fetched=true`、`source_url`、`target_date`、`instrument_identity_status=VERIFIED`、`field_mapping_status=VERIFIED`、`closure_evidence_url`、`closure_evidence_reader_ref`、`closure_evidence_line_start/end`、`provenance=CURRENT_CHATGPT_WEB_OPEN_OBSERVATION`、`read_method=CHATGPT_WEB_OPEN_HISTORICAL_PAGE`、`prior_observation_reused=false`、`finished_at_utc`。
- `closure_evidence_url` 必須為官方交易所／官方市場營運機構網域；頁面缺列、任意 HTTPS、非官方內容或沒有當次瀏覽器 reader 行號，均不得標 CLOSED。
- Fixture bootstrap 與 Source Verification Manifest 必須採用同一套 `closure_evidence_*` 欄位，不得一端要求 `market_calendar_*` 別名而另一端只產生 `closure_evidence_*`。
- Schema 已列明上述欄位；測試需涵蓋無證據、非官方網域及完整官方證據三種情境。
