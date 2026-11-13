# TAC 財報比較資料契約｜Schema v2 提案

日期：2026-11-13
狀態：隔離模擬設計；未修改 main 資料庫、正式排程或 WR。

## 1. 權責結論

- **唯一判讀者：** 財報資料更新／標準化流程呼叫 `earnings_judgment.py`。
- **資料庫：** 保存原始公告、共識來源、標準化比較欄位及判讀結果。
- **HTML 組裝器：** 只讀取已保存且帶有 `judgment_engine_version` 的判讀結果；不得用數字方向、自由文字或字串相等自行推導 Beat／Miss。
- **人工／AI 編輯評論：** 寫入獨立的 `earnings_commentary`，不得取代結構化比較結果；評論中的方向性主張須與判讀結果一致。

GitHub Actions 的排程只負責啟動資料處理程式，不應把判讀規則散落在 workflow YAML 或 HTML assembler。

## 2. 目前正式資料的實測基線

來源：main `data/calendar/weeks/2026-W46.json`，main HEAD `d271d1226ba1c19b431118c9967d57d2bce678fa`，JSON blob `85edcefb1f7b86112e55d43a324c6cb5c8c2fdab`；WR v5.15。

- `schema_version=1`；經濟事件 16、財報事件 48、audit 129；已公布財報 42。
- EPS 實際值 36 筆、預期值 34 筆、兩者皆有 30 筆；EPS actual／estimate basis 自由文字欄位各僅 18 筆。
- 營收實際值 41 筆、預期值 34 筆、兩者皆有 34 筆；營收 actual／estimate basis 自由文字欄位各僅 3 筆。
- EPS 已存方向性判讀 18 筆（Beat 15、Miss 3）；營收已存方向性判讀 25 筆（Beat 17、Miss 8）。
- 22 筆已有營收方向性判讀，但缺少 actual／estimate basis 欄位。
- 42 筆已公布財報均沒有 `judgment_engine_version`。
- W45 仍是 schema_version 1，且沒有 W46 新增的 actual／estimate basis 欄位；同一 schema_version 下已出現欄位漂移。
- 現有 `consensus_source` 與 `revenue_consensus_source` 已能保存來源 URL、觀察時間及 notes；來源物件應保留，不需再建立平行來源資料庫。
- 遷移時不得把單一舊 `eps_currency`／`revenue_currency` 直接複製成 actual 與 estimate 兩欄；只有舊值明確標示「XXX actual; YYY estimate」，或 actual／estimate basis 描述各自明確標示幣別時，才能分別映射。否則 Pending。
- 遷移時不得把單一舊 `revenue_unit` 直接複製成 actual 與 estimate 兩欄；只有 actual／estimate basis 描述各自明確標示相同幣別與尺度時，才能映射成 `USD_BILLION`、`USD_MILLION` 等受控單位。否則 Pending。
- 現有 `eps_currency`／`revenue_currency` 是共用欄位，無法乾淨表達實際值與預期值不同幣別；ONON 以自由文字拼接兩種幣別，證明欄位型別不足。
- `financial_judgment` 是自由文字，沒有版本或與結構化狀態的機器一致性保證。
- `stock_price_reaction` 與 `price_reaction_source` 在本次 42 筆已公布事件中均未填入；這是獨立的股價反應資料完整性工作，不可與 EPS／營收比較混為一談。

## 3. Schema v2 欄位

### 3.1 保留既有原始欄位

保留 `eps_actual`、`eps_estimate`、`revenue_actual`、`revenue_estimate`、`reporting_period`、`source`、`consensus_source`、`revenue_consensus_source` 及既有 audit。既有自由文字 `eps_basis`、`financial_judgment` 暫時保留作歷史相容，不再作程式判讀依據。

### 3.2 必須新增的標準化欄位

| 欄位 | EPS | 營收 | 說明 |
|---|---|---|---|
| actual basis code | `eps_actual_basis_code` | `revenue_actual_basis_code` | 受控代碼，不可使用自由文字 |
| estimate basis code | `eps_estimate_basis_code` | `revenue_estimate_basis_code` | 必須與共識來源定義相符 |
| actual currency | `eps_actual_currency` | `revenue_actual_currency` | ISO 4217 |
| estimate currency | `eps_estimate_currency` | `revenue_estimate_currency` | ISO 4217 |
| actual period | `eps_actual_period` | `revenue_actual_period` | 明確季度／年度 |
| estimate period | `eps_estimate_period` | `revenue_estimate_period` | 必須與實際值同期間 |
| source | 既有 `source` | 既有 `source` | 必須含 URL、observed_at |
| consensus source | 既有 `consensus_source` | 既有 `revenue_consensus_source` | 必須含 URL、observed_at |
| surprise | `eps_surprise` | `revenue_surprise` | actual - estimate |
| surprise percent | `eps_surprise_pct` | `revenue_surprise_pct` | 除以 estimate 絕對值；estimate=0 時 null |
| comparison status | `eps_comparison_status` | `revenue_comparison_status` | 唯一判讀引擎輸出 |
| comparison reason | `eps_comparison_reason` | `revenue_comparison_reason` | 可追溯判讀原因 |

營收另須新增 `revenue_actual_unit`、`revenue_estimate_unit`，不可再以單一 `revenue_unit` 同時代表兩者。

### 3.3 共同判讀與評論欄位

- `judgment_engine_version`：判讀引擎版本；缺少版本不得把舊狀態視為新規則驗證結果。
- `judgment_timestamp`：判讀時間。
- `earnings_comparison_summary`：由引擎產生的 EPS／營收結構化摘要。
- `earnings_commentary`：獨立的質化評論，不得自行覆蓋比較狀態。
- `eps_consensus_conflict`、`revenue_consensus_conflict`：只有來源差異已核實且超出事先定義門檻時才設 true。
- `eps_inline_tolerance_abs`、`revenue_inline_tolerance_abs`：只有來源精度有證據時才填；預設 0，不得任意設定。

### 3.4 Basis code 受控登錄表

目前隔離引擎 v1.0.0 僅接受以下代碼；未登錄代碼一律 Pending，先補充登錄與測試，不得用任意大寫字串繞過。

EPS：
- `US_GAAP_DILUTED_EPS`
- `US_GAAP_BASIC_EPS`
- `US_GAAP_BASIC_AND_DILUTED_EPS`
- `IFRS_DILUTED_EPS`
- `IFRS_BASIC_EPS`
- `IFRS_ATTRIBUTABLE_EPS`
- `IFRS_ADJUSTED_DILUTED_EPS`
- `IFRS_ADJUSTED_BASIC_EPS`
- `NON_GAAP_ADJUSTED_DILUTED_EPS`
- `NON_GAAP_ADJUSTED_BASIC_EPS`
- `NON_GAAP_ADJUSTED_UNSPECIFIED_EPS`
- `NON_GAAP_DILUTED_EPS`
- `NON_GAAP_BASIC_EPS`
- `ISSUER_DEFINED_ADJUSTED_EPS`

營收：
- `US_GAAP_TOTAL_REVENUE`
- `US_GAAP_NET_SALES`
- `US_GAAP_OPERATING_REVENUE`
- `IFRS_TOTAL_REVENUE`
- `IFRS_NET_SALES`
- `IFRS_REVENUE`
- `ISSUER_DEFINED_REVENUE_METRIC`

不得只因名稱相似就把不同代碼視為相同；只有明確核實的代碼相等才能比較。新類型先新增受控代碼並測試，不可退回模糊字串比對。

## 4. 唯一判讀規則

1. 實際值與預期值都必須是有限數字，且各有來源 URL 與 observed_at。
2. actual／estimate basis code 必須存在且完全相同。
3. actual／estimate currency 必須分開記錄且相同。
4. actual／estimate period 必須相同。
5. 營收 actual／estimate unit 必須分開記錄且相同。
6. 任一比較條件缺失：`pending`。
7. 比較口徑、幣別、期間或單位不一致：`incomparable`。
8. 已確認共識來源分歧：`consensus_divergent`；不得任選較有利的數字。
9. 所有條件通過後才計算 actual - estimate；正值 Beat、負值 Miss、落在有來源精度依據的 tolerance 內 Inline。
10. 負 EPS 使用差額方向判斷：例如 actual -0.13、estimate -0.72，實際虧損較小，屬 Beat。
11. EPS 與營收分開判讀；不得以單一總結覆蓋兩者差異。
12. `financial_judgment` 不再作比較判讀來源。機器結果寫入 status／summary，質化評論另存 `earnings_commentary`。

## 5. 自動更新與版本遷移

- 正式資料寫入者仍是既有唯一行事曆更新流程；本次不得另建平行資料庫或第二個寫入者。
- 每次更新順序：擷取原始值與來源 → 標準化 basis／currency／unit／period → 呼叫唯一判讀引擎 → 寫入 status／surprise／version → JSON schema validation → 回讀與 audit。
- 新來源缺欄位時不得清除既有已核實資料，也不得保留過期共識假裝有效；需有來源有效時間及更新時間規則。
- Schema v2 上線時，W45、W46 及後續週檔需以同一遷移工具升級；不可讓同一 schema_version 對應不同欄位集合。
- 舊 v1 記錄可讀取，但其方向性狀態標記為 legacy/unverified；不得冒充 v2 引擎產物。
- 只有正式寫入流程已整合 v2、測試通過且所有必要週檔完成遷移後，才將 schema_version 升至 2。不可先改版本號再補欄位。

## 6. 04:35 唯一寫入者與排程現況

已透過 Automations 私有查詢確認，WR 所稱 04:35 唯一寫入者不是 GitHub Actions cron，而是 ChatGPT automation：

- 任務：`TAC 行事曆資料庫｜每日 04:35 預更新`
- Automation ID：`6ae6dff2200c81919ba2cee4db78f8a5`
- 時區／頻率：Asia/Taipei，週一至週五 04:35。
- 目前狀態：**disabled**；雖然 next_run_time 顯示 2026-11-16 04:35，但不能視為已啟用。
- 最近一次 run：`3db31e2d-2b68-832f-94ea-c4dda4bbd91e`，scheduled_for 2026-11-13 04:35 台灣時間，實際 04:30:35 啟動、04:52:16 完成。
- 該次回報 W46 64 筆（16 經濟、48 財報）、更新 12 筆、其中 11 筆已公布實績、1 筆狀態更新；寫入時聲稱 schema 未變。
- 該 automation prompt 明確要求「schema 未變」驗收，且沒有引用唯一、可執行的財報判讀引擎；因此它目前不會主動完成 Schema v2 欄位遷移，也沒有機制保證每次 Beat／Miss 都依同一套標準化比較條件產生。

main `.github/workflows/` 目錄目前沒有 TAC 行事曆 writer。現有 `.github/workflows/main.yml` 是 S&P 500 volatility updater，不是行事曆抓取器。

**正式整合阻塞：** 唯一 writer 已定位，但目前停用，而且 prompt 仍要求 schema 不變。不能在不更新這個唯一 writer 的情況下直接修改 W46 JSON；也不能另建第二個 writer。Schema v2 上線時，必須同步更新這個 automation 的 prompt／執行契約，並在其重新啟用前完成回歸測試。

## 7. 上線 Gate

- G1：寫入者定位，確認唯一觸發器、程式入口、權限及寫入路徑。
- G2：Schema v2 完整欄位與 enum 驗證。
- G3：W45/W46 舊資料遷移及 42 筆 W46 已公布財報逐筆回歸。
- G4：引擎單元測試、來源缺漏／basis mismatch／currency mismatch／period mismatch／unit mismatch／負 EPS／共識分歧測試。
- G5：HTML assembler 僅讀取 versioned statuses；不再有數字方向 fallback。
- G6：隔日排程模擬，證明新欄位不被覆蓋、舊欄位不被誤清空。
- G7：正式發布仍須使用者審核授權。

本分支完成的程式與測試只代表隔離模擬成果，不等於正式 main 已升級。

## 8. Schema v2 JSON Schema 與 validator

- 已新增 `schemas/tac-earnings-record-v2.schema.json`，定義 EPS／Revenue basis enums、分離幣別／期間／營收單位、來源物件及 engine version/status/reason。
- directional statuses 在 JSON Schema 層必須具備完整 evidence 欄位；validator 再呼叫唯一 `earnings_judgment.py`，檢查 persisted status 與即時計算結果一致。
- validator：`simulation-lab/runner/validate_earnings_v2.py`；包含 self-test，測試方向性紀錄缺幣別應失敗、status 與引擎不一致應失敗、legacy v1 record 不納入 v2 驗證。
- 已加入 simulation workflow 的 deterministic self-tests。最新 workflow commit `db9c085e8d0c88ebcefb5a371feb686826c74a23`，後續 checklist commit `5fca8a236f3d0402166ca9e878921ece2f580832`；截至本次檢查 GitHub 尚未回報這兩個 commit 的 workflow run，因此不可標示 validator CI PASS。先前 engine／renderer／migration CSV 測試的 PASS 仍有效，但不等於新 JSON Schema validator 已通過 CI。

## 9. Commentary 與卡片判讀一致性 Gate

- 實際檢查 builder 發現，雖然 EPS／Revenue 小卡狀態已改為讀取 versioned engine result，兩個 HTML assembly path 仍直接輸出自由文字 `judgment`。這會造成卡片顯示「比較口徑待核實」，但下方評論仍寫「優於／低於預期」的矛盾。
- 已新增 `earnings_commentary(item)`：逐句依 EPS／Revenue persisted status 篩除無法支持或與狀態相反的方向性主張，保留中性營運敘述，最後附上 EPS 與營收各自的引擎狀態。
- 兩個 assembly path 均改用該 helper；不再直接顯示原始 `judgment`。
- 測試新增：unversioned legacy commentary 的 Beat/Miss 抑制、已 versioned EPS Beat 但文字寫 Miss 的衝突抑制、Revenue Pending 時抑制 Beat、保留中性評論。
- 另修正句子切分，避免把 US$1.20 等小數點當成句號。
- 新測試已加入既有 `test_earnings_comparison_status.py`，但本輪最新 commits 尚無 GitHub Actions check-run；因此這部分仍待 CI／實際 11/13 fixture rebuild 驗收。


## 10. 公告前共識快照歷史（Append-only PIT Snapshot History）

### 10.1 為何 attempt history 不足

目前 `eps_consensus_attempts`／`revenue_consensus_attempts` 記錄單次來源階梯的 3 個查找結果；45 筆 released 各 3 attempts，只能證明本輪查找流程，不代表逐日共識快照。每日更新若以新 attempts 陣列取代舊陣列，便無法重建共識修訂路徑。v2 必須把「來源查找紀錄」與「來源值的 PIT 快照」分開保存。

### 10.2 每筆財報事件新增兩個 append-only 陣列

- `eps_consensus_snapshots: []`
- `revenue_consensus_snapshots: []`

每個 snapshot 至少保存：

- `snapshot_id`：以 event_id、metric、provider、data_as_of、period、statistic、value、currency、unit、basis_code、raw_response_sha256 計算的 SHA-256；相同原始值不得重複新增。
- `event_id`、`ticker`、`metric`、`source_level`、`provider`、`source_url`。
- `observed_at`：本系統實際取得來源的時間，必須含時區。
- `data_as_of`：來源明確提供的共識有效日期／時間；不得以 observed_at 代替。
- `provider_recalculated_at`：供應商最後重算時間（若有），獨立保存，不可自動等同 data_as_of 或 published_at。
- `event_date`、來源明確提供的 `period`、`period_end_date`。
- `value`、`statistic`、`currency`、`unit`、`basis_code`、`analyst_count`。
- `raw_response_ref`、`raw_response_sha256`：指向不可覆寫的原始 response 證據檔；不得只保存整理後數字。
- `snapshot_status`、`reason`：明確區分 pre_release_eligible、pending_cutoff_time、pending_required_fields、not_pre_release。

### 10.3 時點與可比較性規則

1. data_as_of 必須早於 event_date，才可標記公告前快照。若 data_as_of 只有日期且與 event_date 同一天，無法證明日內先後，必須 pending_cutoff_time；不可依 observed_at 猜測。
2. 同一來源每日重複回傳相同 data_as_of、period、value、currency、basis、unit 及 raw hash 時，採 snapshot_id 去重；任何值、analyst_count、期間或原始 payload 改變，均新增新 snapshot，不覆寫舊快照。
3. EPS 與 Revenue 必須分開保存快照及來源，不得共用一筆。
4. 每日預更新可同時保存尚未公布事件的公告前快照；事件發布後停止新增「公告前」標籤，公告後資料只能另存 post-release evidence，不得回填 PIT。
5. 每一個 raw response 必須以 SHA-256 驗證，採 create-if-absent；已存在檔案若 hash 不同，不可覆寫，應建立新證據檔並保留舊參照。
6. raw response archive 是原始來源證據，不是第二份可查詢資料庫；結構化欄位仍只存於唯一週 JSON。正式 archive 路徑、授權、保留期限及 writer 權限須先納入正式 WR／schema 規範，未核准前僅在 simulation 驗證。

### 10.4 單一 writer 與排程

- 未來快照由既有唯一 04:30／WR 所規定的行事曆更新 writer 執行，不新增第二個排程或 writer。
- 每次每日輪詢 append-only 保存快照；05:25 早報仍只讀取當週 JSON。
- Ortex TEST 不具 W46 日期範圍，也未取得 TAC 公開展示／再散布授權，不可作為此機制的正式來源。SIM-1.2 的 LSEG → FactSet → Investing.com 順序維持不變。
- 本節是隔離區設計提案；main Schema v1、WR、排程及正式 JSON 均未修改。
