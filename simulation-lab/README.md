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


## 2026-11-22｜SIM-1.4 雙母版同版 SHA 最終對齊

- 2026-11-20 Weekday run `44955117611` 已以 Builder `036d9ab838a1b4e461de52cadf6c33a8d6236758`、Manifest `5080858c6720847086b7df815432d305d6231b3a`、QA Contract `86e13a2a3ee9a186fa7d4f2c29209e4b41d0bfbd`、active SIM-1.3 `116ebb0a6401321148a878fe20c9504df7ce37f7`、candidate SIM-1.4 `371554033cd33efb76062827bc6b340e16f28bc2` 完整通過。
- 2026-11-23 Monday run `44954756293` 通過，但使用 Builder 舊 SHA `60d778c39ffe48140e99e0dad3579ce9f0b33945`。依 SIM-1.4 §8.1，不得與新 Builder 的 Weekday PASS 拼成同版雙母版證據。
- 現以完全相同的最新版 Builder `036d9ab838a1b4e461de52cadf6c33a8d6236758` 重跑 2026-11-23 Monday fixture；固定同一 Manifest／QA Contract／active rules／candidate rules SHA。只有本次 Monday PASS 後，才可標記雙母版候選 Builder 技術驗證完成。
- 本次仍只寫 simulation branch；不更新 main preview、不部署 Pages、不修改正式首頁。


## 2026-11-22｜11/23 手機版三項問題修正驗收

- 使用者截圖指出兩項 mobile UI：上週財報 EPS／營收卡數字被拆行、Fed 官員行程區塊窄欄直排。根因已定位：週一母版既有 mobile CSS 將 earnings metric strong 任意換行；Fed 官員行程容器作為 .fc-fomc grid 第五個 child 未指定跨兩欄，落入單欄自動放置。
- 已在既有 CSS 規則內直接修正（不新增 style block、不新增 DOM）：earnings value 使用 nowrap／keep-all 並保留兩卡並列；Fed agenda 容器與 list 跨兩欄，事件列維持 94px 日期欄 + minmax(0,1fr) 內容欄。母版 blob SHA `e16cc6df649dcee7e09126b4c044479661e399e9`。
- Manifest 更新 Monday simulation SHA，blob `cc37c33c17f0bc1891b86133499e446999a894f8`。
- 新增回歸測試斷言 mobile metric nowrap、Fed agenda full span 與 94px event grid；test blob `ece0ab4a6f7382313d65ca417f5486e07a0df70a`。
- QA Contract 更新為 v1.15 DRAFT，blob `729a4de1f4d7f7dafa0ced7fe3ae95b329f98095`，新增 320/360/390/412px 真實視覺檢查要求。
- W48 財報資料另行查核：main W48 JSON 11 家，EPS／Revenue estimate 欄位全為 null，且 11 家都沒有 Yahoo Finance 查核紀錄；Investing.com Forecast 觀測值雖有，但全部被記為 missing_required_fields，未採用。這違反 SIM-1.4 §5.2 所定 Yahoo Finance Average Estimate 第一順位，且未能證明該流程已執行。不可把缺少 GAAP／Adjusted 欄位本身當作拒絕可比較平均預期的理由。已查得 Yahoo Finance analysis pages 存在多家公司 Current Qtr (Oct 2026) EPS／Revenue Average Estimate，但必須逐一確認該季度與各財報事件 reporting_period 對應後才可寫入；未核實者不得補猜。
- 下一步先跑 11/23 Monday 完整 build／六視窗 QA，核對兩個 mobile 問題實際截圖；W48 另做 11 家 Yahoo 優先、EPS／Revenue 分開選源的來源稽核與 report-layer overlay，不修改 main W48 JSON。


## 2026-11-22｜SIM-1.4 財報共識首筆採用規則落實（不處理 W48）

- 使用者確認工作順序：先落實 SIM-1.4，再處理 W48；本輪不讀取、不修改、不回填 W48 財報資料。
- 統一來源順位：Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates。EPS／Revenue 各自獨立選源；同公司、同財報期間的第一筆有效數值立即採用並停止該指標後續來源搜尋，不做低順位交叉核對。
- SIM-1.4 主文更新：Stage 3、§5.2、附錄處置與版本紀錄已統一順位及停止條件；主文 blob SHA `1f28d2cdffabaa1de933a1432fa473acaf7bfe08`。
- QA Contract 更新為 v1.15 DRAFT，blob SHA `220866dd60c700ebceb8e1c63c349a083c1b512a`，加入首筆採用、獨立 fallback、PIT／分析師人數／完整口徑／raw archive 非阻擋條件。
- 實作更新：`consensus_snapshot_store.py` source level 改為 Yahoo=1、Investing=2、LSEG=3、FactSet=4，新增 `select_first_available_estimate()`；快照必要欄位收斂為來源 URL、期間、數值，其他 metadata optional。blob SHA `fc615a127200b02d935f7b3d16d5454a40daafcd`（後續 selector 修訂以最新 HEAD 為準）。
- `earnings_judgment.py` 的來源層級與證據標籤改為接受已選來源，不以 PIT、分析師數、basis、raw archive、statistic 或 period_end_date 阻擋；blob SHA `47a8ba3fdbd9f0a2cc61975d9a814adeaa5570f9`。
- `investing_earnings_probe.py` 已改為第二順位 source level 2；blob SHA `120eee8e41e8be288da4ba9500028268f2ef0bdd`。
- 新增首筆採用／EPS Revenue 分開 fallback／財報期間不符才遞補測試；新增無 PIT／缺方法論欄位仍可採用的判讀測試。測試執行結果待本次 CI build。
- 本次只做 SIM-1.4 simulation 候選規則與程式驗收，不修改 W48 JSON／Fixture／財報小卡；不修改 main 正式首頁或正式資料。


## 2026-11-22｜SIM-1.4 consensus selector test rerun

- 首輪 CI 暴露兩個舊測試仍把 optional `basis_code` 與 `raw_response_ref` 當作採用必要欄位；程式已按 SIM-1.4 移除阻擋條件，測試預期同步修正為可保留 `pre_release_eligible` 狀態。
- 更新 Yahoo 第一順位測試，明確驗證無 provider data_as_of／EPS basis 仍可用；更新缺 raw archive／basis 測試名稱與預期。未處理 W48。


## SIM-1.4 consensus tests rerun 2

- Corrected the two remaining legacy status expectations: Yahoo capture without provider as-of uses TAC-observed status; a source with provider data-as-of but missing optional EPS basis remains provider-as-of eligible. No W48 files read or changed.


## SIM-1.4 regression rerun 3

- Fixed a test-fixture KeyError in the new selected-consensus evidence test; production logic unchanged. W48 remains untouched.


## SIM-1.4 visual QA correction

- Browser QA identified published earnings values clipped on narrow screens because the Monday mother CSS forced `white-space:nowrap` and `overflow-wrap:normal`. Updated only the simulation Monday mother to allow wrapping while retaining the existing two-column card structure; synchronized its simulation manifest SHA and regression assertion. Next full build reruns 1440/768/412/390/360/320 browser checks. W48 remains untouched.


## SIM-1.4 QA correction｜Manifest SHA field separation

- 前次驗收指出 Monday simulation baseline SHA 與 Manifest 欄位未對齊。已保留正式 main mother SHA `a568e594e55909041d51d8eae7e6fe5f7986c096`，只更新 simulation_blob_sha 為 `dea505a3e1c9e69c3fee2f85f214d3da0ecad3a0`；不得將 simulation SHA 寫入正式 blob_sha。
- 同步修正 SIM-1.4 §5.2 舊順位殘留：Investing.com 必須在 LSEG I/B/E/S、FactSet Estimates 之前。
- 觸發重新跑母版 SHA 鎖、全套測試與 browser QA；W48 不處理。


## SIM-1.4 QA Contract binding fix

- Browser regression passed through mobile card layout, nav/accordion/source-link checks and mother-owned DOM preservation. Exact artifact validation then failed because QA Contract A2 still pinned the pre-fix Monday simulation mother SHA.
- Updated QA Contract to v1.16 DRAFT with Monday simulation SHA `dea505a3e1c9e69c3fee2f85f214d3da0ecad3a0`; official main mother SHA remains unchanged. Updated SIM-1.4 pinned contract blob SHA accordingly. Re-running full artifact validation and persistence; W48 untouched.


## SIM-1.4 source selection integration checkpoint

- `project_w47_yahoo_consensus.py` now invokes the canonical `select_first_available_estimate` independently for EPS and REVENUE and accepts optional lower-priority provider attempts in each capture entry's `provider_attempts` object. A selected provider's source level, URL, observation time, value, currency, units, and analyst count are carried into its snapshot.
- `build_review_html.py` now preserves separate EPS and Revenue consensus source URLs/names/timestamps and renders the two sources independently on earnings cards rather than using one shared provider link.
- This is simulation-only integration. It does not fetch missing lower-tier providers by itself; an actual fallback requires the collector to supply a validated provider attempt in `provider_attempts`. Current W47 Yahoo captures have both metric values, so the correct first-source stop rule should select Yahoo and not query lower tiers.
- Run full SIM-1.4 regression/build now; no main writes and no W48 JSON changes.
