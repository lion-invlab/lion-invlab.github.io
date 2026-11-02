# TAC 投資早報｜工作狀態錨點

> 本檔用途：跨對話延續 TAC 工作的唯一狀態摘要。它不是 Work Rules，不取代 `TAC_WORK_RULES.md`、Manifest、母版或 QA 清單。
> 每次接續工作，必須先讀取 main 最新版 `TAC_WORK_RULES.md`、本檔及 `母版專區/mother-template-manifest.json`，再以 GitHub 實際狀態校正本檔；若本檔與正式檔案或 GitHub 現況衝突，以正式檔案及即時 GitHub 狀態為準。

- 最後更新：2026-11-02（台灣時間；建立時）
- Repository：`lion-invlab/lion-invlab.github.io`
- 基準分支：`main`
- 正式規則：`TAC_WORK_RULES.md` v4.0
- 本檔定位：工作交接／進度錨點；不得據此推定任何功能已完成或任何預覽已通過 QA。

## 1. 目前主線目標

完成 TAC 投資早報 R3 可重複、可靠的每日審核版產製流程。近期最直接的工作目標是完成並驗收 2026-11-02（週一）早報獨立審核版；不是直接發布正式首頁，也不是擴大重構整套架構。

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
