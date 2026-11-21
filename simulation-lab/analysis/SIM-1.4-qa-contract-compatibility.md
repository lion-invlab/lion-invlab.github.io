# SIM-1.4｜雙母版與 QA Contract 相容性核查

日期：2026-11-21  
分支：simulation/tac-process-lab-2026-11-06

## 1. 核對基準

| 資產 | 路徑 | SHA | 結果 |
|---|---|---|---|
| 正式 Manifest | 母版專區/mother-template-manifest.json | fade5e3d88de76a79cb5c1656cc592b98827ab55 | 已讀取 |
| Simulation Manifest | simulation-lab/baseline/mother-template-manifest.json | dc6090c895e2abc17bb16225f4a581ddee5821b1 | 已讀取 |
| 週一正式母版 | 母版專區/TAC_母版_週一_2026-10-28_最終定版.html | a568e594e55909041d51d8eae7e6fe5f7986c096 | Manifest SHA 相符 |
| 平日正式母版 | 母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html | 3785405e331b10ec6189002e480be2a1edbe20ef | Manifest SHA 相符 |
| 週一 simulation baseline | simulation-lab/baseline/monday-mother-template.html | 1ac39d50b138e59f4aabf55fc68560ee277ba6f8 | Simulation Manifest SHA 相符 |
| 平日 simulation baseline | simulation-lab/baseline/weekday-mother-template.html | f010ff118d7a5a2c1f6e834aa24f832766383c2b | Simulation Manifest SHA 相符 |
| Simulation QA Contract | simulation-lab/baseline/mother-template-qa-contract.md | 2d8082159186618f0af9ddb2e799da58884b7ac4 | 已更新為 v1.5 DRAFT，對齊 SIM-1.4 草案，尚未生效 |
| Main QA 清單 | 母版專區/母版結構驗收清單.md | 74a7c90aaaeee497b7b2b134d9569aee615d95c0 | 已讀取，v1.3 |

## 2. 已確認一致的基準

- 正式 Manifest 的 monday／weekdays 路徑與 SHA，均與正式母版檔案實際 SHA 相符。
- Simulation Manifest 的 simulation_path／simulation_blob_sha，均與兩份 simulation baseline 實際 SHA 相符。
- 兩份 simulation baseline 與正式母版分開鎖定；不得把 simulation SHA 寫成正式母版 SHA。
- 兩份母版均有相同核心區塊錨點與 17 項全球主要市場結構；11 ETF 的固定 ticker／href 集合相同，但靜態順序不同；週一另有上週經濟及財報回顧區，平日不得新增。
- 母版 QA 清單列出共用 selector、行事曆卡巢狀結構、週一專用結構、CSS／JS／ID 統計及手機／桌面視覺檢查。

## 3. QA Contract 的版本與引用矛盾

1. 原 v1.4（2026-11-15）契約將定位指向 SIM-1.2，已於 simulation branch 更新為 v1.5 DRAFT（2026-11-21），定位改為 SIM-1.4 候選附件且明確尚未生效。
2. Contract 的 A2 以 simulation baseline SHA 作每日定位依據，這與 Simulation Manifest 相符；主規則必須明確規定使用 simulation_path／simulation_blob_sha，另記正式 mother path／blob_sha 作來源追溯，不可混用。
3. Main 的母版結構驗收清單 v1.3 定位為 main TAC_WORK_RULES.md 的附件；它與 simulation contract 內容重疊，但不是 simulation branch 的執行契約。SIM-1.4 不應把 main v1.3 列為第二份每日 QA 清單。
4. SIM-1.4 主文的附錄 D 應只引用 simulation contract 的固定 SHA；主文保留 Gate／責任／結果定義，不重複列出 selector 與卡片 DOM 詳節。
5. Contract v1.5 DRAFT A2.2 的共用 selector 含 #overview、#sentiment、#news-scan、#global-markets、#industry-bonds-fx-commodities、#calendar、#earnings、#sp500-earnings-health、#fed、#view；這些錨點應用於兩個 simulation SHA，不可用搜尋標題文字或 fallback selector。
6. 週一專用 #last-week-calendar、#last-week-earnings 只允許在 Monday baseline；weekday baseline 必須不存在。週一上週收折預設 closed。
7. 行事曆經濟卡的本週 .econ-toggle 與週一上週 .econ-event-toggle 是刻意不同的 selector；不可為了統一而改寫母版。
8. Contract 對 320／360／390／412／768／1440 viewport 的視覺檢查及互動規則，應作為每次母版 SHA 不變時的既有 QA 基準；只有受影響的差異才定向重跑，但不能把未執行項目標為通過。

## 4. 結構統計

依 contract A2.1 已列正式母版的基準：
- Monday：DOCTYPE 1、html/head/body 各 1、style 124、script 25、ID 183、ID 無重複。
- Weekdays：DOCTYPE 1、html/head/body 各 1、style 120、script 24、ID 174、ID 無重複。

Contract 自身另一份舊清單 v1.3 列 Monday ID 184、Weekdays ID 175，與 v1.4 simulation contract 的 183／174 不同。SIM-1.4 應以目前 simulation contract v1.4 及其 SHA 為當前基準，並在下一次 contract 版本修訂時保留差異紀錄；不能把 main v1.3 的統計直接複製到 simulation contract。

## 5. 尚未完成的實證

- 已完成正式母版與 simulation baseline 的靜態結構比對：Monday 正式／simulation 均 124 style、25 script、183 IDs；Weekday 均 120 style、24 script、174 IDs；兩組 ID 集合完全一致且無重複。兩組母版的 style/script 數量相同；正式／simulation 母版 blob SHA 不同，CSS 內容的完整 parsed diff／逐節點 DOM diff 尚未執行。
- 已完成兩份母版 11 ETF 固定 href 比對：各有 11 個唯一 href，ticker／連結集合一致；但母版示範排序不同，故不得把靜態 DOM 順序當每日排名。每日依當日漲跌幅重新排序。
- visual_regression.mjs 與 Workflow evidence expected_widths 已加入 320px；本次只確認程式碼與 workflow 一致，尚未在瀏覽器完成新 320px build 的 responsive／interaction 測試。
- QA Contract v1.5 DRAFT 的結構規格可作唯一詳細清單候選，但在 Builder 不相容問題解決前，不可宣稱 SIM-1.4 的完整每日組裝流程已通過。

## 6. 最新測試狀態

- GitHub Actions run 44897795972（commit 87ec7dea36ed6465b4bf0386bbf2dc098055ba07）deterministic self-tests 全部通過；包括雙母版 SHA／結構驗收及 11/23 fixture contract。
- 該 run 未執行 HTML build／Playwright；320px 目前只確認已加入 visual_regression.mjs 及 QA evidence expected_widths，尚無 320px 實際瀏覽器結果。
- 11/23 fixture 的六筆 CFD index rows 已被改成待核實並保留 rejected_reference；仍有現貨來源與情緒／FedWatch刷新 blocker，因此不應產生或核准審核版。

## 7. 結論

**QA Contract：可作唯一詳細 QA 規格的候選，但目前需更正過時版本引用並完成實際 DOM／視覺驗證。**  
**正式母版及 simulation baseline：Manifest SHA 登記一致；兩組 ID 集合與 style/script 統計一致，選版機制正確。**  
**SIM-1.4 全流程：尚未通過；Builder compatibility 為目前主要阻擋。QA Contract v1.5 仍是 DRAFT，須待 SIM-1.4 核准後才可生效。**


## 2026-11-21 補充：財報四狀態與來源順位

- QA Contract v1.5 DRAFT Section M 已加入 SIM-1.4 財報狀態契約：只允許 beat／miss／inline／pending；不允許 incomparable、consensus_divergent 等第五種狀態。
- 共識順位更新為 Yahoo Finance Average Estimate 第一、Investing.com 第二；LSEG／FactSet 為後順位歷史／研究證據，不得覆寫已選來源。PIT 是證據層，不是一般數值判讀必要條件。
- SIM-1.4 engine 1.4.0 與 schema 已同步四狀態；不相容的幣別／單位／期間映射為 pending 並保留原因。
- Builder 仍保留 legacy incomparable／consensus_divergent renderer 分支，且 pending 不相容案件目前仍會顯示舊「尚未公布」標籤；依 QA Contract M 應顯示「比較資料尚未齊備」。Builder 保護未修改，這是財報 renderer Gate 的 BLOCKER。


- 最新 deterministic regression run 44897795972 success，包含四狀態財報引擎 1.4.0、來源層級 Yahoo=1／Investing=2／LSEG=3／FactSet=4 及 11/23 fixture contract。未執行 browser QA。
