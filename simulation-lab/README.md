## 2026-11-13｜SIM-1.2 重新執行早報建置

- 依使用者明確指示，重新執行 2026-11-13（週五）審核版完整建置；報價基準日 2026-11-12。
- 使用 date-matched fixture `simulation-lab/fixtures/report-data-2026-11-13.json`；行事曆僅讀取 main `data/calendar/weeks/2026-W46.json`。
- 本次由既有隔離 workflow 重新執行 OHLC 擷取、財報股價反應擷取、DOM 組裝、互動及視覺 QA；不沿用舊 preview HTML。
- 預定輸出僅限 simulation branch `simulation-lab/output/`；QA 全通過後才複製至 main `preview/2026-11-13-simulation.html`。不得修改 `main/index.html` 或 W46 JSON。

# TAC Process Simulation Lab

- Branch: `simulation/tac-process-lab-2026-11-06`
- Active simulation WR: `simulation-lab/TAC_WORK_RULES_SIM.md` (SIM-1.3; verified 2026-11-22)
- Candidate rules: `simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md` (DRAFT only; not active until explicit user approval)
- WR merge basis: SIM-1.1 plus the simulation-branch v5.19 rules; the root-level simulation copy `TAC_WORK_RULES.md` is retired after migration.
- The unified simulation WR is the only authority for the 05:25 simulation report workflow. Do not read the main-branch WR as a second authority for that workflow.
- Main calendar database: `data/calendar/weeks/YYYY-Www.json` is the single shared authoritative source. The independent 04:35 calendar automation is its only writer; the 05:25 simulation report is read-only.
- Main writes remain narrowly separated: the authorized dated simulation review preview, and `index.html` only after explicit user approval under the unified WR. No other main assets may be modified.
- Simulation mother templates, Manifest and QA contract are frozen read-only baselines under `simulation-lab/baseline/`.

## Lab layout

- `simulation-lab/TAC_WORK_RULES_SIM.md`: the active simulation Work Rules (SIM-1.3); do not treat the SIM-1.4 draft as effective.
- `simulation-lab/baseline/`: frozen simulation copies of the approved mother templates, Manifest and QA contract.
- `simulation-lab/analysis/`: contradictions, failure taxonomy, and repair decisions.
- `simulation-lab/fixtures/`: deterministic replay inputs and injected failures.
- `simulation-lab/runs/`: per-run step evidence, output hashes, timings, and pass/fail.
- `simulation-lab/output/`: generated HTML and test artifacts only.

## Required experiment matrix

1. Current SIM-1.2 direct-authoring workflow.
2. Existing repository Snapshot -> validation -> HTML-binding candidate (read-only evaluation; no assumption it is production-authorized).
3. Hybrid workflow: verified source evidence and reusable data ledger, then deterministic DOM-based template population and independent QA.

Run the same fixed input set and injected failures against each candidate. Select a repair only after comparative evidence.

## 2026-11-22｜11/23 審核版重建觸發

- 依使用者指示，重新執行 2026-11-23（一）審核版完整 build；報告日期與 fixture 固定為 2026-11-23，行情基準日 2026-11-20。
- 本次必須執行日期解析、main W48／W47 行事曆唯讀讀取、Builder 組裝、獨立 artifact/provenance、瀏覽器互動、雙母版結構與六種 viewport 視覺 QA；不得以 deterministic self-tests success 代替審核版完成。
- 輸出僅限 simulation branch `preview/2026-11-23-simulation.html` 與對應 QA sidecar；不寫 main、不部署 Pages、不修改正式首頁。
- SIM-1.3 仍是唯一有效規則；SIM-1.4 仍為 DRAFT，本次同時作為候選流程實證，不代表使用者已核准 SIM-1.4 或 Builder。

## Key-levels ownership and data contract (simulation)

**Responsibility boundary**
1. Market-data acquisition is the upstream owner: it must provide OHLC for the five US cash indices, with exact symbol, trading date, quote type, source name and HTTPS source URL. It must not substitute CFD or futures when the cash index is closed.
2. `simulation-lab/runner/key_levels_builder.py` owns validation and pivot calculations only. It does not scrape or invent quotes. It rejects missing/duplicate indices, mismatched dates/names, invalid OHLC, missing source attribution, and non-cash quote types.
3. The producer writes the single downstream contract to `key_levels.items` in the report JSON. `build_review_html.py` consumes only this contract and renders it; it does not retrieve prices or calculate pivots.

**Input contract**: `simulation-lab/fixtures/key-levels-ohlc-2026-11-09.json` is a normalized replay fixture. Each item requires `key`, `name`, `symbol`, `trading_date`, `high`, `low`, `close`, `quote_type=cash_index`, `source_name`, and `source_url`. The five required keys are `dow`, `sp500`, `nasdaq`, `sox`, and `russell2000`.

**Calculation**: `P=(H+L+C)/3`; `S1=2P-H`; `R1=2P-L`, rounded to two decimals using decimal arithmetic. The module preserves the input H/L/C, date, symbol and source link in the generated output.

**Important scope**: this fixture is deterministic test input, not live market data. The live acquisition module must populate the same normalized input contract from verified current OHLC before this producer is used in a live report. Until that connection exists, the workflow proves calculation and assembly only, not live retrieval.

Workflow order: normalized OHLC input → `key_levels_builder.py` → `report-data-*.json:key_levels` → `build_review_html.py`.


## 2026-11-21｜同版雙母版回歸：Weekday

- Monday 同版回歸已以 candidate SIM-1.4 SHA `c5d992b71bb4359b22c266cab00b05d527bdfb0e` 完成（run 44907807730，QA_PASSED；資料型 review_ready=false，僅待四項風險／情緒／FedWatch 截稿刷新）。
- 現觸發 2026-11-20 Weekday fixture 回歸；本次不修改 Builder、Manifest、QA Contract 或 candidate rules，確保 Weekday 使用與 Monday 相同的規則／技術資產 SHA。
- 僅供 simulation branch 測試，不授權 SIM-1.4 生效或正式資產修改。


## 2026-11-22｜SIM-1.4 同版 Weekday 母版實證觸發

- 11/23 Monday build run `44954756293` 已以固定版本組合通過：Builder `60d778c39ffe48140e99e0dad3579ce9f0b33945`、Manifest `5080858c6720847086b7df815432d305d6231b3a`、QA Contract v1.14 `86e13a2a3ee9a186fa7d4f2c29209e4b41d0bfbd`、active SIM-1.3 `116ebb0a6401321148a878fe20c9504df7ce37f7`、candidate SIM-1.4 `371554033cd33efb76062827bc6b340e16f28bc2`。
- 依 SIM-1.4 §8.1，現觸發 2026-11-20（週五）Weekday fixture `simulation-lab/fixtures/report-data-2026-11-20.json` 完整 build，使用完全相同的 Builder／Manifest／QA Contract／active rules／candidate rules SHA，驗證雙母版是否可重現。
- 此次仍為 simulation-only candidate validation；不代表 SIM-1.4 生效、不核准 Builder、不寫 main、不部署 Pages。


## 2026-11-22｜Weekday 財報行事曆來源槽位錯誤修復與重跑

- 同版 Weekday build run `44954985333` 已完成至 Builder，但失敗於 `earnings calendar mother source note missing`。根因：Builder 把 Monday mother 的兩個頂層 `.source` 節點假設套用至 Weekday mother；實際 Weekday mother 沒有此頂層來源說明槽位，個別來源已存在每張財報卡內。此為 Builder 母版分流錯誤，不是母版缺損，不應新增 DOM 或 CSS 補位。
- 已修正 Builder：抽出 `update_earnings_calendar_source_note()`，只在 Monday 情境更新母版既有頂層來源說明；Weekday 情境驗證沒有該 Monday-only 槽位後原樣返回，不改動母版 DOM。
- 已新增 regression test：Monday 保留並更新原有來源說明與隱藏過期示例連結；Weekday 無頂層來源槽位時必須 no-op，且整段 `#earnings` DOM 字串完全不變。
- Builder commit `5db23586cb7307b490a9cbb38ccd84f6065f4f01`，blob `036d9ab838a1b4e461de52cadf6c33a8d6236758`；test commit `73242392402e7440bb928ec829eae81bfb58b3f2`，blob `e3856b23d609340870ae810d0dd5c1dd30a29e28`。
- 以 2026-11-20 Weekday fixture 重新觸發完整 build；本次仍固定 QA Contract／Manifest／active SIM-1.3／candidate SIM-1.4 SHA，驗證修復後雙母版一致性。
