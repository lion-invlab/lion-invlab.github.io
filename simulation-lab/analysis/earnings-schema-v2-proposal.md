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

### 3.4 Basis code 建議

EPS 代碼至少區分：
- `US_GAAP_DILUTED_EPS`
- `US_GAAP_BASIC_EPS`
- `IFRS_DILUTED_EPS`
- `IFRS_BASIC_EPS`
- `NON_GAAP_ADJUSTED_DILUTED_EPS`
- `NON_GAAP_ADJUSTED_BASIC_EPS`
- `NON_GAAP_ADJUSTED_UNSPECIFIED_EPS`

營收代碼至少區分：
- `US_GAAP_TOTAL_REVENUE`
- `US_GAAP_NET_SALES`
- `US_GAAP_OPERATING_REVENUE`
- `IFRS_TOTAL_REVENUE`
- `IFRS_NET_SALES`
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

## 6. GitHub workflow 現況與阻塞

本次讀取 main `.github/workflows/` 目錄，沒有找到 TAC 行事曆資料庫更新 workflow。現有 `.github/workflows/main.yml` 的工作是 S&P 500 volatility data，排程 cron 為 `10 21 * * 0-4`，執行 `scripts/update_data.py` 與 `scripts/update_tac_watchlist.py`，不是行事曆更新器。

main WR v5.15 說明 04:35 排程是行事曆週 JSON 唯一寫入者，但該排程的實際程式／workflow 在目前 main repo 中尚未定位。故不能安全地把新欄位直接加到正式 JSON，也不能宣稱 GitHub Actions 已具備自動抓取／寫入新欄位的能力。正式整合前必須先找回該寫入者的實際程式與排程設定，或由使用者核准建立正式更新流程。

## 7. 上線 Gate

- G1：寫入者定位，確認唯一觸發器、程式入口、權限及寫入路徑。
- G2：Schema v2 完整欄位與 enum 驗證。
- G3：W45/W46 舊資料遷移及 42 筆 W46 已公布財報逐筆回歸。
- G4：引擎單元測試、來源缺漏／basis mismatch／currency mismatch／period mismatch／unit mismatch／負 EPS／共識分歧測試。
- G5：HTML assembler 僅讀取 versioned statuses；不再有數字方向 fallback。
- G6：隔日排程模擬，證明新欄位不被覆蓋、舊欄位不被誤清空。
- G7：正式發布仍須使用者審核授權。

本分支完成的程式與測試只代表隔離模擬成果，不等於正式 main 已升級。
