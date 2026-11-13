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
