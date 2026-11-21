# SIM-1.4 §8.1｜雙母版候選 Builder 技術驗收紀錄

**更新日期：** 2026-11-22  
**分支：** `simulation/tac-process-lab-2026-11-06`  
**範圍：** simulation-only；不含 main 寫入、正式首頁更新或 Pages 部署。

## 驗收結論

候選 Builder 已完成寫入路徑防護，並以同一個最新 Builder SHA 分別通過 Monday 與 Weekday 完整端到端回歸。兩次 workflow 均 completed／success；兩份 QA sidecar 均為 `QA_PASSED`、`review_ready=true`、`review_ready_blockers=[]`，六個 viewport（1440、768、412、390、360、320）均完成視覺驗收。

此結果代表候選 Builder 的雙母版技術回歸及輸出路徑防護測試完成（CANDIDATE_VALIDATED）。**不代表使用者已核准此 Builder 作為唯一 SIM-1.4 生產入口。**兩份 sidecar 均保留 `sim14_builder_approval=NOT_APPROVED`、`sim14_review_ready=false`。

## 本輪精確 Builder 與寫入防護

- Builder：`simulation-lab/runner/build_review_html.py`
- Builder blob SHA：`42eebdfe18394aa7ff4aca6c226b901516ee6bb1`
- 新增輸出路徑解析／限制：只允許標準化輸出至 `preview/YYYY-MM-DD-simulation.html`；解析實際路徑以防止 traversal 與 symlink escape；拒絕寫入正式首頁、母版、Manifest、正式行事曆 JSON、非標準檔名及 preview 目錄外路徑。
- 新增負向測試：`simulation-lab/runner/test_builder_output_guard.py`，blob SHA `a6c3ff9107ab912ea01e694aac6f7d87047f94c8`。涵蓋標準輸出、受保護路徑、路徑穿越／錯誤檔名、preview 目錄 symlink escape、輸出檔 symlink escape。
- 負向測試已納入 workflow deterministic self-tests；Monday 與 Weekday 最新 run 均通過該組測試。
- 此防護是 Builder 層輸出路徑限制，搭配 workflow simulation-branch-only 隔離；不得解讀為對 GitHub 權限或所有其他程式寫入路徑的全面安全保證。

## 兩份最新同版完整回歸證據

### Monday｜2026-11-23

- Workflow run：[`44963378227`](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44963378227)
- Trigger commit：`aee9976633237e2e902eeb385d10ca1012352b4a`
- HTML：`preview/2026-11-23-simulation.html`
- HTML Git blob：`586766c7e44c126406b22aefcf8e3342365d5f7f`
- HTML SHA-256：`211fa41449f83734206858e01222ad1b27339d95b597f0dbecf0e5661c9b7317`
- QA sidecar：`preview/2026-11-23-simulation.qa.json`
- QA blob：`66a4a819e6e4be2fa38f1b2a3a916668b869d94b`
- Sidecar 的 `report_git_blob_sha` 精確綁定上述 HTML；Builder 與 candidate Builder SHA 均為 `42eebdfe18394aa7ff4aca6c226b901516ee6bb1`。
- Sidecar：`QA_PASSED`、`review_ready=true`、`data_review_ready=true`、`content_analysis_gate=PASS`、review blockers 空陣列。
- 六個 viewport：1440／768／412／390／360／320。

### Weekday｜2026-11-20（週五）

- Workflow run：[`44963530736`](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44963530736)
- Trigger commit：`7f7623d85224e3de02f8825b0bc68e878a4bbcde`
- HTML：`preview/2026-11-20-simulation.html`
- HTML Git blob：`aafa41c07ac5d490412a35f296e8169375aaa74a`
- HTML SHA-256：`7a72460622dfb65720e21a013ace79a486d85db950eae4ee9401098d3a5b2f38`
- QA sidecar：`preview/2026-11-20-simulation.qa.json`
- QA blob：`e8232c1f68daec6bf3b05a5e5446abfabf726257`
- Sidecar 的 `report_git_blob_sha` 精確綁定上述 HTML；Builder 與 candidate Builder SHA 均為 `42eebdfe18394aa7ff4aca6c226b901516ee6bb1`。
- Sidecar：`QA_PASSED`、`review_ready=true`、`data_review_ready=true`、`content_analysis_gate=PASS`、review blockers 空陣列。
- 六個 viewport：1440／768／412／390／360／320。

## 共同 provenance（兩次 sidecar 完全一致）

| 項目 | SHA |
|---|---|
| Candidate Builder | `42eebdfe18394aa7ff4aca6c226b901516ee6bb1` |
| Active SIM-1.4 | `e18865fc31a88f98e44cb1f411817e61406a34c1` |
| Superseded SIM-1.4 Draft | `0d64eb9b16202d3e9e6d86a1aa87b7105843d571` |
| Manifest | `8cab2a945b19ffeea5a922353f4f4b8b9c71b9dd` |
| QA Contract v1.16 | `30faa8385e19e5bdca0a2fa5c21eda237c52339a` |
| Monday mother | `b89c76dd37afdc0cf8b406bfd6f06258896c829d` |
| Weekday mother | `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96` |

## Gate 與內容稽核

- 兩次均通過 deterministic self-tests（包含 Builder output guard negative tests）、Investing.com earnings parser、PIT consensus snapshot store、HTML assemble、Playwright navigation／accordion／source links、母版視覺比對、母版 DOM preservation、獨立 artifact/provenance 驗證、日期／行事曆數量／44 項行情／新聞結構驗證、QA sidecar seal 與 simulation-only artifact persistence。
- Monday 報告行情基準日為 2026-11-20；Weekday 報告行情基準日為 2026-11-19。各報告依其 fixture／日期規則驗證，不混用日期。
- Monday 六項全球指數改用 Investing.com 全球指數歷史資料頁／DAX Xetra 現貨收盤口徑，不再以香港站股指 CFD 作為呈現或計算來源；WTI、Brent、GC、SI 採 Investing.com HK 指定合約、同日歷史收市列。
- 週末 VIX、MOVE、CNN Fear & Greed、FedWatch 依使用者確認沿用最新基準快照並保留實際資料時間；不宣稱週日刷新。
- W48 缺乏可驗證 PIT 共識快照者維持待核實，不判定 Beat／Miss；W47／W48 個別修正限審核版 report-layer overlay，不回寫 main 正式行事曆 JSON。
- 財報 EPS／Revenue 依各自可驗證來源與 PIT 完整性判斷；不能因缺少有效共識而產生虛假的預估或 Beat／Miss。
- Fed 官員行程保留母版 prototype 與原始 DOM／子節點樣式；Builder 不得重建母版結構或注入額外 CSS。

## 尚未核准的事項與邊界

兩份最新 sidecar 均明確保留：
- `sim14_builder_approval=NOT_APPROVED`
- `sim14_review_ready=false`
- 唯一 blocker：`Candidate Builder has not been explicitly approved as the unique SIM-1.4 production entry point`

**待使用者核准的精確對象：** `simulation-lab/runner/build_review_html.py`，blob SHA `42eebdfe18394aa7ff4aca6c226b901516ee6bb1`。

本輪只寫入 `simulation/tac-process-lab-2026-11-06`。未修改 main、正式首頁 `index.html`、正式母版、正式 Manifest、正式行事曆 JSON；未部署 Pages。QA sidecar 的 `review_ready=true` 僅代表該份審核 HTML 通過 QA，不等於 SIM-1.4 Builder 已獲核准或正式生產已開放。
