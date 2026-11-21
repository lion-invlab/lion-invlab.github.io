# SIM-1.4 §8.1｜雙母版候選 Builder 技術驗收紀錄

**日期：** 2026-11-22  
**分支：** `simulation/tac-process-lab-2026-11-06`  
**範圍：** simulation-only；不含 main 寫入、正式首頁更新或 Pages 部署。

## 驗收結論

週一母版與週二至週五母版均已使用同一組 Builder／Manifest／QA Contract／Active SIM-1.4 完成完整建置與 QA。兩份審核 HTML 均為 `QA_PASSED`、`review_ready=true`、`review_ready_blockers=[]`；六個 viewport（1440、768、412、390、360、320）均完成視覺驗收。兩個 workflow run 均成功，母版 DOM preservation、瀏覽器互動、獨立 provenance、44 項行情、行事曆筆數與新聞結構 Gate 均通過。

此結果只代表候選 Builder 的雙母版技術驗收完成（CANDIDATE_VALIDATED），**不代表使用者已核准 Builder 作為唯一 SIM-1.4 生產入口**。

## 兩份完整驗收證據

### Monday｜2026-11-23
- Workflow run：[`44962942410`](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44962942410)
- Head commit：`9fb148d2fc9a938c6d4e92e4262702980ac2d39a`
- 全部 39 個工作步驟完成；必要 build、字型、Playwright、互動、母版比對、DOM、獨立驗證、資料結構、QA 封存與 simulation-only persistence 均成功。
- HTML：`preview/2026-11-23-simulation.html`，Git blob `bd18ea5ff40a84f826dc1f4162ee7f6ec7ce242b`，SHA-256 `3b9a2c652b9f286b7b46823002f244912567645f9874b6f5e783ee1fc50d27cd`。
- QA sidecar：`preview/2026-11-23-simulation.qa.json`，blob `774b582b2f22b8be6a79bf96cd04eec742ff8e6e`。
- QA 狀態：`QA_PASSED`；`review_ready=true`；blockers 空陣列；sidecar 綁定 HTML blob SHA 正確。
- 產製日期 2026-11-23，市場基準日 2026-11-20。

### Weekday｜2026-11-20（週五）
- Workflow run：[`44962585698`](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44962585698)
- Head commit：`b90c676b474fbb34a1c8e9eb4d2e78a0e7da5f06`
- 全部必要 build、字型、Playwright、互動、母版比對、DOM、獨立驗證、資料結構、QA 封存與 simulation-only persistence 步驟成功。
- HTML：`preview/2026-11-20-simulation.html`，Git blob `ad27ddea3d81e2b30ebebd1d13600822831a7f53`。
- QA sidecar：`preview/2026-11-20-simulation.qa.json`，blob `1c2d91905b7f1dd7b7e6708424e57872a3aaa702`。
- QA 狀態：`QA_PASSED`；`review_ready=true`；blockers 空陣列；sidecar 綁定 HTML blob SHA 正確。
- 行情基準日 2026-11-19；44 個固定行情欄位均有可顯示報價並逐項檢查來源。

## 兩母版共同 provenance（完全一致）

| 項目 | SHA |
|---|---|
| Candidate Builder `simulation-lab/runner/build_review_html.py` | `b6082923a88ab2b592f2d2765f68d4f4214caca8` |
| Active SIM-1.4 `simulation-lab/TAC_WORK_RULES_SIM.md` | `e18865fc31a88f98e44cb1f411817e61406a34c1` |
| Superseded SIM-1.4 Draft | `0d64eb9b16202d3e9e6d86a1aa87b7105843d571` |
| Manifest | `8cab2a945b19ffeea5b922353f4f4b8b9c71b9dd` |
| QA Contract v1.16 | `30faa8385e19e5bdca0a2fa5c21eda237c52339a` |
| Monday mother | `b89c76dd37afdc0cf8b406bfd6f06258896c829d` |
| Weekday mother | `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96` |

## Gate 與保留事項

- 兩版六個 viewport 視覺回歸通過；Monday 已公布財報 EPS／Revenue 雙卡在手機寬度維持兩欄。
- Fed 官員行程沿用母版 prototype 與原始子節點樣式，不由 Builder 改寫成單欄。
- 44 項行情結構、行事曆數量／日期狀態、新聞結構、來源連結、互動與折疊功能均通過。
- W48 缺乏可驗證 point-in-time 共識快照者仍顯示待核實，不判定 Beat／Miss。
- 週末四項市場指標沿用使用者確認的最新基準快照，報告保留實際資料時間；不得把沿用值描述為週日刷新。
- W47 已公布值與 W48 個別欄位修正屬審核版投影，不回寫 main 正式行事曆 JSON。
- 本輪未修改 main、正式首頁、正式母版、正式 Manifest 或正式行事曆 JSON；未部署 Pages。

## 尚待使用者明確核准

兩份 QA sidecar 均保留：
- `sim14_builder_approval=NOT_APPROVED`
- `sim14_review_ready=false`
- blocker：`Candidate Builder has not been explicitly approved as the unique SIM-1.4 production entry point`

**待核准的精確對象：** `simulation-lab/runner/build_review_html.py`，blob SHA `b6082923a88ab2b592f2d2765f68d4f4214caca8`。在使用者明確核准前，不得標記 `sim14_review_ready`，不得把候選 Builder 宣告為唯一正式生產入口，也不得更新 main 正式首頁。
