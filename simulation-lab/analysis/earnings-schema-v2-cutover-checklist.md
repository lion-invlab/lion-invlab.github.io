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
  - Test commit：`b95192767a2f11e35178fb99fa0127bb4ab934b8`
  - 已回讀確認程式與測試內容；CI status 尚無可見結果，**未標記測試通過**。

## 尚未完成（隔離模擬）

- [ ] 執行新增 estimate_period 回歸測試與完整 earnings test suite。
- [ ] 以最新 main W46（45 released）重新產生 migration preview CSV／audit JSON；舊 42 筆 preview 已過期。
- [ ] 驗證所有沒有來源期間的舊記錄都維持 Pending，不因 reporting_period 被誤判為可比較。
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
