# TAC 投資早報 R3｜main 重建 Phase 0 資產盤點與架構定案

盤點日期：2026-11-26（Asia/Taipei）
Repository：`lion-invlab/lion-invlab.github.io`
目標分支：`main`
盤點基準 HEAD：`7df1f84dded5814b306ba98968915da091b50b6c`
本文件性質：Phase 0 盤點交付；不代表新 Pipeline 已建立或可執行。

## 1. 盤點範圍與方法

已直接讀取 main 分支 Git tree（recursive，391 個項目，未截斷）、主要檔案內容、GitHub Actions workflow 目錄、母版 Manifest、雙母版登記 SHA、行事曆週檔目錄、Chart 3 資料目錄及既有 Session State／Work Log 的指定範圍。

Simulation 分支只確認分支存在，不修改、不搬移、不重寫。後續如需參考 Simulation 程式，必須以唯讀方式讀取，並記錄來源 SHA。

## 2. main 現況基準

| 項目 | 實際狀態 |
|---|---|
| 預設分支 | main |
| main HEAD | `7df1f84dded5814b306ba98968915da091b50b6c` |
| HEAD 提交 | 2026-11-26T03:38:41Z，Update Nasdaq-100 volatility data |
| Repository 權限 | 已確認目前連線具 admin／push 權限 |
| Simulation 分支 | `simulation/tac-process-lab-2026-11-06` 存在；本次未寫入 |
| 新 production 目錄 | 盤點時不存在 |
| 新 main 正式 Pipeline | 尚不存在 |
| 正式首頁 | `index.html` 存在，blob SHA `032090e047a363e7654e36c12adadbe859666bc2`；本次未修改 |
| 舊正式規則 | `TAC_WORK_RULES.md` v5.17，blob SHA `0210e8e04f4f6b2374997b82a658e15781932e67` |
| 母版 Manifest | `母版專區/mother-template-manifest.json`，blob SHA `fade5e3d88de76a79cb5c1656cc592b98827ab55` |
| Session State | `TAC_SESSION_STATE.md`，blob SHA `fb7c634bad4c13b17aeb91731894ee5c7973c34b` |
| Work Log | `TAC_WORK_LOG.md`，blob SHA `8007d9fd7c2df1dc1453a734d57342050c300ebb` |

## 3. 現有資產盤點與處置建議

### 3.1 規則、母版與執行紀錄

| 資產 | 現況 | Phase 0 處置／後續 |
|---|---|---|
| `TAC_WORK_RULES.md` | v5.17；包含舊六步驟、舊資料擷取與舊交付要求 | Phase 1 以新 MASTER WR 取代其唯一正式規則角色；舊檔保留為歷史參考或加相容導讀，避免雙重權威 |
| `母版專區/mother-template-manifest.json` | 雙母版 SHA 已登記 | 保留作唯一核准母版清單；新 production manifest 只引用，不複製母版 |
| 週一母版 | `母版專區/TAC_母版_週一_2026-10-28_最終定版.html`；SHA `a568e594e55909041d51d8eae7e6fe5f7986c096` | A 類候選：保留原檔，經獨立解析與輸出驗證後引用 |
| 週二至週五母版 | `母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html`；SHA `3785405e331b10ec6189002e480be2a1edbe20ef` | A 類候選：保留原檔，經獨立解析與輸出驗證後引用 |
| `母版專區/母版結構驗收清單.md` | v1.3；含 SHA 綁定 selector 契約 | A 類參考；需轉成新 QA 契約的可執行檢查，不照搬舊的每日工作流程 |
| `母版專區/TAC_WORK_RULES.md` | 舊版規則副本 | 檢查是否仍有引用；不得保留為第二權威 |
| `TAC_SESSION_STATE.md`／`TAC_WORK_LOG.md` | 舊流程進度及證據紀錄 | 先保留；新 Pipeline 建立獨立 Run ID／Run 狀態格式後，定義新舊記錄邊界，不直接混寫每日新流程 |

### 3.2 現有程式與測試

main 根目錄 `scripts/` 現有資產包括：
- 行情擷取：`fetch_tac_global_indices.py`、`fetch_tac_sector_etfs.py`、`fetch_tac_treasury_yields.py`、`fetch_tac_treasury_fred_fallback.py`、`capture_tac_fedwatch_fallback.mjs`
- 舊 Snapshot 流程：`assemble_tac_daily_snapshot.py`、`validate_tac_daily_snapshot.py`、`ingest_tac_snapshot_comment.py`、`render_tac_market_snapshot_to_html.py`
- HTML／版型驗證：`validate_mother_template.py`、`validate_tac_html_binding.py`、`validate_tac_layout_contract.py`、`validate_tac_report.py`、`tac_browser_layout_regression.mjs`
- 欄位與映射：`tac_html_binding_map.json`、`tac_market_field_map.json`
- 其他市場／公司資料及 WR lock 程式：`update_data.py`、`update_tac_watchlist.py`、`update_nasdaq100.py`、`update_profiles.py`、`tac_wr_lock.py` 等。

處置原則：這些程式不能因為存在就視為新 Pipeline 的正式元件。Phase 1 先建立功能／輸入／輸出／副作用對照；Phase 2 逐項決定直接採用、包裝、重寫或排除。禁止將多個舊入口同時保留為正式生產入口。

### 3.3 GitHub Actions 現況

main 的 `.github/workflows/` 盤點到 22 份 workflow：

- `archive_index.yml`
- `chart2-preview-browser-qa.yml`
- `chart3-preview-visual-qa.yml`
- `company_nasdaq100.yml`
- `company_profiles.yml`
- `company_profiles_nasdaq100.yml`
- `main.yml`
- `mother-template-guard.yml`
- `pages.yml`
- `simulation-workflow-lint.yml`
- `tac-chart3-bootstrap.yml`
- `tac-chart3-incremental.yml`
- `tac-chart3-ingest.yml`
- `tac-chart3-sp500-increment-merge.yml`
- `tac-chart3-stress-analysis-tests.yml`
- `tac-five-site-browser-poc.yml`
- `tac-market-source-capture.yml`
- `tac-simulation-lab.yml`
- `tac-simulation-run-monitor.yml`
- `tac-sp500-increment-qa.yml`
- `us-mmf-chart-visual-qa.yml`
- `us-mmf-public-data-qa.yml`
- `volatility-sticky-columns.yml`

註：上列實際共 23 份（逐項盤點後以清單為準；不是 22 份）。其中：
- `main.yml` 名稱為 Update S&P 500 Volatility Data，排程 cron `10 21 * * 0-4`，執行 `update_data.py` 與 `update_tac_watchlist.py`，會寫入 `data/`；它不是 TAC 早報正式 Pipeline。
- `archive_index.yml` 監看 `index.html` push，另有 cron `10 17 * * 0-4`，會從 index 歷史 commit 建立 `history/` 封存。這與新 Stage 6 的核准後封存責任必須整併，避免雙重封存／錯誤日期。
- `pages.yml` 監看 preview、history、research、Chart 3 data、index 等路徑並部署 Pages；新 Stage 6 應重用部署能力，不另建競爭部署器。
- `tac-simulation-lab.yml` 位於 main，觸發來源是 Simulation 分支 push／workflow_dispatch，內容明確 checkout Simulation 並將產物交付 main/preview。新 main Pipeline 上線前保留供舊流程歷史參考；新 Pipeline 完成切換時必須停用這條跨分支正式交付路徑，不能讓兩套流程同時產出同一日期報告。
- `tac-market-source-capture.yml` 標示 simulation only，checkout Simulation；不得作為 main 的正式行情擷取器。
- Chart 3 有多個 bootstrap／incremental／ingest／merge／QA workflow；需盤點唯一資料寫入者及 S&P 500 日增量的交接，避免 Stage 2 與舊 workflow 重複寫入。
- 其餘公司資料、波動率、MMF、Chart 2／3 QA workflow 屬其他產品功能，除非確認與早報衝突，否則保留。

### 3.4 行事曆資料庫

正式路徑已存在：`data/calendar/weeks/YYYY-Www.json`。
目前目錄包含 W44、W45、W46、W47、W48 五份週檔；W48 SHA 為 `342a51861991cfaa7367d83dffa91a71f6fa7cf5`。

重建計畫指定行事曆排程為週 JSON 唯一寫入者，早報 Stage 3 唯讀。新 Runner 不得自行修改週 JSON，也不得另建平行資料庫。Phase 1 必須從實際 W48 schema 與現行更新 workflow 反推正式欄位契約，再定稿 DATA_SCHEMA。

### 3.5 Chart 3

正式資料實際位於 `data/tac-chart3/`，不是計畫草案中提及的 `data/chart3/`。包含：
- `manifest.json`、市場壓力彙總 JSON、QA JSON、SHA sidecar、release schedule；
- VIXCLS、NFCI、NFCICREDIT、STLFSI4 四組歷史／vintage 資料；
- S&P 500 1927–2026、1993–2026 compact JSON 及 `sp500_daily_increment.jsonl`；
- 呈現端 `research/tac-chart3/chart3-preview.html`；
- 下載及資料處理程式 `research/tac-chart3/tac_fred_alfred_download.py`。

後續整合必須沿用現有 `data/tac-chart3/` 正式資料位置，不能依草案新建 `data/chart3/`。Stage 2 是 S&P 500 每日增量的唯一正式寫入者；Chart 3 舊排程應轉為補充檢查／非競爭性驗證，具體改造於 Phase 3／6 完成。

### 3.6 Preview／歷史報告

- `preview/` 已存在，含 2026-11-24 的 HTML、QA、delivery、receipt 產物。
- 2026-11-26 已存在 `preview/2026-11-26-review.html`、`preview/2026-11-26-review.qa.json`、`preview/2026-11-26-review.delivery.json`；此三檔是既有歷史產物，不因新架構而覆蓋或改名。
- `history/` 已存在，根目錄亦有多份日期 HTML；新 Stage 6 必須先盤點現行 history index schema 與 archive workflow，沿用既有歷史 URL 慣例，避免雙重封存。
- 新規劃路徑 `preview/YYYY-MM-DD-review.html` 與現有 `preview/YYYY-MM-DD-review.{html,qa.json,delivery.json}` 命名可相容；Delivery receipt 的副檔名／命名需在 PUBLISH_CONTRACT 明確統一。

## 4. 主要跨檔案依賴與風險（重建時必須同步檢查）

| 修改位置 | 必須同步檢查的關聯資產 |
|---|---|
| MASTER WR／Stage WR | STATUS_ENUM、DATA_SCHEMA、SOURCE_POLICY、RUN／HANDOFF、QA、PUBLISH 契約、Runner 實際行為 |
| 行情欄位／來源規則 | 44 欄位清單、母版 KPI／表格、欄位 map、資料 Schema、狀態轉換、分析引用、QA |
| Stage 2／行情 Runner | Investing.com 頁面讀取、使用者提供截圖的優先採用規則、來源時間、狀態、重試策略、FedWatch、Chart 3 S&P500 寫入 |
| Stage 3 | Wxx JSON schema、04:35 排程唯一寫入者、時區、已公布事件與共識欄位、週一回顧區塊 |
| Stage 4 | 新聞時間窗、5+10 數量、三段總結、市場情緒、分析引用行情狀態 |
| Stage 5／Builder | 雙母版 SHA、Manifest、DOM 定位契約、CSS／JS、頁面模組、Chart 3 引用、四類 QA |
| Stage 6／發布 | preview 三件套、Pages workflow、history archive workflow、index.html 核准權限、正式網址與歷史索引 |
| 排程／Workflow | 04:35 calendar、05:25 report、05:30 Chart 3；新舊 workflow 去重、concurrency、branch scope、權限及觸發條件 |
| Chart 3 | `data/tac-chart3/` schema、S&P500 increment、舊 ingest／merge workflow、chart renderer、每日唯一 writer |

## 5. Phase 0 架構定案

採用重建計畫原定結構，不新增第二套資料庫或第二個生產入口：

- `production/MASTER_WR.md`
- `production/stages/STAGE_1_CONTEXT.md` 至 `STAGE_6_DELIVERY.md`
- `production/contracts/`：DATA_SCHEMA、STATUS_ENUM、SOURCE_POLICY、RUN_CONTRACT、HANDOFF_CONTRACT、HTML_BUILDER_CONTRACT、QA_CONTRACT、PUBLISH_CONTRACT
- `production/config/`：production manifest、schedule config
- `production/runner/run_daily_report.py`：唯一正式入口及六個 Stage runner
- `.github/workflows/tac-production.yml`：main 專用正式 Workflow
- 沿用既有 `母版專區/`、`data/calendar/weeks/`、`data/tac-chart3/`、`research/tac-chart3/`、`preview/`、`history/`、`index.html`。

架構責任：
1. Calendar updater 是 Wxx JSON 唯一 writer；Stage 3 唯讀。
2. Stage 2 是早報行情資料集唯一 writer；每項資料完成後鎖定，不被後續階段覆寫。
3. Stage 2 是 S&P 500 Chart 3 日增量唯一正式 writer；既有 Chart 3 workflow 不得同時寫入相同日期資料。
4. Stage 5 是當次審核版 HTML 唯一 writer。
5. Stage 6 是當次 preview sidecar／delivery receipt 唯一 writer；Pages workflow 僅負責部署，不重寫報告內容。
6. 正式首頁與歷史封存只在使用者核准後執行；自動 archive workflow 必須與新核准流程整併，避免未核准即封存或封存錯誤日期。
7. 每次 Run ID 唯一；Stage 輸出綁定同一 Run ID，失敗只從最後有效輸出恢復。
8. Simulation 分支及其資產唯讀保留，不納入 main 執行依賴。

## 6. Phase 0 尚待 Phase 1 詳查的項目

以下不阻止 Phase 0 架構定案，但在對應契約／程式實作前必須取得原始內容並完成比對：
- 完整 44 欄位與每一項 Investing.com 商品 URL／來源優先序。
- FedWatch 動態頁解析及截圖數值證據欄位。
- W48 行事曆完整 schema、財報共識來源層級及更新排程實作。
- Chart 3 manifest、increment merge／ingest workflow 的完整寫入路徑及冪等規則。
- history/index.json schema 與舊 archive workflow 觸發細節。
- Pages 部署公開 URL 與 preview 子路徑驗證方式。
- 外部既有排程的實際啟用狀態及新舊切換步驟；不得在 Phase 0 提前停用或新增排程。

## 7. Phase 0 結論與下一階段

Phase 0 已完成主要 main tree、正式母版、Manifest、舊 WR、workflow、行事曆、Chart 3、preview／history 的盤點與依賴識別。新架構路徑已定案。

**重要發現：**
- main 尚無 `production/` 新架構。
- 舊 WR v5.17 與新重建計畫的權責及流程不同，不能直接疊加。
- 舊 Simulation workflow 仍由 main 上的 workflow 定義跨分支執行並交付 main/preview；新系統啟用前不可與新入口並行。
- 現有正式母版 SHA 與 Manifest 一致，應直接沿用。
- Chart 3 真正正式資料路徑是 `data/tac-chart3/`，須修正計畫草案中的路徑差異。
- 舊 archive workflow 可能在首頁更新後自動封存，必須與新核准發布流程整併。
- 現有 Pages workflow 已支援 preview／history／Chart 3 部署，應沿用而非另建部署系統。

下一步進入 Phase 1：先建立 MASTER WR 與八份共用契約的資料模型及責任界線，再寫六份 Stage WR；所有規則完成交叉一致性檢查後，才開始 Phase 2 Runner 實作。不得跳過契約直接寫 Runner。
