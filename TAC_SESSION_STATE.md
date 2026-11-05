# TAC 投資早報｜工作狀態錨點

> 本檔用途：跨對話延續 TAC 工作的唯一狀態摘要。它不是 Work Rules，不取代 `TAC_WORK_RULES.md`、Manifest、母版或 QA 清單。
> 每次接續工作，必須先讀取 main 最新版 `TAC_WORK_RULES.md`、本檔及 `母版專區/mother-template-manifest.json`，再以 GitHub 實際狀態校正本檔；若本檔與正式檔案或 GitHub 現況衝突，以正式檔案及即時 GitHub 狀態為準。

- 最後更新：2026-11-02（台灣時間；建立時）
- Repository：`lion-invlab/lion-invlab.github.io`
- 基準分支：`main`
- 正式規則：`TAC_WORK_RULES.md` v4.0
- 本檔定位：工作交接／進度錨點；不得據此推定任何功能已完成或任何預覽已通過 QA。

## 1. 目前主線目標

完成 TAC 投資早報 R3 可重複、可靠的每日審核版產製流程。2026-11-02（週一）早報已完成審核、使用者核准、更新正式首頁並完成 GitHub Pages 部署。接續主線改為修正正式首頁發布觸發鏈，並收斂每日自動產製流程；不得把本次部署成功誤認為所有 QA 項目永久全通過。

## 2. 正式規則與核准母版（建立時已重新讀取 main）

### 正式規則
- 路徑：`TAC_WORK_RULES.md`
- 版本：v4.0（2026-11-02，單一流程與責任整併版）
- 建立時 blob SHA：`4b18a156805f19521356a247e7e11f1cfacbded6`
- 每次接續都必須重新讀取，不可假設此 SHA 仍是最新。

### Manifest
- 路徑：`母版專區/mother-template-manifest.json`
- 建立時 blob SHA：`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`
- Manifest 明確鎖定兩份核准母版及其 SHA：

| 情境 | 路徑 | 核准 blob SHA |
|---|---|---|
| 週一 | `母版專區/TAC_母版_週一_2026-10-28_最終定版.html` | `0ea4775c5d15899a1e0b0a97c78744d90b8fff22` |
| 週二至週五 | `母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html` | `e5976190efd4c7fcc92cd623bfa94926997cc672` |

母版 SHA 以每次工作時重新讀取的 Manifest 為準，不得直接沿用本表。

## 3. 2026-11-02 審核版目前已知狀態

- 預覽檔已存在於 main：`preview/2026-11-02.html`。
- 最近一次已知 blob SHA：`e0e6c72b293b4abd97c0a0bdb6b9d58f1851f367`。
- 最近一次已知 main commit：`b006d67ec2c3cf02a31d8a73c8089f0013fecc09`。
- 最近一次已知預覽檔約 384,186 字元。
- 最近一次靜態盤點：DOCTYPE 1、head 1、style tags 124、script tags 25、id attributes 183。
- 已知存在：週一「上週經濟行事曆」、「上週財報行事曆」、「盤面觀察重點」及「審核版草稿」標示。
- 已知文字搜尋「待驗收」出現 2 次、「待核實」出現 28 次。
- 「Market Sentiment」英文標籤搜尋不到，不能僅憑此字串認定區塊不存在；須檢查實際 DOM、畫面及內容。
- 以上僅是上次靜態盤點，不代表完整資料、結構、互動、視覺 QA 通過，也不代表 Pages 線上部署已驗證。接續時須重新 fetch 預覽檔，並依 WR v4.0 及唯一 QA 清單完成驗收。
- 使用者先前要求保留預覽版；不得任意刪除或以新檔取代同日路徑。

### 最近已知預覽相關 commits（僅供追溯）
1. `b006d67ec2c3cf02a31d8a73c8089f0013fecc09` — Place core-observation disclosure inside approved callout container
2. `7e4453d81f34768e44ae2eb01ed435bf654e564c` — Restore approved focus-core disclosure and update QA status
3. `c3a496ffb50afe8b6f76b04520f85cb82a409e5a` — Record final 2026-11-02 TAC preview QA evidence
4. `4a413220c54b8384560e6fcf925c6ee9e0c2ca26` — Ground FedWatch rate-range interpretation in official Oct 28 FOMC decision
5. `61950472dfca0678e44ae2eb01ed435bf654e564c` — Restore exact approved FOMC panel hierarchy and keep source reference

## 4. 行事曆資料庫狀態

- 唯一路徑：`data/calendar/weeks/YYYY-Www.json`。
- 2026-W45 檔案已知存在：`data/calendar/weeks/2026-W45.json`。
- 上次讀取內容：economic events 17 筆、earnings events 33 筆；`wr_version` 欄位為 `3.12`。
- coverage 的 incomplete 是動態進行中狀態；使用者已明確說明這是正常現象，不可單憑 incomplete 判定故障或阻止早報。
- `actual=null` 在事件尚未公布前屬正常，不得預填或推估。
- 待辦：依 WR v4.0 核對 W45 JSON 的 schema、欄位與更新器版本相容性；不要只為了讓 `wr_version` 顯示 4.0 而直接改 JSON。早報製作原則上只讀取資料庫；03:30 維護工作負責寫入。

## 5. 自動化與分支現況（未驗收，不得宣稱完成）

建立時已知存在以下分支；分支存在不等於功能整合或完成：
- `review/2026-11-02-monday-report` — `7236d53b5915fe42aa4a7086f4f151f14100ee89`
- `review/2026-11-02-mother-structure-repair` — `73768965b16227f08c498b0ec23fc3ba03608942`
- `tac-renderer-safe-refactor-20261102` — `1ada29046e1f28f5307a3da21dba3405699c7ce4`
- `tac-r3-orchestrator-integration-20261101` — `e608cfdf8495d31c07b13ec531b06376492b6506`
- `tac-r3-p0-integration-20261101` — `76b29fef763378023895e88d0dd0c8808f6b24c5`
- `tac-full-report-integration-20261101` — `94e5e692fc0f8569868a36e48e7e62ffbcd84663`
- `tac-deploy-after-validation-20261031` — `95ac92797a4da626d3d47678b5bbcdbbef0b53f6`
- `tac-pages-preview-only-deploy-20261031` — `980adac4379ecfee0bd781d464e14dd487c66e11`
- `tac-daily-report-automation` — `b7da4b439e79b38729479c073474e8289d9330f5`

WR v4.0 明確要求：擷取器、Renderer、Orchestrator 必須經實際整合測試、正反向測試及完整產出驗收後，才可稱為完成。Capture-only/source-probe 不等於正式資料。接續工作應先盤點 main 上的真實程式、workflow、測試及執行證據，再決定最小修復，不要另建平行架構或無差別重跑測試。

## 6. 已知排程（建立時記錄；prompt 是否符合 WR v4.0 尚未重新驗證）

1. TAC 早報｜冬令時間 05:25  
   Task ID：`6ae1819903348191951f91de2b2e0591`  
   工作日週一至週五，05:25。
2. TAC 早報｜夏令時間 05:00  
   Task ID：`6ad9e48c33c081918a32b34fa3bb9e9c`  
   工作日週一至週五，05:00；僅 EDT 生效，EST 不執行。
3. TAC 行事曆資料庫｜每日 03:30 更新  
   Task ID：`6ae6dff2200c81919ba2cee4db78f8a5`  
   每日 03:30，只維護週資料庫，不製作早報、不修改 HTML。

待辦：檢查三個現存排程的 prompt 是否已跟上 WR v4.0；如需調整，先確認其工具能力與任務設定，避免重複建立排程。

## 7. 下一步（依序執行；優先最小可行閉環）

1. **重新確認即時基線：** 讀取 main 最新 WR、Manifest、雙母版 SHA、預覽檔、W45 JSON、QA 清單及 main 最新 commit；確認本狀態檔仍與現況一致。
2. **先驗收既有 11/02 預覽：** 不重做已完成內容；依唯一 QA 清單核對母版結構、資料、互動、視覺及 Pages 部署。未實測項目如實標示。
3. **只修已證實問題：** 僅在預覽允許範圍內修正；每次修改先讀最新 SHA，完成後回讀並確認母版、Manifest、首頁未被修改。
4. **完成一份可交付審核版：** 回報資料缺漏、QA 各類狀態、GitHub commit/blob SHA、Pages 是否可開啟。不得把未通過項目包裝成通過。
5. **之後收斂自動化主線：** 以同一條六步驟流程驗證資料入口、日曆讀取、HTML 更新、四類 QA 與預覽輸出；先查明現有模組可否接合，禁止無必要重構。
6. **排程與連續性：** 核對現有排程 prompt；後續重要工作完成、狀態改變或交接前更新本檔，記錄最新 main commit、實測證據與下一步。

## 8. 嚴格保護與操作原則

- 不修改正式首頁 `index.html`，除非使用者明確核准指定審核版。
- 不修改雙母版、Manifest、設計重構資產，除非使用者明確核准相應變更。
- 不刪除既有 `preview/2026-11-02.html`。
- 不建立第二份 WR、第二套行事曆資料庫、第二個 Orchestrator 或平行 Renderer。
- 不把 GitHub commit、workflow 綠燈、靜態檢查或分支存在當成完整驗收。
- 不重複重抓已核實且沒有新證據的資料；依 WR v4.0 單項處理失敗、一次待處理清單檢查。
- 使用者已授權助手在既定範圍內自主推進，不必每一步詢問「是否繼續」；但正式首頁發布仍必須遵守 WR 的明確核准閘門。
- 對話切換不會自動在背景延續執行。新對話應先讀本檔及正式規則，再核對 GitHub 現況後接續；不可只依賴聊天摘要。

## 9. 每次交接更新格式

每次更新本檔時，至少更新：
- 最後更新日期／時間（Asia/Taipei）
- main 最新 commit SHA
- 正在處理的單一主線任務
- 已完成事項（附檔案路徑、commit 或測試證據）
- 未完成／待核實／未測試事項
- 最新預覽檔路徑與 blob SHA（若適用）
- 下一個具體動作
- 本輪未修改的保護檔案確認

> 狀態標籤定義：**已完成**＝有可回讀的檔案／commit／測試證據；**待核實**＝已有資料但尚不能裁決；**未測試**＝尚無實際測試證據；**未通過**＝測試已執行且結果不符合門檻。


## 10. 上一輪對話的故障脈絡與交接補充（2026-11-02）

此節補足建立本狀態檔前，上一輪對話中曾發生、但原狀態摘要未完整記錄的關鍵歷史。它是歷史紀錄；當前實際狀態仍須以重新 fetch 的 main 檔案與測試為準。

### 10.1 預覽版曾經歷的結構性驗收失敗
- 早期的 `preview/2026-11-02.html` 雖已提交 GitHub，但與核准週一母版差異重大：當時檢查記錄缺少 12 個必要區塊、出現重複 `<head>`、CSS style tags 約 72 組（母版 124 組）、JavaScript script tags 約 2 組（母版 25 組）。
- 當時視覺測試因結構不符而跳過，GitHub Pages 也尚未驗證。這代表那個版本不能交付為完整審核版。
- 早期提交紀錄：`3a419835eace884e87c0efe0dee59f0381d3020d`；更早一次自動化重跑 Run ID：`08392cbd-67e8-832f-a978-963b5c8c5887`，當時仍執行中，預覽 SHA 未更新。這些是歷史狀態，不代表目前檔案仍有相同缺陷。

### 10.2 後續修復提交
上一輪後段已知預覽相關修復依序包括：
- `61950472dfca0678e44ae2eb01ed435bf654e564c` — 恢復核准 FOMC 面板層級並保留來源參照。
- `4a413220c54b8384560e6fcf925c6ee9e0c2ca26` — FedWatch 利率區間解讀補上官方 2026-10-28 FOMC 決策依據。
- `c3a496ffb50afe8b6f76b04520f85cb82a409e5a` — 記錄 2026-11-02 預覽 QA 證據。
- `7e4453d81f34768e44ae2eb01ed435bf654e564c` — 恢復核准的盤面觀察核心說明並更新 QA 狀態。
- `b006d67ec2c3cf02a31d8a73c8089f0013fecc09` — 將核心觀察 disclosure 放回核准的 callout 容器。
- 後續讀取到的預覽 blob SHA：`e0e6c72b293b4abd97c0a0bdb6b9d58f1851f367`。
- 以上提交證明曾做過這些修復，不等於全部視覺、互動或 Pages 測試已實際通過。必須重新讀取最新預覽及測試證據，逐項確認早期缺陷是否已消除。

### 10.3 使用者在上一輪對話的明確授權與限制
- 使用者已授權助手在 TAC 早報既定範圍內自主推進，不必每一小步詢問是否同意，也不應要求使用者反覆輸入「繼續」。
- 目標是完成 2026-11-02 的獨立審核版，讓使用者可以審核；不是直接發布正式首頁。
- 使用者曾詢問是否要刪除預覽版。處理原則是保留 `preview/2026-11-02.html` 作為當前工作成果及驗收對象，不得擅自刪除。
- 使用者要求若對話過長，應盡可能透過此狀態檔接續，不要要求其重新敘述工作。
- 自主推進不等於可繞過 WR 的正式發布閘門；`index.html` 仍須使用者明確核准指定審核版後才能更新。

### 10.4 真正的接續起點
接續工作應從「重新驗收現有修復後的預覽版」開始，而不是從頭重做早報，也不是把工作停在建立交接文件：
1. 重新 fetch `preview/2026-11-02.html`，記錄當前 blob SHA。
2. 以 Manifest 鎖定的週一母版作為唯一本體基準，重新比較必要 DOM、CSS、JavaScript、ID、卡片欄位及星期專屬區塊。
3. 先確認早期「缺 12 區塊、重複 head、72/124 CSS、2/25 JS」是否已修復；不要預設已修復，也不要預設仍存在。
4. 結構通過後才執行桌面、手機及 320px 視覺檢查，以及 tabs、導航、紅色圓形加號收折、行情連結等互動測試。
5. 實際確認 Pages 預覽網址可正常載入；未能實測的項目明確標示未測試。
6. 交付獨立審核版及 QA 結果；保留預覽檔，不觸碰正式首頁。


## 11. 2026-11-02 接續驗收進度（本輪即時回讀）

最後更新：2026-11-02 10:05:49（Asia/Taipei）

### 11.1 最新基線已回讀
- main 最新狀態檔 blob SHA（更新前）：`de5a50e3250cf92f828843c4bc65e5da66318563`。
- WR v4.0 blob SHA：`4b18a156805f19521356a247e7e11f1cfacbded6`。
- Manifest blob SHA：`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`。
- 週一核准母版 blob SHA：`0ea4775c5d15899a1e0b0a97c78744d90b8fff22`，與 Manifest 一致。
- 預覽 `preview/2026-11-02.html` blob SHA：`e0e6c72b293b4abd97c0a0bdb6b9d58f1851f367`。
- 正式首頁 `index.html` blob SHA 仍為 `bf853317df07920d4a91db7103c2f95b0a1ed725`；本輪未修改。
- W45 DB blob SHA：`c15b7aaee56b95b38d5983bbf174f3e9bba894b2`；updated_at 為 `2026-11-02T03:32:09+08:00`，`wr_version` 仍為 `3.12`。本輪未修改。

### 11.2 預覽結構靜態比對
- 預覽與週一母版均為 DOCTYPE 1、head 1、body 1、style 124、script 25。
- 預覽 ID 數 250；母版 ID 數 184。母版全部 184 個 ID 均保留；額外 66 個 ID 對應本次上週／本週經濟與財報事件卡。
- 預覽有 2 組重複 ID：`tac-toolbar-bubble-preview-v1`、`tac-toolbar-bubble-preview-v1-js`；同樣重複存在於核准母版。Actions validator 已將其標記為「pre-existing duplicate IDs retained from approved master」，故本輪不改母版，也不在預覽中自行消除。
- 本輪靜態檢查未發現失效內部錨點。
- 預覽共有 86 個 details，初始 open 屬性 0；週一上週經濟與財報區塊及其 ID 均存在。
- 預覽內含 25 個 econ-event、41 個 earnings-accordion、21 個 radio inputs；紅色 32px 收折控制相關 CSS 規則存在。以上屬靜態盤點，不代表已逐項點擊互動。
- 母版與預覽標題日期不同（母版 2026/10/26、預覽 2026/11/02），符合當日報告日期更新。

### 11.3 已找到的實際 GitHub Actions 證據
- Structural Gate run：`41374656254`，commit `b006d67ec2c3cf02a31d8a73c8089f0013fecc09`，結論 success。
- 日報驗證輸出：`PASS 2026-11-02.html: correct weekday master anchors, structure and local links`；並明確警告兩組重複 ID 是核准母版既有問題。
- 該 workflow 明確聲明：Structural Gate 不等於 browser/visual 或 data-verification pass。
- Playwright layout regression 實測通過：desktop-1440、tablet-768、mobile-320；輸出稱已截圖並檢查 section geometry、computed layout 與 overflow。Regression artifact ID：`13110409382`。
- Pages deploy run：`41374723228`，commit 同為 `b006d67...`，deploy job conclusion success；部署 artifact ID：`13110816508`。
- 本輪 web 頁面讀取工具無法直接開啟 Pages URL，因此記錄為「Actions 部署成功；本輪直接頁面載入未能獨立驗證」，不可將兩者混為一談。
- 上述 Playwright workflow 是版面／溢位回歸，未提供收折、tabs、導航等實際點擊互動測試證據。

### 11.4 本輪驗收判定
- **已通過：** 來源鎖定、母版 SHA、基本文件骨架數量、母版 ID 保留、局部錨點、Structural Gate、desktop/tablet/320px layout regression、Pages deploy job。
- **已知母版既有警告：** 兩組重複 ID；不得未經核准修改母版。
- **未測試：** 逐卡紅色圓形加號實際點擊／收折、週一兩個上週區塊展開／收合、FedWatch/FOMC tabs、導航、行情連結逐項開啟。
- **待核實：** 44 項行情數值與資料日期／口徑、11 個產業 ETF 數值、FedWatch 當下機率及時間、新聞 5+10 則原文時間與來源、行事曆事件欄位與公布值、分析與行情同步、Pages URL 實際載入。
- 因資料驗證及互動測試未完成，預覽目前**尚不得標示為完整 QA 通過或最終可交付**。

### 11.5 保護檔案狀態與下一步
- 本輪未修改 `index.html`、雙母版、Manifest、W45 DB 或預覽 HTML。
- 正式首頁 SHA 與已知核准 SHA 一致。
- 下一步：先做預覽內容資料稽核（44 市場指標、11 ETF、FedWatch、新聞、行事曆），逐項以來源與日期核對；同時規劃並執行瀏覽器互動測試。不得因 Pages deploy success 就跳過這些 Gate。


## 12. 2026-11-02 預覽資料 QA 與重新 Gate 結果

最後更新：2026-11-02 10:12:42（Asia/Taipei）

### 12.1 本輪最終檔案基線
- 預覽 `preview/2026-11-02.html` blob SHA：`e3171fd4b6309e0f97ad01d958b596b1e0b8448e`。
- WR `TAC_WORK_RULES.md` blob SHA：`4b18a156805f19521356a247e7e11f1cfacbded6`。
- Manifest blob SHA：`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`。
- 週一母版 blob SHA：`0ea4775c5d15899a1e0b0a97c78744d90b8fff22`。
- W45 DB blob SHA：`c15b7aaee56b95b38d5983bbf174f3e9bba894b2`。
- 正式首頁 `index.html` blob SHA：`bf853317df07920d4a91db7103c2f95b0a1ed725`（仍應與正式核准 SHA `bf853317df07920d4a91db7103c2f95b0a1ed725` 相同；本輪未修改）。
- 本輪未修改 WR、Manifest、雙母版、W45 DB 或正式首頁。

### 12.2 本輪預覽內容修正
- FedWatch：直接再次讀取 Investing.com Fed Rate Monitor，頁面最後更新仍為 2026-10-31 00:35 EDT；11/02 10:05 台灣時間複核時，最新可見 12/09 會議機率仍為維持 30.2%、升息一碼 69.8%。預覽總結與來源註記已明確標示為延遲約 45 小時 30 分的快照，不得當作即時市場機率。
- FactSet 盈餘健康度：將來源註記中殘留的 24% 已公布比率修正為 FactSet 10/30 官方報告的 60%，與主文一致。
- 預覽 metadata：`meta name="report-date"` 從母版舊日期 2026-10-26 更新為 2026-11-02。
- 母版內隱藏的舊 `data-sync-warning` 文案已更新為 11/02 審核狀態；該區塊因母版原有 `body.release-ready` class 而仍被 CSS 隱藏。
- 曾嘗試把 body class 改為 `review-pending`，但 DOM contract 明確保護 body class，Gate run `41376263139` 因此失敗。已恢復母版原有 `release-ready` class；修復後 Gate 通過。不得為了顯示警示而改母版或繞過結構契約。
- 已知母版矛盾：母版 CSS 註解表示審核版應保留警示、只有全部驗收後才加 `release-ready`，但核准母版本身已帶 `release-ready`。本輪僅記錄，不修改母版。

### 12.3 市場數據抽核
- 44 項市場指標已逐項抽核：17 個全球指數、11 個產業 ETF、3 個美債期限殖利率、6 個外匯、2 個能源商品、2 個貴金屬、VIX、MOVE、CNN Fear & Greed。
- 17 個指數與 11 個 ETF 的 2026-10-30 歷史收盤／漲跌幅與 Investing.com 香港站相符。
- 6 個外匯、WTI、Brent、黃金、白銀、VIX、MOVE 與 2026-10-30 歷史資料相符。
- 美國財政部官方 2026-10-30 日殖利率：2Y 4.56%、10Y 4.94%、30Y 5.31%，已核對。
- CNN Fear & Greed：官方 CNN 頁無法直接讀取，採 FGScore 標示為 CNN Provider Index 的備援值 26.0 Fear；已保留來源限制。
- Brent 價格吻合歷史資料，但合約月份／合約識別仍標示待覆核。
- 以上 44 項屬人工逐項歷史值抽核；並不代表 Investing.com 當下頁面一定即時更新。

### 12.4 新聞與行事曆 QA
- Global Focus News 5 則、Market Hot Headlines 10 則均已逐項核對來源頁、原始報導及時間窗（2026-10-30 12:00 至 2026-11-01 22:15 台灣時間）；OpenAI 融資目標新聞的 Investing 頁無法直接開啟，但由 FT／Reuters／Investing.com 搜尋結果交叉核對。
- 上週經濟行事曆 8 筆，全部五星；已公布事件均含前值、預估、實際值及影響判讀。
- 上週財報行事曆 8 筆，全部五星；均含 EPS／營收實際值、共識比較及財報後首個常規交易日股價反應。
- 本週經濟行事曆 17 筆，13 筆四星、4 筆五星；本週財報行事曆 33 筆，31 筆四星、2 筆五星。符合 WR 的本週四／五星、上週五星篩選規則。
- 官方尚未確認精確時間的事件保留「時間待核實」／`time_known=false`，不得自行填入推測時間。
- W45 DB coverage incomplete 是動態狀態，依使用者說明不視為錯誤。

### 12.5 最新 Gate、瀏覽器測試與部署
- 先前失敗的 body class 嘗試：run `41376263139`，失敗原因只有 body class 與核准母版不同；已恢復。
- 最新 Structural Gate run：`41376350033`，commit `0c2c645d0e2f89c6e0705726da72b34a5c252627`，結論 success。
- Validator 輸出：`PASS 2026-11-02.html: correct weekday master anchors, structure and local links`；兩組重複 ID 仍明確標為核准母版既有警告。
- Playwright layout regression：desktop-1440、tablet-768、mobile-320 全部通過；每個 viewport 都截圖並檢查 section geometry、computed layout、overflow，另實際點擊第一個 details disclosure 與第二個 TAC tab radio label；測試腳本並非全卡／全導航的完整點擊測試。
- Screenshot artifact：`13110989045`（run `41376350033`）。
- Pages deploy run：`41376413692`，commit `0c2c645...`，deploy job success。
- 本輪 web 工具仍無法直接載入 Pages URL；因此只能記錄 GitHub Pages deploy job success，不能宣稱已由本輪直接瀏覽器獨立確認頁面載入。

### 12.6 最終交付判定
- **通過：** 預覽 DOM 結構契約、母版錨點／結構／內部連結、桌面／平板／320px 版面回歸、details 基本收折冒煙測試、TAC tab 基本切換冒煙測試、44 項市場欄位抽核、新聞來源與時間窗、行事曆星等篩選及上週已公布實績欄位。
- **保留：** 母版兩組重複 ID；CNN 使用備援來源；Brent 合約月份待覆核；母版 `release-ready` class 與隱藏警示的註解矛盾。
- **尚未完整測試：** 所有紅色 32px 加號逐張點擊、所有 tab、所有導航項目逐項點擊；本輪 Pages URL 無法直接載入驗證。
- **正式首頁未發布。** 目前僅為 11/02 獨立審核版，不能宣稱所有 QA Gate 全數通過，也不得修改 `index.html`，直到使用者明確核准指定審核版。


## 13. 2026-11-02 最終審核版補漏與部署

最後更新：2026-11-02 10:15:52（Asia/Taipei）

### 13.1 上週經濟卡片影響判讀補漏
- 重新讀取 W44 `data/calendar/weeks/2026-W44.json`，確認上週 8 筆五星經濟事件均有 actual、status=released 及 `impact_judgment`。
- 原預覽卡片只顯示前值、預估、實際、來源，未把資料庫已有的結果比較／市場影響判讀呈現；這違反 WR v4.0 F2。
- 已在 8 張既有卡片的「實際」欄位內，以文字內容更新標籤為「實際與判讀」，補上結果比較及市場影響；未增加 DOM 元件、未改母版結構。
- 八張卡片 ID：`prev-au-cpi-202609`、`prev-rbnz-rate-20261028`、`prev-boc-rate-20261028`、`prev-fomc-rate-20261028`、`prev-us-gdp-20261029`、`prev-us-pce-20261029`、`prev-ecb-rate-20261029`、`prev-boj-rate-20261030`。
- 上週 8 張五星財報卡已含 EPS／營收實際值、共識比較、財報判讀與首個常規交易日股價反應，無需改動。

### 13.2 最新預覽與驗收證據
- 最新預覽 blob SHA：`1106c98b0347e20ef33154e928d7cee1268f2d0e`。
- 最新預覽 commit：`d5974dc226dfaa45bfd41ad5c43c43a31ccf1153`。
- 最新 Structural Gate run：`41376653308`，結論 success。
- Validator：`PASS 2026-11-02.html: correct weekday master anchors, structure and local links`。
- Playwright：desktop-1440、tablet-768、mobile-320 全部通過；每個 viewport 都檢查區塊幾何、computed layout、overflow，並測試第一個 details disclosure、第二個 TAC tab label 的點擊切換。
- 最新截圖 artifact：`13111781056`。
- 最新 Pages deploy run：`41376710207`，commit `d5974dc...`，結論 success。
- 直接開啟 `https://lion-invlab.github.io/preview/2026-11-02.html` 的本輪 web 工具仍回傳不可讀取；只能確認 deploy job success，不能聲稱本輪已獨立瀏覽器載入確認。

### 13.3 目前仍保留的限制
- 完整互動仍未逐項點擊全部 25 張經濟卡、41 張財報卡、全部 tabs 與導航；目前 Playwright 僅在三種 viewport 各測一個 details 和一個 tab。
- CNN Fear & Greed 使用已標示的 FGScore 備援；Brent 合約月份仍待覆核。
- 母版兩組重複 ID 與 `body.release-ready`／隱藏審核警示的註解矛盾仍是母版既有問題；本輪不改母版。
- 正式首頁未發布；使用者核准前不得修改 `index.html`。

### 13.4 最終保護基線
- WR SHA：`4b18a156805f19521356a247e7e11f1cfacbded6`。
- Manifest SHA：`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`。
- 週一母版 SHA：`0ea4775c5d15899a1e0b0a97c78744d90b8fff22`。
- W44 DB SHA：`ea4f17badae8c7f7727f8fe1df3aadba8dfc2c98`。
- W45 DB SHA：`c15b7aaee56b95b38d5983bbf174f3e9bba894b2`。
- 正式首頁 SHA：`bf853317df07920d4a91db7103c2f95b0a1ed725`；應維持 `bf853317df07920d4a91db7103c2f95b0a1ed725`，本輪未修改。
- 本輪只修改 `preview/2026-11-02.html` 與 `TAC_SESSION_STATE.md`；沒有修改 WR、Manifest、雙母版、W44/W45 DB 或正式首頁。


## 14. 2026-11-02 接續驗收補充（最新 main 回讀）

最後核對：2026-11-02（台灣時間）
- main HEAD：`c83ef57131840e1469a098dca86381a20af5fec0`，commit message：`Record final TAC 2026-11-02 preview validation and impact analysis`。
- 本節寫入前，`TAC_SESSION_STATE.md` blob SHA：`20cd7555fe402012b877743f97d25453236ac657`。
- 正式 WR v4.0 SHA：`4b18a156805f19521356a247e7e11f1cfacbded6`；Manifest SHA：`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`；週一母版 SHA：`0ea4775c5d15899a1e0b0a97c78744d90b8fff22`；預覽 SHA：`1106c98b0347e20ef33154e928d7cee1268f2d0e`。
- 預覽內容最後一次變更 commit：`d5974dc226dfaa45bfd41ad5c43c43a31ccf1153`（補入上週經濟事件結果比較與市場影響判讀）；後續 main HEAD 的 `c83ef57...` 只更新本狀態檔，沒有改預覽。
- 最新結構 Gate：run `41376653308`，job `125058254224`，結論 success。Log 明確指出：市場欄位契約檢查是結構檢查，不代表行情數值／日期／來源已核實；HTML validator 通過週一母版 anchors、結構與 local links；兩個重複 ID 是母版既有警告；Structural Gate 本身不是完整資料或互動驗收。
- 最新 Playwright layout regression：同一 run，desktop-1440、tablet-768、mobile-320 全部通過 section geometry、computed layout、overflow；截圖 artifact `13111781056`。測試腳本 `scripts/tac_browser_layout_regression.mjs` 目前只逐 viewport 點擊第一個 details disclosure 及第二個 TAC tab，並未逐項測完所有卡片、tabs、導航。
- Pages deploy run：`41376710207`，結論 success，對應預覽 commit `d5974dc...`。本輪 web 開啟 Pages URL 仍不可讀取，因此「部署 job 成功」已確認，但「本輪獨立瀏覽器實際載入 URL」仍未確認。
- 最新靜態盤點：母版／預覽分別為 style 124／124、script 25／25、ID attribute 183／183；預覽 HTML 另有 86 個 details 與 86 個 summary、10 個 `tac-tab-radio`、21 個 radio、258 個 anchors（其中 13 個頁內錨點，未發現缺失目標）、0 個初始 open details。預覽實際 `id` attributes 共 183 個、181 個唯一 ID；兩組重複 ID 僅為 `tac-toolbar-bubble-preview-v1` 與 `tac-toolbar-bubble-preview-v1-js`，與母版一致。
- 上週經濟／財報兩區及其導航存在；兩區初始收折。行事曆紅色圓形加號 CSS 可見 32px 寬、高、min-width／flex-basis 設定。
- 正式首頁 `index.html` SHA 仍為 `bf853317df07920d4a91db7103c2f95b0a1ed725`，未修改。未修改 WR、Manifest、母版或 W45 DB。
- **交付狀態：** 結構 Gate 與三種 viewport 版面回歸通過；靜態結構盤點完成；全卡片／全 tabs／全導航逐項互動測試尚未完成；Pages URL 本輪獨立載入未確認。不得標示為完整 QA 全通過；正式首頁仍未發布。


## 15. 互動結構盤點續驗（2026-11-02）

- 本輪重新讀取預覽 SHA：`1106c98b0347e20ef33154e928d7cee1268f2d0e`；目前 main HEAD：`d7e5544717326641a6f2e4658ee68671dcbe7b06`。
- 全部 21 個 radio 分屬 7 組：tac-news 2、tac-global 3、tac-assets 5、week-econ-tab 3、week-earnings-tab 3、fed-live-tab 2、focus-tab 3。
- 21 個 radio 全部具有對應的 `label[for]`；每個 radio ID 都能在 HTML/CSS 找到對應的 `:checked` 規則（靜態檢查）。
- 13 個頁內導航連結的目標 ID 全部存在；未發現空 href 或缺少 href 的 anchor。
- 86 個 `details` 都有直接子層 `summary`；靜態確認不代表 86 個收合動作都已在真實瀏覽器逐一點擊。
- 本輪未執行真實瀏覽器全項互動測試；Pages URL 仍因外部讀取工具不可存取而無法完成獨立載入確認。不可標示互動 Gate 通過。
- JS 事件綁定的靜態抽查結果：`[{"id":"tfn-close","containsIdLiteral":true,"getElementById":1,"querySelector":0},{"id":"tac-toolbar-bubble-preview-v1","containsIdLiteral":false,"getElementById":0,"querySelector":0},{"id":"tac-toolbar-bubble-preview-v1-js","containsIdLiteral":false,"getElementById":0,"querySelector":0}]`。
- 正式首頁、預覽 HTML、WR、Manifest、母版均未修改；僅追加本狀態檔紀錄。


## 16. Brent 合約核實與預覽內容修正（2026-11-02）

- 查證來源：Investing.com 2026/10/30 Brent 歷史列為 US$117.64、+2.40%；Reuters 明確報導 2026/10/30 到期的 December Brent futures 結算 US$117.64；ICE 官方 expiry 表列 Dec26 最後交易日 2026/10/30、最終結算日 2026/11/02。
- 因此已解除原先「Brent 合約月份待覆核」警示；核實口徑為 2026 年 12 月（Dec26）合約。Investing.com 當前頁面合約代碼標籤與 10/30 歷史日期列不完全同口徑，故以日期歷史列並用 Reuters／ICE 交叉確認，沒有改動價格或漲跌幅。
- 已更新唯一審核版 `preview/2026-11-02.html`：commit `41920966ca625f20ab1a4ec93510a8ec03fff893`；新 blob SHA `1206f3ae5f25110789cdfca373a9a72f516393e1`。改動僅限頂部審核提示、Brent 資料來源說明及頁尾 Brent 狀態；沒有改行情值、CSS、JavaScript、DOM 結構或首頁。
- 更新後回讀確認：預覽 SHA 為 `1206f3ae5f25110789cdfca373a9a72f516393e1`；style 124、script 25、head 1；Brent pending 字樣已清除，Reuters 與 ICE 來源連結已寫入。
- 新一輪 Structural Gate run `41377564345`（head SHA `41920966...`）已啟動；截至本紀錄更新時仍在執行，market snapshot／mapping／binding／treasury／DOM self-test／dated report structure 等步驟均已 success，Playwright Chromium 安裝尚在進行，故新一輪瀏覽器回歸與 Pages 部署尚未確認。
- 關於時間戳：FedWatch 來源區的 08:21 是本次報告初次擷取時間；10:05 是再次直接讀取頁面的複核時間。兩者代表不同動作，並非資料矛盾，不需修改。
- 本輪沒有改動 `index.html`、WR、Manifest、母版、W45 DB。正式首頁仍未發布；互動逐項實測及 Pages 預覽網址獨立載入仍待完成。


## 17. 全量互動驗收與 Pages 實際部署確認（2026-11-02）

- PR #265 已合併：`72e9030502f090b93b91ea21349790007e3cd110`。僅更新既有 `scripts/tac_browser_layout_regression.mjs`、`.github/workflows/pages.yml`，以及在預覽結尾加入不渲染的 QA HTML 註解以觸發同一條既有驗證／部署流程；沒有新增 Orchestrator、Renderer 或平行產線。
- PR 最終驗證：Structural Gate run `41378335021` success；Market Field Contract run `41378334912` success。Main push Structural Gate run `41378467559` success。
- Playwright 已在桌面 1440px、平板 768px、手機 320px 三種 viewport 實際執行：
  - 86 個 `details > summary` 全部逐一切換並恢復原狀。
  - 21 個 radio tab 全部逐一點擊並確認 checked。
  - 13 個頁內導航連結全部點擊並確認目標。
  - 已核准母版中具備 32×32px 紅色圓形控制的上週經濟卡及財報卡逐項檢查；版面幾何與水平溢位檢查全部通過。
  - Browser regression 最終 log：`TAC BROWSER LAYOUT REGRESSION PASSED`。Artifact run `41378467559`。
- **仍保留兩項母版層級警告，不宣稱全視覺規格完全通過：**
  1. 核准週一母版的本週經濟卡沒有對應的 plus-control markup；本次 preview 有 17 個 `.econ-event-toggle` marker，但母版 CSS 的 selector 與 markup 不一致，因此這 17 個 marker 沒有紅色圓形樣式。需要正式母版／Renderer 修正；依既有授權限制，本輪未修改正式雙母版或 Manifest。
  2. 產業收合控制在核准母版及 preview 桌面／平板為 30×30px，手機 320px 為 32×32px；preview 與母版一致。未擅自改動鎖定母版。
- Pages deploy run `41378554136` success；部署後 smoke test 實際對 `https://lion-invlab.github.io/preview/2026-11-02.html` 執行 curl，回傳 HTTP 200，並確認頁面標題及週一專屬 `last-week-calendar`、`last-week-earnings` 區塊存在。這是本輪首次有自動化實際載入已部署預覽 URL 的證據。
- 最新預覽 blob SHA：`ea51a256f05e3858d2f7370d7c5c83590eb6c817`；最新 main HEAD：`72e9030502f090b93b91ea21349790007e3cd110`。
- 正式首頁 SHA 仍為 `bf853317df07920d4a91db7103c2f95b0a1ed725`；WR SHA `4b18a156805f19521356a247e7e11f1cfacbded6`；Manifest SHA `6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`；週一母版 SHA `0ea4775c5d15899a1e0b0a97c78744d90b8fff22`；週二至週五母版 SHA `e5976190efd4c7fcc92cd623bfa94926997cc672`。以上均保持不變，首頁未發布。
- FedWatch 時間說明：08:21 是初次擷取，10:05 是再次直接讀取複核，非時間戳矛盾；但來源頁最新快照仍延遲約 45 小時，必須繼續標示為延遲快照，不得稱即時數據。
- Brent Dec26 合約已交叉核實並更新預覽說明。CNN Fear & Greed 本輪使用備援來源；白銀合約月份仍標示待核。故本輪 QA 狀態為：**結構、三種尺寸版面、已存在互動控制、部署 URL 通過；母版 plus 規格缺口及部分行情來源時效／合約資訊仍待處理。** 正式首頁仍未發布。


## 18. 白銀 Dec26 合約核實與第二次預覽部署（2026-11-02）

- 已核實 Investing.com 香港站 2026/10/30 白銀歷史列為 US$49.276、-5.93%，合約頁標示 2026 年 12 月（SIZ6）；合約清單 Dec26 行亦為 49.276、-3.104、-5.93%。故白銀月份待核已解除。
- 更新 preview 內容僅限貴金屬卡：meta 行改為黃金 GCZ6／白銀 SIZ6 均為 2026 年 12 月合約；白銀列標示 SIZ6（2026年12月）；來源區加入 Investing.com 香港站白銀歷史資料及合約清單連結。未改價格、漲跌幅、CSS、JS 或 DOM 結構。
- 預覽更新 commit：`277927f485e651f100bf3c4b7eb734df0e803d36`；新 preview blob SHA：`3f13e08722c02952e84e050ecd35e0495c5ae0f5`。
- 新 Structural Gate run `41378735011` success，Playwright 三種 viewport regression success；Pages deploy run `41378810037` success。部署後 smoke test 再次確認 `https://lion-invlab.github.io/preview/2026-11-02.html` 回傳 HTTP 200，且週一專屬兩個上週行事曆區塊存在。
- 正式首頁 SHA 仍為 `bf853317df07920d4a91db7103c2f95b0a1ed725`，未發布。最新 main HEAD（本節寫入前）為 `277927f485e651f100bf3c4b7eb734df0e803d36`。
- 本次解除白銀合約月份待核。仍待處理：FedWatch 原始快照延遲約 45 小時，CNN Fear & Greed 本輪使用備援來源；正式母版本週經濟 plus 控制缺口與產業 disclosure 桌面／平板 30px 問題依既有母版保護限制保留為警告。正式雙母版、Manifest、WR、首頁均未修改。


## 19. FedWatch 最新來源再核（2026-11-02）

- 再次查詢 Investing.com Fed Rate Monitor，2026/12/09 會議仍顯示維持 3.75%–4.00% 為 30.2%、升至 4.00%–4.25% 為 69.8%；頁面更新時間仍為 2026/10/31 00:35 EDT。
- 這確認本報告標示「延遲快照」是正確的；沒有新原始頁面數值可替換，不得將第三方頁面的 73% 或其他不同口徑數字替代 Investing.com。
- 本次只做來源核對，沒有修改 preview 或任何 GitHub HTML。下一輪若頁面更新時間推進，再重新讀取原始頁面並記錄新的台灣時間。


## 20. 2026-11-02 審核核准、正式首頁發布與部署狀態（本節優先於舊節）

最後更新：2026-11-02（Asia/Taipei）
- 本節是 2026-11-02 當日最新狀態；第 11–19 節中「正式首頁未發布」、「Pages URL 未驗證」等內容均屬當時歷史紀錄，若與本節衝突，以本節為準。
- 使用者已審核並明確核准 2026/11/02 週一早報上傳首頁。
- 預覽檔：`preview/2026-11-02.html`；目前回讀 blob SHA：`a206e668944f5c617cc4282516ea53a78b25845e`。
- 正式首頁：`index.html`；目前回讀 blob SHA：`0802cd3d9d014bc9d31a507562eea5d09b34e561`。該內容與核准預覽版的報告內容一致。
- 首頁更新 commit：`1a5d2b747d19148867f847873dd6598cdbecac09`。
- 因原 Pages workflow 沒有由單獨的 index.html 更新觸發，已在預覽加入不渲染的 HTML 註解觸發既有驗證／部署鏈；觸發 commit：`b46d50c4ecdd5a1861d5278ace559a292bd6b8d5`。
- Structural Gate run `41381264105`：completed / success。
- Pages deploy run `41381338839`：completed / success；部署 head SHA 與觸發 commit 一致。Deploy job 的 canonical preview URL verify step 已成功。
- 預覽網址：https://lion-invlab.github.io/preview/2026-11-02.html
- 正式首頁：https://lion-invlab.github.io/
- 本次部署成功不等於消除所有既有母版／視覺規格警告，也不代表所有市場來源永遠即時；未實測項目仍依 QA 證據揭露。
- 重要工作決策、修改及部署紀錄已新增至根目錄 `TAC_WORK_LOG.md`；建立 commit：`367527ee7eeb85564a2739f71d00543842723a55`。
- 接續優先事項：修正 Pages workflow，使經使用者核准的正式首頁更新能可靠觸發既有驗證與部署；避免未來再依賴修改預覽檔註解的臨時觸發方式。保持報告內容與核准母版不變，先分析 workflow 的最小修正方案。
- 本次工作沒有修改 WR、Manifest、雙母版或行事曆資料庫；僅依使用者核准更新正式首頁，並更新預覽觸發註解及工作紀錄／狀態檔。


## 21. 2026-11-02 每日產製規格固定化與排程健檢
- 正式規則已更新為 WR v4.1（排程規格繼承與單一流程版）；最新規則要求 03:30 只維護週資料庫，05:00／05:25 共用同一份產製流程並依 EDT／EST 分流，所有內容規格繼承 main 最新 WR。
- 已修正 05:00 夏令時間排程 prompt：刪除與現行 WR 不一致的舊 CME-only FedWatch 規則，改為明確服從最新 WR；保留 EDT 才執行、EST 不執行的條件。排程仍啟用，時間未變。
- 03:30 行事曆資料庫排程已確認使用 data/calendar/weeks/YYYY-Www.json，且只寫入週 JSON；目前啟用。
- 05:25 冬令時間排程目前啟用，prompt 與 WR v4.1 的資料路徑、FedWatch 及審核版／核准閘門一致；下一個台灣工作日目標為 2026-11-03 05:25。
- 05:25 最近一次 last_run 記錄為 failed，但工具回傳的 latest_result 是較早 run 的舊結果，無法據此判斷這次失敗根因；需在可取得該次執行錯誤詳情後再定位。不能宣稱排程錯誤全部修復。
- 三個排程均沒有授權自行更新首頁；05:00／05:25 只產出 preview/YYYY-MM-DD.html。11/02 早報已核准發布的狀態仍依第 20 節記錄。
- 未修改 Manifest、雙母版、行事曆 JSON、preview 或 index.html。Pages workflow 正式首頁發布觸發缺口仍待獨立修復。
- 工作紀錄：TAC_WORK_LOG.md 已新增本次排程查核及 WR v4.1 變更。


## 22. 2026-11-02｜目前交接狀態：WR runtime lock PR #270
- 目前工作分支：`fix/tac-wr-runtime-lock-20261102`；PR #270 尚未合併，main 仍維持 WR v4.2，分支內 WR 為 v4.3。
- PR 內容：WR v4.3 執行鎖規則、`scripts/tac_wr_lock.py`、Structural Gate lock + artifact、snapshot schema 動態版本與 SHA provenance、三個排程 prompt 更新、Pages workflow lock 與 index.html 部署觸發修正。
- 三個 Automations ID：03:30 `6ae6dff2200c81919ba2cee4db78f8a5`、05:00 `6ad9e48c33c081918a32b34fa3bb9e9c`、05:25 `6ae1819903348191951f91de2b2e0591`；均已回讀確認啟用，且 prompt 含 WR 最新版本鎖定要求。排程時間未變。
- 目前 PR head SHA：`626058495a6910e58b8d9f52284c05a94b0d4140`。最新 Structural Gate run `41385521727`：lock、artifact、Python self-test、snapshot schema／assembler、母版欄位與 HTML binding、行情 collector、DOM contract 已通過；Playwright 尚待完成。Mother Template Guard run `41385521784` success。
- 重要限制：prompt 更新成功不等於排程實際執行成功；WR v4.3 尚未進 main；main 最新 WR 仍是 v4.2，直到 PR 合併。歷史 W45 `wr_version=3.12` 不應回填。
- 下一步：取得 run `41385521727` 最終結果與 lock artifact；修復任何失敗；通過後合併 PR #270，確認 main WR v4.3 及 workflow 觸發；再驗證 Pages 部署鏈及下一次排程產線確實回報相同 WR lock。


## 23. 2026-11-02｜目前交接狀態：WR v4.3 已合併
- main 正式 WR：v4.3；blob SHA `45da40e9350d1fbb9f7660f2f28d9e46ed278678`。
- PR #270 已合併，merge commit `798219a4813d3292780b9104302793e44590f791`。
- 統一鎖定工具：`scripts/tac_wr_lock.py`。Structural Gate 與 Pages workflow 均在執行時建立 WR lock，記錄版本、commit SHA、blob SHA、內容 SHA-256；CI lock artifact 已成功上傳。
- PR Structural Gate run `41385521727`：completed / success；所有資料 schema、assembler、母版 binding、行情 collector、DOM contract、Playwright steps 完成。Mother Template Guard run `41385521784` success。
- 三個排程仍啟用，prompt 已加入每次讀取 main HEAD + WR 的版本鎖定：03:30 `6ae6dff2200c81919ba2cee4db78f8a5`、05:00 `6ad9e48c33c081918a32b34fa3bb9e9c`、05:25 `6ae1819903348191951f91de2b2e0591`。03:30 會更新行事曆 JSON 既有 `wr_version` 欄位為當次 lock 版本；歷史 audit 不重寫。
- Pages 部署鏈已修正：Structural Gate 納入 index.html；Pages 在 gate 成功後可部署 preview 或正式首頁，並驗證通用 TAC 核心區塊。未因本次 workflow 文件更新而發布任何報告內容。
- 保護檔案：index.html、雙母版、Manifest、W45 JSON 均未修改。W45 現存 `wr_version=3.12` 是歷史執行版本，下一次 03:30 維護時才應更新為 v4.3。
- 尚待驗證：合併後 main push 的獨立 Structural Gate／Pages workflow_run 最終結果；下一次 03:30 與 05:25 排程是否真的輸出一致 WR lock。不得把 PR 測試成功等同排程端到端已驗證。


### 追加狀態｜WR lock 後續強化（2026-11-02）
- `scripts/tac_wr_lock.py` 已加入台灣時間欄位 `locked_at_taipei`，同時保留 UTC。
- 快照產生／驗證改為優先讀取 `TAC_WR_LOCK_FILE` 中的 active lock 版本與 SHA，不再以 checkout 工作樹版本覆蓋 lock；沒有 lock file 時才使用當前 checkout 的 WR 版本。
- 最新程式 commits：`b268cfc3b51cc9c7a732c98a712cf336b84afb04`、`23cb4986e3be0ebd35befafcb57ea3bf7b8169a7`。兩筆已在 main，但對應 post-merge Structural Gate run 尚未取得可核實狀態。
- 下一步優先取得這兩筆 main 更新的 CI 執行結果；不可把 PR #270 的通過結果當成後續 main refinement 已測通。

- 追加防漏：正式快照組裝器 `scripts/assemble_tac_daily_snapshot.py` 已要求 `TAC_WR_LOCK_FILE`，缺少 active lock 不會產生正式快照；self-test 不受影響。Pages workflow 的手動部署現在也必須執行部署後 URL 驗證。
- 新 commits：`6ca519a0801a1f5471883649ec219f3bb6d42d41`、`9cc5a10e38c59e98bcbf62b774d5455e6bcf751e`、`cd23d81b20c0a20c0ba609ba7d7952cad3d89f37`。這些 post-merge main commits 的 Structural Gate 最終狀態尚未取得。

- 驗證限制補充：PR run `41385521727` 的 Playwright step 因 PR 沒有 dated preview 變更而跳過，僅 workflow step 成功結束，沒有執行新報告的實際視覺比較。


---

# 12. 2026-11-04｜WR v5.1 自動化殘留核對與接續錨點（最新優先）

> 本節是 2026-11-04 的最新交接狀態；若與上方第 1–11 節的舊歷史描述衝突，以本節、main 最新 WR v5.1、Manifest 及即時 GitHub 狀態為準。舊節保留作歷史，不得照舊啟動已退役流程。

## 12.1 最新基線（2026-11-04 回讀）
- Repository：`lion-invlab/lion-invlab.github.io`，branch：`main`。
- 本次核對時 main HEAD：`8abec31cb1440de973f840b034830bf4bc538028`。
- 正式 WR：`TAC_WORK_RULES.md` v5.1；blob SHA：`daadc59c0b5043e2c38e6cc3b83fc205160d3177`。
- 本狀態檔修改前 blob SHA：`2eb4b767392713937bc5d94544a1fc91b328a296`。
- Manifest：`母版專區/mother-template-manifest.json`；blob SHA：`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`。
- 唯一 QA 清單：`母版專區/母版結構驗收清單.md`；blob SHA：`d2d90c990972f117414e169b07e1df69f79c49aa`。
- Manifest 仍鎖定週一母版 SHA `0ea4775c5d15899a1e0b0a97c78744d90b8fff22`、週二至週五母版 SHA `e5976190efd4c7fcc92cd623bfa94926997cc672`；本輪未修改母版或 Manifest。

## 12.2 WR v5.1 現行生產原則（覆蓋舊版排程／管線描述）
- 每日早報由 ChatGPT 單一執行者直接完成；使用者提出需求時開始，不設早報或行事曆資料庫自動排程入口。
- 行情直接查核並填入核准母版；行事曆只使用 `data/calendar/weeks/YYYY-Www.json`。
- 不以 WR Lock、Issue #319 relay、Snapshot、Assembler、Renderer、Collector、Orchestrator 或 GitHub Actions 成功作為早報生產前置條件。
- 舊 Snapshot、lock、workflow artifact、collector、assembler、renderer、validator 及歷史流程程式僅供歷史資料／必要回查，不得冒充當次資料或正式生產前置。
- 每日交付仍須寫入並回讀 `preview/YYYY-MM-DD.html`，完成資料與內容、母版結構、互動、視覺四類 QA；未實測項目標示未測試。
- 正式首頁 `index.html`、雙母版、Manifest 仍屬保護範圍；正式發布必須經使用者明確核准指定預覽版。

## 12.3 本輪已核對的 workflow 與執行證據
- main 的 `.github/workflows/` 目前有 8 個檔案：`archive_index.yml`、`company_nasdaq100.yml`、`company_profiles.yml`、`company_profiles_nasdaq100.yml`、`main.yml`、`mother-template-guard.yml`、`pages.yml`、`volatility-sticky-columns.yml`。
- `tac-report-validation.yml` 不在目前 workflow 目錄；TAC Daily Report Structural Gate 已退出目前 workflow 清單。
- 2026-11-04 的歷史 run 顯示 Structural Gate 曾多次失敗；之後 Pages workflow 與已退役 Gate 脫鉤。Pages 最新相關 run 成功只證明部署工作成功，不代表早報內容／視覺 QA 通過。
- Mother Template Guard run `41774120466`（run #194，commit `8abec31cb1440de973f840b034830bf4bc538028`）成功；jobs 顯示週一母版、週二至週五母版、週末拒絕、Manifest SHA 篡改拒絕、日期檢查均成功。這是母版保護測試，不是每日預覽驗收。
- Pages run `41772569357`（run #1383）成功；部署成功不等於報告內容正確。
- Pages run `41754765860` 的 event 為 `workflow_run`，結論 `skipped`；兩個部署 jobs 均 skipped。不得把 skipped 當成部署成功。

## 12.4 已讀取程式及已確認依賴
- `scripts/assemble_tac_daily_snapshot.py`（blob `d7877a0541c6355fef702bfe56a8dc09a8a79851`）：匯集 source fragments，明確不抓行情、不編輯 HTML；import `validate_tac_daily_snapshot.py` 的 validator 與 sample snapshot。
- `scripts/validate_tac_daily_snapshot.py`（blob `d5f63940a5ff412b7d831a9fbac7e11c449e8daa`）：使用 `tac_wr_lock.py` 讀取 WR 版本／lock，驗證 snapshot provenance 與 schema。
- `scripts/tac_wr_lock.py`（blob `8e3734a5d60ca274aa663ec65d277a3843f4b2cc`）：解析 Git ref 的 WR 版本、commit、blob SHA 與內容 hash；屬舊 lock 流程工具。
- `scripts/render_tac_market_snapshot_to_html.py`（blob `b920e0e64efcc082975dfb3318376885d81817db`）：只負責市場 snapshot 欄位綁定；檔頭明確聲明不是完整審核版 renderer，新聞、分析、經濟與財報行事曆需其他輸入／後續階段。
- `scripts/ingest_tac_snapshot_comment.py`（blob `b2ce160766c8ef4549b77ba0640073537119a0b7`）：驗證 Issue #319 的認證 snapshot handoff 與 WR lock 欄位，屬舊 handoff。
- `scripts/validate_tac_report.py`（blob `919a9270feda2b0e86b6e5d1a6fa8a97960a28b5`）：舊結構驗證器；會呼叫 `validate_mother_template.py`、`validate_tac_layout_contract.py`、`validate_tac_market_mapping.py`；自身聲明不驗證行情正確性或視覺。
- `scripts/validate_tac_layout_contract.py`（blob `aa6fee03cc2c8e609236a1f24973922516fd4e45`）：唯讀 DOM 結構／動態卡片契約檢查。
- `scripts/validate_tac_market_mapping.py`（blob `4f6d8c34f3ea50975a5fc000b0fb701808effa77`）：唯讀市場欄位／列數檢查；輸出明確限定為 structure only，不驗證報價日期或來源。
- `scripts/validate_tac_html_binding.py`（blob `3f2fc593e3b3b60e44e5d6196929a9c0bd7c3af9`）：檢查雙母版 snapshot-to-DOM binding slots。
- `scripts/tac_browser_layout_regression.mjs`：Playwright 瀏覽器比較工具，檢查 1440／768／320 視窗、區塊幾何、部分 computed styles、overflow、details、radio tabs、內部連結及部分加號尺寸；目前沒有接入現行 workflow。已知目前程式對本週經濟 plus 與 sector plus 的母版既有尺寸缺陷只輸出 WARN，不會 fail，因此其 PASS 不代表所有 plus 規格均符合。
- `scripts/capture_tac_fedwatch_fallback.mjs`（blob `23b60139f466fe771e4fc08c2210965f9cfe3b65`）：只讀 Investing.com Fed Rate Monitor fallback capture；明確標記 fallback only，不是 CME；目前未證實接入正式 workflow。

## 12.5 交叉引用掃描結果與限制
- 已檢查現行 8 個 workflow、主要 TAC scripts 及部分文件的文字引用。
- 可確認的程式內直接依賴：Assembler → Snapshot validator → WR lock；Report validator → Mother template validator、Layout contract validator、Market mapping validator。
- `TAC_WORK_LOG.md` 仍有歷史引用 Assembler、WR lock、Snapshot validator；屬工作歷史記錄，不代表目前生產呼叫。
- GitHub code search connector 對這些精確檔名未回傳可用結果；因此本輪不能宣稱完成整個 repository 所有 189 個檔案的全面依賴掃描。尚未逐一讀取的其他測試、資料、設定及所有文件引用，仍列待核實。
- 沒有證據顯示現行 8 個 workflow 會呼叫 Snapshot／Assembler／Renderer／WR Lock；但也未把所有 repo 內可能的非 workflow 呼叫入口完全排除。

## 12.6 本輪修改與保護狀態
- 本次只更新本狀態檔作為交接錨點；沒有修改 WR、Manifest、雙母版、`index.html`、每日 preview、行事曆 JSON、workflow 或任何生產程式。
- 更新前狀態檔 blob SHA：`2eb4b767392713937bc5d94544a1fc91b328a296`。
- 本次核對／更新前 main HEAD：`8abec31cb1440de973f840b034830bf4bc538028`。
- 更新後 commit SHA：`29299c2b2fec2e95feb0ce2c8e76baeb37b10573`；更新後狀態檔 blob SHA：`bfae7cbd7d766287ccb93e7ce897ea4aa07c4d26`。已重新 fetch 回讀，確認第 12 節存在且內容完整。

## 12.7 下一步唯一工作位置
1. 完成尚未覆蓋的 scripts／tests／config／docs 依賴引用掃描，特別確認舊 snapshot／lock／renderer 有沒有非 workflow 的呼叫入口。
2. 依證據把程式分類為：仍獨立使用（保留）、歷史參考（保留但不得作生產前置）、疑似可停用（只列建議，不自行刪除）。
3. 檢查目前正式 preview／每日早報工作是否需要任何這些舊工具；依 WR v5.1 原則不把它們重新接回生產流程。
4. 除非發現明確、已證實的依賴或安全問題，否則不刪除程式、不重構 workflow、不改 WR／母版／Manifest／首頁。
5. 每完成一個階段，立即更新本狀態檔的本節，記錄路徑、SHA、證據、未測試項目及下一步，避免跨對話重複核對。

## 12.8 狀態標籤
- 已完成：本節列明的 WR、Manifest、QA 清單、workflow 目錄、指定程式及指定 Actions run 已讀取。
- 待核實：完整 repo-wide 依賴引用掃描、其他 scripts/tests/config 的間接呼叫、browser regression 工具的實際執行證據。
- 未測試：本輪未執行任何舊工具的 self-test、未執行 Playwright browser regression、未對當日 preview 做 QA。
- 未修改：除本狀態檔外，所有正式／生產資產均未修改。


## 12.9｜階段 3 補充：剩餘 scripts 分類（2026-11-04）
- 已補讀其餘主要 scripts 的檔頭／用途，並對照目前 workflow：
  - **獨立保留，不屬 TAC 早報產線：** `update_data.py`、`update_tac_watchlist.py`（S&P 500／TAC watchlist volatility 資料）；`update_nasdaq100.py`（Nasdaq-100 volatility）；`update_profiles.py`、`update_nasdaq100_profiles.py`、`validate_profiles.py`（公司資料檔維護與驗證）；`test_volatility_sticky_columns.mjs`（volatility.html 的 Chromium／WebKit 欄位固定測試）。相應 workflow 已存在且與早報分離，保留。
  - **母版保護必要工具：** `validate_mother_template.py`，由 `mother-template-guard.yml` 使用，屬現行保留工具。
  - **歷史／非正式早報前置：** `fetch_tac_global_indices.py`、`fetch_tac_sector_etfs.py`、`fetch_tac_treasury_yields.py`、`fetch_tac_treasury_fred_fallback.py`（舊行情擷取器）；`validate_tac_key_levels_daily.py`（Yahoo Finance key-level CI artifact）；`capture_tac_fedwatch_fallback.mjs`（Investing.com FedWatch fallback capture）；Snapshot／Issue #319 handoff／Assembler／Renderer／WR lock／相關 snapshot validators。依 WR v5.1，不作每日早報前置，不重新接回產線。
  - **獨立但目前未證實有排程入口：** `tac_browser_layout_regression.mjs`。它有實際瀏覽器檢查能力，但沒有現行 workflow 呼叫；不能宣稱每日執行。
  - **仍在使用：** `validate_mother_template.py`；`validate_tac_report.py` 及其 layout／market mapping validators 保留在 repo 作歷史或手動診斷用途，但其目前無 workflow 呼叫證據，且不作正式日報 Gate。
- Workflow 直接呼叫關係（依已讀取 YAML）：`main.yml` → `update_data.py`、`update_tac_watchlist.py`；`company_nasdaq100.yml` → `update_nasdaq100.py`；`company_profiles.yml` → `update_profiles.py)、`validate_profiles.py`；`company_profiles_nasdaq100.yml` → `update_nasdaq100_profiles.py`；`mother-template-guard.yml` → `validate_mother_template.py`；`volatility-sticky-columns.yml` → `test_volatility_sticky_columns.mjs`。Pages／archive workflow 與 TAC Snapshot 工具無直接依賴。
- 本輪確認的歷史工作程式依賴鏈：`assemble_tac_daily_snapshot.py` → `validate_tac_daily_snapshot.py` → `tac_wr_lock.py`；`validate_tac_report.py` → `validate_mother_template.py`、`validate_tac_layout_contract.py`、`validate_tac_market_mapping.py`。以上只說明程式內依賴，不代表現行生產呼叫。
- **掃描邊界：** 已讀取 8 個現行 workflow、主要 TAC scripts（包含上述檔案）及 TAC 規則／工作紀錄／母版驗收文件；沒有逐一讀取 repo 全部 189 個 blob，也未對所有 HTML、JSON、資料及歷史 demo 做全文掃描。因此「完整 repo-wide 零引用」仍不可宣稱。
- **結論：** 現行每日 TAC 早報不需要舊 Snapshot／Assembler／Renderer／WR Lock／Issue relay；依 WR v5.1 保持直接製作。獨立 Dashboard 與母版保護 workflow 保留。無刪除建議可在未完成全面依賴掃描前執行。

### 階段 3 狀態
- 已完成：現行 workflow 直接呼叫盤點；主要 scripts 的用途分類；已知 Python／Node 直接依賴鏈；過期狀態檔已更新。
- 待核實：repo 其他未讀取的 HTML／JSON／歷史文件是否仍有僅供參考的字串引用；非 workflow 的外部手動呼叫／排程系統是否存在。
- 未測試：本輪未執行舊工具 self-test、Playwright regression 或每日 preview QA。
- 未修改：除 `TAC_SESSION_STATE.md` 外，未修改任何 scripts、workflow、資料、preview、母版、Manifest 或首頁。


## 13. 2026-11-04 審核版 QA 證據核查（續查）

核查基準：main 最新 WR v5.1（blob SHA `daadc59c0b5043e2c38e6cc3b83fc205160d3177`）、Manifest（`6f1fb4d3b350961c3adb28e7ff2f9dd4932e560e`）、QA 清單（`d2d90c990972f117414e169b07e1df69f79c49aa`）。本節只記錄檢查結果；未修改每日預覽、母版、Manifest、WR、首頁、資料庫或工作流程。

### 13.1 審核版檔案存在與母版來源
- `preview/2026-11-04.html` 存在於 main，blob SHA：`1358a0e5d75fa320cc67440424a4403ca7631d02`，405,210 bytes；title 為 2026/11/04（三）審核版。
- 依星期應使用 Tue–Fri 母版。Manifest 登記路徑及 SHA 與 main 實際母版相符：`母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html`，SHA `e5976190efd4c7fcc92cd623bfa94926997cc672`。
- 靜態 ID 比較：母版 174 個 ID（173 個唯一），預覽 175 個 ID（174 個唯一）；母版 ID 集合沒有缺項，預覽新增 `tac-news-title-summary-hierarchy`。兩份文件均含一個重複 ID `tac-toolbar-bubble-preview-v1-js`，屬共同既有問題，不能算作預覽新增。此結果僅為 ID 集合檢查，不等同完整 DOM 差異驗收。
- 「上週經濟行事曆／上週財報行事曆」文字出現在母版規則註解及 CSS 註解；僅憑全文字串搜尋不能判定頁面實際顯示。需另對可見 DOM／導航做驗證，不把註解命中誤報為頁面顯示錯誤。

### 13.2 四類 QA 證據狀態
- **內容／資料 QA：未完成證據核對。** 預覽警示標示行情 40/44 項已核實、WTI／Brent／GC／SI 待核實；本次尚未逐項重查來源及行事曆／新聞／財報內容，因此不把頁面自述當成獨立驗證。
- **母版結構 QA：部分靜態檢查，整體未通過／未完成。** 核准母版 SHA 本身正確，且 ID 集合沒有缺項；但尚未完成清單 J 所要求的完整結構差異稽核、卡片欄位與連結逐項驗收。ID 比較不是完整結構驗收。
- **互動 QA：未測試。** 本次沒有對 11/04 預覽執行真實瀏覽器點擊、tabs、收折、導航及連結操作。
- **視覺 QA：未測試。** 本次沒有對 11/04 預覽執行桌面、常見手機及 320px 實際瀏覽器截圖比對。

### 13.3 Actions 證據裁決
- Run `41755764881`（TAC Daily Report Structural Gate，commit `b81c72c0de2d01b4f1c923a46f6b009607b6109b`）雖顯示 success，但該 run 鎖定 WR v4.19；`validate_tac_report.py --changed-only` 日誌明確輸出「SKIP: no dated report changed in this commit/PR; historical previews are not revalidated」。
- 同一 run 的 Playwright Chromium 安裝與 desktop/mobile regression 步驟均為 skipped；`artifacts/tac-layout/` 沒有檔案可上傳。故該 run 不能證明 11/04 預覽通過結構、互動或視覺 QA。
- Run `41774120466` 的 Mother Template Guard success 只驗證核准母版／Manifest 規則；Run `41772569357` 的 Pages success 只證明部署步驟成功。兩者均非每日預覽 QA 證據。
- 11/04 預覽頁尾聲稱「桌面視覺與互動 QA 完成」，目前未找到對應執行紀錄或截圖支持；此聲明應視為**未有證據支持**，不得當作通過。320px 行動版則明確標示未測。

### 13.4 本輪結論與限制
- 目前可確認預覽存在、日期正確、週別應用母版路徑正確且核准母版 SHA 相符；不能據此推定每日內容、結構、互動或視覺 QA 全數通過。
- 本輪只讀取了主要規則、QA 清單、Manifest、指定母版、指定預覽及相關 Actions runs/jobs/logs；未檢查全 repo 每一個檔案，也未對預覽執行瀏覽器測試。
- 本次沒有修改任何正式資產或預覽，亦未發布首頁。後續若要把頁尾 QA 聲明改為符合證據的狀態，必須先完成實際測試並依 WR v5.1 做最小差異更新與回讀；本次不擅自修改預覽。


## 14. 2026-11-04 線上預覽桌面瀏覽器實測（續查）

測試對象：`https://lion-invlab.github.io/preview/2026-11-04.html`。使用 TinyFish 真實瀏覽器於約 1353px 桌面 viewport 執行，Run ID：`209e351d-bdec-44d8-a6be-71f4c4c94143`，結果 completed。此測試只操作公開預覽頁，未修改任何內容。

### 14.1 實際執行與結果
- 頁面載入成功；顯示 2026/11/04（三）審核版及行情基準日 2026/11/03。
- 10 個導覽項目可見；抽測市場情緒內部錨點可正常平滑跳轉。
- 實際點擊經濟 QRA 卡片及 Novo Nordisk 財報卡片，兩者均可展開及再次收折。
- 實際切換 FedWatch／FOMC 兩活頁，成功；切換今日觀察「今日關鍵價位／今日核心觀察」，成功。
- Q4 精選基金彈窗的 × 關閉按鈕可用。
- 桌面約 1353px 未觀察到水平溢位或內容裁切；測試涵蓋上述指定互動，不代表所有互動元件逐一測試。
- 實際可見導覽只有「本週經濟行事曆」及「本週財報行事曆」；頁面沒有顯示「上週經濟行事曆」或「上週財報行事曆」。此前原始碼全文搜尋命中是註解／CSS 註解，不是可見頁面區塊。
- 側欄歷史日期輸入框預填 10/16/2026，與報告日期不同；尚未確認是否為刻意示範預設值，列為待核實，不直接判定故障。

### 14.2 QA 狀態修正
- **桌面互動 QA：抽樣通過。** 本節 Run ID 提供實際點擊證據；不擴大宣稱所有控制均已逐一測試。
- **桌面視覺 QA：部分觀察通過。** 確認桌面載入及主要版面無明顯溢位／裁切；尚未完成與母版逐區截圖比對，因此整體視覺回歸仍未完成。
- **320px 行動版：未測試。** 本次瀏覽器工作流程沒有實際執行 320px viewport 測試；不得沿用桌面結果推定手機通過。
- **內容／資料 QA：未完成。** 本次是 UI／互動實測，不是行情、新聞、行事曆與財報逐筆來源核實。
- **母版結構 QA：未完成。** 可見導覽與部分互動實測不能取代完整 DOM／卡片／差異清單。

### 14.3 頁尾聲明裁決
預覽頁尾原文「桌面版與互動 QA 完成」較本次證據範圍更廣：桌面指定互動抽測已有支持，但完整桌面視覺回歸及所有互動元件並未逐一完成；320px 明確未測。故此頁尾整體 QA 完成聲明仍屬過度概括，尚不應據此宣稱四類 QA 完成。本次未修改預覽頁尾，避免未經完整 QA 就改寫審核版。

### 14.4 執行限制
嘗試以本機 Chromium CLI 另做 320px 載入時逾時，未取得頁面或截圖；因此 320px 仍記「未測試」，不將逾時解讀為版面失敗。未修改預覽、母版、Manifest、WR、首頁或工作流程。


## 2026-11-05｜11/05 審核版新增「專題報導」工具入口

- 任務：依使用者確認的專題報導工具欄試作，將「專題報導」新增為今日審核版側邊工具欄第四個同層級入口。
- 修改檔案：`preview/2026-11-05.html`；僅在既有 `<aside class="tac-side-tools">` 中，於歷史早報日期快捷區後、工具欄 footer 前新增一個沿用 `tac-side-link`／`tac-side-icon` 的連結項目。
- 目的地：`https://lion-invlab.github.io/preview/special-report-tools-preview.html`；使用新分頁開啟（`target="_blank" rel="noopener"`）。
- 寫入前 preview blob SHA：`a235ca869a308e30607dcfce67928f992f0d3803`。
- 寫入 commit：`d26326c9b9d19806c03089ad68ed910ff356a8fb`；寫入後回讀 preview blob SHA：`a32f3dc3d672a79edff72e5da0e750b38b603147`。
- 專題索引試作檔 `preview/special-report-tools-preview.html` blob SHA：`84efea25ba41eb35e9eaece2253c6f768e6bcdb6`。
- 回讀確認：新增入口文字僅出現一次、href 正確；沿用既有工具欄樣式，不新增 CSS／JS，不改變原有歷史早報日期快捷功能。
- 保護檔案確認：`index.html` 回讀 SHA 仍為 `a235ca869a308e30607dcfce67928f992f0d3803`，且不含新入口；雙母版、Manifest 未修改。
- 驗收狀態：GitHub 檔案寫入及回讀已完成；靜態檢查確認側欄新增項目與目的地正確。真實瀏覽器點擊、不同 viewport 視覺／互動及 Pages 線上實際載入本次未測試，不宣稱完整 QA 通過。
- 下一步：交付 11/05 審核版供使用者檢視；未經使用者核准，不更新正式首頁。專題索引頁仍為獨立試作，不代表已建立正式根目錄專題入口。
