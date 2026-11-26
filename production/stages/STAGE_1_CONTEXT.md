# Stage 1｜開工基準與母版鎖定

## 輸入
MASTER_WR、Stage 1 本身及 Stage 2–6 WR、共用 contracts、production/config/mother-template-manifest.json、雙母版、MOTHER_TEMPLATE_QA、報告日期及 main 行事曆 JSON。Stage 1 讀取自身規範是執行依據，不構成前置 Stage 依賴。

## 執行
1. 以 Asia/Taipei 確定 report_date、星期及最近已完成交易日；週末不自動製作。
2. 週一選 Monday template，讀取本週及上週 ISO-week JSON；週二至週五選 Weekday template，只讀本週 JSON。
3. 記錄 main 起始 commit、MASTER WR／六份 Stage WR／全部共用 contracts／Manifest／母版／QA blob SHA，另固定 Builder approval record、Builder、Stage Runner／依賴模組、PORT_MANIFEST 與 tac-production.yml 的 blob SHA，以及週 JSON 路徑與 SHA。以 governance.blob_shas 固定清單保存；所有版本均固定於同一個起始 main commit，不得混用執行途中更新的 HEAD。
4. 驗證模板 SHA 與 Manifest 完全一致、週別情境正確、JSON 可解析、schema/日期合理。不得 fallback 到 main 舊母版、首頁、歷史報告或前次 preview。
5. 建立唯一 Run ID 與 run-context；記錄保護範圍及當次輸出路徑。Run context 必須包含後續 Stage 可直接使用的固定 report_date、trading_date、mother key/path/blob SHA、Manifest SHA、calendar commit、週 JSON SHA 及 governance blob SHA 清單。

## 輸出
run-context.json、基準 SHA 清單、calendar read receipt、Stage 1 receipt（含 run-context SHA 與 governance file count）。

## 驗收與交接
必要路徑、SHA、日期、星期情境全部正確才 PASS。將固定日期、交易日、44 項欄位清單、母版及來源規格交給 Stage 2。Stage 1 不修改母版、Manifest 或 calendar JSON。
