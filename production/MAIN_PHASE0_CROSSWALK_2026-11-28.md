# TAC Main Phase 0｜Workflow／Runner／Automation 交叉盤點

**盤點日期：** 2026-11-28  
**Repository：** `lion-invlab/lion-invlab.github.io`  
**盤點分支：** `rebuild/tac-main-autonomous-e2e-20261128`  
**基準：** 本分支由當前 Main 建立；Simulation 僅唯讀參考。

## 1. 本輪範圍與限制

已讀取 Main 的 MASTER WR、六份 Stage WR、RUN/HANDOFF/STATUS 契約、Main production Workflow、Run state 與 submission validator、Builder approval、雙母版 Manifest、目前 ChatGPT Automation 任務設定。已核對 24 個 workflow 檔案的觸發／權限／主要寫入路徑訊號。

本輪只做盤點與架構文件，不修改 Main、線上 Automation、排程、首頁、Preview、資料庫或 Simulation。原始 Claude/Gemini 完整診斷文件尚未在 Main repo 或可用檔案庫檢索到；架構決策文件已明確標示這項來源限制，不把摘要冒充原始報告。

## 2. 已確認的正確基礎

1. Main 已有 MASTER WR、六份 Stage WR、共用契約、Run-scoped artifacts、Stage-specific runners。
2. `run-state.json` 已定義六階段狀態、state_version、expected previous status、lease、SUBMITTED 與 PARTIAL 規則。
3. `accept_stage_submission.py` 已提供 Run-bound submission 驗證及原子檔案替換 helper。
4. Stage 1 已拆成獨立短 job；handoff 先提交後才進入 Stage 2/3 job。
5. Stage 2／4 的 ChatGPT worker 僅提交 Run-scoped artifact；GitHub Runner 是 state writer。
6. Stage 3 從 Stage 1 鎖定的週 JSON 唯讀投影；Calendar updater 是週 JSON writer。
7. Stage 5 Builder 有精確 blob SHA approval；目前核准 SHA 僅適用於該 Builder blob。
8. Stage 6 審核版與正式首頁發布已分離；首頁 lock 及使用者核准仍是必要條件。
9. 現有 Main 驗證 workflow run `46104850103` 的 `validate-main-production` job 為 SUCCESS；但 production jobs 全部 SKIPPED。這是程式／契約驗證，不是 Stage 1–6 E2E。

## 3. 必須處理的整合缺口

### P0-A｜Workflow concurrency 不符合可靠排隊語義

目前 `.github/workflows/tac-production.yml` 在 workflow 層使用：

```yaml
concurrency:
  group: tac-main-production-${{ github.ref }}
  cancel-in-progress: false
```

這把同一 branch 的整份正式流程序列化，但 GitHub concurrency group 不提供 FIFO 工作佇列；同一 group 只保留一個 pending run，新 pending 可能取代先前 pending。這與 MASTER WR「同日期不得重複、不同有效工作不得無聲消失」的目標不一致。

**處理方向：** 移除整份 workflow 的 branch-global concurrency；把唯一 Run reservation 收斂到 Stage 1 短 job，使用報告日期識別的 reservation；在建立 Run 前仍須以 Main 最新狀態驗證唯一候選。若平台不能提供可證明的原子 reservation，必須以 fast-forward-only Git commit 作競爭仲裁，push 衝突後重新讀取並重新判定，禁止盲目重試或 force push。此項尚未實作。

### P0-B｜Stage 1 Run reservation 目前不是完整的原子 Active Run 仲裁

Stage 1 會掃描既有 Run、判斷 legacy/stateful、決定 supersedes，再建立新 Run。單靠先讀取再建立，若兩個 dispatch 併發，仍需證明競爭者不能同時通過檢查。

**處理方向：** reservation 必須在唯一短 job 內完成；所有候選檢查、建立初始 Run state、提交與遠端回讀須形成單一可驗證仲裁。拒絕第二個有效 Run，且不得依賴第二套 lock DB。需增加並行觸發測試。

### P0-C｜ChatGPT worker 的 Stage 2→3→4 單次喚醒假設尚未驗收

目前啟用的 Automation 是一個 Stage 2–6 worker，prompt 要求同一次 invocation 提交 Stage 2、等待同 Run Stage 2／3 PASS，再做 Stage 4。GitHub Stage 2/3 job 最長等待 15 分鐘；Stage 4/6 build job 亦輪詢 editorial submission。

這個設計只有在實際 Automation invocation 能跨越 Stage 2 handoff、等待 GitHub Stage 3、再提交 Stage 4 時才成立。僅有 prompt 指令不能證明平台會持續執行，也不能把一次 DEFERRED 當作自動喚醒。

**處理方向：** synthetic E2E 必須實測完整跨階段等待、失敗／逾時與恢復。不可先擅自建立第二個排程或改動現有線上 prompt；若平台無法支援單次 invocation，提出最小改動方案供核准。

### P0-D｜Worker automation 目前啟用狀態需以即時記錄為準

本輪 `peek` 讀到任務 `Automation_f4da15cd95c881918c7412cdd6f35bb2` 為 enabled，下一次執行為 2026-12-01 05:00（台灣）。其最近一次執行回報 11/28 因 Stage 1 handoff 缺失而 BLOCKED；該回報文字曾表示任務被停用，但當前 task record 顯示 enabled。兩者有歷史狀態不一致，正式切換前必須再確認，不得只依 run narrative 判定。

本輪未修改任務 prompt 或 schedule。

### P1-E｜Run state transition 寫入責任需逐一核對

目前狀態契約指定 Main workflow 為唯一 state writer；ChatGPT 不得更新 state。需將每個 runner 中的 state mutation、receipt write、Git commit/push 全部列入責任矩陣，確認不會由 Stage Runner、acceptance helper 與 workflow shell 重複寫同一個 state transition。已有 atomic write helper，不代表跨 workflow／Git commit 的 CAS 已自動成立。

### P1-F｜Main Builder 的驗證範圍不可誤讀

`builder-approval.json` 核准的是精確 Main Builder blob `89cedbb36ec75628c813291adf1bd025c589266e`。最近一次 Main validate run `46104850103` 成功證明 deterministic code validation；其中 Stage 1–6 production jobs skipped。不可把它當成 integrated E2E 或新架構的正式交付證據。

## 4. Workflow 24 檔分類（初步）

| Workflow | 初步定位 | 重建期間處置 |
|---|---|---|
| archive_index.yml | 歷史封存／首頁保護鎖 | 保留；正式切換前核對 lock 與 trigger |
| chart2-preview-browser-qa.yml | Chart 2 視覺 QA | 保留 |
| chart3-preview-visual-qa.yml | Chart 3 視覺 QA | 保留 |
| company_nasdaq100.yml | 公司資料更新 | 保留，另核對寫入範圍 |
| company_profiles.yml | 公司資料更新 | 保留，另核對寫入範圍 |
| company_profiles_nasdaq100.yml | 公司資料更新 | 保留，另核對寫入範圍 |
| main.yml | 舊版市場／watchlist 工作流 | 保留；不可當作 44 項行情備援 |
| mother-template-guard.yml | 母版保護／檢查 | 保留 |
| pages.yml | GitHub Pages 部署 | 保留；核對部署來源與審核版路徑 |
| simulation-workflow-lint.yml | Simulation 規則檢查 | 不改 Simulation；確認 Main 上鏡像是否有副作用 |
| tac-chart3-bootstrap.yml | Chart 3 初始化 | 保留 |
| tac-chart3-incremental.yml | Chart 3 資料更新 | 保留；Stage 2 唯一寫入權須明確 |
| tac-chart3-ingest.yml | Chart 3 ingest | 保留；核對是否重複寫入 |
| tac-chart3-sp500-increment-merge.yml | S&P 500 增量合併 | 非阻塞下游；不得成為第二個行情來源 |
| tac-chart3-stress-analysis-tests.yml | Chart 3 分析測試 | 保留 |
| tac-five-site-browser-poc.yml | 瀏覽器 POC | 保留；不可進正式行情路徑 |
| tac-market-source-capture.yml | Simulation capture experiment | Main 正式流程不得呼叫 |
| tac-production.yml | 唯一 Main 早報 Pipeline | 本次核心施工目標 |
| tac-simulation-lab.yml | Simulation runner／Preview | 保留原貌；不得觸碰 Simulation 資料 |
| tac-simulation-run-monitor.yml | Simulation monitor | 保留原貌；確認不得觸發 Main |
| tac-sp500-increment-qa.yml | S&P 500 增量 QA | 保留 |
| us-mmf-chart-visual-qa.yml | MMF 圖表 QA | 保留 |
| us-mmf-public-data-qa.yml | MMF 公開資料 QA | 保留 |
| volatility-sticky-columns.yml | 舊市場模組 UI／資料檢查 | 保留；核對是否寫入正式路徑 |

此表是觸發／權限／寫入路徑初步分類，不代表已逐一驗證每個 Workflow 的所有 job、第三方 action 或完整執行副作用。下一輪需針對會寫入 `main`、`preview`、`history`、`data/` 的工作流完成逐 job 路徑核對。

## 5. 下一個施工順序

1. 完成 tac-production 的 Stage 1 reservation 與 concurrency 修正設計。
2. 逐一比對 run_state、acceptance helper、Stage 2/3/4/5/6 runner 的 state writer 與 SHA contract。
3. 建立 synthetic worker handoff harness，模擬 ChatGPT Stage 2/4 artifacts，不抓真實行情、不改 Automation。
4. 將新 build branch 加入 validation trigger，讓每次提交可執行 deterministic Main tests。
5. 先通過單元／契約測試，再做兩種母版的完整 synthetic Stage 1–6 E2E。
6. 通過後才申請真實 11/30 fresh-data E2E；不更動首頁及正式排程。

## 6. 本輪狀態

- Phase 0：進行中，核心流程與 24 workflow 初步分類已完成。
- Architecture Decision：已建立並修正來源歸屬說明。
- Main branch：未修改。
- Simulation branch：未修改。
- Automation prompt／schedule：未修改。
- Homepage／formal archive／production schedule：未修改。
- Integrated synthetic E2E：尚未執行。
- 2026-11-30 Preview：尚未產出。
