# TAC 行事曆資料庫｜04:35 預更新 Automation v2 執行契約（草案）

狀態：2026-11-13 已套用至正式 04:35 ChatGPT automation；任務仍維持 disabled，等待 main Schema v2、判讀引擎及歷史遷移完成後再評估啟用。
適用任務：`TAC 行事曆資料庫｜每日 04:35 預更新`
唯一正式資料路徑：`data/calendar/weeks/YYYY-Www.json`

## 0. 啟動前硬性檢查

1. 讀取 main 最新 `TAC_WORK_RULES.md`，記錄 WR 版本、main HEAD SHA、WR blob SHA。
2. 讀取正式 Schema v2 契約及判讀引擎版本。正式 main 尚未包含對應程式／契約時，停止正式資料庫寫入並回報，不得自行先升級 JSON。
3. 確認本任務仍是唯一週 JSON writer；不得建立第二個排程或另一個獨立 writer。
4. 04:35 任務目前停用；本草案不代表授權重新啟用。

## 1. 每日資料擷取與保留

- 只處理當週既有週檔；不得產製 HTML、preview、index、母版、Manifest 或 WR。
- 以穩定 event_id 增量 merge/upsert；不得盲目整檔覆蓋、刪除既有事件或以空值覆蓋已核實資料。
- 每筆 actual、estimate 必須分別保留來源 URL、publisher、observed_at；保留來源 notes 及 secondary_refs。
- 無可靠來源或無法確認的欄位維持 null／pending；不得根據一般市場常識推估數字、幣別、會計口徑或單位。
- 既有已核實數據不得被較舊或未核實來源覆蓋；共識更新必須記錄原值、新值、來源及觀察時間。

## 2. Schema v2 財報欄位

### EPS
- `eps_actual`, `eps_estimate`
- `eps_actual_basis`, `eps_estimate_basis`（原始描述，保留）
- `eps_actual_basis_code`, `eps_estimate_basis_code`（受控代碼）
- `eps_actual_currency`, `eps_estimate_currency`
- `eps_actual_period`, `eps_estimate_period`
- `source`, `consensus_source`（來源物件須含 URL 及 observed_at）
- `eps_surprise`, `eps_surprise_pct`
- `eps_comparison_status`, `eps_comparison_reason`

### Revenue
- `revenue_actual`, `revenue_estimate`
- `revenue_actual_basis`, `revenue_estimate_basis`
- `revenue_actual_basis_code`, `revenue_estimate_basis_code`
- `revenue_actual_currency`, `revenue_estimate_currency`
- `revenue_actual_unit`, `revenue_estimate_unit`
- `revenue_actual_period`, `revenue_estimate_period`
- `source`, `revenue_consensus_source`
- `revenue_surprise`, `revenue_surprise_pct`
- `revenue_comparison_status`, `revenue_comparison_reason`

### 共用
- `judgment_engine_version`
- `judgment_timestamp`
- `earnings_comparison_summary`
- `earnings_commentary`
- `eps_consensus_conflict`, `revenue_consensus_conflict`（僅來源差異已核實時使用）
- `eps_inline_tolerance_abs`, `revenue_inline_tolerance_abs`（僅有來源精度證據時使用）

不得只保留一個 `eps_currency`、`revenue_currency` 或 `revenue_unit` 來同時代表 actual 與 estimate。

## 3. Basis code 與比較規則

唯一可接受的 basis code 以正式 `earnings_judgment.py` registry 為準。未登錄的 code 不得自行發明；先維持 Pending，提出 registry 更新及測試。

- actual 與 estimate basis code 必須相同。
- actual 與 estimate currency 必須相同。
- actual 與 estimate period 必須相同。
- Revenue actual 與 estimate unit 必須相同。
- actual、estimate 都須是有效數字，且各自來源 URL／observed_at 可追溯。
- 缺任何必要資料：`pending`。
- basis、currency、period、unit 不一致：`incomparable`。
- 已核實共識來源顯著分歧：`consensus_divergent`。
- 所有比較條件通過後，才以 actual - estimate 判定：正值 Beat、負值 Miss、落在有證據支持的 tolerance 內 Inline。
- 負 EPS 仍按差額方向判讀；例如 -0.13 優於 -0.72。
- EPS 與 Revenue 必須分開判讀，不能以其中一項代表整份財報。
- 不得直接信任歷史 `eps_comparison_status`、`revenue_comparison_status` 或 `financial_judgment`；必須重新依 v2 證據計算。

## 4. 引擎執行要求

- 正式 writer 必須呼叫已部署的 `earnings_judgment.py`，版本及 registry 必須與正式 main 一致。
- 若 automation runtime 無法實際執行該程式，不得聲稱已執行；所有未經程式驗證的方向性結果保持 Pending，並在報告中明確指出阻塞。
- 不可在 prompt 中複製一份獨立 Beat／Miss 演算法，避免程式與文字規則分岔。
- 寫入後每筆需帶 `judgment_engine_version`、`judgment_timestamp`、comparison reason。
- `financial_judgment` 舊欄位僅供歷史相容；新評論寫入 `earnings_commentary`，不可包含與結構化狀態矛盾的 Beat／Miss 主張。

## 5. Schema version 與遷移

- 不再要求「schema 未變」；改為要求「schema_version 與已部署正式 Schema 完全一致」。
- 只有正式 main 已部署 Schema v2、engine、validator 及 migration tests 後，才可把週 JSON schema_version 升為 2。
- W45、W46 舊資料需使用經測試的遷移工具；不得在每日例行更新中臨時拼湊歷史遷移。
- 舊 v1 directional statuses 沒有 v2 engine version 時，視為 legacy/unverified；不能自動沿用。
- 新版 schema 寫入失敗或驗收不通過時，停止本輪寫入並保留原始 JSON，不得回退到 v1 格式繼續寫。

## 6. 寫入與回讀驗收

1. 先 fetch 最新週檔及 blob SHA。
2. 計算增量差異，記錄新增／更新／保留／待核實。
3. 以 event_id merge/upsert，只寫唯一週 JSON 路徑。
4. 重新 fetch 同一路徑，確認 JSON 可解析、schema_version 正確、event_id 唯一。
5. 驗證每個方向性 status 都有同版本 engine、basis code、分離幣別、期間、來源及必要單位。
6. 檢查 Beat/Miss/Inline 與 surprise 數值一致；不符合即停止，不可把錯誤標成已完成。
7. 確認 audit 保留且新增完整；回讀 blob SHA 與最後寫入 SHA 一致。
8. 回報 WR／main／JSON SHA、各類事件數、已公布財報更新數、EPS／Revenue 狀態統計、Pending／Incomparable 名單、驗收結果。

## 7. 05:25 早報流程邊界

05:25 早報流程仍然對行事曆 JSON 嚴格唯讀：只讀、核對、記錄 SHA；不得新增、修改、刪除、merge/upsert 或回寫任何 JSON 欄位。04:35 未完成或新公布資料來不及納入時，只能在早報審核版標示待核實，不得由 05:25 補寫。

## 8. 啟用條件

此 v2 prompt 只有在以下條件全部完成後才可套用並重新啟用：
- Schema v2、engine、validator 已進入正式 main。
- W45／W46 migration 完成並通過逐筆驗收。
- 04:35 automation prompt 已替換為本契約。
- 端到端模擬通過，且隔日更新不會覆蓋 v2 欄位。
- 使用者確認正式恢復 04:35 排程。
