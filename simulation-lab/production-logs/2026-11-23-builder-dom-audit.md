# 2026-11-23 TAC 投資早報｜HTML Builder DOM 第二層稽核

日期：2026-11-21  
目標報告：2026-11-23（一）  
分支：`simulation/tac-process-lab-2026-11-06`  
有效規範：SIM-1.3  
正式環境：唯讀；不修改 main、不部署正式首頁

## 本輪發現

1. Today Focus 核心觀察原先清空整個 `.callout` 後重建標題、文字和收折區，且刪除第二個母版細節容器。
2. 今日關鍵價位原先注入 `key-level-index`／`key-level-row` 新卡片包裝層，而非使用母版既有內容槽。
3. 財報卡原先清空 `.earnings-accordion-details`／`.earnings-results-grid`，重建 EPS、營收卡和 detail-field；週一／平日母版的欄位數本來不同，不能統一重建成另一種 DOM。
4. 原 DOM validator 未覆蓋 Today Focus 三分頁及財報卡內層母版槽位。

## 已修正

- 核心觀察：更新原有標題與文字節點，保留母版收折區及兩個細節容器。
- 關鍵價位：改用既有 `.key` 內容槽，以中文標籤及換行呈現五項價位；保留 disclosure 和 summary，不再新增卡片 wrapper。
- 財報卡：以既有母版原型為準，原位更新 EPS／營收兩卡、實際／預期列、狀態、證據註記及既有 detail-field。
  - 週一即將公布卡：保留母版 1 個欄位，將完整預估與共識資訊放入該槽。
  - 平日即將公布卡：保留母版 5 個欄位。
  - 週一已公布卡：採用上週財報母版原型的 2 張結果卡及 3 個欄位。
  - 平日已公布卡：採用平日母版原型的 2 張結果卡及 5 個欄位。
- 新增 `test_earnings_card_dom_preservation.py`，涵蓋週一／平日即將公布與已公布卡片。
- 新增 Today Focus 與財報卡母版結構 Gate。

## CI

- `44910833366`：success；新增財報卡原位更新回歸測試及 deterministic self-tests 通過。
- `44910900283`：正在執行新增 DOM validator 的 self-test-only workflow；完成後以本檔案提交觸發完整 11/23 build。
- 舊 run 的失敗是測試斷言仍期待已移除的舊程式碼片段；已依新實作更新斷言。未把舊失敗當作驗收通過。

## 下一步及限制

1. 完成 `44910900283`。
2. 觸發 11/23 Monday full build，確認 HTML Builder、DOM contract、provenance、瀏覽器互動及六種 viewport。
3. 只有完整 Build/QA 通過，才更新 simulation preview。正式首頁仍需使用者明確批准。
4. VIX、MOVE、CNN Fear & Greed、FedWatch 仍需在 2026-11-23 05:25 台灣時間前刷新；未刷新不得標記 REVIEW_READY。
5. SIM-1.4 仍為 DRAFT，未核准為唯一 Builder 入口；SIM-1.3 繼續生效。


## DOM Gate 後續修正

- Full build `44910974273`：HTML 組裝、瀏覽器互動、母版對照均通過；新增 Today Focus DOM Gate 失敗。
- 根因：核心觀察收折區原有第二個文字節點在更新時被替換成空字串，序列化後該文字節點消失，導致 callout DOM skeleton 不一致。這不是母版本身錯誤，也不是放寬 Gate 的理由。
- 修正 commit：`e994f60`。現在保留原有第二個文字節點並填入「其餘補充資料已整併於上方。」；不刪節點、不放寬 DOM Gate。
- 本次提交會重新觸發完整 11/23 build。前一 run 未通過 DOM Gate，不輸出 QA-passed preview。


## 第二輪 Full Build 驗收結果

- DOM validator deterministic run `44910900283`：success。
- Full build `44910974273`：因核心觀察 disclosure 第二個文字節點消失而未通過 DOM Gate；已由 `e994f60` 修復，未放寬 Gate。
- Full build `44911112651`：success。HTML assembly、瀏覽器互動、母版對照、DOM contract、artifact/provenance、44 項行情、行事曆及新聞結構全部通過。
- 輸出 HTML blob：`3bf2c6659b7b388cdbc6eb492daf2e31a9693a3f`；QA JSON blob：`cadcd11bf7efd330228eef80256b782f531b042f`；HTML SHA-256：`c8b27bcd1a13f148c7ab0846cad90033d8459a96be6f03f1202f1521366cade4`。
- QA JSON：`QA_PASSED`，但 `review_ready=false`，因 VIX、MOVE、CNN Fear & Greed、FedWatch 尚待 11/23 05:25 前刷新。
- 後續 `45e8879` 只將原有 disclosure 第二個粗體標題更新為「其他補充：」，不改變 DOM。現在以本次提交觸發 final full build，確保最終 QA JSON 的 Builder SHA 對應最新程式碼。


## Final Build（最新 Builder SHA 對齊）

- Final full build run `44911272905`：success。最新 Builder commit `45e8879` 已完成全流程驗收。
- QA JSON `builder_blob_sha=ffc2b319c6bc0e31d97b60197b96564b35394681`，與分支最新 Builder blob SHA 完全一致。
- 最終 HTML blob SHA：`505de1d6df7c2258244ff9b727d6fa0b832b9e59`。
- 最終 QA JSON blob SHA：`4c908c28830c6bdc9b502d11dd9eb672756de56b`。
- 最終 HTML SHA-256：`9f751c4f6762105ceac5db804f9133fa420f7c1b956f55cbd145a6b923d594e0`。
- 狀態：`QA_PASSED`，但 `review_ready=false`。VIX、MOVE、CNN Fear & Greed、FedWatch 仍待 2026-11-23 05:25 台灣時間截稿前刷新；不把 QA_PASSED 說成 REVIEW_READY。
- 六 viewport 1440／768／412／390／360／320 通過；Fed 官員行程、FedWatch、上週經濟及財報行事曆均保留。
- 本檔、程式、審核版及證據均留在 simulation branch；main／正式首頁未修改。


## 2026-11-21｜能源商品名稱欄位擠壓修正

- 使用者提供 11/23 審核版手機截圖，指出 WTI／Brent 商品名稱後方不應附加合約月份，避免擠壓報價欄。
- Builder 修正：商品列名稱連結只顯示母版原有商品名稱；合約代碼／月份留在既有 `.tab-panel-meta` 來源說明。未改母版、CSS、DOM 結構或價格資料。
- Builder commit `168c389873dc91a67212237446cfc6b8320ee809`；Builder blob `f96d5d7cdcc1029b3bcd99ed3979303627d36d9b`。
- Regression test commit `b583fda68a6724d75514b9677e37302d4e5e128a`；CI run `44913183956` success（compile + deterministic tests）。
- 現在重新執行 2026-11-23 Monday full build，以驗收實際 HTML、DOM、互動及桌面／手機視覺；未完成前不宣稱畫面修正已交付。


## 2026-11-21｜三項審核版缺陷修正（第二輪）

1. **商品名稱連結與報價來源拆分：** 新增 `instrument_url`，WTI／Brent／黃金 GC／白銀 SI 名稱連結指向對應 Investing.com HK 合約歷史頁；`source.url` 保留實際報價證據來源（CME／Investing），避免把行情來源冒充商品頁。
2. **財報卡星等樣式：** 原 Builder 複製第一張五星彩卡後，只更新星號文字，未同步移除 `five-star-earnings`／`five-star-company` class，造成四星公司仍套用五星外觀。新增依實際 TAC 星等同步 class。
3. **行事曆分頁順序／空白文案：** 原 Builder 在逐組處理時將 group append 回 panels，空組 continue 留在原位，導致 DOM 次序錯亂；且只刪除 details 卡，未清除舊 empty-state 文字。現改為保留母版原始三組順序、清除 list 內舊文字／舊卡片，空組保留正確 empty-state。分類統一依明確發布狀態及 Asia/Taipei 報告截點判斷；未到截點的 pending_verification 不得提前歸入已公布。
4. 新增 regression tests：商品連結與報價來源分離、4／5 星 class、日期／狀態分類、清除過期空白文案；並加入輸出 DOM 三分頁順序驗證。
5. 所有修改只在 simulation branch，未修改母版、main 行事曆 JSON 或 main/index.html。待完整 Builder／DOM／視覺 QA 通過後，再更新 main 同日 preview。
