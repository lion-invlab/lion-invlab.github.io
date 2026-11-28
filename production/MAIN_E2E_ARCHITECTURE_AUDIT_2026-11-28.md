# TAC 投資早報 R3｜Main E2E 全面重建稽核與施工紀錄

**稽核／施工日期：** 2026-11-28  
**Repository：** `lion-invlab/lion-invlab.github.io`  
**正式分支：** `main`（唯讀基線）  
**施工分支：** `rebuild/tac-main-e2e-architecture-20261128`  
**Simulation 參考分支：** `simulation/tac-process-lab-2026-11-06`（唯讀，未修改）

## 1. 本次施工目標與邊界

目標不是修一個 workflow step，而是讓 Main 有一條真正可恢復、Run ID 唯一、Stage 1–6 自動串接的早報生產線。

本分支已獲授權的工作範圍：Main 的 WR、Contracts、Runner、Workflow、Tests、文件與隔離測試分支。以下項目仍未執行，必須取得明確核准：

- 合併重建 PR。
- 修改線上 ChatGPT Automation 任務提示詞。
- 更改或啟用正式生產排程／切換正式生產流程。
- 執行正式市場行情擷取或正式 E2E 早報。
- 更新正式首頁 `index.html` 或正式封存。

Simulation 分支完全唯讀。本分支未修改 Simulation branch、未更新 Main 正式首頁、未修改任何線上 Automation 排程或提示詞。

## 2. 重要根因修正：不再依賴 Connector push 喚醒 Workflow

先前 Main 設計把 Stage 4 editorial JSON 的 Git push marker 當成 Stage 4–6 workflow 的喚醒事件。這個前提沒有可靠證據。

本次回查歷史資料，只有 Simulation branch 的 workflow 執行紀錄，沒有足以證明 GitHub Connector commit 能觸發 Main Actions 的完整 Run ID／event／check 證據。本次隔離驗證分支的 commit 也沒有查到相應的 Actions Run 或 Check。因此，不能把 Connector push 觸發視為已驗證能力。

**正式架構已改為同一個排程 Workflow Run 內完成 Stage 1–6：**

1. `schedule-window` 確認台灣／紐約時區及當日排程。
2. `capture-and-calendar` 建立／恢復唯一 Run，執行 Stage 1–3，並輸出精確 `run_id` 與 `report_date`。
3. `build-and-deliver` 以 `needs.capture-and-calendar` 接續同一 Run；等待該 Run 的 Stage 4 editorial JSON、Stage 4=SUBMITTED 及 SHA 相符，再執行 Stage 4 Runner、Stage 5 Builder/QA、Stage 6 Preview。
4. Stage 4 commit marker `[tac-stage4-submit:<run_id>]` 只作稽核標籤，不觸發第二個 Workflow。
5. Stage 2 與 Stage 4 ChatGPT worker 的提交只更新 Run-scoped artifacts 與 `run-state.json`；已執行中的 GitHub job 輪詢狀態，不依賴 push event。

這個設計不要求第二個 push-triggered workflow，不要求使用者手動按「繼續」，也不會因 Connector push 沒有喚醒 Actions 而中斷。

## 3. Main 現況與既有資料隔離

稽核時 Main HEAD 為：

`d401f31bdd2c016ff5497934ac5230c08763c551`

Main 已有六份 Stage WR、Runner、Contracts、兩份母版與正式 workflow，但原有 Run 目錄中有舊 Run 缺少 `run-state.json`。這些舊 Run 不能被當作可恢復 Run，也不能複製其行情、Fixture 或 Receipt。

本分支已實作：

- 唯一權威狀態：`production/runs/<run_id>/run-state.json`。
- 同一 Workflow retry 沿用穩定 Run ID。
- 新 Run 的 Run ID 綁定 report date 與 GitHub workflow run ID。
- 沒有 `run-state.json` 的 Legacy Run 只列入新 Run 的 `run-context.json: legacy_prior_run_ids`；不讀取、不複製、不覆寫。
- 有 stateful Run 時，正常排程不得另建同日期 Run。
- Recover 只選取唯一、有效、未交付且沒有 Stage 5/6 或 Preview 證據的 Run；候選不唯一即 fail-closed。
- Rerun 使用新 Run ID，記錄 supersedes 關係；舊 Run 與其輸出保留。

## 4. Stage 1–6 職責與交接

| Stage | 執行者 | 職責與交付 |
|---|---|---|
| 1 | GitHub Actions | 唯一建立 Run、Run lock、Run context、Fixture、report-data、治理文件 SHA pin、初始 run-state 與 Stage 1 receipt。快速交付後退出。 |
| 2 | ChatGPT Automation + GitHub Runner | ChatGPT 依 Stage 2 WR 直接讀取 Investing.com Historical Data 表格，完成 44 項行情與 FedWatch；使用者當日截圖依規範優先；最多 4 頁並行；不得 Cloudflare bypass、不得用搜尋摘要／Yahoo／未核准 API 替代。提交同一 Run 的 Observation 與 sidecar；GitHub Runner 驗證並凍結快照、寫 Receipt／狀態。 |
| 3 | GitHub Actions | 驗證並凍結 Stage 2 輸出，唯讀行事曆／財報 DB，處理休市與已公布狀態，產出 Stage 3 receipt 與 Stage 4 Research Bundle。不得重抓行情或寫行事曆 DB。 |
| 4 | ChatGPT Automation + GitHub Runner | ChatGPT 依完整 Stage 4 WR、Research Bundle 與五層分析規則產生新聞、三段總結、Market Sentiment、六領域政治掃描、盤面觀察重點及策略；提交 Run-scoped editorial JSON。GitHub Runner 驗證綁定後改 PASS。不得使用外部 LLM API。 |
| 5 | GitHub Actions | 以正式 Monday／Weekday 母版執行 Builder、DOM／互動／視覺 QA，產生 QA receipt。Stage 2 PARTIAL 時不得偽裝 PASS。 |
| 6 | GitHub Actions | 產生三檔 Main Preview、驗證 Git blob SHA、Pages deployment 與公開 URL；成功後 overall status 為 `AWAITING_APPROVAL`。不得更新首頁。 |

六個 Stage 的 WR 已加上 Main E2E v1.2 版本標記；每個 Stage 開工前必須執行 WR Preflight，核對 MASTER_WR SHA、本 Stage WR SHA、前一 Stage Receipt SHA、Run ID、日期與交付物完整性。

## 5. Run-state 與恢復語義

`RUN_CONTRACT.md` 已更新至 v1.3，`HANDOFF_CONTRACT.md` 已更新至 v1.3，`MASTER_WR.md` 已更新至 v1.7。

核心規則：

- 每個 Run 只有一個權威 `run-state.json`，以 state_version + Git blob SHA compare-and-swap 更新。
- Stage 2/4 ChatGPT worker 必須先 claim RUNNING 並設定 lease；有效 lease 不可搶占，過期 lease 才能恢復。
- Stage 2/4 提交 Observation／Editorial JSON 後，必須讀回並核對完整 bytes SHA，才可轉 SUBMITTED。
- Stage 2/4 Runner 只接受同一 Run 的 SUBMITTED handoff。
- Stage 2 PARTIAL 是終態；Stage 5 PARTIAL 使 Stage 6=SKIPPED；不得把 PARTIAL 當成可重開狀態。
- FAILED 可依 state machine 使用 recovery=true 回 READY；DEFERRED 可安全恢復；不得因一次失敗停用 Automation。
- Stage 3/5/6 Runner 可在同一 Run 的 FAILED 狀態下安全恢復，且跳過已 PASS 階段。
- Stage 6 receipt 的 `DELIVERED_AND_PUBLICLY_VERIFIED` 不等於首頁發布核准；overall status 保持 `AWAITING_APPROVAL`。

## 6. Stage 2 與 Stage 4 Run-scoped handoff

- Stage 2 Observation：`production/runs/<run_id>/market-history-web-observations.json`。
- Stage 2 screenshot sidecar、CNN sidecar 與原圖均放在同一 Run 目錄。
- Stage 4 Editorial：`production/runs/<run_id>/stage4-editorial-content.json`。
- Stage 4 JSON 綁定 `run_id`、`report_date`、`market_snapshot_sha256`、`research_bundle_sha256`、`stage3_receipt_sha256`、`stage4_wr_sha256`。
- Stage 4 build job 等待內容檔與 Stage 4 SUBMITTED 狀態的 SHA 相符；不讀取舊日期共用檔，不依賴 marker push。
- Stage 2／Stage 4 任務提示詞草案已建立於 `production/CHATGPT_AUTOMATION_PROMPT_MAIN_v1.2.md)，並納入 Stage 1 governance pin。線上 Automation 尚未更新。

## 7. Preview、Pages 與 Simulation 隔離

Main Stage 6 原本使用 `preview/<date>-review.*`，與 Main 上的 Simulation mirror workflow 可能寫入的根層 Preview 檔名衝突。

本分支將 Main Preview 改為：

- `preview/main/YYYY-MM-DD-review.html`
- `preview/main/YYYY-MM-DD-review.qa.json`
- `preview/main/YYYY-MM-DD-review.delivery.json`

Simulation 保留既有 `preview/` 根層輸出，未修改 Simulation workflow 或 Simulation branch。

Pages 觸發關係已整理：

- Main Stage 6 使用明確的 `workflow_dispatch` 呼叫 `pages.yml`。
- Simulation mirror workflow 保留其既有明確 Pages dispatch。
- Chart 3 增量／合併／Bootstrap 完成後，透過 `workflow_run` 觸發 Pages／視覺 QA。
- `pages.yml` 不再因 `preview/*.html` push 或 `data/tac-chart3/**` push 重複部署；這些交付改由明確 dispatch／workflow_run 負責。
- Chart 3 Bootstrap 已與日常 Chart 3 writers 共用 `tac-chart3-data-maintenance` concurrency group。

## 8. Chart 3 非阻塞下游

- Stage 2 仍是 S&P 500 每日增量的早報唯一寫入者，不另抓第二份 S&P 500 報價。
- Main production workflow 完成後，Chart 3 workflow_run 以 `workflow_run_id` 對應唯一 Run，核對 Stage 2=PASS/PARTIAL、Stage 3=PASS 與必要 Receipt 後才接手。
- Chart 3 不依賴 Stage 4 marker push，不與 Stage 4–6 共用資料鎖，也不得阻塞早報主線。
- Chart 3 Incremental、S&P 500 Merge、Bootstrap 共用自己的資料維護鎖；Pages／Visual QA 在相應 workflow 完成後接續。
- Chart 3 失敗只影響 Chart 3 下游，不改寫 Stage 2/3 結果，不阻止早報 Preview。

## 9. 24 個 Workflow 稽核摘要

| Workflow 類別 | 已確認的責任／寫入範圍 | Main 早報主線處理 |
|---|---|---|
| `tac-production.yml` | Main Stage 1–6 唯一正式生產入口；寫入 Run artifacts、Main Preview | 本分支重整為同一 Workflow Run 的兩段 job |
| `pages.yml` | 共用 Pages 部署服務；push、workflow_dispatch、workflow_run | Main Preview 明確 dispatch；Chart 3 workflow_run；避免重複 push 部署 |
| `archive_index.yml` | 只封存已核准的既有正式首頁／歷史報告；有 publication lock | 不封存審核 Preview；排程未修改 |
| `main.yml`、`company_nasdaq100.yml` | 舊有 yfinance／波動度資料寫入 `data/`；排程約台灣 05:10／05:20 | 不屬於 Stage 2 44 項來源，不得當備援；與 Run-scoped 產物路徑分離 |
| `company_profiles.yml`、`company_profiles_nasdaq100.yml` | 週末公司資料更新 | 獨立資料 writer，不屬於早報行情擷取 |
| `mother-template-guard.yml` | 母版保護檢查 | 保留 |
| `simulation-workflow-lint.yml` | Simulation workflow lint | Simulation 專用，不修改 |
| `tac-simulation-lab.yml` | Simulation branch 流程，可發布根層 Simulation Preview | 保持唯讀；Main Preview 改用 `preview/main/` 避免覆寫 |
| `tac-simulation-run-monitor.yml` | Simulation run 監控／通知 | 只讀，不介入 Main Run |
| `tac-market-source-capture.yml` | Simulation 擷取實驗／artifact | 不作 Main Stage 2，不修改 |
| `tac-chart3-incremental.yml`、`tac-chart3-sp500-increment-merge.yml`、`tac-chart3-bootstrap.yml` | Chart 3 資料 writer | 共用 Chart 3 lock；精確 Run handoff；下游非阻塞 |
| `tac-chart3-ingest.yml` | 手動 ingest／artifact | 不寫 Main 正式早報輸入 |
| `tac-chart3-stress-analysis-tests.yml`、`chart3-preview-visual-qa.yml` | Chart 3 測試／視覺 QA | QA／下游 |
| `chart2-preview-browser-qa.yml`、`tac-sp500-increment-qa.yml`、`volatility-sticky-columns.yml` | 專項 QA | 不建立正式 Run |
| `tac-five-site-browser-poc.yml` | 手動瀏覽器 POC | 不寫正式資料 |
| `us-mmf-chart-visual-qa.yml`、`us-mmf-public-data-qa.yml` | US MMF 研究資料／QA；資料 writer 僅寫研究分支 | 不屬於 Main 早報 |
 
所有 24 個 workflow 的 trigger、branch／path filter、permissions、concurrency、寫入範圍與 cross-workflow handoff 已逐一檢視。未授權的排程或正式流程未更動。

## 10. PR #363 處理

PR #363（只修改舊 `tac-production.yml`）未合併。本分支保留其中有價值的 Stage 1 輕量化與 Run／日期／SHA 綁定概念，但不採用長時間 push marker／polling 作為跨 workflow 主交接，也不把 PR #363 直接合併。

## 11. 本分支實際變更範圍

- `production/runner/run_state.py` 與狀態測試：統一 Stage 1–6 state machine、lease、PARTIAL 終態、FAILED 恢復、AWAITING_APPROVAL。
- Stage 2 Run-scoped handoff validator、receipt、Runner 與測試。
- Stage 3/4/5/6 Runner：Run ID、Receipt SHA、state transition 與安全恢復。
- `create_run_fixture.py`：穩定 Run ID、Legacy Run 隔離。
- `tac-production.yml`：Stage 1–3 輸出 Run ID／日期；Stage 4–6 job 依賴 capture job，於同一 workflow run 輪詢 Stage 4 提交。
- Chart 3 workflows：以 workflow_run_id 對應精確 Main Run；Chart 3 writers 共用 lock。
- `pages.yml`：去除 Preview／Chart 3 重複 push deployment 路徑。
- Main Preview namespace：`preview/main/`。
- MASTER_WR、六份 Stage WR、RUN／HANDOFF contracts、ChatGPT Automation prompt、PORT_MANIFEST、稽核文件。

## 12. 驗證狀態與未完成門檻

**驗證狀態：尚未執行正式 E2E**

目前沒有執行正式行情擷取、正式早報、Pages 正式 Preview 或首頁更新。

本次隔離分支的 GitHub Connector commit 未取得 Actions Run／Check，因此不能宣稱 push-trigger 已驗證，也不能宣稱 Python tests、compileall 或 workflow YAML 已通過。正式生產流程未啟動。

下一個必要驗證是對本分支執行 Main validation workflow（`workflow_dispatch mode=validate` 或等效的受控 CI），確認：

1. Workflow YAML／job graph 可被 GitHub Actions 接受。
2. Python compileall 與全部 Runner unit tests 通過。
3. Run-state transition／Legacy Run isolation／Stage 2 handoff／Stage 4 schema tests 通過。
4. Stage 4–6 job 依賴與 output binding 正確。
5. Chart 3 workflow_run exact Run resolver 與 Pages dispatch／workflow_run 無重複觸發。
6. 之後才可提出正式排程與 Automation prompt cutover。

### 尚需明確核准

- 合併本分支 PR。
- 將線上 ChatGPT Automation 任務更新為 `production/CHATGPT_AUTOMATION_PROMPT_MAIN_v1.2.md`。
- 啟用／切換正式 Main 生產流程及任何排程變更。
- 執行第一個正式完整 E2E Run。
- 正式首頁更新仍需另外核准，不包含在本次重建授權內。

## 13. 未變更確認

- Main `index.html` 未修改。
- Main 正式排程未修改。
- 線上 ChatGPT Automation 提示詞與排程未修改。
- 未執行正式行情擷取。
- Simulation branch 未修改。
- PR #363 未合併。
- 本次所有程式、WR、Contracts、Workflow 與文件變更僅位於隔離施工分支。
