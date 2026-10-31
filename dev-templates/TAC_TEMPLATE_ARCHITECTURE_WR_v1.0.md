# TAC 動靜態分離版｜專案專屬工作規則（WR）

**文件版本：** v1.0-DRAFT  
**專案名稱：** TAC 動靜態分離母版架構  
**專案代號：** `TAC-Template-Architecture`  
**適用分支：** `tac-template-architecture`  
**適用目錄：** `dev-templates/`  
**參照正式規則：** repo 根目錄 `TAC_WORK_RULES.md` v3.4（2026-10-31）  
**文件狀態：** 專案測試草案；尚未取得正式採用核准，不得視為已啟用的每日生產流程。

---

## 0. 文件定位、效力與優先順序

1. 本文件是 **TAC 動靜態分離母版架構專案**的專屬工程規則，處理固定版面與每日變動資料的分離方式、資料寫入邊界、結構保護、自動化測試及專案驗收。
2. 本文件參照根目錄正式 `TAC_WORK_RULES.md` v3.4。v3.4 是 TAC 投資早報正式生產規則及金融內容規範的唯一權威來源；本文件不取代、不複製、不修訂 v3.4。
3. 適用事項分工：
   - **金融內容與資料品質：** 完全遵守根目錄 WR v3.4，包括資料來源優先序、報價口徑、新聞真實性、行事曆分類、總結與圖釘評論、補漏閉環及交付要求。
   - **動靜分離工程實作：** 依本文件及本專案經驗收的 Slot Map、Selector Registry、Repeat Group Policy、結構指紋與測試程式執行。
   - **衝突處理：** 使用者最新明確指示優先；金融內容規則以根目錄 v3.4 為準；工程實作不得以技術便利為由違反 v3.4 或正式母版保護規則。發現矛盾先停止相關寫入並回報。
4. 本文件目前僅存在於專案測試分支的 `dev-templates/`，是專案規格草案，不是正式生產區第二份 WR，不得複製到根目錄、母版專區或其他正式位置，也不得宣稱已取代 v3.4。
5. 在使用者完成專案測試、驗收並明確核准前，本文件及現有候選規格**不授權**產生正式開發母版、啟用每日自動寫入、更新正式首頁或修改正式雙母版。

## 1. 專案目標與核心原則

### 1.1 目標

把 TAC 早報拆成兩種責任：

- **靜態層（Static Shell）：** 固定版面、DOM 骨架、CSS、JavaScript、導航、tabs、卡片結構、互動控制、收合功能、響應式規則及固定欄位。
- **動態層（Dynamic Data）：** 每日／每週需要更新的行情、漲跌、新聞、事件、財報、FedWatch、摘要、觀察與評論等經核實內容。

目標是讓每日更新器只處理核准的資料插槽，不再反覆重建或重寫整份 HTML，也不因更新資料而改變版面。

### 1.2 不可妥協原則

1. 固定的是結構與元件設計；變動的是經核實的資料內容。
2. **資料更新不是版面修改授權。** 不得因資料缺漏、筆數變化或程式方便而刪除、重排、簡化或重建固定元件。
3. 每個可寫入節點必須先列入明確 allowlist，包含模板情境、容器範圍、selector、允許更新的欄位及預期命中數。
4. 未列入 allowlist 的節點一律唯讀；selector 命中數不符、身份不明或父子關係不同，立即停止，不得猜測替代 selector。
5. 週一與週二至週五是兩份獨立模板，必須各自建基線、各自定位、各自驗收；不得把兩份 DOM 合併成一份假想共用模板。

## 2. 正式來源與檔案保護

### 2.1 正式母版來源

唯一正式結構基準仍是根目錄 WR v3.4 第 1 節及正式 manifest 登記的兩份母版：

- 週一：`母版專區/TAC_母版_週一_2026-10-28_最終定版.html`
- 週二至週五：`母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html`

每次工程測試開始前，必須重新讀取正式 manifest，核對兩份母版的路徑與 blob SHA。不得以專案分支中較舊的副本、歷史報告、預覽頁或其他 HTML 取代正式基準。

### 2.2 測試期間禁止修改

在專案尚未獲正式採用前，以下檔案一律視為唯讀：

- 根目錄 `TAC_WORK_RULES.md`（正式 v3.4）。
- `母版專區/TAC_WORK_RULES.md`（舊副本不具權威性）。
- 週一與週二至週五兩份正式母版。
- `母版專區/mother-template-manifest.json`。
- 正式首頁 `index.html`。
- 使用者已指定的每日預覽檔，包括 2026/11/02 預覽。

測試只可在 `tac-template-architecture` 分支及 `dev-templates/` 專案範圍進行。不得把整個測試分支合併至 `main`；日後如需採用，必須另提精確變更清單、差異檔案及驗收結果，經使用者明確核准後再按最小變更方式處理。

## 3. 三層資料與模板架構

### 3.1 第一層：正式靜態母版（唯讀基準）

- 保留完整 HTML、CSS、JavaScript、DOM、卡片、欄位、按鈕、tabs、收合、導航及響應式結構。
- 只作為結構基準與開發母版來源，不直接接受每日資料寫入。
- 正式母版 SHA 與 manifest 不符時，停止工作，不得自行更新 SHA 或另找替代版本。

### 3.2 第二層：開發母版（尚未建立）

- 必須由對應的正式週一或平日母版逐位元複製，再依已驗收的插槽設計標記動態欄位。
- 保留所有固定元件及其互動；清空動態內容時，也不得刪除必要卡片原型、欄位、收合控制或列表容器。
- 週一與週二至週五各有自己的開發母版，禁止跨模板複製不同的結構。
- 開發母版只有在所有必要插槽、資料群組、結構指紋、瀏覽器及手機測試通過，且使用者明確核准後，才可進入採用評估。

### 3.3 第三層：每日資料集與更新產物

- 每次報告先產生可追溯的當日資料集，再依模板情境與 allowlist 寫入開發母版。
- 資料集應保留來源、原始網址、擷取時間、交易日期／事件時間、標的身份、單位及價格口徑等必要欄位；欄位定義依 v3.4 與各指標規範。
- 同一資料集應能重現該次輸出；不可在寫入 HTML 的過程中臨時猜值、改口徑或混用來源。
- 產物先寫入獨立日期預覽，不直接覆寫正式首頁或母版。

## 4. 每次更新的標準作業流程

每次更新必須依序執行，不得跳過前置閘門：

1. **讀規則與確認環境：** 讀取根目錄 WR v3.4、本文件及相關專案規格；確認分支、報告日期、台灣時區、週一／平日模板情境。
2. **核對基準：** 讀取 manifest，確認正式母版路徑與 SHA；檢查專案基線與核准版本相符。
3. **蒐集並核實資料：** 按 v3.4 完成行情、新聞、經濟／財報事件、FedWatch 及其他內容核實；未核實項目明確標記，不得進入正式資料欄位冒充有效值。
4. **建立資料集：** 將核實結果整理成明確欄位與 repeat-group 清單；每筆資料保留可追溯來源及時間口徑。
5. **插槽定位：** 依該模板的 selector registry 與 Slot Map 定位。每個 selector 必須驗證命中數、元素身份、祖先容器及欄位關係。
6. **套用資料：** 只更新 allowlist 中明確授權的文字、數值、連結及資料屬性；不得整段覆蓋固定容器。
7. **結構差異檢查：** 執行 HTML5 正規化 DOM 指紋、固定節點／屬性差異、ID／錨點及 repeat-group 骨架檢查。
8. **瀏覽器測試：** 驗證 tabs、details/summary、紅圓加號展開／收合、導航、連結與手機版幾何；桌面及 320px 手機寬度至少須有可重現測試。
9. **內容閉環：** 依 v3.4 每輪補漏閉環規則，核對行情與摘要／觀察、總結、市場情緒及行事曆資料一致。
10. **產出獨立預覽：** 僅寫入測試分支的獨立日期檔；確認檔案來源、差異範圍及部署狀態。
11. **逐項回報：** 區分已完成、測試通過、待核實、未測試及未通過；不得以寫入或 commit 成功代替內容與部署驗收。
12. **發布閘門：** 只有使用者明確核准，才可依正式 v3.4 的發布流程提出部署；本專案本身不授權發布。

任何步驟失敗，停止後續寫入與部署；修復後重跑受影響測試及必要的完整測試。

## 5. 動態插槽（Slot）管理規則

1. Slot Map 是插槽候選清單；只有已通過 DOM parser、selector 唯一性、父子關係及瀏覽器測試的項目，才能標記為「已驗收可寫入」。
2. 每個插槽至少記錄：
   - 唯一名稱與用途。
   - 適用模板（Monday / Weekdays / Both）。
   - 精確容器與 selector。
   - 預期命中數或合法筆數型態。
   - 可更新欄位與允許的屬性。
   - 明確禁止修改的欄位／祖先／同層控制。
   - 對應資料來源與內容驗收規則。
   - 測試案例及最後驗收版本。
3. Selector 必須以容器限定；禁止以全頁泛用 class（例如 `.row`、`.r`、`.newsitem`）直接進行全域寫入。
4. Selector Registry 中的命中數只用於確認母版定位，不得把母版當下的動態資料筆數當作每日目標、上下限或限制。
5. `protected_container_only` 的容器不得整段覆寫；若只完成容器定位、尚未完成內層欄位定位，仍屬不可寫入。
6. 候選 Slot 不等於寫入權限。任何新增、改名、擴大 selector 或改變允許屬性，都必須先修改規格、補測並保留變更紀錄。

## 6. Repeat Group（動態筆數群組）

### 6.1 動態群組

以下群組依真實事件或資料筆數增減，不設母版樣本筆數的目標、上限或下限：

- 本週經濟事件卡。
- 本週財報卡。
- 週一專屬的上週經濟事件卡。
- 週一專屬的上週財報卡。

母版目前看到的 12／16／3／7 張只是樣本數，不是每日更新限制。

### 6.2 固定結構

- 外層容器、status group、標題、tab radio／label／nav／panel、列表 wrapper、卡片欄位骨架、details/summary、紅色圓形加號／減號、來源收折、CSS、JavaScript 與 aria／互動屬性均固定。
- 新增卡片只能複製同一份正式母版、同一群組中的完整卡片原型；不得自行拼裝，也不得從另一模板搬用。
- 移除卡片只限資料核實後不應出現的事件；不得為湊足樣本數而補造事件或保留過期事件。
- 每張新增或保留卡片都須通過卡片骨架指紋；允許變動的僅限已登記資料欄位及明確允許的來源 href。

### 6.3 空狀態

- 列表與 empty-state 是不同的 status-group 變體，不等於單純把 repeat-group 筆數改為零。
- 只有同一模板、同一行事曆區塊已存在實際 HTML empty-state 原型，且驗證器已驗收時，才可切換。
- 不得只因 CSS 有 empty-state class 就自行拼裝節點；不得跨模板搬用 empty-state。
- 目前專案已確認：週一母版本週經濟／財報區塊有可測試的既有 empty-state 原型；平日母版本週區塊及週一上週區塊沒有同區塊原型，必須拒絕自動轉換。

## 7. 固定結構與資料寫入的明確邊界

### 7.1 一律固定、不得由每日更新器修改

- HTML 文件骨架、固定 ID、class、DOM 階層及固定節點順序。
- CSS、樣式值、字體、顏色、間距、尺寸、響應式規則及動畫。
- JavaScript、事件監聽器、tabs／radio／label 關係、details/summary、收合按鈕及導航。
- 卡片外框、固定欄位 label、來源收折區結構、aria 屬性及互動控制。
- 固定筆數行情列與產業 ETF 列的結構及順序規格。
- 週一／平日各自專屬或不存在的區塊差異。

### 7.2 僅在 allowlist 核准後可更新

- 已定位的文字、日期、數值、漲跌狀態、連結 href、來源顯示文字及明確登記的 aria-label／比例數值等資料屬性。
- Repeat Group 中，依已驗收規則新增／移除同模板、同群組的完整子項。
- 每個插槽實際允許的欄位，必須以 Slot Map 與 Selector Registry 的驗收狀態為準；不得因本節列舉就推定所有欄位已開放。

### 7.3 禁止的更新方式

- 不得以整個 `innerHTML` 覆蓋 `#calendar`、`#earnings`、新聞區、行情區、Fed 區或其他固定容器。
- 不得以 regex 或字串全域取代處理重複 class／文字，除非該操作已由明確測試限定至唯一節點且納入 allowlist。
- 不得直接重寫整張卡片、整個 tab panel、整個 status group 或整份 HTML。
- 不得將資料缺漏當成刪除欄位、刪除卡片骨架或隱藏固定元件的理由。
- 不得把「目前尚未定位」的區域當作可自動更新區域。

## 8. 目前插槽驗收狀態與禁止自動寫入區

截至本文件建立時，專案規格與測試顯示：

1. 已建立候選 selector registry，31 個候選定位曾通過 selector 命中數稽核；此結果只代表定位命中數符合基準，不代表全部插槽已獲寫入授權。
2. Repeat Group、status-group 變體、雙母版結構指紋及部分 Chromium 瀏覽器測試已有通過紀錄；每次新提交仍須重新執行 CI，不得沿用舊 run 當作本次驗收。
3. 已測試 tabs 切換、details 開合及 320px 手機列表幾何；紅圓加號專項視覺與點擊、日期排序資料層及 2026/11/02 預覽非破壞性測試仍須完成。
4. 以下區域仍未完成精確欄位定位，禁止每日更新器自動寫入：
   - 頁首 KPI（且正式雙母版沒有獨立 KPI 區塊，不得自行新增）。
   - 總結、盤面觀察重點及市場情緒中尚未完成精確定位的欄位。
   - SOX、VIX、MOVE、CNN Fear & Greed 等分散卡片中尚未列入可寫入 allowlist 的欄位。
   - WTI、Brent、Gold、Silver 商品卡行情列。
   - 週一上週經濟及財報卡的完整欄位。
   - Fed FOMC 會議區。
   - 任何標記為 `protected_container_only` 或尚未完成內層欄位定位的容器。
5. 任何專案狀態文件、測試報告或口頭回報，均須區分「候選定位」「selector 稽核通過」「欄位寫入測試通過」「瀏覽器互動通過」「可供使用者驗收」；不可合併成單一的「已完成」。

## 9. 金融內容與資料更新規範

1. 每日資料來源、報價日期與口徑、新聞真實性及時間窗、經濟／財報事件狀態、總結、圖釘評論及補漏閉環，全部直接遵守根目錄 WR v3.4，不在本文件另造一套較寬鬆標準。
2. 動靜分離只改變資料如何整理及寫入，不降低查證標準、不改變資料來源優先序，也不允許用舊資料填補空格。
3. 行情先完成核實，再更新相應摘要／觀察；更新後必須依 v3.4 檢查總結、市場情緒、關鍵價位、圖釘評論與行事曆是否一致。
4. 每張新聞卡仍須有真實可開啟的原始報導；不可將行情頁或指數漲跌改寫成新聞。
5. 每張事件卡的日期、台灣時間、狀態、實際值、預期值及來源，依 v3.4 及其行事曆規則核對；Repeat Group 數量只由實際事件決定。
6. 已公布且內容完整、來源可追溯的財報卡，依 v3.4 規則保留，不得因動靜分離而重抓或重製完整卡片。

## 10. 結構指紋與自動化驗收

每次候選更新至少執行下列檢查：

- [ ] 正式 manifest 及週一／平日母版 SHA 鎖定。
- [ ] HTML5 parser／browser-normalized DOM 可正常解析；記錄 parser 診斷，不將 parser 修復提示誤當成瀏覽器失敗。
- [ ] 固定 DOM 指紋、固定祖先與同層節點未改變。
- [ ] 固定 ID、錨點及重複 ID 基線未出現未授權變動。
- [ ] Selector 命中數、元素身份、父子層級及模板差異符合 registry。
- [ ] Repeat Group 的列表 wrapper、卡片骨架及動態筆數規則通過。
- [ ] Status Group 只使用同模板、同區塊既有 empty-state 原型。
- [ ] 固定 CSS、JavaScript、tab、details/summary、紅圓加號／減號與 aria／事件處理未被更動。
- [ ] 連結文字與 href 對應正確；target／rel 遵守正式規則。
- [ ] Chromium 瀏覽器互動測試通過，包含 tabs、卡片展開／收合及相關點擊。
- [ ] 320px 手機版無不預期溢出、覆蓋或水平捲動；桌面版亦完成版面檢查。
- [ ] 內容資料與 v3.4 核實結果一致，補漏閉環完成。
- [ ] 輸出只寫入專案測試預覽；正式首頁、雙母版、manifest 與正式 WR 保持不變。

**驗收原則：** 任一強制測試失敗即不得標示為可審核完成；修復後必須重跑相關測試。未執行的測試標示「未測試」，不得推定通過。

## 11. 專案分支、版本與變更管理

1. 專案開發及測試限於 `tac-template-architecture` 分支與 `dev-templates/`。
2. 每次提交須說明目的、修改檔案、是否影響 allowlist、測試項目及結果。
3. 不得把 91 commits ahead 等大型測試分支整支合併到 `main`；採用時只可透過獨立分支與最小變更 PR。
4. 修改 Slot Map、Selector Registry、Repeat Group Policy、驗證器或結構指紋程式時，必須同步更新相應測試，不可只改文件而宣稱規則已實作。
5. 不得覆寫舊測試報告來掩蓋失敗；新測試應留下新的 CI run、commit SHA 及結果。
6. 若正式母版或 v3.4 更新，先停止專案基線寫入，重新讀取正式版本、比對差異並評估影響；未完成重新鎖定前不得繼續。
7. 每次更新後須回讀 GitHub 實際檔案，核對 commit SHA、blob SHA、分支及內容；不得只憑寫入 API 回應宣稱驗收完成。

## 12. 專案階段與啟用閘門

本文件建立時的狀態為「架構驗證／測試階段」，尚未到正式每日自動更新階段。

進入下一階段必須逐項滿足：

### Gate A：規格完整
- [ ] 週一及平日完整 Slot Map 均完成。
- [ ] 所有允許寫入欄位都有 selector、欄位型態、命中數及測試案例。
- [ ] 所有未定位區域明確列為禁止寫入。
- [ ] 動態 Repeat Group 與 status-group 變體規格定版。

### Gate B：開發母版完成
- [ ] 由正式雙母版分別建立開發母版。
- [ ] 固定結構與正式母版指紋一致。
- [ ] 清除／替換動態資料時沒有破壞任何固定元件。
- [ ] 週一／平日專屬結構均正確保留。

### Gate C：資料寫入與內容驗收
- [ ] 建立可重現的每日資料集與欄位 mapping。
- [ ] 所有已開放插槽完成實際寫入、回讀及資料正確性測試。
- [ ] 新增／移除事件卡與排序符合 v3.4 及 Repeat Group 規則。
- [ ] 行情、摘要、總結、情緒、評論與日曆完成補漏閉環。

### Gate D：瀏覽器與裝置驗收
- [ ] 週一與平日分別完成桌面及手機版測試。
- [ ] tabs、收折、紅圓加號／減號、導航、連結及動態卡片均通過。
- [ ] 320px 手機寬度與常見桌面寬度均無版面破壞。
- [ ] 2026/11/02 預覽已完成非破壞性對照測試，且未更動原預覽。

### Gate E：使用者採用核准
- [ ] 提交完整差異清單、測試報告、限制與未解項目。
- [ ] 使用者明確核准採用動靜分離更新流程。
- [ ] 使用者另行核准任何正式母版、首頁或發布流程變更。

**未通過任何 Gate，不得跨階段啟用。** Gate A–D 測試通過不等於自動取得 Gate E 採用核准。

## 13. 交付與進度回報格式

每次工作回報至少包含：

1. **目前階段：** 規格盤點／selector 定位／開發母版／資料寫入／結構測試／瀏覽器測試／使用者驗收。
2. **本輪修改：** 實際檔案與內容，不只列計畫。
3. **驗收證據：** branch、commit SHA、CI run、通過／失敗測試。
4. **保護檢查：** 正式 WR v3.4、雙母版、manifest、首頁及既有預覽是否保持未修改。
5. **未完成事項：** 具體缺少的 selector、測試、資料或核准。
6. **狀態標籤：** 已完成／測試通過／待核實／未測試／未通過。

不得以「檔案已建立」「commit 成功」「CI 部分通過」宣稱整個動靜分離專案已完成。

---

## 附錄 A｜本文件參照的專案規格

以下文件是工程規格或測試附件，不是另一份正式 WR；均須服從本文件與根目錄 WR v3.4：

- `dev-templates/README.md`
- `dev-templates/slot-map-v1.4.md`（目前雙母版插槽盤點入口；v1.3、v1.2 與專項 map 保留作歷史／佐證）
- `dev-templates/selector-registry-v1.json`
- `dev-templates/repeat-group-policy-v1.1.md`
- `dev-templates/dom-count-audit-v1.md`
- `dev-templates/scripts/` 下的結構指紋、selector、repeat-group、status-group 及瀏覽器測試程式

若附件與正式母版實際結構或根目錄 WR v3.4 不一致，停止相關寫入，先修訂附件並重新測試；不得自行採用不一致的舊規格。

## 附錄 B｜建立紀錄

- 2026-10-31：依使用者要求，參酌根目錄正式 WR v3.4，於 `tac-template-architecture` 測試分支的 `dev-templates/` 建立專案專屬 WR v1.0-DRAFT。
- 本文件只建立專案治理與工程規則，不代表開發母版已建立、動態寫入已啟用或專案已通過採用驗收。


## 2026-10-31 測試進度補記（不改變 DRAFT 狀態）

- Run #84（41176330236）已通過 38 項單元／整合測試、5 項瀏覽器測試及 61 個候選 selector cardinality 稽核；葉節點寫入正反向防護測試已建立。
- Run #88（41176456247）已通過 43 項單元／整合測試、5 項瀏覽器測試及 61 個 selector 稽核；正規化經濟／財報排序函式測試通過。
- 日期排序目前僅完成獨立資料層及測試，尚未接入每日資料整理／更新器，尚未完成實際事件端到端排序。
- 週一母版本週經濟卡缺少加號節點仍為正式母版缺口；未經使用者授權不得修改正式母版。
- 本文件仍為 DRAFT，不授權每日自動寫入、正式首頁部署或雙母版變更。

## 2026-10-31 Run #93 補充

- 週一上週財報 EPS／營收實際與預期 leaf、優劣狀態與補充註記已完成欄位定位及正向／負向測試；Run #93 通過 44 項單元／整合測試、5 項瀏覽器測試及 68 個 selector 稽核。
- 股價當日表現、來源連結安全葉節點及分析文字拆分仍待完成；不可覆寫整個分析值容器。
- 本週經濟週一母版加號缺口仍待使用者授權後才能修正式母版。

## 2026-10-31 Run #99–#100 補充｜來源連結欄位

- 來源容器本身保持 protected；僅將其中 13 個 anchor leaf 註冊為獨立來源連結欄位，平日母版預期為 0。
- 測試用來源連結更新函式僅允許更新 href 與 anchor label，並驗證絕對 HTTP(S) URL、更新數量一致、拒絕 javascript: 及保留 target／rel 屬性。
- Run #99 與 #100 均通過 46 項單元／整合測試、5 項瀏覽器測試及 72 項 selector cardinality。
- 此函式尚未整合每日資料匯入或 Repeat Group 更新流程；Gate A 仍未完成，文件仍為 DRAFT。

## 2026-10-31 Run #101｜來源連結測試閉環

- Run #101（41177005842）通過 48 項單元／整合測試、5 項瀏覽器測試、雙母版 SHA、DOM 指紋及 72 項 selector cardinality。
- 來源連結更新器已驗證逐 anchor 更新 href／label、保留 target／rel，並拒絕 javascript:、錯誤 selector 及數量不符。
- 尚未接入每日資料匯入或 Repeat Group updater；不得當作正式生產寫入授權。

## 2026-10-31 Run #112｜市場情緒與總結欄位補記

- Run #112（41177327390）通過 51 項單元／整合測試、5 項瀏覽器測試及 77 項 selector cardinality。
- VIX／MOVE 漲跌幅、CNN 中英文狀態、核心解讀文字及總結標題已完成 leaf mapping 測試。
- 總結正文、今日觀察複合容器、CNN 狀態父容器及 marker style 維持 protected；不可用 textContent／innerHTML 整段覆寫。
- 本文件仍為 DRAFT，Gate A 未完成，不授權正式生產寫入。

## 2026-10-31 Run #112、#117｜總結／市場情緒欄位與 81 Selector 驗收

- Registry 已擴充至 **81 個候選 selector**。Run #117（41177564911）通過 51 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、DOM 結構指紋及 selector cardinality 稽核。
- 市場情緒新增獨立欄位：VIX 漲跌幅、MOVE 漲跌幅、CNN 恐懼貪婪英文狀態、中文狀態及核心解讀文字。原有 CNN 狀態複合容器、marker 容器、核心解讀容器與今日市場焦點容器均改為 protected，禁止整段覆寫。
- 總結標題可獨立更新；總結內文含混合格式／子節點，維持 protected，不允許以單一文字更新器整段覆蓋。
- Run #116 曾因週一上週經濟來源 anchor 預期命中數錯設為 7 而失敗。回查正式鎖定週一母版後，確認實際為 4 個 anchor（其中一個來源欄有兩個連結），已將 registry 預期值修正為 4；Run #117 通過。
- 經濟來源 anchor 的 4 個節點已定位；獨立正向更新測試仍在 Run #118 執行中，尚未宣告完成。
- Run #112：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177327390
- Run #116（失敗原因已修正）：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177458151
- Run #117：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177564911

## Run #118｜上週經濟來源 anchor 實際更新測試完成

- Run #118（41177611606）通過 **52 項單元／整合測試、5 項 Chromium 瀏覽器測試**，雙母版 SHA、DOM 指紋及 81 selector cardinality 稽核通過。
- 新增測試以週一正式母版確認上週經濟來源欄位的 4 個 anchor leaf，逐一更新 href／label，並確認目標 anchor 數量一致。
- Run #118 是 4 個經濟來源 anchor 定位與更新器的測試閉環；仍未接入每日資料匯入器或 Repeat Group updater。
- https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177611606

## Run #125–#126｜今日觀察重點文字片段更新器驗收（84 Selectors）

- Registry 現有 **84 個候選 selectors**，新增三組固定結構文字片段欄位：市場觀點、今日關鍵價位（五個獨立值段）、今日核心觀察。
- 專用更新器僅寫入明確登記的子節點 tail 文字，不替換父容器、不變更子節點標籤與結構；只接受精確命中一個父節點、固定子節點索引及標籤、正確資料筆數。
- Negative tests 覆蓋資料筆數錯誤、錯誤子節點標籤、使用一般 leaf writer 寫入 text-segments selector 等情境。
- Run #125（41177770274）與 Run #126（41177778541）均完整成功：52 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、DOM 結構指紋與 selector cardinality 稽核全通過。
- 此更新器已完成獨立測試，但尚未接入每日資料更新器或 Repeat Group updater；Gate A 尚未完成。
- Run #125：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177770274
- Run #126：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177778541

## Run #132｜上週經濟行事曆欄位與文字片段更新器修正驗收

- Run #132（41178152876）完整成功：**56 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋及 84 個候選 selector cardinality 稽核通過。
- 上週經濟行事曆新增獨立欄位測試：時間、國家、事件名稱、前值、預估、實際各 3 個葉節點；日期欄位既有測試保留；固定欄位標籤 12 個節點禁止一般文字更新器改寫。
- 修正 text-segments updater 的 Registry 查找：同一 CSS selector 可能同時有 protected-container 與專用 text-segments 登記，更新器現只接受唯一一筆 text_segments 類型登記，避免錯誤選到保護項目。一般 leaf writer 仍不得寫入 text-segments 欄位。
- Run #127–#131 曾因上述登記查找歧義而失敗；原因已定位並修正，Run #132 完整重跑成功，舊失敗紀錄不視為驗收通過。
- 目前仍屬欄位定位與獨立更新器測試，尚未接入每日資料更新器、資料來源 mapping 或 Repeat Group updater；Gate A 尚未完成。
- https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41178152876

## 2026-10-31 Run #137｜Registry 唯一性修正驗收

- Registry 由 84 個候選 selector 收斂為 **81 個**；市場觀點、今日關鍵價位、核心觀察三組 text-segments 登記已合併至原有 selector，不再建立重複 CSS selector。
- 新增 test_registry_has_no_duplicate_css_selectors，明確要求 Registry 內所有 selector 唯一；文字片段測試改用合併後的正式登記名稱。
- 文字片段更新器只接受唯一一筆 text_segments 登記，並驗證命中數、索引、標籤、筆數與字串型別；一般 leaf writer 仍不得改寫此類欄位。
- Run #137（41178495179）完整成功：**57 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、81 個候選 selector cardinality 稽核及測試報告上傳均成功。
- Run #136（中間提交）因 Registry 已先合併而測試尚未同步更新，故失敗；其後 Run #137 已以一致版本完整通過。此中間失敗不列為最終驗收。
- 此次完成 Registry 唯一性治理，不代表資料匯入器、Repeat Group 更新器或每日產製流程已接通；Gate A 仍未完成，Gate B–E 尚未啟動／核准。
- Run #137：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41178495179

## 2026-10-31 Run #142｜本週經濟行事曆 8 個欄位 Mapping

- Registry 擴充至 **89 個候選 selector**，新增本週經濟卡 8 個欄位：日期、時間、國家、事件名稱、重要性星級、前值、市場預估、實際數值。
- 週一母版 12 張卡、週二至週五母版 16 張卡均以實際 DOM 核對；8 個 selector 在兩版均命中預期數量，所有目標均為純文字 leaf。
- 新增雙母版正向寫入測試：逐欄位驗證 selector 命中數、leaf 結構及更新結果。現有觀察重點、來源欄位、固定 label、details／summary 及卡片骨架仍受既有保護規則約束。
- Run #142（41178651534）完整成功：**58 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、89 個候選 selector cardinality 及測試報告上傳成功。
- 本次僅完成既有母版卡片的欄位定位與 leaf 更新驗證；尚未建立週經濟卡片的資料來源 Mapping、動態新增／移除後的欄位寫入流程，亦未接入日期排序。Gate A 尚未完成。
- Run #142：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41178651534

## 2026-10-31 Run #147｜本週財報摘要欄位 Mapping

- Registry 擴充至 **94 個候選 selector**，新增本週財報卡 5 個摘要欄位：美國公告日期／時段、台灣時間、公司名稱、公司代號／產業副標題、重要性星級。
- 週一與週二至週五母版各 16 張本週財報卡；五個 selector 在兩版均命中預期數量，且全部為純文字 leaf。
- 新增雙母版正向寫入測試，逐欄位驗證命中數、leaf 結構與更新結果；固定 summary、toggle、details、欄位 label、來源與複合內容仍受保護。
- Run #147（41178787398）完整成功：**59 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 個候選 selector cardinality 及測試報告上傳成功。
- 本次只完成財報卡摘要欄位 Mapping；卡片內各種不同欄位（EPS、營收、觀察重點、公布時段、來源）仍需按 label／結構分別處理，來源 anchor 與含子節點容器不得交由一般 leaf writer 覆寫。Repeat Group 實際資料更新尚未接通，Gate A 尚未完成。
- Run #147：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41178787398

## 2026-10-31 Run #156｜Repeat Card Label-aware Detail Leaf Guard

- 為本週經濟與財報 Repeat Group 新增明確的 detail-field allowlist 與 label-aware 更新器；Registry 仍為 **94 個候選 selector**，不增加泛用或模糊 selector。
- 更新器只接受已登記 repeat／monday_only 卡片 selector，逐張卡依固定 label 找到同一欄位的直接 value 子節點；必須唯一命中、value class 正確且沒有子節點。先驗證所有卡片及欄位，再一次寫入，避免中途失敗造成部分更新。
- 可寫 label 明確限定：週一經濟／財報為「觀察重點」；平日經濟為「市場影響」；平日財報為「財報判讀與股價反應」。這些是兩版既有母版的真實 label 差異，不跨模板套用。
- 來源欄位（例如「資料來源」「來源」）不在 allowlist；含 anchor 或其他子節點的 value 一律拒絕。測試涵蓋未知 label、更新筆數不符、巢狀 value 拒絕，以及失敗前不會部分寫入。
- Run #156（41179095028）完整成功：**61 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 個候選 selector cardinality 與測試報告上傳均成功。
- Run #153–#155 為開發中間版本：初版測試誤假設兩種母版使用相同 label，實際核對後發現平日版分別使用「市場影響」及「財報判讀與股價反應」；已按兩版實際 DOM 調整 allowlist 與測試，Run #156 才是完整驗收版本。
- 本更新器仍是測試用安全 guard，尚未接入資料匯入器或 Repeat Group 新增／移除流程；不能視為每日自動更新已啟用。Gate A 尚未完成。
- Run #156：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41179095028

## 2026-10-31 Run #163｜Repeat Card Source Anchor Guard

- 在既有 94 個候選 selector 下，新增 Repeat Group 卡片的 label-aware source anchor 更新器；不增加或放寬一般文字 leaf allowlist。
- 只接受週經濟／週財報卡片 selector 及明確來源 label（經濟「資料來源」；財報「來源／資料來源」）。逐卡找到唯一來源欄位及直接 value 容器，只允許既有直接 anchor leaf 的 href 與文字 label 更新。
- 更新前先驗證全部卡片：來源 label、value 容器、anchor 數量、anchor 層級、anchor leaf 結構及 URL。只接受絕對 HTTP(S) URL，拒絕 javascript:、無 host、帳密及控制字元；來源 anchor 數量不符或需要新增／刪除 anchor 時拒絕更新。
- 寫入僅改 anchor href／文字，保留 target、rel、class、tail 及來源容器；所有目標先完成驗證再寫入，避免部分更新。來源欄位仍不得由一般 label-aware text updater 覆寫。
- 測試涵蓋週一／平日、經濟／財報來源欄位、不同 anchor 數量、屬性保留、錯誤 label、anchor 數量不符、javascript URL 拒絕及失敗不部分寫入。
- Run #163（41179318013）完整成功：**63 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 個候選 selector cardinality 與測試報告上傳成功。
- 本更新器只更新現有來源 anchor，不建立／刪除 anchor、不接管來源選擇與事實核實，也未接入每日資料匯入或 Repeat Group 新增／移除流程。Gate A 尚未完成。
- Run #163：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41179318013

## 2026-10-31 Run #168｜本週財報全部純文字 Detail Labels 驗證

- 在 94 個候選 selector 基礎上，擴充 weekly earnings repeat-card 的 detail label allowlist，沒有增加泛用 selector。
- 週一母版可更新的純文字 detail labels：觀察重點、EPS 共識、正式公布時間；平日母版：公布時段、EPS 預估／實際、營收預估／實際、財報判讀與股價反應。
- 每個 label 仍須在各卡片中唯一命中；只更新直接相鄰的 earnings-detail-value leaf。來源 label 不在文字 allowlist，含 anchor／子節點的來源容器仍交由 source-anchor 專用更新器。
- Run #168（41179488654）完整成功：**63 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 個候選 selector cardinality 與測試報告上傳成功。
- 本次補齊的是既有母版中的純文字 detail 欄位定位與安全更新驗證；不代表新資料已匯入或 Repeat Group 已動態新增／刪除。Gate A 尚未完成。
- Run #168：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41179488654



## 2026-10-31 Run #41180947602｜行事曆資料契約層補充（不改變 DRAFT 狀態）

本次新增 `scripts/tac_calendar_dataset.py` 與對應測試，作為經濟／財報資料進入後續更新流程前的標準化驗證入口。其定位僅為資料契約及排序層，不是資料爬取器、HTML 更新器或每日生產程式。

### 資料契約要求

1. 資料集必須明確包含 schema_version、report_date、template、economic_events、earnings_events；template 僅接受 monday 或 weekdays。
2. 每筆事件必須具備唯一 event_id、ISO YYYY-MM-DD event_date、event_timezone、1–5 星 importance、可選 event_time，以及至少一筆 source_records。
3. 每筆 source_records 必須包含 source_name、label、絕對 HTTP(S) URL、含時區 offset 的 accessed_at。來源缺漏、不安全網址或查證時間沒有時區時，整筆資料驗證失敗，不得補猜。
4. 經濟事件另須提供 country、event_name；其 event_date／event_time 按事件當地時區解讀。
5. 財報事件另須提供 taiwan_display_date、company_name、subtitle、release_session。event_date 是美國公告日期，排序依據不得被台灣顯示日期取代；release_session 僅接受 pre_market、during_market、after_market、unspecified。
6. details 若存在，只接受 label 對應字串的 mapping。未知或錯誤型別應停止，不可自動轉型或填入推測值。
7. 排序沿用 `tac_calendar_sort.py`：經濟依日期／當地時間；財報依美國公告日期／公告時段／可用時間。未知時間排在同日已知時間後，排序穩定且不得改寫輸入資料。
8. 本契約不代表資料內容已符合正式 WR v3.4 的事實核實要求；來源優先序、重要性篩選、實際值與市場影響判斷仍須另行依 v3.4 完成。

### 測試與限制

- 新增 15 項資料契約測試，覆蓋正常排序、未知時間、重複 ID、錯誤日期／重要性／公告時段、來源缺漏、不安全 URL、查證時間時區及美國公告日期與台灣顯示日期分離。
- 初次提交後檢查 CI 日誌，發現 workflow 使用明確測試檔清單，未自動納入新測試；已修正 `.github/workflows/tac-template-architecture-tests.yml`，確保資料集測試正式納入後續每次 CI。
- Run #41180947602：**78 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 selectors cardinality 及稽核報告上傳通過。
- 尚未完成真實資料匯入、欄位 Mapping、Repeat Group 新增／移除及資料寫入閉環；不可宣稱每日生產已接通。Gate A 仍未完成；Gate B–D 未完成；Gate E 尚待使用者核准。
- 驗收紀錄：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41180947602

本補充只記錄工程契約及測試狀態，不改變本文件 v1.0-DRAFT 身分，不構成正式採用或每日生產授權。
