# TAC Stage 2 行情資料擷取改造專案

**建立日期：** 2026-11-26  
**Repository：** `lion-invlab/lion-invlab.github.io`  
**工作分支：** `simulation/tac-process-lab-2026-11-06`  
**規範基準：** SIM-1.4；本專案依 2026-11-26 使用者正式指示增補 Stage 2 截圖優先與下游快照唯讀規則。  
**專案狀態：** DESIGN_LOCKED / IMPLEMENTATION_IN_PROGRESS

## 1. 專案目標

把 TAC 44 項行情資料的取得、證據、Manifest、Fixture 與快照鎖定整合成單一 Stage 2 入口。Stage 2 完成後，Stage 3、Stage 4、Builder、QA、Publisher、Pages 與 Chart 3 只消費鎖定資料，不再各自擷取或核實同一批 44 項行情。每日關鍵價位維持獨立資料流程，不納入本專案的 Stage 2 44 項行情防重抓範圍。

## 2. 正式資料取得規則

### 2.1 Investing.com 歷史數據頁

每一項尚未由截圖提供的必要欄位，使用瀏覽器直接開啟 Investing.com 對應商品的正式頁面，進入 Historical Data，讀取實際表格。至少核對商品／合約身分、資料日期、Price／Close、Open、High、Low、Change % 及該項必要欄位。

禁止以一般搜尋摘要、搜尋結果價格片段、未核准 API 或其他第三方來源替代。不得繞過 Cloudflare。頁面已載入但表格無法讀取時記錄 `TOOL_READ_FAILURE`；頁面與表格可讀但無目標資料列時記錄 `SOURCE_NO_DATA`。

### 2.2 使用者截圖優先（適用全部 44 項）

- 截圖可辨識商品、日期及數值時，直接採用截圖，不再重讀網頁核對已提供欄位。
- 不因網頁延遲而以舊值覆蓋截圖值。
- 截圖未提供的必要欄位才讀取 Investing.com Historical Data 頁補足。
- 截圖欄位與網頁補足欄位共用同一 Observation Schema，逐欄記錄來源方式與證據。
- 對外來源標示仍依商品正式來源契約；若該商品來源為 Investing.com，正文仍標示 Investing.com 歷史數據，不揭露「依使用者截圖」。
- 截圖 SHA 必須指向實際證據檔案；不一致或無法確認的雜湊不得宣稱已驗證。

## 3. Stage 2 單一輸出與凍結點

Stage 2 一次產生並封存：

1. 44 項 Observation bundle（包含每項每欄位的輸入方式與來源證據）。
2. 44 列 Manifest。
3. 當輪 Fixture。
4. 原始截圖／瀏覽器觀察證據索引。
5. Fixture、Observation bundle、Manifest、證據檔及 Receipt 的 SHA-256。
6. 批次 ID、報告日期、交易日期、資料版本及 Stage 2 receipt。

Receipt 建立即為 Stage 2 的 44 項行情快照凍結點。下游不得改寫這 44 項行情值、狀態或來源證據。只允許針對明確缺漏欄位進行單項補值；補值不得重跑其他 43 項。

## 4. 下游資料流

### Chart 3

S&P 500 收盤價使用 Stage 2 已鎖定的 44 項行情資料寫入 Chart 3 增量資料庫。Chart 3 更新不得另行擷取同一收盤報價；若 Chart 3 需要 Stage 2 未提供的其他欄位，依 Chart 3 自身資料契約處理，不得覆寫 Stage 2 快照。

### 每日關鍵價位（獨立模組，不屬於 Stage 2）

每日關鍵價位保留既有獨立 Yahoo Finance 日線 OHLC 擷取流程（`collect_key_levels_ohlc.py`），以及同交易日且具來源證據的人工／官方 OHLC override。不得將此模組改成消費 Stage 2，也不得因 Stage 2 防重抓規則而取消或限制其既有 Yahoo Finance 流程。每日關鍵價位須獨立封存交易日、來源、擷取時間與 SHA；其資料不得回寫或覆蓋 Stage 2 的 44 項行情快照。

### Stage 3–6

行事曆、新聞、分析、Builder、QA、Publisher、Pages 僅讀取 Stage 2 的 44 項行情快照；可檢查結構與 SHA，不得外部重讀已鎖定的 44 項行情。每日關鍵價位獨立模組依自身來源契約執行，不屬於此項限制。

## 5. 現況盤點（2026-11-26）

已識別的既有元件：

- `simulation-lab/runner/browser_verify_market_history.py`：Playwright 歷史頁讀取及 44 項觀察，目前主要路徑仍以瀏覽器逐項讀取為主，尚未支援完整截圖優先與欄位級合併。
- `simulation-lab/runner/build_market_source_verification_manifest.py`：由 Fixture 與 observation bundle 產生 44 列 Manifest；已有部分 screenshot 判斷邏輯，但欄位名稱、證據 SHA 與狀態尚未完全符合欄位級混合來源規格。
- `simulation-lab/runner/validate_market_snapshot.py`：驗證 44 項 Fixture 基本結構與來源中繼資料。
- `simulation-lab/runner/handoff_sp500_to_chart3.py`：S&P 500 資料交接至 Chart 3 的既有入口。
- `simulation-lab/runner/collect_key_levels_ohlc.py`：每日關鍵價位既有獨立 Yahoo Finance 日線 OHLC 流程；本專案保留，不修改其來源契約或改為消費 Stage 2。
- `.github/workflows/tac-simulation-lab.yml`：現有 Stage 2 呼叫鏈及後續資料交接須整合為單一入口。

## 6. 改造工作包與驗收

### WP1｜Observation Schema 統一

- 定義 row-level 與 field-level provenance。
- 統一 `HISTORICAL_PAGE`、`USER_PROVIDED_SCREENSHOT`、`TOOL_READ_FAILURE`、`SOURCE_NO_DATA` 等狀態。
- 截圖值優先；網頁只補未提供欄位。
- SHA-256 對標準化 Observation 與原始證據分別計算，禁止混用。

### WP2｜單一 Stage 2 擷取器

- 先載入使用者截圖觀察清單。
- 截圖已提供欄位不再開啟網頁。
- 其餘必要欄位以 Playwright 開啟 Investing.com Historical Data 表格。
- Cloudflare／工具讀取失敗如實記錄，不切換未核准來源。
- 每項只建立一份最終 Observation，保留嘗試紀錄但不重複核實已鎖定值。

### WP3｜Manifest、Fixture 與 Receipt

- Manifest 固定 44 列且每列唯一。
- 每列保存標的身分、資料日期、欄位值、逐欄輸入方式、來源 URL、證據 SHA、狀態。
- Fixture 與 Manifest 僅由 Stage 2 Observation 產生，不再由下游補寫。
- Receipt 綁定報告日、交易日、Run ID、批次 ID、Fixture SHA、Manifest SHA、Observation SHA。

### WP4｜Chart 3 與每日關鍵價位分流

- Chart 3 只使用 Stage 2 的 S&P 500 鎖定收盤價，不另行抓取同一收盤報價。
- 每日關鍵價位保留獨立 Yahoo Finance 日線 OHLC 擷取及同交易日人工／官方覆寫機制；不併入 Stage 2 44 項，也不回寫 Stage 2。
- 兩條資料流各自封存日期、來源、擷取時間與 SHA，不得互相覆蓋。

### WP5｜下游唯讀與防重抓測試

- Stage 3、4、Builder、QA、Publisher、Pages 不得對已鎖定的 Stage 2 44 項行情發出外部來源請求。
- 增加測試證明已鎖定值不會被後續 Fixture、Manifest 或 Builder 改寫。
- 增加單項補值測試，證明其餘 43 項 SHA／值不變。
- 每日關鍵價位的 Yahoo Finance OHLC 是明確排除項，必須有獨立測試證明 Stage 2 防重抓不會攔截或改寫它。

## 7. 必須完成的驗收案例

1. 截圖同時提供 Close 與 Change %：直接採用，網頁不再讀取該兩欄。
2. 截圖只提供 Close：Close 直接採用，網頁只補必要的 Open／High／Low／Change %。
3. 截圖提供多項 OHLC：已提供欄位不得由網頁覆蓋。
4. 同一商品同時有截圖與較舊網頁值：截圖優先。
5. Investing.com 頁面載入、表格不可讀：`TOOL_READ_FAILURE`。
6. 表格可讀但無目標交易日列：`SOURCE_NO_DATA`。
7. 截圖證據 SHA 不符：不得標示 VERIFIED。
8. Stage 2 Receipt 完成後，下游模擬任何 Stage 2 行情 URL 請求均應被測試攔截。
9. S&P 500 Stage 2 收盤值寫入 Chart 3，數值與 SHA 可追溯。
10. 每日關鍵價位仍可獨立取得 Yahoo Finance OHLC，且不讀取或改寫 Stage 2 快照。

## 8. 明確不在本專案授權範圍

- 不修改 `main/index.html`、正式首頁或正式母版。
- 不修改已核准 Builder 的程式或 SHA。
- 不修改 QA Contract、母版 Manifest 或正式行事曆 JSON。
- 不繞過 Cloudflare，不加入未核准資料供應商。
- 不將 PARTIAL／PENDING／TOOL_READ_FAILURE 偽裝成 VERIFIED。
- 不把每日關鍵價位既有獨立 Yahoo Finance OHLC 流程併入 Stage 2。
- 不把本專案完成等同正式早報發布授權。

## 9. 完成定義

只有 WP1–WP5 全部實作、單元測試與負向測試通過、完整 44 項 E2E 產生鎖定快照、Chart 3 消費 Stage 2 鎖定收盤價、每日關鍵價位獨立 Yahoo Finance OHLC 流程保持正常、下游防重抓測試通過，才可標記 `STAGE2_REDESIGN_ACCEPTED`。在此之前狀態保持 `IMPLEMENTATION_IN_PROGRESS` 或 `PARTIAL`，不得宣稱改造完成。

## 10. 實作紀錄

### 2026-11-26｜第一批程式改造

- `build_market_source_verification_manifest.py` 已調整為支援欄位級截圖證據：不再要求將整個商品的 `source_role` 改成截圖來源；來源契約仍保留 Investing.com。
- Manifest 會分別保存每個截圖欄位的證據路徑、SHA-256 與擷取時間；截圖欄位與歷史頁欄位可在同一筆 Observation 混合記錄。
- 截圖單獨驗證時，`source_page_fetched` 必須維持 false，不得因截圖證據存在而誤報成已讀取 Investing.com 網頁。
- 新增 `test_stage2_field_provenance.py`，涵蓋純截圖、截圖＋歷史頁混合欄位及錯誤 SHA 阻擋；並納入既有 Manifest regression test 的執行入口。
- Simulation workflow 定義暫不修改，以維持與 main/default workflow mirror 的 SHA 一致；新測試由既有 Manifest regression suite 呼叫，不另改 workflow。
- 本批尚未完成截圖檔案自動載入、Playwright 缺欄位選擇性讀取、Fixture 自動合併、Observation bundle／Receipt 產生與完整 E2E；不得標記為完成。
