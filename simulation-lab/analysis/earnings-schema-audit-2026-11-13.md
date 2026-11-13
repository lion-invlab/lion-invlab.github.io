# W46 財報資料欄位與來源完整性盤點｜2026-11-13 最新回讀

## 最新正式資料基準

- Repository：`lion-invlab/lion-invlab.github.io`
- Production branch：`main`
- Main HEAD：`68223e3aa384ae4d75311a243eb029da3c55b32c`
- Main WR：v5.15；blob SHA：`23b52f27b7afad083bbe28ed86021e04759f198d`
- W46：`data/calendar/weeks/2026-W46.json`
- W46 blob SHA：`ec246b8a765c64b798e348ce8df2760ea89cc5e1`
- W46 updated_at：`2026-11-13T18:59:36+08:00`
- schema_version：1
- Events：16 economic / 48 earnings / 129 audit
- Released earnings：45

> 本文件取代同日較早、以 42 筆 released earnings 與舊 W46 blob SHA 為基準的盤點。所有數字均由本次重新讀取 main JSON 計算；不得把舊報告的數字沿用為最新結果。

## 已公布財報欄位覆蓋（45 筆）

| 欄位 | 有值筆數 |
|---|---:|
| EPS actual | 38/45 |
| EPS estimate | 36/45 |
| EPS actual basis code | 18/45 |
| EPS estimate basis code | 15/45 |
| EPS actual currency | 19/45 |
| EPS estimate currency | 19/45 |
| EPS actual period | 45/45 |
| EPS estimate period | 0/45 |
| Revenue actual | 44/45 |
| Revenue estimate | 36/45 |
| Revenue actual basis code | 5/45 |
| Revenue estimate basis code | 2/45 |
| Revenue actual currency | 4/45 |
| Revenue estimate currency | 4/45 |
| Revenue actual period | 45/45 |
| Revenue estimate period | 0/45 |
| Revenue actual unit | 3/45 |
| Revenue estimate unit | 3/45 |
| judgment_engine_version | 0/45 |

### 數值缺漏名單

- EPS actual 缺值：PBR、CBRS、HIVE、SKYD、VG、ASTS、KSPI。
- EPS estimate 缺值：PBR、CBRS、VOD、GIB、KSPI、RBA、CNH、BAP、ALC。
- Revenue actual 缺值：BAP。
- Revenue estimate 缺值：PBR、CBRS、VOD、GIB、KSPI、RBA、CNH、BAP、ALC。

## 共識來源查核紀錄（45 筆）

| 指標 | Attempt 總數 | unavailable | not_pre_release | missing_required_fields | adopted |
|---|---:|---:|---:|---:|---:|
| EPS | 135 | 123 | 6 | 6 | 0 |
| Revenue | 135 | 123 | 6 | 6 | 0 |

- 每家公司每指標均留下 3 級來源查核紀錄；這代表「查核流程有紀錄」，不代表「共識值已取得」。
- LSEG I/B/E/S 與 FactSet Estimates 本輪均因執行環境沒有登入／API 權限而 unavailable。
- Investing.com 結果中，EPS 與 Revenue 各有 6 筆 not_pre_release、6 筆 missing_required_fields，其餘 33 筆 unavailable；沒有任何一筆符合完整採用條件。
- EPS 與 Revenue 的 selected consensus source object 各為 0/45。
- 舊來源物件仍各有 37/45 筆保存在 legacy 欄位；這些是歷史證據，不等於本輪來源階梯已採用，也不能自動視為符合 v2 的期間／口徑要求。
- 不得把 attempt 數量、legacy source 數量或舊數值覆蓋率當成有效共識取得率。

## 目前已存比較狀態（均為 legacy／未經 v2 引擎驗證）

| 狀態 | EPS | Revenue |
|---|---:|---:|
| Beat | 17 | 19 |
| Miss | 3 | 8 |
| Null | 25 | 18 |

45 筆 released records 全部沒有 `judgment_engine_version`。上述 Beat／Miss 只能視為歷史欄位值，不能宣稱已由統一 v2 規則驗證。

## Schema 漂移與期間欄位風險

- W45 與 W46 都標示 schema_version=1，但欄位集合不同；同一 schema_version 已出現 schema drift。
- W46 所有 45 筆 released records 的 EPS／Revenue estimate_period 均為空；actual period 45/45。
- `reporting_period` 只可作為 actual period 的來源；不可複製到 estimate_period。Estimate period 必須由共識來源明確提供。
- 2026-11-13 在 simulation branch 發現舊遷移函式 `migrate_legacy_record()` 曾把 `reporting_period` 複製到 actual 與 estimate 兩側，會錯誤製造「期間相符」證據。
- 已在隔離分支修正：只允許 reporting_period 填 actual_period；estimate_period 沒有明確來源證據時保持 null，判讀結果必須 pending。
- 修正程式 commit：`d0d8a1af6b137964364ed842823f4864e7aa619b`。
- 新增回歸測試 commit：`b95192767a2f11e35178fb99fa0127bb4ab934b8`。
- 截至本次回讀，該測試 commit 沒有可見的 GitHub status checks；測試尚未標記 PASS，須等待 CI 或可執行環境實測。

## 排程與寫入權責現況

- 目前啟用的唯一資料庫更新 automation：`TAC 行事曆資料庫更新`，ID `6af6d10c62448191819f04b976c64cf4`，每日 04:30 Asia/Taipei。
- 該 automation prompt 已補入公告前／公告後資料擷取欄位及 coverage matrix，並已修正其 W46 基準敘述；目前仍啟用，下一次排程為 2026-11-14 04:30。
- 另一個 Schema v2 automation：`TAC 行事曆資料庫｜每日 04:35 預更新`，ID `6ae6dff2200c81919ba2cee4db78f8a5`，目前 disabled；不得與 04:30 任務同時啟用成雙 writer。
- Main WR v5.15 的文字仍記載 04:35；目前啟用 automation 實際為 04:30，兩者存在設定／文件時間不一致。尚未修改 WR 或排程，不得默默把其中一方當成已同步。
- Main 正式 Schema v2、判讀引擎與 strict validator 尚未部署；正式 JSON 仍是 schema_version=1。不可提前把 main JSON 升成 v2。

## 結論與下一步

1. W46 已完成一次回填與來源查核紀錄，但 EPS／Revenue 有效共識採用數仍為 0；資料庫尚未完整。
2. 先完成 estimate period 不可推定的遷移修正測試，再重新產生 45 筆 in-memory migration preview。
3. 重新評估現有 legacy source 及其他可追溯來源能否提供公告前快照、期間、basis、幣別與單位；未能證明的值維持 pending，不得猜填。
4. 完成 Schema v2、engine、validator、W45/W46 migration 與 assembler integration 的隔離測試後，才可評估正式 main 部署。
5. 正式資料庫寫入權限仍由唯一 updater automation 持有；不得新增第二個週 JSON writer。
