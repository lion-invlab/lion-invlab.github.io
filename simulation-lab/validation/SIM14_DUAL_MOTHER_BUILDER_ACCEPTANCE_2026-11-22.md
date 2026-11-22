# SIM-1.4 §8.1｜雙母版候選 Builder 技術驗收紀錄（最新證據校正版）

**更新日期：** 2026-11-22  
**分支：** `simulation/tac-process-lab-2026-11-06`  
**範圍：** simulation-only；不含 main 寫入、正式首頁更新或 Pages 部署。

## 驗收結論

候選 Builder 已以**同一個實際 blob SHA**完成 Monday 與 Weekday 兩份母版完整端到端回歸。兩個 GitHub Actions workflow 均 completed／success；兩份 QA sidecar 均為 `QA_PASSED`、`review_ready=true`、`data_review_ready=true`、`content_analysis_gate=PASS`，`review_ready_blockers=[]`，六個 viewport（1440、768、412、390、360、320）均有視覺證據。

此結果先完成候選 Builder 雙母版技術驗證；使用者隨後於 2026-11-22 09:07（台灣時間）明確核准精確路徑與 SHA。現已升格為 SIM-1.4 唯一正式生產入口，兩份 sidecar 均同步為 `sim14_builder_approval=APPROVED`、`sim14_review_ready=true`。

## 本次鎖定資產

| 資產 | 路徑 | 實際 blob SHA |
|---|---|---|
| Active SIM-1.4 | `simulation-lab/TAC_WORK_RULES_SIM.md` | `db31aedbf9325183dc4115e147939d524c9acec5` |
| Candidate Builder | `simulation-lab/runner/build_review_html.py` | `40a3bc70a22bfd1aa4798149599fbd63a1f25efa` |
| Manifest | `simulation-lab/baseline/mother-template-manifest.json` | `8cab2a945b19ffeea5b922353f4f4b8b9c71b9dd` |
| QA Contract v1.16 | `simulation-lab/baseline/mother-template-qa-contract.md` | `30faa8385e19e5bdca0a2fa5c21eda237c52339a` |
| Monday mother | `simulation-lab/baseline/monday-mother-template.html` | `b89c76dd37afdc0cf8b406bfd6f06258896c829d` |
| Weekday mother | `simulation-lab/baseline/weekday-mother-template.html` | `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96` |

## Monday｜2026-11-23

- Workflow run：[`44964279548`](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44964279548) — completed／success。
- Workflow head commit：`42cd32b2bbf4d35c509e95ec8aa0b1d60f2a4d38`。
- Fixture：`simulation-lab/fixtures/report-data-2026-11-23.json`，SHA `948b504a0fba8ba45653cacc0a43cff5377e91a7`。
- HTML：`preview/2026-11-23-simulation.html`，Git blob `7cf64495ff19395d9c68ea156f627e139fa4be32`，SHA-256 `264fe60cba165719631b74fec5e7994e15cfcf3001f01e4864dc01a99d04b4ab`。
- QA sidecar：`preview/2026-11-23-simulation.qa.json`，Git blob `38051d094dd71489ed41d7c2091ce1368b3cf61f`。
- Sidecar 綁定的 Builder／Candidate Builder SHA 均為 `40a3bc70a22bfd1aa4798149599fbd63a1f25efa`；HTML blob SHA 與 branch 上實際 HTML blob 一致。
- QA：`QA_PASSED`；`review_ready=true`；`data_review_ready=true`；`content_analysis_gate=PASS`；blockers 空陣列；六個 viewport 全部列入證據。
- Sidecar 已更新為 `sim14_builder_approval=APPROVED`、`sim14_review_ready=true`、`sim14_blockers=[]`，並記錄核准時間、精確 Builder 路徑／SHA 與兩次雙母版 workflow run。

## Weekday｜2026-11-20（週五）

- Workflow run：[`44964439803`](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44964439803) — completed／success。
- Workflow head commit：`a5adbd78cc6c6c027bc8a99afaa5308525da6397`。
- Fixture：`simulation-lab/fixtures/report-data-2026-11-20.json`，SHA `7b2858217a0492dd84e24e56d3b93897380007e8`。
- HTML：`preview/2026-11-20-simulation.html`，Git blob `0a701740468d8bba3394a000200d2d03e0e26ffb`，SHA-256 `fb552021d4007b47ebc4154e77de05e0c22742b4fe99df6e83a75d514cfeda01`。
- QA sidecar：`preview/2026-11-20-simulation.qa.json`，Git blob `574971356af1d4531d1b2f25bcf0004e9f687d92`。
- Sidecar 綁定的 Builder／Candidate Builder SHA 均為 `40a3bc70a22bfd1aa4798149599fbd63a1f25efa`；HTML blob SHA 與 branch 上實際 HTML blob 一致。
- QA：`QA_PASSED`；`review_ready=true`；`data_review_ready=true`；`content_analysis_gate=PASS`；blockers 空陣列；六個 viewport 全部列入證據。
- Sidecar 的 SIM-1.4 核准欄位已更新為 `APPROVED`／`true`，`sim14_blockers=[]`；核准 provenance 記錄精確路徑、SHA、時間及兩次回歸 run。

## 驗收範圍

兩次 workflow 均執行並通過：deterministic self-tests（含輸出路徑負向測試）、財報 parser／PIT snapshot store 測試、HTML 組裝、Playwright 導覽／tabs／accordion／來源連結、母版視覺比較、DOM preservation、獨立 artifact／provenance 驗證、日期／行事曆數量／44 項行情／新聞結構驗證、QA sidecar seal 及 simulation-only artifact persistence。

資料與內容限制依各自 sidecar 的 `data_audit`／`pending_items` 記錄。兩份 sidecar 的 `review_ready=true`、`data_review_ready=true`、`sim14_builder_approval=APPROVED`、`sim14_review_ready=true` 是分別記錄且均已核對的狀態；本次核准只關閉 Builder 核准 Gate，不代表 live data acquisition／production schedule 端到端驗收已完成。

## 舊紀錄校正

本文件先前版本引用 Builder SHA `42eebdfe18394aa7ff4aca6c226b901516ee6bb1` 及舊 workflow run `44963378227`／`44963530736`。這些不是目前兩份最新 sidecar 所綁定的候選 Builder／run。**本次以 branch 上兩份實際 QA sidecar 與其綁定的 HTML blob 為準，統一校正為 Builder SHA `40a3bc70a22bfd1aa4798149599fbd63a1f25efa`、Monday run `44964279548`、Weekday run `44964439803`。**

## 核准結果與後續權限邊界

- 使用者已於 2026-11-22 09:07（台灣時間）明確核准精確對象：`simulation-lab/runner/build_review_html.py`，blob SHA `40a3bc70a22bfd1aa4798149599fbd63a1f25efa`。
- 此路徑與 SHA 已寫入唯一有效 SIM-1.4 規則第 8.1 節及版本紀錄；兩份 QA sidecar 已更新 `sim14_builder_approval=APPROVED`、`sim14_review_ready=true`、`sim14_blockers=[]`。
- 不修改 main、正式首頁 `index.html`、正式母版、正式 Manifest、正式行事曆 JSON；不部署 Pages。這些仍須各自明確授權。
- Builder 核准及雙母版技術驗收完成，不代表每日 live data acquisition／正式生產排程已完成端到端驗收。
