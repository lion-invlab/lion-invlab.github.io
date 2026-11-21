# SIM-1.4｜HTML Builder 相容性稽核

日期：2026-11-21  
範圍：僅 simulation branch  
對象：simulation-lab/runner/build_review_html.py  
檔案 SHA：04d5976e38ab0da24e19bbe4607da8f1c20e1d35  
母版基準：Manifest 正式 SHA monday a568e594e55909041d51d8eae7e6fe5f7986c096／weekdays 3785405e331b10ec6189002e480be2a1edbe20ef；simulation baseline SHA monday 1ac39d50b138e59f4aabf55fc68560ee277ba6f8／weekdays f010ff118d7a5a2c1f6e834aa24f832766383c2b。

## 結論

**狀態：BLOCKED，不得核定為 SIM-1.4 唯一 Builder。**

本次完成全檔靜態檢查（2,703 行、176,746 字元）。已檢查 Workflow 執行定義及近期 run；尚未執行新的成功 Python build、未產生新 HTML、未完成 Playwright／視覺回歸。因此本報告不是 Builder 相容性通過證明。

## 已確認的實作行為與相容性問題

| 程式位置（約略行號） | 實際行為 | 對母版零退化契約的影響 | 判定 |
|---|---|---|---|
| 701–717 | BeautifulSoup 解析母版、移除舊 provenance comment、追加 TAC_CALENDAR_SOURCE comment；另在 head 追加 summary heading CSS | 新增 style／comment，非純內容槽位更新；若 DOM/CSS 數量需與母版完全一致即不相容 | BLOCK |
| 708–714 | 新增 style id=tac-summary-heading-size-alignment | 改動母版 CSS 節點數及 cascade | BLOCK |
| 718–826 | 對週一上週收折區追加 disclosure CSS，並改寫 summary 子節點，新增 marker／label span | 變更既有 details/summary DOM、樣式及互動呈現；違反不得重建／改造母版控制的原則 | BLOCK |
| 779–826 | 新增 tac-simulation-layout-authority-v1 CSS，並 append 至 body | 新增 CSS 到 body，直接改變母版原有樣式基線 | BLOCK |
| 828–883 | 修改 Fed 標題，清空 .fc-fomc-weekly-events，再依行事曆資料重建整個官員行程區塊 | 不是替換既有內容槽位，而是重建區塊內容；須證明目標節點及子結構為允許更新槽位，並比對原母版 | BLOCK |
| 892–931 | 新增／替換 energy mobile CSS | 修改既有 CSS cascade；即使為修復顯示，也必須先有核准的母版／技術契約授權 | BLOCK |
| 963–989 起 | 動態建立專題焦點 feature、metrics 等 DOM，並寫入 inline styles | 新增頁面元件與樣式，不屬於純內容填值；必須證明專題區塊是已核准的可選槽位 | BLOCK |
| 多處 set_text／field.clear | 先清空節點，再重新 append 子節點 | 可能刪除節點內原有 icon、class 子節點、連結或語意標籤；需逐 selector 列出允許清空範圍及保留結構測試 | BLOCK |

## CLI、Workflow 與實際測試狀態

- CLI 必要參數：--data、--output、--expected-master-sha；選用參數：--key-levels-live、--price-reactions、--earnings-consensus-projection。
- 程式依 simulation Manifest 選定 Monday／weekdays simulation baseline，驗證實際 Git blob SHA 同時等於 Manifest simulation_blob_sha 與 CLI expected SHA，並拒絕週末日期。
- Workflow .github/workflows/tac-simulation-lab.yml 有 build／qa-only 兩種 dispatch 模式；build 依 fixture 日期選版、擷取 earnings price reactions、呼叫本 Builder，接續執行 interaction_smoke.mjs、visual_regression.mjs、validate_review_artifact.py、44 indicators／新聞數量驗收、QA evidence 封存及 simulation branch 回讀 SHA。
- 最近一次已完成的 deterministic self-test run 44895586059 於 test_1123_fixture.py 失敗；其餘先前測試（calendar source guard、dual mothers、Fear & Greed、summary headline、earnings judgement/schema、report-layer status／calendar overrides 等）均已通過至該失敗點。失敗原因不是 Builder 本身，而是 fixture 與 test 的截稿欄位契約不一致：fixture 的 report_cutoff_taipei 與 news_cutoff_taipei 均為 2026-11-21 17:57:31，test 卻硬編碼要求兩者都等於 2026-11-23 05:25。該 fixture 的 news_window_taipei 已封口於 11/21 17:57:31，但報告日期為 11/23；應分離 report cutoff 與 news cutoff，並同步測試。
- 目前最新兩個 push smoke runs 因 concurrency cancel-in-progress 互相取消；最新 pending run 尚待完成。不得把 cancelled／pending 記為通過。
- QA Contract v1.5 DRAFT 已增加 320px viewport，但 Workflow visual regression 的預設尺寸仍需檢查並同步增加 320px，否則主契約與執行器不一致。

## 已確認的正面基礎

1. 使用真正的 BeautifulSoup DOM parser，而非以固定字串 index 作為主要 DOM 定位工具。
2. 透過 calendar_source_guard 讀取 main 權威行事曆並投影資料；有 calendar SHA 與 branch scope 檢查。
3. 有 report-layer overlays，並在多處保護 main JSON 不被寫入。
4. 引入 earnings_judgment 模組；部分財報投影有事件 ID、日期、來源及狀態檢查。
5. 程式包含 fail-closed 條件，遇到來源或事件身分不符時會 raise。

## 必須補齊的驗收，才可重新評估

- [ ] CLI 全參數、預設值、必要檔案、輸入輸出路徑與副作用清單。
- [ ] 逐函式／逐 selector 的 DOM 寫入白名單：允許修改的文字、屬性、子節點，以及禁止觸碰的節點。
- [ ] 對兩份 SHA 鎖定母版分別做輸入／輸出 DOM diff；所有差異逐節點分類，CSS／JS／既有互動節點不得未經授權變更。
- [ ] 母版 CSS／JS 數量、內容 SHA、ID、錨點、tabs、radio、details/summary、收折預設狀態及卡片結構的自動化前後比對。
- [ ] 週一與平日各一份真實 fixture build；不得以 smoke test 或 Python compile 取代。
- [ ] 行事曆 source guard、財報判讀、新聞、44 項行情、11 ETF 排序、FedWatch、三區市場評論等完整 fixture contract tests。
- [ ] 負向測試：Manifest SHA 不符、母版缺失、selector 缺失／重複、事件 ID 不存在、main calendar SHA 改變、資料日期錯置、現貨／CFD 商品身分錯置、輸出路徑指向保護檔案。
- [ ] Playwright 互動及視覺回歸；至少 320／360／390／412／768／1440 px，並同步更新 Workflow／visual_regression.mjs。
- [ ] 輸出 HTML 回讀 SHA、HTML DOM diff、Pages／preview 可開啟性另行驗證。

## 建議處置

目前不修改 Builder 程式，也不將其列為唯一入口。SIM-1.4 應將它標記為「候選 Builder，尚未通過母版相容性 Gate」。若使用者希望保留現有視覺修復，必須先將那些差異列成獨立、可審核的明確授權變更；不得用「Builder 自動加 CSS」繞過母版零退化規則。

## 目前可宣告的證據狀態

- 靜態檢查：完成。
- 真正 Python build：未測試。
- DOM 前後差異測試：未測試。
- Playwright／視覺 QA：未測試。
- 唯一 Builder 核准：未核准。
