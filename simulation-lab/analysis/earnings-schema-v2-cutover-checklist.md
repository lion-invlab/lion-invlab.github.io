# TAC 財報判讀 Schema v2｜正式切換清單

狀態：未部署；目前只有 simulation branch 實作與測試。

## 已完成（隔離模擬）
- [x] W46 42 筆欄位盤點與 W45/W46 schema drift 確認
- [x] 唯一判讀引擎與受控 basis registry
- [x] HTML assembler 改為只讀 versioned judgment
- [x] v1 → v2 保守 in-memory migration preview
- [x] 42 筆 migration CSV 與 audit JSON
- [x] GitHub Actions 測試成功（run 43378999223）
- [x] 確認 04:35 writer 是 ChatGPT automation，且目前 disabled
- [x] 草擬 04:35 automation v2 prompt


- [x] 明確的 per-record JSON Schema v2（`schemas/tac-earnings-record-v2.schema.json`）
- [x] Schema v2 validator：JSON Schema + engine status consistency（`simulation-lab/runner/validate_earnings_v2.py`）
- [ ] 新增 validator 的 GitHub Actions 回歸執行成功（等待本次 commit CI）


- [x] HTML assembler 的兩個財報評論輸出路徑改為狀態一致性過濾，不再無條件輸出自由文字方向性評論
- [x] 新增 commentary contradiction regression cases（legacy pending、EPS opposite polarity、Revenue pending）
- [ ] 新增 renderer/commentary guard 的 CI 執行成功與 11/13 fixture rebuild visual/content QA

## 尚未完成（正式 main）
- [ ] 將 engine、schema validator、migration 工具及 assembler 修改部署至正式 main
- [ ] 正式 Schema v2 JSON Schema 與版本遷移程式
- [ ] 逐筆補齊 42 家 basis code、actual/estimate currency、period、revenue unit、來源
- [ ] W45、W46 歷史資料遷移及回讀 SHA 驗收
- [x] 更新唯一 04:35 ChatGPT automation prompt，取消「schema 未變」規則（2026-11-13 已套用；任務仍 disabled）
- [ ] 確認 automation runtime 能實際執行正式判讀引擎；若不能，需設計可執行的驗證步驟，不得只靠自由文字承諾
- [ ] 隔日 04:35 實際增量更新演練
- [ ] 05:25 唯讀驗證
- [ ] 使用者核准後才重新啟用 04:35 排程
- [ ] 使用者審核 11/13 v2 財報小卡及整份審核版

## 不可跳過的安全限制
- 不得另建第二個週 JSON writer。
- 不得在 Schema v2 未完整部署前修改正式 JSON。
- 不得把 legacy/unversioned Beat／Miss 當成新規則已驗證。
- 不得覆蓋原 11/13 審核版或正式首頁。
- 不得把隔離測試 PASS 說成 production ready。

## 2026-11-13｜Validator 與舊資料遷移硬化（隔離修正分支）

修正分支：`simulation/earnings-v2-validator-hardening-2026-11-13`

- [x] Validator 改為 fail-closed：0 筆 v2、空資料集、部分 v2／部分 legacy 均不得回報 rollout valid。
- [x] 增加已公布財報筆數及可選 expected count 核對。
- [x] Validator 重新計算並核對 status、reason、surprise、surprise_pct、summary，防止只改 status 或只留下舊計算欄位。
- [x] 舊資料遷移不再把單一 `reporting_period` 複製到 estimate period；它只可作為 issuer actual period 的保守來源。
- [x] 移除根據自由文字 notes 推定 estimate basis code 的路徑；共識口徑必須由 estimate basis 欄位明確提供。
- [x] 新增期間缺漏、自由文字口徑推定、零筆 v2、混合版本、錯誤 surprise／reason／summary 回歸測試。
- [x] 新增隔離 GitHub Actions workflow，於修正分支執行 engine、calendar projection、renderer 及 validator 測試。
- [x] 最新測試 run：`43410005264`，commit `7221da801b72665482655490fb5e7a9c1c2362d2`，結果 success。
- [ ] 將共識來源證據欄位逐項對照 SIM-1.2 F3-補充2，補足來源級別、資料有效時間、指標／期間／統計口徑及採用／跳過原因。
- [ ] 對 W45、W46 做逐筆 v2 遷移預演；每筆 EPS 與營收分開列出缺漏及可否比較。
- [ ] 把引擎、Schema、validator 與 writer contract 整合後再提正式 main；目前不得修改 main JSON、啟用 04:35 automation 或宣稱 production ready。

注意：CI success 僅證明此隔離分支上的回歸測試通過，不代表 main 已部署，也不代表 W46 已完成遷移。

### 來源階梯證據補強（同一隔離修正分支）
- [x] Schema v2 新增 `eps_consensus_attempts[]` 與 `revenue_consensus_attempts[]`，逐筆記錄來源層級、provider、URL、查核時間、資料有效時間、期間、數值、幣別／單位、basis code、統計口徑、分析師樣本數（若有）、採用／跳過結果及原因。
- [x] 唯一判讀引擎強制檢查 LSEG → FactSet → Investing.com 順序、不得跳級、不得在已採用後繼續搜尋。
- [x] 採用共識必須有具時區的 `data_as_of`，且早於財報公告時間；selected consensus source 必須與唯一 adopted attempt 一致。
- [x] EPS 與 Revenue 分開保存來源查找歷程；營收採用紀錄必須提供單位。
- [x] 增加 First Available Wins、來源 fallback、公告後共識不可採用、缺少來源歷程不得方向性判讀等回歸測試。
- [x] Strict validator 對每筆已公布財報的 EPS／營收分別檢查來源歷程；已採用必須唯一且在找到後停止，未採用必須完整查完三級，否則 Gate fail。
- [x] 最新程式／Schema CI：run `43410484429`，commit `506416ab143f8b161ab8c8076f2d860b2f7a8f9d`，結果 success。
- [ ] 將新增的 attempts 欄位納入正式 writer 的擷取與 merge/upsert；目前只完成 Schema／engine／測試契約，尚未接入正式 04:35 writer。
