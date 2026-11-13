# TAC 財報判讀 Schema v2｜正式切換清單

狀態：未部署；目前只有 simulation branch 實作與測試。正式 main 仍為 schema_version=1。

## 最新正式資料基準（2026-11-13 回讀）

- Main HEAD：`68223e3aa384ae4d75311a243eb029da3c55b32c`
- Main WR：v5.15，blob SHA `23b52f27b7afad083bbe28ed86021e04759f198d`
- W46 JSON：`data/calendar/weeks/2026-W46.json`
- W46 blob SHA：`ec246b8a765c64b798e348ce8df2760ea89cc5e1`
- schema_version=1；16 economic / 48 earnings / 45 released / 129 audit。
- EPS／Revenue 各 135 筆 source attempts，但各 0 筆 adopted；舊 legacy source object 各 37 筆。
- EPS actual／estimate：38／36；Revenue actual／estimate：44／36。
- EPS estimate_period 0/45；Revenue estimate_period 0/45。
- 45 筆 released records 均無 judgment_engine_version；舊 Beat／Miss 不可視為 v2 驗證結果。

## 已完成（隔離模擬）

- [x] 唯一判讀引擎與受控 basis registry。
- [x] HTML assembler 改為只讀 versioned judgment。
- [x] v1 → v2 保守 in-memory migration preview 工具。
- [x] per-record JSON Schema v2 與 validator（僅 simulation branch）。
- [x] HTML assembler 的兩個財報評論輸出路徑改為狀態一致性過濾。
- [x] commentary contradiction regression cases。
- [x] 04:35 Schema v2 automation prompt 已更新，但該任務仍 disabled。
- [x] 發現並修正 migration bug：不得把 reporting_period 複製到 estimate_period。
  - Code commit：`d0d8a1af6b137964364ed842823f4864e7aa619b`
  - 回歸測試 commit：`b95192767a2f11e35178fb99fa0127bb4ab934b8`
  - 測試案例同步修正 commit：`5142f4255bb8d95dc4be3e4b6b4ee8c353b69b95`
  - GitHub Actions run `43415581638`：整體 success；deterministic self-tests 與 main 唯讀 schema audit 均 success。報告組裝／瀏覽器／視覺 QA 因本次是 push smoke run 而 skipped，不能視為端到端驗收。

## 尚未完成（隔離模擬）

- [x] 執行新增 estimate_period 回歸測試與 deterministic earnings self-test suite；GitHub Actions run `43415581638` 通過。
- [x] 以最新 main W46（45 released）重新產生 read-only migration preview CSV／audit JSON；輸出已檢查，45 筆 EPS：41 pending／4 incomparable；Revenue：44 pending／1 incomparable；方向性判讀皆為 0。
- [x] 驗證缺乏明確 consensus period 的舊記錄不會由 reporting_period 補值；未達條件者維持 Pending，已知 basis／currency 衝突則標示 Incomparable。
- [ ] 逐筆確認 45 筆 legacy consensus source 的公告前時間、財報期間、EPS basis、Revenue definition、幣別及單位；無證據者不得採用。
- [ ] 評估新增資料來源前，先確認其 point-in-time 歷史快照、存取權、欄位定義與可重複取得性；未經規則核准不得改變 SIM-1.2 的來源優先順序。

## 尚未完成（正式 main）

- [ ] 將 engine、schema validator、migration 工具及 assembler 修改部署至正式 main。
- [ ] 正式 Schema v2 JSON Schema 與版本遷移程式。
- [ ] 逐筆補齊 EPS／Revenue basis code、actual／estimate currency、period、Revenue unit 及來源證據。
- [ ] W45、W46 歷史資料遷移及回讀 SHA 驗收。
- [ ] 確認唯一 updater automation 的 runtime 能實際執行正式判讀引擎；若不能，不得只靠 prompt 聲稱已執行。
- [ ] 隔日增量更新演練與 05:25 唯讀驗證。
- [ ] 使用者核准後才評估恢復 Schema v2 writer；不得自動啟用 disabled 的 04:35 任務。

## 排程權責與文件不一致（待處理）

- 啟用中的唯一更新任務：`TAC 行事曆資料庫更新`，ID `6af6d10c62448191819f04b976c64cf4`，每日 04:30 Asia/Taipei。
- 另一個 v2 任務：`TAC 行事曆資料庫｜每日 04:35 預更新`，ID `6ae6dff2200c81919ba2cee4db78f8a5`，disabled。
- Main WR v5.15 文字仍寫 04:35，與目前啟用任務 04:30 不一致。尚未修改 WR／排程；不得建立雙 writer，也不得默默宣稱已同步。

## 不可跳過的安全限制

- 不得另建第二個週 JSON writer。
- 不得在 Schema v2、engine、validator、migration 與 assembler 尚未完整部署前修改正式 JSON 的 schema_version。
- 不得把 legacy/unversioned Beat／Miss 當成新規則已驗證。
- 不得以 attempt history 筆數代表共識值取得率。
- 不得把隔離測試 PASS 說成 production ready。
- 不得覆蓋歷史早報、preview 或正式首頁。


## 最新 workflow artifact provenance（2026-11-13）

- Run：`43415581638`；commit：`5142f4255bb8d95dc4be3e4b6b4ee8c353b69b95`；結論 `success`。
- 本次 CSV／audit JSON 由唯讀 schema audit step 產生；45 筆 migration preview 沒有任何 EPS／Revenue 方向性 Beat/Miss/Inline。
- Artifact 內的 2026-11-13 HTML 不屬於本次生成：runner metadata 是 `report_date=self-test-only`，且組裝、瀏覽器、視覺回歸步驟均 skipped。不得用該 HTML 當作本次審核版交付。
- Main 未被修改，仍為 schema_version=1；v2 尚未 cut over。


## ORTEX TEST API feasibility — 2026-11-13

- [x] Actual API request using documented TEST key: AAPL, MSFT, AMC each HTTP 200 with 10 rows; no credits consumed; simulation run `43416557107` success.
- [x] Confirmed response fields for EPS / Revenue consensus, fiscal period, period end, currency, estimate-as-of and analyst counts.
- [ ] TEST key W46 PIT coverage: not verified. The service overrode the requested 2026-11-05–11-13 window and returned resolved dates 2026-05-17–2026-10-14 (first row 2026-05-18).
- [ ] EPS normalized basis mapping to GAAP / Adjusted and Basic / Diluted.
- [ ] Revenue unit semantics beyond absolute amount in row currency; preserve raw value and currency meanwhile.
- [ ] Production API access and public display / redistribution rights.
- [ ] Full 45-ticker W46 point-in-time coverage and per-event period matching.

**Decision:** technical connectivity is proven; data eligibility, W46 backfill, production adoption and licensing are not. Do not change SIM-1.2 source priority and do not use TEST responses for W46 judgments.

- [x] Raw TEST response evidence archived and read back: `simulation-lab/runs/ortex-test-probe-43416810131.json` (blob SHA `b082a2ca778521fcdb2b383935d8f4f4c599fd03`); follow-up run `43416810131` success.

- [ ] ORTEX 書面確認 Professional／Institutional licence 可涵蓋 TAC 公開展示、PIT 歷史保存及再散布；個人／TEST key 不得用於 TAC 公開產品。


## Append-only PIT snapshot history — required before production cutover

- [ ] 每筆事件具獨立 `eps_consensus_snapshots` 與 `revenue_consensus_snapshots` 歷史陣列；不得以當日 attempts 取代歷史 snapshots。
- [ ] 每筆 snapshot 保存 data_as_of、observed_at、event_date、period、basis、currency、unit、analyst_count、raw response ref／SHA-256。
- [ ] 同日只有 date、沒有時間戳的 data_as_of 不得自行推定為公告前。
- [ ] 同一 snapshot id 冪等去重；新值／新原始 payload 只 append，不覆寫舊證據。
- [x] Simulation prototype + deterministic tests pass；連續多日增量演練確認歷史陣列不被覆蓋（3 日 unchanged + 5 日 EPS／Revenue dual-metric regression；17 tests pass，workflow `43420023980`）。
- [ ] 正式 WR／唯一 updater automation／raw evidence archive 權限及保留政策須經審核後才可變更；目前 production 未部署。

**Main W46 audit count correction:** 直接回讀 JSON 的 `audit.length=132`；先前 129 是較早統計截點。

- [x] Simulation append-only snapshot helper + 13 deterministic tests passed in workflow `43417361875`.
- [x] TEST raw response evidence archived in simulation branch: `simulation-lab/runs/ortex-test-probe-43417361875.json` (blob SHA `3e38b54c89a9bcfed043289a4348984bea3e298d`).
- [ ] Integrate the snapshot helper with the single authorised production writer only after full simulation multi-day regression, licence review, WR update approval and explicit production deployment approval.

- [x] Three-day unchanged-value polling retains three distinct observed_at snapshots and idempotently ignores exact replay; verified in workflow `43417601486`.

- [ ] `published_at` 欄位明確存在；可為 null，但不得由 observed_at、data_as_of 或 provider_recalculated_at 推定。

- [x] `published_at` added to v2 PIT snapshot schema and builder as an explicit nullable field; test verifies preservation.
- [x] Initial CI indentation failure was corrected; follow-up workflow `43417937668` succeeded, including 13 snapshot tests and read-only main audit.

- [x] 16 deterministic PIT snapshot tests passed, including Draft 2020-12 JSON Schema validation and published_at null/timezone checks (run `43418109555`).
- [x] Latest raw probe archived: `simulation-lab/runs/ortex-test-probe-43418109555.json` (blob SHA `3f2024ed34a7fdad6bc5b7f023e9a6140667883d`).

- [ ] 正式唯一 writer 尚未接入 append-only snapshots；已核對 task `6af6d10c62448191819f04b976c64cf4` Enabled、每日 04:30 Asia/Taipei、next run 2026-11-14 04:30；現行 prompt 不含兩個 snapshot arrays。
- [ ] 取得正式 writer prompt／WR／archive retention 變更授權後，才可把 snapshot store 接入唯一 writer；不得另建排程或 writer。


## Five-day regression update — 2026-11-13

- [x] Five-day EPS／Revenue append-only polling regression passed in workflow `43420023980` (17 tests total).
- [x] Value changes do not overwrite earlier snapshots; unchanged daily polls remain distinct by observed_at; exact replay is idempotent.
- [x] Same-day date-only data_as_of remains Pending; EPS and Revenue arrays remain independent.
- [ ] Durable raw-response archive destination and retention/licensing approval remain unresolved. Until an approved archive exists, production snapshots must not be labelled `pre_release_eligible` merely because a hash exists; preserve `raw_response_ref=null` and `pending_required_fields`.
- [x] Integrate the append-only snapshot contract into the existing unique 04:30 updater prompt after encoding the raw-archive limitation. Post-update readback confirms the same task remains Enabled with the same schedule and ID. This does not deploy Schema v2 or authorize a separate/manual main W46 write; first scheduled writer execution remains pending.
