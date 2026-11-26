# Stage 2｜44 項行情及獨立 FedWatch

## 輸入
Stage 1 run-context、SIM-1.4 來源規則、選定母版欄位、當日使用者截圖 sidecar（若存在）。

## 執行順序
1. 建立本輪 blank-first market fixture：清除所有舊 close/change/score/OHLC、舊 Observation、截圖紀錄、evidence hash/time 與含舊數字的備註；保留欄位身分、來源 URL、quote_type、日期及非行情內容。不得沿用舊 fixture 數值。
2. 先讀取當日 screenshot sidecar 並驗證 report_date、trading_date、商品身分、正式 Investing.com URL、欄位標籤、圖片路徑與 SHA-256。使用者提供且可辨識商品、日期及數值的截圖優先於全部 44 項行情，不限 MOVE。已提供欄位直接採用，不重抓、不覆蓋；缺欄才補讀。
3. 對仍需讀取的項目，瀏覽器直接開啟 Investing.com 對應商品 Historical Data 頁，讀取實際歷史數據表格及指定交易日列。不得以搜尋摘要、第三方 API、Yahoo Finance 或其他未核准來源取代；不得繞過 Cloudflare。
4. 同時最多開啟 4 個不同歷史資料頁（concurrency=4）。每頁獨立記錄商品／合約、日期、Close／Price、Change／Change %、必要 OHLC、URL、查核時間、讀取方法與狀態。不得縮短 timeout 或提高並行數規避限制。已完整由截圖提供欄位的頁面不開啟。
5. 第一輪完整掃描 44 項；符合標的、交易日、欄位、口徑及證據者立即鎖定。後續只刷新 PENDING／缺欄／有具體疑義項目；不重抓已鎖定值。頁面表格可讀但無目標日期列為 SOURCE_NO_DATA；工具無法讀取頁面／表格列為 TOOL_READ_FAILURE。
6. 建立 44 列 Observation、source manifest、metadata audit、fixture 及 Stage 2 receipt，綁定 workflow_run_id、attempt、report/trading date、batch_id 與 SHA-256。verified+pending+closed+missing 等狀態計數須合計 44。Observation SHA 是標準化觀察紀錄 SHA，不得冒充原始 HTTP response SHA。
7. FedWatch 獨立讀取 Investing.com Fed Rate Monitor，記錄當下時間、會議日期、現行利率區間、各目標區間機率及來源；CME 僅作方法／交叉核對。
8. 將本輪已核實 S&P 500 現貨正式收盤交接至既有 `data/tac-chart3/sp500_daily_increment.jsonl`。沿用既有 append 程式、SHA、防重、日期遞增及衝突停止規則；不得另抓第二份報價、不得重建歷史底稿。
9. 截圖純輸入、截圖與歷史頁混合、純歷史頁及官方觀察均逐欄記錄來源。截圖來源仍依商品契約標示 Investing.com 對應商品頁；不得在報告正文寫「依使用者截圖」。

## 輸出
market fixture、44-row Observation bundle、source manifest、metadata audit、Stage 2 snapshot receipt、FedWatch object、Chart 3 S&P500 increment handoff、未結項目清單及耗時統計。

## 驗收與交接
44 項逐項有值或明確狀態；未核實值不得進入分析當成事實；PENDING 不得讓 Runner crash；Stage 3–6 對行情快照唯讀。首次 concurrency=4 真實早報測試須記錄起訖、總耗時、實際網頁讀取數及各狀態數。
