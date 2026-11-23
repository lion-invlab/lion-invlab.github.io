# TAC 投資早報｜統一模擬工作規範 SIM-1.4（正式生效版）

> **狀態：ACTIVE／正式生效。生效日期：2026-11-22。** 本文件為 TAC 投資早報 simulation branch 唯一有效工作規範。SIM-1.3 已封存為歷史版，不再與本版並列有效。SIM-1.4 生效不代表 Builder 已獲核准、審核版已 REVIEW_READY 或正式首頁已獲發布授權。本版仍嚴格禁止修改 main、正式母版、正式 Manifest、正式首頁及正式行事曆 JSON。

- 專案：TAC 投資早報
- Repository：`lion-invlab/lion-invlab.github.io`
- 工作分支：`simulation/tac-process-lab-2026-11-06`
- 生效日期：2026-11-22
- 核准方式：使用者於 2026-11-22 明確授權將 SIM-1.4 Draft 修訂後升格為正式規範
- 前版基準：`simulation-lab/archive/TAC_WORK_RULES_SIM_1.3_ARCHIVE.md`（SIM-1.3 歷史封存版）
- 時區：Asia/Taipei（UTC+8）

---

## 0. 核心原則、權限與狀態

### 0.1 規則優先權
1. 使用者當次明確指示優先；其次為經核准生效的 SIM-1.4；再其次為本文件明列的唯一技術契約及資料來源契約。
2. 助理建議、聊天摘要、舊交接、歷史版本、程式註解及自動化 prompt 均不得創造或覆寫規則。
3. SIM-1.3、SIM-1.2、v5.x 及補充條文在 SIM-1.4 生效後均為歷史資料，不再與 SIM-1.4 並列有效。
4. 發生本文件內部衝突時，先依本文件的專門章節優先於一般原則；仍無法裁決時標記 BLOCKED，不得自行猜測。

### 0.2 權限邊界
- SIM-1.4 的規則、程式、Fixture、測試、技術回歸及原始 QA 產物只在 `simulation/tac-process-lab-2026-11-06` 分支修改與保存。
- main 原則唯讀；唯一例外是本規範 Stage 6 明定的「已通過 QA 審核版交付」：只可新增／更新指定日期的 `main:preview/YYYY-MM-DD-review.html`、同名 QA sidecar 及交付收據。不得修改其他 main 路徑。
- 正式母版、main Manifest、main QA 附件、`index.html`、正式歷史報告及正式行事曆 JSON 均受保護；審核版交付不得觸及這些檔案。
- main `data/calendar/weeks/YYYY-Www.json` 是早報唯一行事曆資料來源；工作日 04:35 專用排程是唯一寫入者。早報流程 05:25 嚴格唯讀。
- simulation QA 全部適用強制 Gate 通過且 sidecar 標示 `REVIEW_READY` 後，只代表可提供 Simulation 審核版，不構成 main preview 交付授權。必須先由使用者審核並明確核准該份 HTML 的確切 SHA-256；交付只能透過獨立、具 main 寫入能力的明確授權動作，並核對完全相同的 HTML SHA-256 後，將同一 HTML 與 sidecar 原樣交付 main preview。目前 `.github/workflows/tac-simulation-lab.yml` 僅存在 Simulation 分支，未安裝於 main/default branch，因此不可假設可由 `workflow_dispatch` 從預設分支觸發；不得為此擅自將該 Workflow 加入 main。push tag、每日排程及一般 build 一律只產生 Simulation 審核版，不得交付 main。交付時必須核對 Git blob SHA／SHA-256 不變；不得重新組裝、改寫內容或重跑完整 QA。
- main preview 的交付檢查只驗證路徑、檔案存在、HTML／sidecar SHA 與 simulation QA 收據綁定一致、交付收據完整；不構成第二次內容／技術 QA。Pages 可開啟性另行如實標示。
- 正式首頁只有使用者對 main preview 中已唯一識別的 HTML SHA 明確核准後才可更新。歷史封存只在正式發布後另行執行。
- simulation workflow 禁止 deploy Pages、修改 `main:index.html`、使用 production secrets 或自動發布正式首頁；main 寫入權限僅限 Stage 6 preview 交付白名單路徑。

### 0.3 保護與修改閉環
每次修改前取得目標檔案最新內容與 SHA；確認授權範圍；採最小必要差異；執行相應測試；寫入後回讀並核對 SHA、內容及未授權檔案未變。不得平行寫入同一路徑。遇到 SHA 競爭或更新失敗，重新讀取最新版本並重新比對，不得強制覆蓋。

### 0.4 狀態定義
- **BLOCKED**：關鍵基準錯誤／不存在、母版或日期情境錯誤、資料來源版本無法確認、組裝器無法安全定位、核心行情身分錯誤，或權限不符；不得交付審核版。
- **PARTIAL**：必要流程可繼續，部分非核心欄位待核實／暫缺／未測試；必須完整揭露，且不得標示 REVIEW_READY。
- **REVIEW_READY**：六階段必要輸入、完整內容、HTML 組裝及所有適用強制 QA 均通過；允許交付審核版，仍不代表正式發布。
- 資料狀態另使用 VERIFIED、BACKUP_VERIFIED、PENDING、MISSING、CLOSED、NOT_APPLICABLE、NOT_TESTED；不得把未測試或暫缺轉寫成通過。
- 單一非核心欄位缺漏不得停止無依賴的其他工作。44 項固定欄位須完整保留；已核實者顯示數值，交易所休市顯示 CLOSED／休市，其他缺值顯示「待核實」，不得用舊日期補值或虛構數字。只要核心行情身分、報告日期、母版或組裝器沒有錯誤，就應繼續完成可完成的報告內容與 HTML；缺值須在資料狀態與畫面清楚揭露。BLOCKED 只用於真正無法安全組裝或核心基準錯誤，不得把非核心資料缺漏升格為全流程停工。

### 0.5 30 分鐘目標
30 分鐘是流程效率目標，不是資料正確性豁免。已取得且符合標的、日期、欄位、口徑及證據的資料立即鎖定，不再重抓；後續只處理待辦項目。超時必須記錄真正耗時與阻塞原因，不得為達標跳過來源讀取、Gate 或 QA。

---

## 1. 唯一權威資產與資料基準

### 1.1 唯一規則與技術附件
- 本規範唯一工作規範路徑為 `simulation-lab/TAC_WORK_RULES_SIM.md`；本路徑是唯一有效規則入口。 `scripts/tac_html_binding_map.json` 為歷史映射附件，除非本草案另列其 SHA、selector 與 Builder 對照並經核准，不構成額外 DOM 寫入授權。
- 母版選擇唯一依據：`simulation-lab/baseline/mother-template-manifest.json`。
- 核准母版結構、DOM、互動與視覺的唯一詳細 QA 契約：`simulation-lab/baseline/mother-template-qa-contract.md`。main 的 `母版專區/母版結構驗收清單.md` 是正式母版來源附件，不是 simulation 每日 QA 的第二份活動清單；其結構規格只有在與 simulation 契約一致且 SHA 基準相符時供來源追溯，不得兩份交替裁決。
- 正式行事曆資料：main `data/calendar/weeks/YYYY-Www.json`，無平行資料庫。
- Builder：唯一正式生產入口必須符合第 8.1 節使用者核准的精確路徑與 SHA。**本版唯一正式 Builder 已核准：** `simulation-lab/runner/build_review_html.py`，blob SHA `2cb0a90e53b10c31aca20503f93a5b324091c0a7`。此核准只解除 Builder approval Gate；仍須完成本次真實資料 Stage 1–6 E2E、資料／內容 Gate 與完整 QA，通過前不得標示 REVIEW_READY 或交付。
- 執行狀態及證據：依第 10 章規定的根目錄兩份既有紀錄分工；讀取時以實際路徑及 SHA 為準。

### 1.2 開工鎖定資料
記錄 SIM 規則版本／SHA、Manifest SHA、週一或平日母版路徑／SHA、QA Contract SHA、main HEAD、當週及上週 JSON SHA、報告日期、行情基準日、輸出路徑、Builder 候選版本／SHA、Fixture SHA。任一必要基準缺失或不一致，依 0.4 分類，不得 fallback。

### 1.3 母版保護
- 週一使用週一母版，週二至週五使用平日母版；週末不自動製作。
- 每日只允許更新核准內容槽位及當日資料；不得重設 CSS、JS、DOM、互動、響應式結構、字體、色彩、間距或版面。
- Manifest SHA 不符即停止。不得用舊 preview、首頁、歷史報告或手動重建頁面替代母版。
- DOM 必須由真正 DOM parser 定位；不得用 regex、字串切片、標題搜尋或固定字元位置取代。
- 每個核准母版 SHA 的完整結構解析只需一次；每日做 SHA 核對、定位錨點快速檢查及輸出 DOM 驗證。
- **漲跌色彩固定：上漲／正值使用紅色，下跌／負值使用綠色；** 不得套用其他市場慣例反轉顏色。同類漲跌數字的字級、粗細、行高及對齊一致。
- **行情名稱與連結：** 中文名稱在上、英文代碼以較小字級置於下方，不加括號；連結只包商品／指數名稱或代碼，不得包住點位、漲跌幅或評論文字。
- **行事曆星等視覺：** 完整顯示五格星等；五星事件標題使用 TAC 紅色，四星沿用核准母版既有樣式，不另造卡片樣式。
- 不得重新加入使用者已要求刪除的總結區下方「關鍵重點」膠囊或同義替代元件。
- **工具欄提示互動：** 若所選母版包含工具欄說明泡泡，使用者首次捲動／觸控移動時必須立即提前隱藏泡泡，不等待原定延遲；泡泡隱藏不得連帶移除工具欄呼吸燈／高亮提示，呼吸燈仍依母版原定時間持續（除非使用者點擊或母版原始行為另有定義）。必須分別驗收泡泡與呼吸燈，未實測不得宣稱實機通過。

---

## 2. 每日唯一製作流程（六階段）

六階段是同一條生產流程，不是六次獨立審批。每日開工時讀取一次當前有效 SIM-1.4 並記錄 SHA；當日流程沿用該版本，不要求每一階段前後重讀整份規範。只有規範或相關程式在當日被修改時，才重新讀取受影響段落並核對新 SHA。每階段只保留必要輸入、輸出與交接紀錄；不得重複建立收據、重複核對已鎖定資料，或讓同一事實經過多層等價 Gate。

### Stage 1｜開工基準與母版鎖定
**輸入：** 本版規則、Manifest、QA Contract、雙母版、報告日期、main 行事曆 JSON。
**執行：** 確認台灣日期／星期、行情基準日、週一或平日情境、保護範圍、各基準 SHA；讀取當週 JSON，週一另讀上週 JSON。
**輸出：** 基準清單、來源 SHA 收據、日期／母版情境。
**驗收：** 必要路徑存在、SHA 相符、日期正確、main 保護範圍清楚。失敗為 BLOCKED。
**交接：** Stage 2 使用固定報告日期、行情基準日、核准母版欄位清單與來源規格。

### Stage 2｜44 項行情及獨立 FedWatch
**輸入：** Stage 1 基準、核准母版固定欄位、附錄 A 來源契約。
**執行：** 逐項直接讀取指定原始網頁；第一輪完整掃描。符合標的、交易日、報價欄位、口徑及證據的值立即鎖定。第二輪只刷新缺值／疑義項目；第三輪只改用同一來源系統歷史頁或日期查詢；其後才按該指標規定啟用備援。已鎖定值不得無理由重查或覆寫。
**輸出：** 44 項逐項行情台帳；每項含標的身分、數值／狀態、資料日期／時區、報價欄位、來源 URL、查核時間、來源角色、口徑、實際輪次及備援原因。每筆已核驗資料另保存瀏覽器觀察紀錄，至少包含來源 URL、標的／合約身分、資料日期、實際讀取欄位與數值、漲跌欄位與數值、查核時間及讀取方法；對該觀察紀錄的標準化內容計算 SHA-256。FedWatch 獨立紀錄，不計入 44 項。
**驗收：** 44 項每項均有數值或明確狀態；VERIFIED／BACKUP_VERIFIED 須有完整瀏覽器觀察紀錄及其紀錄 SHA-256，且顯示值與觀察值一致；未核實值不流入分析作為確定事實。原始 HTTP response body／raw_response_sha256 僅屬可選的額外封存證據，不是數值核驗或 Stage 2 PASS 的必要條件。不得把觀察紀錄雜湊冒充原始 HTTP 回應雜湊。若瀏覽器觀察紀錄本身缺少必要欄位或其 SHA-256 無法重算一致，該筆證據才列為缺漏；來源頁可讀但沒有目標日期資料列，應標示 SOURCE_NO_DATA；工具無法讀取來源頁才標示 TOOL_READ_FAILURE。
**交接：** 完整行情台帳及鎖定值提供 Stage 3–5；待核實狀態一併傳遞。

### Stage 3｜行事曆與財報事件
**輸入：** Stage 1 的 main JSON SHA；Stage 2 行情；附錄 C、D。
**執行：** 早報對 JSON 嚴格唯讀；逐筆核對事件 ID、日期／時區、公司／國家、狀態、實際值、預期值、來源、星等及分頁。財報共識固定由 Yahoo Finance Average Estimate 第一順位；該指標缺值、不可讀或期間不符時，依序遞補 Investing.com、LSEG I/B/E/S、FactSet Estimates。EPS／Revenue 各自獨立選源，取得第一個可用平均預期後停止該指標主來源搜尋。
**輸出：** 經濟與財報事件顯示資料、已公布實際值、共識來源與判讀、股價反應及待核實項目。
**驗收：** JSON SHA、事件 ID 唯一、日期／時區正確、已公布實際值有來源、EPS／Revenue 分開判讀、跨幣別比較有明確換算。
**交接：** 供 Stage 4 分析及 Stage 5 組裝；不得將早報查核結果寫回 JSON。

### Stage 4｜新聞與市場分析
**輸入：** 已鎖定行情、Stage 3 事件、新聞時間窗及來源契約。

**執行：** 讀取原始報導，核對發布時間／時區；新聞整理與投資分析分開撰寫。分析內容必須分成三個不同層級，禁止互相塞版或重複堆疊：

1. **總結小卡（讀者 30 秒掌握）：** 位於報告最上方，負責交代當週／當日最重要的市場主軸、核心風險及明確立場。建議控制在手機約 1–2 個畫面；只保留一個有辨識度、能點出市場矛盾的主標題、一句開場觀點，以及「市場正在改變什麼／眼前風險／今日立場」等精簡內容。不得將五層分析全文、長篇數據清單或多組操作條件塞入小卡。標題可有情緒張力與讀者共鳴，但不得煽情、誇大或超出證據。
2. **市場深度解析（完整文章）：** 必須置於總結小卡之後，固定依下列五層順序撰寫，不得任意調換、合併或將政治分析降格為新聞摘要：
   - 一、政治與地緣政治局勢：每日掃描美國政府與國會政策、美中戰略競爭、中東、俄烏、台海、朝鮮半島、國際貿易與關稅、制裁與出口管制、日本／歐洲／中國及其他主要經濟體政治變化，以及能源與戰略資源。只納入有可靠證據且對經濟、企業或市場具實質影響的事件；若當日無重大且可核實的新變化，不得硬湊政治敘事。逐項區分「已正式生效／執行」「已宣布但尚未實施」「政治人物立場或談話」「市場預期」「未核實消息」，不得混為既成政策或事實。
   - 二、政策傳導與企業／產業鏈影響：說明政策、監管、關稅、制裁、補貼、財政措施、出口管制及地緣事件如何影響產業、企業、供應鏈、資本支出、訂單、營收、成本、利潤、融資、營運資金與現金流。區分公司正式公告、可靠媒體報導及分析推論；不得把調查寫成違規已證實，也不得以單一公司推論整個產業。
   - 三、宏觀經濟傳導：分析事件如何傳導至經濟成長、通膨、就業、消費、投資、財政、央行政策、利率及企業獲利；交代傳導方向、時間差、受影響經濟體與可能抵銷因素，不得將尚未發生的影響寫成已實現結果。
   - 四、金融市場定價、情緒與風險：整合全球股市與跨區域結構、債券殖利率、匯率、能源／貴金屬、信用、波動率、市場廣度、技術趨勢及可查證資金流，說明市場正在定價什麼、哪些資產已反映或尚未反映風險。指標只能支持其實際代表的結論；不得把極端恐懼直接等同落底，也不得使用未核實 OHLC 計算支撐壓力。
   - 五、機構資金動向與投資策略：分析可查證的機構持倉／資金流與模型估算；模型估算必須明確標示「估算」而非實際成交流。提出基準／風險／嚴重情境，逐一列出觸發條件、傳導路徑、受影響資產、領先指標、策略與判斷失效條件；明確說明目前先做什麼、優先降低何種風險、何種條件才分批加碼、何種情況重新防禦。
3. **盤面觀察重點／今日觀察：** 作為可快速執行的日常訊號，應比完整文章更精簡，只保留當日最重要的觀察變數、確認條件與失效條件；不得把五層文章原文再貼一次。

**政治／地緣政治每日掃描與傳導要求：** 六個掃描領域為（1）美國政策與政治，（2）美中競爭，（3）地緣政治：中東、俄烏、台海、朝鮮半島，（4）國際貿易、關稅、制裁與出口管制，（5）主要經濟體政治：日本、歐洲、中國及重要新興市場，（6）能源與戰略資源。先核對原始公告／正式文件與可靠報導的發布時間、法律／執行狀態及適用範圍，再判斷市場重要性。每項重大事件須盡可能完成「事件 → 政策／執行 → 產業／企業 → 宏觀經濟 → 金融市場 → 投資策略」傳導；缺乏證據的環節明確標示未知，不得補寫推測。不得把政治人物表態等同政府決策，不得把宣布等同生效，不得把市場預期等同政策事實。若沒有重大新事件，允許明確記錄「本日未發現足以改變市場定價的重大已核實政治／地緣政治變化」，不為了填滿篇幅硬寫。政治掃描是分析流程，不代表每天都必須產生政治方向性交易結論。

**操作建議必須具體，不得曖昧：** 至少回答「現在先做什麼、優先檢視／降低什麼風險、什麼條件出現才分批加碼、什麼情況下應再度防禦」。每項建議須對應可觀察條件或風險因子，並交代判斷失效條件；不得只寫「審慎觀望」「留意風險」「逢低布局」等無法執行的空泛語句。這是市場層級策略框架，不可假裝知道讀者個人持倉、成本或風險承受度。

**文字品質：** 使用繁體中文與一般投資人能理解的語言；專業術語首次出現時以中文解釋。語氣要有溫度、節奏與讀者共鳴，能把數據背後的市場矛盾說清楚，但不得用戲劇化措辭代替證據。事實、推論、情境與策略須清楚區分；不以重複新聞標題或逐項行情漲跌充篇幅。

**分析品質與因果推論（強制）：**
- 總結小卡與五層深度解析必須以自然、流暢的繁體中文撰寫；不得使用固定句型堆疊、新聞摘要拼貼或行情逐項改寫代替分析。
- 每一項重要判斷須交代「已確認事實 → 傳導機制 → 受影響對象／資產 → 市場定價 → 投資動作」，並標明哪些是事實、推論、情境假設及策略。無證據支持的環節必須明確寫「未知／尚無足夠證據」，不得補造因果。
- 結論須有方向及可執行性：說明目前先做什麼、降低或檢查何種風險、何種可觀察條件成立才分批加碼，以及何種條件使原判斷失效並重新防禦。不得以「後續觀察」「值得持續關注」「市場仍需觀察」「審慎觀望」等空泛句作為結論；若需等待，必須寫明等待的具體數據／事件、觸發門檻及等待期間的部位處理。
- 總結只濃縮市場主軸、核心矛盾、風險與立場；五層文章負責完整論證；盤面觀察重點只列當日可驗證訊號，不得三處重複貼文。

**AI 融資鏈與信用傳導（強制掃描，證據不足時不得硬下結論）：**
- 當 AI 資本支出、GPU 採購、資料中心建置或雲端算力合約成為市場主軸時，必須檢查 NVIDIA 與 AI 雲端業者之間可查證的投資、採購承諾、預付款、長約、客戶／供應商集中及其他資金安排；不得僅以「資本支出高於營收」概括風險。
- 同步檢查 AI 雲端業者及資料中心專案的公司債、可轉債、銀行融資、私募信貸、專案融資、租賃及其他已披露資金來源，並追蹤融資成本、信用利差、債務到期、抵押品、擔保／承諾、應收帳款、現金流與再融資能力。
- 必須建立「融資條件收緊 → 資金成本／可得性改變 → GPU 採購與資料中心投資調整 → 算力供需及供應商訂單 → 企業營收／毛利／現金流 → 相關股票、債券與信用資產重新定價」的傳導鏈；逐段列出證據及未知環節。
- 嚴格區分（1）融資條件收緊，（2）信用風險重新定價，（3）個別企業違約／專案取消，（4）整條融資鏈瓦解。不得由前兩者直接推論後兩者，更不得在沒有違約、流動性或契約證據時宣稱系統性崩解。
- 對 NVIDIA 及相關雲端業者的交易／投資關係，只有在公司公告、監管文件、債券文件、法院／監管紀錄或可靠媒體具體報導可核實時才能寫入；區分已簽約、意向、投資承諾、媒體引述及市場推測。沒有公開證據時明確標示未披露，不得把傳聞當成融資事實。

**總結與深度解析的來源顯示邊界（強制）：**
- 五層 market_analysis.sources 及總結相關來源欄位仍須完整驗證、計入 receipt 的 source_count，並保留來源 label、URL、狀態及可得時間等內部證據。
- 但總結小卡與五層深度解析的最終 HTML 可見區域不得產生「資料來源」文字、來源連結、來源收折區或任何替代顯示元件。來源只留在 Fixture、驗證收據、QA sidecar／內部稽核資料及必要 provenance，不得顯示於上述兩個版面區域。
- 此規則只適用總結與五層深度解析；新聞、行情、商品、債券、匯率、行事曆及其他區域原有來源標示與收折區完全維持，不得擴大刪除。

**局部更新與完整組裝的分流（強制）：**
- 單純修改總結文字或五層分析文字，必須使用獨立的既有 HTML 區塊局部更新器，只更新指定 DOM 節點；不得重新執行行情擷取、新聞整理、行事曆載入、完整 Builder 或整份早報 E2E。
- 局部更新器必須使用 DOM parser 與 Manifest／母版 selector，保留目標區塊以外的 DOM、CSS、JS、互動、收折結構及 provenance；更新前後須比較非目標 DOM 指紋，並產生記錄目標 selector、輸入 Fixture SHA、來源 receipt、更新前後 HTML SHA-256 及測試結果的局部更新收據。
- 總結文字更新只更新總結標題／段落槽位；深度分析文字更新只更新五層文章段落槽位。若兩者同時修改，仍只更新這兩個指定區域。
- CSS／母版結構變更、行情／新聞／行事曆資料變更或多模組整合變更，才按影響範圍執行對應模組與完整組裝／E2E。局部更新成功不等於整頁完整 QA 通過；必須標示局部 QA 範圍及尚未重跑的全頁項目。

**輸出：** 5 則全球焦點新聞目標、10 則市場熱門頭條目標、總結小卡、依固定順序完成的五層市場深度解析、精簡盤面觀察重點／今日觀察，以及完整來源證據。五層文章必須輸出為 Fixture 的 `market_analysis` 物件，固定鍵為 `political`、`policy_industry`、`macro`、`markets`、`strategy`；每層均包含非空 `paragraphs`（純文字段落陣列）及 `sources`（至少一筆來源，含 `label`、`url`、`published_at`／`checked_at` 可得時間與 `status` 分類）。另須輸出 `political_scan`：包含 `checked_at`、`domains_checked`（六個固定代碼 `us_policy`、`us_china`、`geopolitics`、`trade_sanctions`、`major_economies`、`energy_resources`，每日全部完成）、`findings` 陣列及無重大事件時的 `no_material_change_note`。每項 finding 必須含事件標題、所屬領域、狀態分類（固定代碼 `formally_effective`、`announced_not_implemented`、`political_statement`、`market_expectation`、`unverified`）、來源 URL／發布時間／查核時間，以及 `transmission` 的 policy、industry、macro、markets、strategy 五個環節（無法證實者明確填「未知」）；重大事件另須提供 baseline、risk、severe 三種情境的觸發條件、資產影響、領先指標、策略及失效條件。來源必須可追溯至原始文件／報導；同一來源可在多層重用，但不得以沒有來源支持的分析段落充數。
**驗收：** 不灌水、不以報價冒充新聞、不重複新聞事件；事實、推論、情境與策略分離；總結小卡與完整文章明確分層；五層標題及順序正確；操作建議具備執行動作、觸發條件與失效條件；總結符合週一或平日格式。
**交接：** Stage 5 接收可直接組裝的各層內容、層級／順序識別，以及每則新聞原文 URL、時間、查核證據。

### Stage 2–4｜組裝前輸入收據（進入 Stage 5 前的強制交接）
Stage 2、3、4 的成果不得只靠 Fixture 內嵌欄位或前次 QA sidecar 口頭宣稱完成；在呼叫唯一 Builder 前，必須產生本次 Workflow 專屬的輸入收據，將三階段輸入鎖定為同一份報告日期、同一分支及同一執行批次。

**收據必須記錄及驗收：**
1. **執行身分：** repository、固定 Simulation branch、report_date、GitHub workflow_run_id、run_attempt；不接受 main 或其他分支產物混入。
2. **Stage 2 行情：** Fixture SHA-256、44 項行情 metadata/date audit SHA-256、44 項 source-observation manifest SHA-256；逐筆檢查 44 項身份、分組數量、共同交易日、來源 URL、既有瀏覽器觀察紀錄、觀察值／漲跌欄位、查核時間及 observation_record_sha256。既有觀察紀錄可沿用；本次未重新擷取來源頁或未獨立重核數值時，必須如實記錄 false，不得宣稱本次重新抓取或重新核驗。raw_response_sha256 為可選證據，不得列為必要 Gate。
3. **Stage 3 行事曆：** 以單次 fetch 得到的 main commit SHA 為唯讀基準，當週與上週 JSON 均須由同一 commit 讀取；記錄兩份 canonical ISO-week 路徑、blob SHA、week_id、日期範圍及經濟／財報事件數。不得混用不同 main commit、Fixture 舊版行事曆或不同日期 JSON。Builder provenance 的 main commit／兩週 blob SHA 必須與輸入收據完全一致；若 main 在收據與 Builder 讀取之間更新，應停止並重跑整個輸入收據及組裝，不得拼接兩版資料。
4. **Stage 4 新聞與分析：** 核對 5 則 Global Focus News、10 則 Market Hot Headlines、每則新聞 HTTPS URL、發布時間／時區／台灣時間、更新時間狀態、摘要及封口時間窗；核對五層分析鍵、每層非空段落及來源、六個政治／地緣政治掃描領域及 findings。不得把截稿時間外消息混入本期。
5. **收據本身：** 產生 `simulation-lab/output/prebuild-stage-input-receipt.json`，狀態必須為 PASS，並計算該檔 SHA-256。Builder 執行前必須確認收據存在且 SHA 未變；任何輸入缺漏、日期／身份／SHA 不一致、main commit 不一致或執行批次不一致，均為 BLOCKED，不得呼叫 Builder。
6. **QA 綁定與封存：** QA sidecar 必須記錄收據路徑、SHA-256 及完整收據內容；核對 Fixture、行情 audit／manifest、main commit 與兩週 blob SHA 均與 Builder provenance 相符，並核對 workflow_run_id／attempt。Simulation branch 封存時，將同一收據另存至 `simulation-lab/runs/prebuild-stage-input-receipt-YYYY-MM-DD-RUN_ID.json`；commit／rebase 後及遠端回讀時都必須驗證相同 Git blob SHA。明確 main preview 交付 Gate 亦必須驗證 sidecar 內收據存在、PASS、SHA 正確及同批次；缺漏不得交付。
7. **責任邊界：** 此收據只證明 Stage 2–4 輸入完整性、來源識別與批次一致性，不等於 HTML、DOM、互動、視覺或內容 QA 通過；Stage 5 仍須獨立完成所有適用 Gate。不得把 pre-build receipt PASS 單獨標示為 REVIEW_READY。

**唯一實作入口：** `simulation-lab/runner/validate_prebuild_stage_inputs.py`；其正向／負向測試由 `simulation-lab/runner/test_prebuild_stage_inputs.py` 覆蓋，Workflow wiring 由 `test_simulation_workflow_delivery_gate.py` 驗收。不得另建平行收據或第二套 Stage 2–4 流程。

### Stage 5｜唯一 HTML Builder 組裝與 QA
**輸入：** 核准母版、Manifest、Fixture、Stage 2–4 成果、PASS 的組裝前輸入收據及其 SHA-256、QA Contract。
**執行：** 正式生產只能使用經使用者核准的唯一 Builder。Builder 核准前，允許在 simulation branch 的隔離環境以候選 Builder 執行 Fixture／雙母版回歸測試；此階段只屬候選驗證，不得寫入 main、不得宣稱 Builder 已核准或正式 REVIEW_READY。所有 DOM 更新只作用於核准槽位；先產出指定日期 simulation preview，執行第 9 章 Gate 與四類 QA。只有全部適用強制 Gate 通過、Builder 精確核准、資料及內容均達 REVIEW_READY，才可進入 Stage 6 的 main preview 交付。
**輸出：** simulation branch 完整審核版 HTML、組裝收據、Stage 2–4 輸入收據、QA sidecar（含輸入收據完整內容及 SHA-256）、QA 報告、HTML SHA-256。
**驗收：** 組裝輸入完整、輸出有效、QA 全部適用強制項目通過。候選 Builder 的技術測試通過，只能標示 CANDIDATE_VALIDATED；使用者尚未核准 Builder 路徑及 SHA 前，不得標示 SIM-1.4 REVIEW_READY。
**交接：** Stage 6 接收 HTML 本體、SHA、QA 報告、來源與母版識別。

### Stage 6｜審核版交付
**輸入：** Stage 5 simulation branch 的 REVIEW_READY sidecar、完整 QA 證據及唯一 HTML Git blob SHA／SHA-256。
**執行：**
1. 先將 simulation HTML 與 QA sidecar commit 並 push 至 simulation branch；回讀遠端兩檔，確認與本次 QA 輸出完全一致。
2. 只有 sidecar 同時滿足 `status=QA_PASSED`、`review_ready=true`、`data_review_ready=true`、`content_analysis_gate=PASS`、`sim14_builder_approval=APPROVED`、`sim14_review_ready=true`、`sim14_blockers=[]`，且 `report_git_blob_sha` 等於實際 HTML Git blob SHA，才具備交付資格；此資格不等於使用者已授權 main 寫入。
3. 必須先提供 Simulation 審核版及 QA Sidecar 給使用者檢視。只有使用者明確核准該份 HTML 的確切 SHA-256 後，才可進入 main preview 交付；不得以「review_ready=true」、排程觸發、push tag、先前日期核准或概括口頭同意代替。
4. main 交付必須由使用者在審核後另行明確授權，並傳入64位小寫十六進位的已核准 HTML SHA-256；該值必須與 QA sidecar 的 `report_sha256` 及實際 HTML SHA-256 完全一致。任何缺漏或不一致均在讀取／寫入 main 前 BLOCKED。目前 Simulation-only Workflow 不具備從 default branch 觸發 main 交付的條件；若要採用 `workflow_dispatch`，必須先取得使用者對將 main-capable delivery workflow 加入 main 的獨立授權。一般 build、push tag、每日 05:25 排程永遠只產生 Simulation 審核版。
5. 將同一 HTML bytes 與同一 QA sidecar bytes 原樣複製至 main：`preview/YYYY-MM-DD-review.html`、`preview/YYYY-MM-DD-review.qa.json`。禁止重新呼叫 Builder、改寫 sidecar、修補 HTML 或改變任何內容。
6. 在 main 同次 commit 新增 `preview/YYYY-MM-DD-review.delivery.json`，記錄來源 simulation branch／commit／workflow run、兩份來源路徑、HTML Git blob SHA 與 SHA-256、QA sidecar Git blob SHA、使用者核准的 SHA、交付時間及狀態。交付收據不得改寫 QA sidecar。
7. push main 前先 fetch 最新 main，僅在獨立 worktree 套用三個白名單檔案；若遇衝突或目標路徑已有不同內容，停止並標示 BLOCKED，不得覆蓋或強制推送。
8. push 後從遠端 main 回讀 HTML、sidecar、delivery receipt；驗證 HTML／sidecar Git blob SHA 與 simulation 完全相同，且收據記載值吻合。交付完整性檢查不重跑完整 QA。
9. Pages URL 只有在實際開啟成功後才標示可預覽；否則明確標示尚未部署／未驗證。
**輸出：** main preview 可預覽連結、simulation／main 雙端回讀 SHA、交付收據、原 QA 摘要及未結事項。
**驗收：** 只驗證交付路徑、存在性、原樣 SHA、sidecar 綁定及收據完整；不再執行第二次完整內容／DOM／視覺 QA。
**權限：** 僅可寫入上述 main `preview/` 三個指定檔案；絕不修改 `index.html`、正式母版、Manifest、正式行事曆 JSON 或歷史報告；不做歷史封存；不視為使用者已核准正式發布。

---

## 3. 行情資料契約

### 3.1 固定數量與欄位
- 固定行情共 44 項，計數組成為：全球主要市場 17 項（含 SOX）、11 大產業 ETF 11 項、美國公債殖利率 3 項、外匯 6 項、能源與貴金屬 4 項、風險情緒指標 3 項（VIX、MOVE、CNN Fear &\u0020Greed）；合計 44 項。SOX 已包含在全球主要市場 17 項，不得重複計數。ETF 已包含在 44 項，不得另加計。
- ETF：XLE、XLF、XLK、XLI、XLY、XLP、XLU、XLV、XLB、XLRE、XLC。只顯示漲跌幅，依當日漲跌幅排序，保留母版原欄位及互動。
- FedWatch 為獨立政策機率資料，不計入 44 項。
- 44 項逐項實際欄位名稱，以核准母版及 Manifest 對應版本為唯一依據；不得依本章摘要自行增刪或猜測。類別涵蓋全球主要股市、11 大產業 ETF、美國 2Y／10Y／30Y、公債／外匯／能源／貴金屬及風險情緒欄位。

### 3.2 直接讀取與鎖定
1. 正式行情由執行者直接開啟、刷新及讀取附錄 A 指定原始網頁；搜尋摘要不能代替網頁歷史數據讀值。
2. Investing.com 香港站指定歷史數據頁為相應指標首選時，必須切換至歷史數據分頁，核對指定交易日期的 Close／收盤欄及漲跌幅；不得拿盤中 Last、搜尋摘要或其他日期代替。
3. 頁面框架載入但表格未呈現，狀態是 TOOL_READ_FAILURE，不是 SOURCE_NO_DATA。記錄嘗試方式及結果，按來源契約繼續。
4. 讀取成功且標的、日期、欄位、口徑、證據完整者立即鎖定。只有來源正式更正或新證據證明身分／日期／欄位錯誤才重開。
5. 不使用 repo 內停用的行情 collector 輸出作為正式行情；既有程式只供歷史參考或 parser 測試，除非使用者另行核准重新啟用。

### 3.3 日期、交易日與商品身分
- 依各標的所屬交易所／主管機構官方交易日曆核對目標日期。只有官方確認休市才標示「休市｜原因」；來源延遲或工具讀取失敗不可推定休市。
- 現貨、CFD、期貨、連續合約、結算價及平台 Close／Last 必須分開辨識。
- **現貨指數正式收盤與漲跌幅不得由同名 CFD 取代。** 正常交易日亦不得將 CFD 當成現貨成交。CFD 只能作獨立參考欄位，明確標示 CFD、報價時間及來源；現貨市場官方休市時不得以 CFD 顯示當日現貨漲跌。
- 凡來源 quote_type 為 cfd_index_reference_series／CFD 的 44 項現貨指數，該筆正式行情 display 與 change_display 一律標示「待核實」，原始 CFD 值只能放在 rejected_reference／稽核紀錄，不得進入行情卡、總結、評論或計算。必須列入 review_ready_blockers，取得現貨／官方指數來源後才可解除。
- Builder 或 Workflow 必須有自動化負向 Gate：只要 CFD 指數記錄仍帶數字顯示，就阻止該審核版通過；不得只靠 source.note 註記或人工提醒。
- 期貨必須記錄交易所、商品代碼、交割月份、交易日期、報價類型。連續合約不得冒充單一月份官方結算。
- WTI、Brent、GC、SI 依基準日最新完整交易日成交量為主，交叉核對未平倉量、到期／交割限制及換月訊號；四者可採不同月份。歷史報告保留當時月份，不因後續換月而回寫。
- **商品可見名稱不得附加任何合約月份、合約代碼或商品根代碼**（例如 CLF27、LCOF7、GCZ6、SIZ6、GC、SI），行情列固定顯示「WTI 原油期貨」「Brent 原油期貨」「黃金期貨」「白銀期貨」，避免擠壓欄位。母版既有的「黃金期貨 GC」「白銀期貨 SI」只可作為 DOM 定位用的內部母版標籤；Fixture 必須另提供 `display_name`，Builder 只更新既有 anchor 的文字節點為上述短名稱，不得改變 href、class、父子層級或任何 DOM／CSS。完整合約代碼、月份、交易所及報價口徑統一放在收折的資料來源說明，不得出現在行情摘要列、區塊 meta 或市場觀察文字。**商品報價與日漲跌幅必須取自同一 Investing.com HK 歷史數據頁、同一合約、同一資料日期的「收市價／升跌幅」欄；不得以即時 Last、盤後 Last、即時 CFD 報價或不同月份合約替代。** `source.url` 必須與 `instrument_url` 一致，且兩者均指向該商品歷史數據頁；來源說明須列出資料日期、收市價、日漲跌幅、完整合約代碼、合約月份及交易所。
- 商品名稱的超連結必須指向 Investing.com 對應商品的歷史數據頁，並在當次輸出前直接開啟確認頁面標題、交易所及合約月份與本次選定合約相符；不可只檢查網域或沿用上一期 cid。若頁面動態換月或合約身分不符，必須更新 href 或標示待核實，不得宣稱連結驗收通過。
- 官方 settlement 與平台 Close／Last 不同時，先確認差異及商品身分；不得混用不同月份或不同交易日。

### 3.4 特殊指標
- **SOX：** 優先 Investing.com HK 半導體指數歷史頁；Yahoo Finance `^SOX` 備援／交叉核對。採現貨指數指定日期正式收盤。
- **VIX：** 優先 Investing.com HK；Cboe 歷史資料作官方交叉核對；Yahoo Finance `^VIX` 備援。採指定交易日正式收盤。
- **MOVE：** Investing.com HK 歷史頁優先；若指定日期缺值，TradingView ICE BofA MOVE 報價頁第二；Yahoo Finance `^MOVE`、CNBC `.MOVE`、EODData `INDEX:MOVE` 依序備援。必須核對指定日期、Close、時間戳與精度。
- **CNN Fear & Greed：** 優先 CNN Business 儀表板當前分數及 Last updated；Previous close 只作前收，不得冒充當前值。官方頁不可讀時依序嘗試 CNN graphdata 端點，再使用 FGScore 的 CNN Provider Index、Financial Context Tracker 的 CNN Tracker。不得使用第三方自估分數；GitHub 歷史資料只作歷史回查。
- **FedWatch：** 當次製作時讀取 Investing.com Fed Rate Monitor，記錄查核時間、目標 FOMC 會議及各利率區間機率；CME FedWatch 僅作方法與交叉核對，不得把 Investing.com 數據稱為 CME 官方數據。機率合計及視覺呈現一致；無法讀取即標待核實，不使用舊快照自行推算。

### 3.5 來源衝突及狀態
- 來源差異先比對標的、交易日期、時區、欄位、合約及口徑；無法解釋則 PENDING，不取平均、不猜值、不以舊值覆蓋新值。
- 狀態固定：VERIFIED、BACKUP_VERIFIED、PENDING、MISSING、CLOSED、NOT_APPLICABLE、NOT_TESTED。
- 未核實數字不得作為確定分析依據；主畫面保留欄位並顯示適當狀態，不得留白造成零值誤解。

---

## 4. 行事曆資料契約

1. 唯一正式路徑為 main `data/calendar/weeks/YYYY-Www.json`（ISO week）。週一讀取本週及上週；週二至週五讀取本週。
2. 工作日 04:35 排程是唯一 JSON 寫入者；早報流程嚴格唯讀。05:25 發現 04:35 後的新實際值、事件異動、缺漏或矛盾，只記錄於 Work Log 及審核版的資料來源／審核區，交由下一輪 04:35 更新。
3. 禁止 simulation 建立平行 JSON、複製資料庫、修補、merge/upsert、覆蓋或刪除正式事件。
4. 讀取時記錄 main commit SHA、週 JSON blob SHA、ISO week、timezone、updated_at、wr_version、coverage 及事件數。讀取期間版本變更，重新讀取最新版本並記錄 SHA。
5. 核對事件 ID 唯一、原始發布時間與台灣時間、國家／公司、事件類型、星等、狀態、actual、forecast、previous、來源及分頁。未到公布時間 actual=null 是正常狀態，不得預填。
6. 經濟與財報均使用 TAC 自主五星制。當週只呈現四星、五星；週一上週回顧只呈現五星。外部星等不可機械換算；評級證據不足則待核實，不列入已確認精選。
7. 經濟事件已公布時呈現實際、預期、前值（適用時）、結果及市場影響解讀；高於預期不必然利多，低於預期不必然利空。
8. 財報事件必須區分財報發布時段與電話會議／webcast 時間。postponed 必須標示已延期／改期；不得將電話會議時間當作發布時間。
9. 分頁狀態為已公布／已發布、今日公布、即將公布，並正確處理延期、取消及待核實。今日依台灣時間由早到晚；即將公布由近到遠；已公布由新到舊。事件搬移沿用穩定 ID，不得重複或遺失。
10. 每日早報只讀取與呈現 JSON，不因 coverage=incomplete 就阻斷早報；需確認必要事件集合及 schema 可用。核心事件缺失或 JSON 損壞為 BLOCKED，非核心缺漏按 PARTIAL 處理。
11. **公布狀態必須依截稿時點重新判定，不得直接照抄 JSON 的狀態字串。** 事件時間先轉換為 Asia/Taipei，再依台灣報告日期及 `report_cutoff_taipei` 分類：①已核實發布狀態／實際值且發布時間不晚於截稿者列入「已公布」；②台灣日期等於報告日期、尚未確認發布者列入「今日公布」，即使預定時刻晚於早報截稿也仍屬今日公布；③台灣日期晚於報告日期者列入「即將公布」；④預定日期已過，或報告日已知時刻早於截稿，但沒有可核實發布證據者，列入「已公布／待核實」分頁，卡片明確顯示「公布狀態待核實」，不得把原始 status 改成 released／published，不得填造 actual 或 Beat/Miss。若有可核實來源確認公告已發布、但發行公司實際值尚未核實，顯示「公告已發布；實際值待核實」，原始 status 仍維持 pending_verification。pending_verification 若事件日期／時間尚未到截稿點，仍依台灣日期放在「今日公布」或「即將公布」，卡片顯示「公布狀態待核實」，不得因 status_source 或 report_layer_status_only 旗標而提前移入已公布分頁。日期或時刻未知的報告日事件不得假設為午夜已過，應列「今日公布」。延期與取消必須明確標示，不得顯示成一般即將公布。每筆事件必須且只能出現在一個正確分頁，並驗證無重複、無遺漏。

---

## 5. 財報資料契約

### 5.1 公司與發布資料
- 美國公司依 TAC 重要性納入。非美國公司僅納入 NYSE、Nasdaq、NYSE American 等美國交易所正式掛牌普通股、ADR／ADS；OTC／OTCQX 或僅在海外掛牌者不納入。以公司 IR、交易所、SEC 或存託機構核實。
- 發布時間優先公司 IR；分清美股盤前／盤後、台灣日期及美東日期。正式季度／年度財報、自結／初步數字、月營收不得混稱。
- 公司正式公告是 actual 唯一依據；保存原文 URL、公告時間、期間、幣別、單位、EPS basis 及查核時間。

### 5.2 共識來源與選用
1. EPS 與 Revenue 分別選源，不要求兩者來自同一平台。
2. **固定順位：Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates。** Yahoo Finance 是第一順位，Investing.com 是第二順位，其餘依序遞補。
3. 每個指標依序查 Yahoo Finance、Investing.com、LSEG I/B/E/S、FactSet Estimates 的同一財報期間 Average Estimate；前一順位缺值、未提供、無法讀取、期間不符或無法取得可用平均預期時，才查下一順位。取得第一個有效平均預期後，該指標立即鎖定並停止其餘來源搜尋。
4. 每一指標一旦取得符合同公司、同財報期間的有效預估值，立即鎖定並停止該指標的後續來源搜尋；不得為了交叉核對而繼續抓取低順位來源。不得混合、平均或因數字較高／較低而任意切換。EPS 與 Revenue 可分別採不同來源；卡片標示實際採用來源及可取得的分析師人數。
5. 每一指標保存來源 URL、查核時間、資料／公告時間（若可得）、財報期間、estimate、幣別、單位、分析師數（若可得）、EPS methodology（若可得）、採用或跳過原因。
6. Yahoo observed_at 只代表 TAC 觀測時間，不得冒充供應商 data_as_of。PIT 原始回應、時間戳及 SHA 可作證據保存，但不再是一般數值判讀的先決門檻。
7. Yahoo EPS／Revenue 欄位未揭露的 methodology、Basic／Diluted 或 Revenue 指標定義，必須如實註記；不得自行推估或把未揭露口徑描述成已確認。此類註記依 5.3 的實用型數值比較規則處理，不得單獨阻斷數值判讀。

### 5.3 比較與狀態
- actual 與 estimate 必須同公司、同財報期間、同指標；比較前確認幣別、單位及可比口徑。
- EPS 保留 GAAP／Adjusted／Non-GAAP／Normalized、Basic／Diluted 等來源可得資訊。若來源未揭露完整細項，仍可做數值比較，但必須透明標註「來源未揭露口徑」，不得宣稱已完成嚴格同口徑比較。
- Revenue 核對指標定義、幣別、單位及期間。不能確認指標定義時，保留數值及來源註記，不得把不同指標冒充同口徑。
- 單位不同先作精確單位換算；幣別不同不得直接相減。只有取得可靠匯率、明確報價方向及換算時點後才可換算，並保存原始值、匯率、換算值與來源。無法可靠換算則不產生 Beat/Miss，標示「幣別不可比」。
- EPS 與 Revenue 分別計算。基本狀態：優於預期、符合預期、低於預期、尚未公布／數值尚未齊備。差異在預期值絕對值 1% 以內視為符合預期；零預期值不得用百分比門檻，按數值差及精度規則判斷並註明。負 EPS 按有號數值比較。
- 數值已齊備且可比較時必須輸出判讀，不得因缺少 PIT、分析師人數或部分方法論欄位阻斷。若幣別、單位、期間明確不相容，或發行公司明確聲明不可比較，公開狀態仍使用 pending，卡片標示「比較資料尚未齊備」並說明原因；不得建立 incomparable 第五狀態，也不得偽造 Beat/Miss。來源未揭露 GAAP／Adjusted 細節本身不得阻止數值比較。來源間估值差異以 conflict flag／註記透明揭露，不得用「共識來源分歧」取代優於／符合／低於判讀。
- EPS 與 Revenue 各自獨立；其中一項資料不足不影響另一項。公開狀態僅允許四種：beat、miss、inline、pending（優於／低於／符合／尚未公布或資料尚未齊備）；不得出現 incomparable、consensus_divergent 或其他第五種狀態。
- 卡片必須保留 EPS／Revenue 雙實績卡並列，顯示 actual、estimate、幣別／單位、狀態、來源；下方保留發布時段、兩項比較、財報判讀、股價反應及來源。手機仍維持兩欄並列。
- **財報卡片版面以 SHA 鎖定核准母版為唯一基準。** Builder 只能填入母版既有 EPS／Revenue 卡片槽位或複製母版核准原型；不得自行重建卡片外框、改寫父層 DOM、追加／覆蓋 CSS、改變卡片順序、間距、字級或桌機／手機欄數。驗收須比對輸出與對應母版的卡片 DOM 層級、class、子節點及 CSS；數值與狀態正確但版型不一致仍判定失敗。

### 5.4 公告後股價反應
- 僅對已發布、具美股上市代號且 session 明確為盤前／盤後的事件計算。
- 盤前公告：公告日收盤相對前一交易日收盤；盤後公告：下一個美股交易日收盤相對公告日收盤。先轉 America/New_York 日期。
- 缺少完整兩日 Close 不得計算；必須標示比較日期、百分比、來源與觀察區間。此為收盤至收盤變動，不可宣稱純粹由財報造成。
- 價格反應不能由財報 Beat/Miss 推定，兩者分開呈現。

---

## 6. 新聞資料契約

1. 新聞時間窗採台灣時間及原始發布時間：週一自前一個美股交易日台灣時間 12:00 起；週二至週五自前一日台灣時間 12:00 起；至本次實際截稿時間。
2. 優先鉅亨網、Investing.com；重大國際事件可採 Reuters、AP 等可靠原始報導。
3. 每則必須直接開啟原始報導，保存標題、原文 URL、原始發布時間、時區、最後更新時間（若有）、查核時間、摘要與使用區塊。
4. 搜尋結果排序時間、爬取時間、更新時間不可代替原始發布時間。無法確認原始時間者待核實或剔除。
5. 全球焦點新聞目標 5 則，以宏觀事件為主；市場熱門頭條目標 10 則，涵蓋總經、市場、企業、個股、財報、併購、AI、半導體等。兩區避免重複同一事件。
6. 行情報價、殖利率、FedWatch 機率及數據儀表板不得包裝成新聞。
7. 合格新聞不足時減少數量並說明，不杜撰、不灌水。摘要先寫事件事實、背景及影響，來源放卡片連結。

---

## 7. 市場分析與文字規格

### 7.1 週一總結
週一固定且只包含三大項，依序為「上週主軸」「風險觀察」「操作建議」。
- **上週主軸：** 回顧上週最重要且解釋市場定價變化的政策、政治、地緣、央行或企業事件；說明賣壓傳導及上週最後交易日反彈性質。槓桿去化、margin call、程式交易等只有證據支持才能寫成事實，否則標示推論。
- **風險觀察：** 聚焦本週尚未發生的數據、央行／政府政策、監管、重要財報及指引，盡可能列出核實日期、台灣時間、共識及影響資產。
- **操作建議：** 提出明確偏多／偏空／中性及可執行的進攻、防守、等待或分批策略；指出產業理由、估值／籌碼風險、節奏、部位與判斷失效條件。不得因跌幅大就建議抄底，不保證報酬。
- 週五美股行情可作週一亞洲市場的未來催化劑，但不可機械套用方向。

### 7.2 週二至週五總結
採精簡市場判斷，以當日主軸、風險及操作含意組成；不得強加週一三大項上週回顧格式。

### 7.3 全週共通
- 總結必須有市場主軸、明確立場、因果分析、市場溫度及操作方向；證據不足時說明分歧點、較可能情境及反轉條件。
- 不複製行情卡片，不逐項列出指數漲跌；數字只有在論證不可替代時才出現，同一數字在總結最多一次。
- 新聞事實、數據事實、分析推論及策略建議清楚區分。
- 禁止把資料查核、待核實項目、備援過程及 QA 狀態寫進總結。
- Market Sentiment 只判讀風險偏好、情緒指標一致性及轉折確認；不重複總結原因或策略。
- 「盤面觀察重點」及各區 📌評論說明市場現象、已核實驅動、意義、驗證條件與風險；不重複報價、不解釋技術來源口徑。
- 全球市場評論三區必須分別綁定美國、亞洲、歐洲面板，只引用該區指數與可靠區域消息；禁止跨區錯位。輸出需逐面板保存標題、評論、指數及語意檢查結果。
- 資料變動後只核對受影響區塊：總結、情緒、盤面觀察、相關評論、今日觀察及相應分頁。逐項標示已更新／核對無須修改／待核實。
- 不把相關性寫成因果；不得虛構市場敘事或精確價位。



### 7.4 分析內容品質 Gate（總結、情緒、盤面觀察與 📌評論）
本條是 Stage 4 的強制內容規格，並納入 Stage 5 資料與內容 QA；技術 build 成功、HTML 結構正確或行情數字完整，均不能替代本 Gate。

**A. 總結必須形成投資判斷**
- **週一總結：** 固定且只包含三段，依序為「上週主軸」「風險觀察」「操作建議」，不得增設平行總結項目。
- **週二至週五總結：** 依核准平日母版的五個原生摘要文字槽位呈現；目前 Manifest 鎖定的平日母版有五個槽位，Fixture 的 `summary_points` 必須恰好五筆並逐一對應。不得為了套用週一格式，把平日摘要縮成三筆；不得改造母版 DOM 或以 CSS 隱藏多餘槽位。五個槽位的標籤可依當日市場內容命名，不強制使用「當日主軸／風險觀察／操作建議」三個固定標籤。
- **主軸內容：** 指出本期最重要的市場事件／變化，以及市場正在重新定價什麼；不得只把指數漲跌換句話說。
- **風險內容：** 優先列出尚未發生、可能改變市場判斷的事件／數據／財報；有可核實日期、時間及影響路徑時應列明。沒有可靠日期／時間時不得猜測，改列可驗證的市場條件。
- **操作內容：** 必須表達投資立場（偏多、偏空、中性或防禦）、至少一項可執行動作，以及能觸發調整或推翻目前判斷的條件。依當日證據選擇相關資產／產業及操作節奏，不要求每篇總結機械式列齊所有資產、加碼、減碼、避險及失效條件。
- 策略須由已核實資料推導。若資料不足以支持單一方向，明確採中性／等待，說明分歧證據及何種條件出現後才改變立場；不得為了看似明確而虛構因果或價位。

**B. 市場評論採因果鏈，不抄行情**
每則區域或資產 📌評論以「發生什麼事 → 已核實驅動因素 → 對獲利／利率／估值／資金／供需的影響 → 後續驗證條件 → 投資應對」組成。
- 必須區分「已確認事件」「數據事實」「分析推論」「策略建議」。相關性不得寫成因果；單一新聞不得被描述為整個市場跌勢的唯一原因。
- 若無法確認漲跌主因，須直說「主因尚無法由現有證據確認」，並說明已知催化因素與仍待驗證的假說，不可自行補故事。
- 區域評論標題與內容必須一致；美國、亞洲（可涵蓋中國）、歐洲各自只引用該區指數及區域消息。不得出現美股內容放在歐洲標題、重複評論或口徑備註冒充市場評論。
- 各市場／產業／債券／匯率／商品評論不得重複行情卡已顯示的漲跌數字；只有解釋因果不可替代時才引用數字，且同一數字不得在同區評論重複。
- 債券評論必須先核對殖利率方向與避險敘事是否一致；若股債同跌／殖利率上行，不得稱公債買盤避險，除非另有同日資金流證據。
- 商品評論不得只憑價格同向或反向推定美元、利率、地緣、去槓桿為主因；須有當日來源支持，否則標示為待驗證假說。

**C. Market Sentiment 分工**
- 只判讀風險偏好、情緒指標是否同向、壓力來自股票／債券／信用哪一層，以及何種條件代表情緒改善或惡化。
- 不重複總結市場新聞，不逐項抄寫指標漲跌，不代替總結提出另一套策略；可提出風險狀態與觀察門檻，但不得把單一情緒指標當成買賣訊號。
- 指標資料日期、更新時間不一致時，必須說明觀察時點差異，不得將不同日期讀值描述為同時發生。

**D. 盤面觀察重點**
- 必須用一段話整合跨市場最重要的定價矛盾、資金／基本面傳導及下一個可驗證指標；不得只是把新聞摘要串接。
- 至少包含一個明確的投資決策含意，以及一個能推翻目前判斷的條件。

**E. 強制驗收**
- Stage 4 輸出前逐欄驗收：週一總結三段是否完整；平日摘要是否恰好對應平日母版五個原生槽位；五層深度解析標題及順序是否完整；政治／地緣政治是否完成六領域掃描並區分政策狀態；重要政治事件是否完成政策、產業、經濟、金融市場及策略的傳導鏈；基準／風險／嚴重情境是否具觸發條件與失效條件；區域標題與內容是否對應；每則評論是否具事件／驅動／影響／驗證／應對；是否重複報價、是否出現無證據因果、操作方向是否可執行。
- Stage 5 QA 必須對 Fixture 與最終 HTML 同時檢查以上內容；任一主要區塊只有漲跌幅重述、缺乏可辨識驅動／投資意涵，或操作建議無方向與條件，content_analysis_gate 必須為 FAIL，data_review_ready=false，不得標示 REVIEW_READY。
- QA sidecar 新增 content_analysis_gate（PASS／FAIL）、analysis_sections_checked（必須逐一記錄五層標題及順序）、political_geopolitical_scan（PASS／FAIL／NOT_TESTED）、political_domains_checked、political_event_status_classifications、policy_transmission_completeness、scenario_analysis_coverage、unsupported_causal_claims、duplicate_quote_restatements、actionability_findings；不可用技術 QA 的 QA_PASSED 取代。政治掃描若未執行或來源不足，必須如實標示 NOT_TESTED／PARTIAL，不得默認 PASS。
- 修正分析內容後，必須重新組裝 HTML 並重新執行受影響的內容／資料 QA；不得只改 Fixture 或只改 HTML 而不核對兩者一致。

---

## 8. HTML 組裝契約

### 8.1 Builder 唯一入口核准程序
1. 唯一 Builder 尚未核准前，任何程式不得被宣稱為正式唯一入口；SIM-1.4 不預設 `build_review_html.py` 已通過。
2. 候選 Builder 必須提交技術驗收報告，至少說明：CLI／API、必填輸入、Fixture schema、母版路徑與 SHA 驗證、行事曆唯讀及 Gate 0、財報判讀接線、DOM parser、可寫入 selector／槽位白名單、輸出路徑、錯誤處理、log／provenance、重跑冪等性。
3. 必須以核准週一與平日母版各執行至少一次；核對輸出完整保留原始 CSS／JS、DOM、互動、響應式行為；不得新增未授權 style/script、重建非授權 DOM 或把資料內容硬編碼於程式。
4. 必須測試缺少／錯誤 Fixture、Manifest SHA 不符、母版錨點缺失、main JSON 無效、JSON 版本變更、欄位缺漏、重複 ID、輸出路徑錯誤等負向案例。
5. 必須證明 Builder 不會寫 main JSON、母版、Manifest、正式首頁或其他保護檔案。
6. 通過以上測試後，提交候選 SHA、測試證據及差異報告，由使用者明確核准其路徑與 SHA。核准後 SIM-1.4 正式版只列該一個 Builder；任何其他組裝入口均禁止作每日生產路徑。
7. Builder 核准前，允許在 simulation branch 以候選 Builder 執行完整隔離測試及雙母版回歸，作為核准依據；不得將候選測試結果宣稱為 Builder 已核准、正式生產通過或 SIM-1.4 REVIEW_READY。不得以手工拼 HTML 冒充候選 Builder。
8. **本版唯一正式 Builder 已核准：** `simulation-lab/runner/build_review_html.py`，blob SHA `2cb0a90e53b10c31aca20503f93a5b324091c0a7`。核准依據：使用者於 2026-11-23 明確核准此精確路徑及 SHA；同一 SHA 已完成 GitHub Actions run `45043061827`，狀態 completed／success，涵蓋 deterministic tests、11/23 Fixture、雙母版候選 Builder 整合、來源顯示邊界、局部更新、六視窗響應式及 Fed 官員行程互動驗收。此核准僅解除 Builder approval Gate，不代表真實資料 E2E 或報告內容已通過。
9. **歷史 Builder 核准紀錄（截至 2026-11-22）：** `simulation-lab/runner/build_review_html.py`，blob SHA `16254bfa249814ac75e62cf8acbad2828f366fe6` 曾獲使用者核准，僅適用於該精確 SHA。分支後續版本 `02f2d87e12e340cb377eb99dbda42cbb77d58129` 未獲核准；其後候選版本 `2cb0a90e53b10c31aca20503f93a5b324091c0a7` 已於 2026-11-23 取得本版第 8 點所列精確核准。不同 SHA 的測試證據不得合併宣稱為同一版本通過。

### 8.2 組裝限制
- 輸入必須包含核准母版、Manifest、Fixture、44 項行情、行事曆唯讀收據、財報判讀、新聞與分析內容。
- Builder 只能更新核准內容槽位；所有 selector 綁定母版 SHA。錨點缺失、重複或父子關係錯誤即停止該區塊，禁止 fallback。
- **五層深度解析必須有正式核准的文章內容槽位：** 若週一／平日 simulation 母版、Manifest 及 Builder 尚未共同定義並核准該槽位，不得由 Builder 臨時新增 DOM、以 CSS 偽造區塊或把文章塞入總結小卡；Stage 5 必須 BLOCKED，列出缺少的母版／Manifest／Builder 核准項目，待使用者明確授權母版變更後再同步雙母版及相關 QA。單次審核版的人工預覽修改不等於永久核准生產槽位。
- 重複事件卡以核准母版原始節點 clone；保留 details/summary、tabs、radio、ID 規則、CSS、JS、字體、互動及響應式結構。
- 不得在輸出後以 CSS／JS 追加修補來掩飾 DOM 組裝錯誤；新增任何樣式／腳本需使用者明確核准並同步母版基準。
- 輸出 HTML 必須包含來源／版本 provenance：報告日期、規則 SHA、Manifest SHA、母版 SHA、QA Contract SHA、Fixture SHA、main HEAD、週 JSON SHA、Builder SHA。

---

## 9. QA、Gate 與交付狀態

### 9.1 三道流程 Gate
- **Gate 0｜輸入與權限：** 報告日期、星期情境、規則版本、Manifest、母版 SHA、QA Contract、main JSON 路徑／SHA、Fixture schema、Stage 2–4 組裝前輸入收據（PASS 且執行批次／SHA 一致）及權限均正確。失敗為 BLOCKED。
- **Gate 1｜資料與內容：** 44 項行情均有值或明確狀態；財報、行事曆、新聞及分析具來源與正確日期；關鍵商品身分錯誤不得放行。分析內容另須通過 Stage 4 的三層架構檢查（總結小卡／五層深度解析／盤面觀察重點），並通過政治／地緣政治掃描與傳導分析 Gate，否則不得 REVIEW_READY。非核心資料缺漏可 PARTIAL，但不得 REVIEW_READY。
- **Gate 2｜HTML 與 QA：** 候選 Builder 的隔離測試、HTML 結構、互動、視覺及資料呈現適用項目全部通過，才可標示 CANDIDATE_VALIDATED；只有使用者明確核准該 Builder 路徑及 SHA 後，才可將它升格為唯一生產入口並標示 SIM-1.4 REVIEW_READY。強制項目未通過不得 REVIEW_READY。
- QA sidecar 必須保存 `prebuild_input_receipt_path`、`prebuild_input_receipt_sha256` 及完整 `prebuild_input_receipt` 物件；收據中的 Fixture、行情 audit／manifest、main commit 與兩週 calendar blob SHA 必須與實際 Builder provenance 一致，並綁定同一 workflow run／attempt。QA sidecar 必須分開記錄 `QA_PASSED`（技術／結構／互動／視覺測試結果）、`data_review_ready`（資料與內容是否達截稿標準）、`sim14_builder_approval`（使用者是否核准指定 Builder 路徑及 SHA）及 `sim14_review_ready`（是否符合本版 Stage 5／6 的完整 REVIEW_READY）。`review_ready` 舊欄位只表示資料層狀態，不得單獨代表 SIM-1.4 REVIEW_READY；Builder 未核准時 `sim14_review_ready` 必須為 false。

### 9.2 四類 QA（檢查範圍，不是四道 Gate）
1. **資料與內容 QA：** 日期、行情基準日、44 項欄位、商品身分、來源、行事曆事件、財報實際／共識、新聞時間窗、數字與分析一致；另核對總結小卡是否精簡、五層分析是否完整且順序正確、政治事件分類與傳導鏈是否有證據、基準／風險／嚴重情境是否完整、盤面觀察是否精簡不重複、操作建議是否包含具體動作／觸發條件／失效條件。
2. **母版結構 QA：** 母版 SHA、DOM 錨點、ID 唯一、區塊／卡片數、欄位、連結、CSS／JS 完整、差異白名單。
3. **互動功能 QA：** tabs、radio、導航、details／summary、經濟／財報展開控制、來源展開、連結與觸控行為；如母版包含工具欄說明泡泡，另測首次捲動／觸控移動立即隱藏及呼吸燈獨立持續。
4. **視覺回歸 QA：** 320、360、390、412、768、1440px；檢查上漲紅／下跌綠、五星標題 TAC 紅、中文名稱／英文代碼層級、字級、間距、卡片、排序、對齊、溢位，並確認繁體中文字型實際載入。未實際執行的尺寸或字型檢查標 NOT_TESTED，不可宣稱通過。

### 9.3 QA 範圍與重跑
- 完整早報首次交付前執行一次全範圍 QA。
- QA 後新增單次專題，不要求無差別重跑整份早報 QA；必須對新增區塊及其影響的 DOM、樣式、互動、資料來源與手機版範圍執行定向 QA，並標示該區塊未納入原 QA。不得將未測試寫成通過。
- 任何變更影響母版結構、共用 CSS／JS、全域導航、核心行情、行事曆事件分類或多區分析時，必須擴大重跑受影響 QA；重大結構變更重跑完整 QA。
- QA 後任何 HTML 內容變更都使原 HTML SHA 定版失效。重新產出新 SHA，對受影響範圍重新 QA；不得沿用舊定版。

### 9.4 定版、QA 豁免及發布
- 「定版」只代表使用者核准一個明確 HTML SHA，不是一般的「看起來可以」或對某日期的概括同意。
- 核准後 HTML 任何位元變更，原核准失效，必須重新識別 SHA 並取得新的明確授權。
- QA 豁免須由使用者明確指定要豁免的 Gate／測試項目及目標 SHA；紀錄理由、風險及未測試／未通過狀態。不得把豁免標示成 QA 通過。
- 不得豁免已知重大行情日期錯誤、商品身分冒用、正式行事曆 JSON 被早報寫入、未授權修改 main／母版／首頁等權限違規。
- 審核版、正式首頁、歷史封存是三個獨立狀態：審核版不等於正式發布；Pages 部署成功不等於內容 QA 通過；正式首頁更新不自動代表歷史封存完成。
- main preview 交付及正式首頁更新均須使用者明確核准指定審核版 HTML SHA；審核版審閱、main preview 交付、正式首頁更新是三個獨立授權狀態。正式首頁更新前另須使用者對 main preview 中已唯一識別的 HTML SHA 明確核准；發布後回讀首頁 SHA／內容並確認部署。歷史封存另行執行，只在正式發布後新增／核對 history，並驗證首頁未被封存流程修改。

---

## 10. 狀態管理、恢復與計時

### 10.1 Session State 與 Work Log 分工
- `TAC_SESSION_STATE.md`（Repository 根目錄）：當前活動任務的唯一狀態錨點。只保存目前報告日期、最後完成階段、輸入／輸出路徑及 SHA、各階段狀態、待處理項目、下一步及恢復位置。
- `TAC_WORK_LOG.md`（Repository 根目錄）：追加式重要證據紀錄。保存關鍵來源查核、重要裁決、修正、QA 結果、發布／交付回讀及時間紀錄；不複製整份 Session State。
- 本次實際核對確認上述兩檔均存在於 Repository 根目錄；本規範不得將它們誤報為 simulation-lab 子目錄檔案或缺檔。若未來路徑／檔案確實不存在，先列為 STATE_STORE_MISSING，核對 Git tree 後再依授權處理；不得虛報讀取或建立。
- 不另建 Snapshot、第二份台帳、第二個 session、流程協調器或平行資料庫。

### 10.2 階段交接
每階段完成後，先重新 fetch 並完整讀取最新 SIM-1.4 主文、記錄規則 SHA，再更新 Session State；重大來源裁決、修正、Gate／QA 結果同步追加 Work Log。下一階段開始前再次完整讀取最新 SIM-1.4，核對 SHA 及本階段條款，並確認必要輸入路徑及 SHA 存在且可讀；只接收完整可用部分，未完成項目保留狀態，不得口頭跳關。
中斷恢復時讀取最新規則、Session State、Work Log 及所指向來源，從最後有證據的交接點繼續；來源 SHA 未變且成果仍存在者不得重做。

### 10.3 計時
每階段記錄實際開始／結束時間（Asia/Taipei）、有效工作時間、等待時間、重試時間及阻塞原因。計時不能與完成狀態矛盾；若紀錄矛盾，以檔案、commit、輸出及原始來源證據重建，無證據不得認定完成。

---

## 11. 正式發布、封存與版本管理

1. simulation 審核版僅依當次授權寫入指定 preview 路徑；寫入後 fetch 回讀，核對日期、內容、commit SHA、blob SHA 及 HTML SHA-256。
2. Pages 實際開啟驗證另記錄網址、時間、部署狀態及頁面內容；若無法驗證，明確標示「GitHub 已寫入、Pages 未驗證」。
3. 使用者核准指定 HTML SHA 後，才可進行正式首頁更新。首頁更新前讀取最新首頁與 SHA；更新後回讀並驗證只改授權範圍。
4. 歷史封存只在正式發布後執行；獨立核對歷史路徑與內容，驗證 `index.html` 未被封存流程修改。
5. 社群分享文案是發布後獨立產物，不得影響早報 QA 或發布授權。
6. 本文件核准生效後，SIM-1.3 完整保留為歷史版；舊規則不得再被引用為有效規定。任何 SIM-1.4 修訂均直接修改唯一規則主文及變更紀錄，不得新增補充條文堆疊。

---

## 附錄 A｜44 項行情來源與欄位核對表

### A1. 固定欄位基準
44 項固定欄位以核准母版實際欄位為唯一計數依據。類別計數為全球主要市場 17（含 SOX）、ETF 11、美債 3、外匯 6、能源與貴金屬 4、VIX／MOVE／CNN 情緒 3，合計 44。下列清單明列各類別名稱；實際欄位 selector／標籤與連結仍須由核准母版逐項抽取，避免只憑摘要判斷欄位對應：
- 全球主要市場：道瓊、S&P 500、Nasdaq Composite、Russell 2000、SOX、Nikkei 225、KOSPI、台灣加權、Singapore STI、S&P/ASX 200、上海綜合、深證成指、Hang Seng、FTSE 100、DAX、CAC 40、STOXX Europe 600。
- 11 大產業 ETF：XLE、XLF、XLK、XLI、XLY、XLP、XLU、XLV、XLB、XLRE、XLC。
- 美國公債：2Y、10Y、30Y。
- 外匯：DXY、USD/TWD、EUR/USD、GBP/USD、AUD/USD、USD/JPY。
- 能源及貴金屬：WTI、Brent、Gold GC、Silver SI。
- 風險情緒：VIX、MOVE、CNN Fear & Greed；SOX 已列於全球市場清單。FedWatch 獨立列示。
- 以上分類計數合計 44；Stage 1 必須核對本附錄 A1.1 的 44 欄 selector／標籤／href；若母版 SHA 改變、任一欄缺失或兩份母版不一致，即 BLOCKED，不能自行補想像標的。

### A1.1 核准母版實際 44 欄位／DOM 定位表（已抽取）

**抽取基準**
- Simulation Manifest：`simulation-lab/baseline/mother-template-manifest.json`，SHA `c78338984192a9251adc247ae1b0044629de89db`。
- Monday baseline：`simulation-lab/baseline/monday-mother-template.html`，SHA `ce15c803cc778be35302eec96f6a5d123bf49624`。
- Weekday baseline：`simulation-lab/baseline/weekday-mother-template.html`，SHA `940761077a3f3ad1b47b325a8d2a1a6800e3a679`。
- 44 欄位定位已在更新後雙母版回歸中確認未因新增五層文章槽位而改變；每日仍以 Manifest 與 SHA 鎖定母版為準。
- 對應正式母版 SHA：Monday `a568e594e55909041d51d8eae7e6fe5f7986c096`；Weekday `3785405e331b10ec6189002e480be2a1edbe20ef`。
- 下表以兩份 SHA 鎖定 simulation baseline 的實際 HTML anchor／href 抽取。兩份母版使用相同的 44 欄位類型、名稱及固定連結；17 項全球指數順序一致。11 檔 ETF 的示範排名順序在兩份母版不同（母版內是不同日期的示範漲跌排序），每日必須按當日核實漲跌幅重新排序，不得沿用任一母版的示範排名。

| # | 類別 | 母版標籤 | DOM 定位 | 母版固定 href |
|---:|---|---|---|---|
| 1 | 全球指數 | 道瓊工業指數 | `#global-markets #tac-global-panel-0 .row a.global-index-link（面板內第 1 筆）` | https://hk.investing.com/indices/us-30 |
| 2 | 全球指數 | 標普500指數 | `#global-markets #tac-global-panel-0 .row a.global-index-link（面板內第 2 筆）` | https://hk.investing.com/indices/us-spx-500 |
| 3 | 全球指數 | 那斯達克綜合指數 | `#global-markets #tac-global-panel-0 .row a.global-index-link（面板內第 3 筆）` | https://hk.investing.com/indices/nasdaq-composite |
| 4 | 全球指數 | 羅素2000指數 | `#global-markets #tac-global-panel-0 .row a.global-index-link（面板內第 4 筆）` | https://hk.investing.com/indices/smallcap-2000 |
| 5 | 全球指數／SOX | 費城半導體指數 | `#global-markets #tac-global-panel-0 .row a.global-index-link（面板內第 5 筆）` | https://hk.investing.com/indices/phlx-semiconductor |
| 6 | 全球指數 | 香港恆生指數 | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 1 筆）` | https://hk.investing.com/indices/hang-sen-40 |
| 7 | 全球指數 | 上海綜合指數 | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 2 筆）` | https://hk.investing.com/indices/shanghai-composite |
| 8 | 全球指數 | 深證成指 | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 3 筆）` | https://hk.investing.com/indices/szse-component |
| 9 | 全球指數 | 日經 225 | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 4 筆）` | https://hk.investing.com/indices/japan-ni225 |
| 10 | 全球指數 | 韓國 KOSPI | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 5 筆）` | https://hk.investing.com/indices/kospi |
| 11 | 全球指數 | 台灣加權指數 | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 6 筆）` | https://hk.investing.com/indices/taiwan-weighted |
| 12 | 全球指數 | 新加坡海峽時報指數 STI | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 7 筆）` | https://hk.investing.com/indices/singapore-straits-time |
| 13 | 全球指數 | 澳洲 S&P/ASX 200 | `#global-markets #tac-global-panel-1 .row a.global-index-link（面板內第 8 筆）` | https://hk.investing.com/indices/aus-200-historical-data |
| 14 | 全球指數 | 英國 FTSE 100 | `#global-markets #tac-global-panel-2 .row a.global-index-link（面板內第 1 筆）` | https://hk.investing.com/indices/uk-100 |
| 15 | 全球指數 | 德國 DAX | `#global-markets #tac-global-panel-2 .row a.global-index-link（面板內第 2 筆）` | https://hk.investing.com/indices/germany-30 |
| 16 | 全球指數 | 法國 CAC 40 | `#global-markets #tac-global-panel-2 .row a.global-index-link（面板內第 3 筆）` | https://hk.investing.com/indices/france-40 |
| 17 | 全球指數 | STOXX Europe 600 | `#global-markets #tac-global-panel-2 .row a.global-index-link（面板內第 4 筆）` | https://hk.investing.com/indices/stoxx-600 |
| 18 | 產業 ETF | XLE 能源 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLE 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr-energy-select-sector-fund |
| 19 | 產業 ETF | XLK 資訊科技 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLK 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr-select-sector---technology |
| 20 | 產業 ETF | XLRE 房地產 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLRE 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/real-estate-select-sector-spdr?cid=959413 |
| 21 | 產業 ETF | XLU 公用事業 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLU 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr-select-sector---utilities |
| 22 | 產業 ETF | XLB 原材料 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLB 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr-materials-select-sector-etf |
| 23 | 產業 ETF | XLV 醫療保健 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLV 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr---health-care |
| 24 | 產業 ETF | XLI 工業 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLI 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/industrial-sector-spdr-trust |
| 25 | 產業 ETF | XLF 金融 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLF 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/financial-select-sector-spdr-fund |
| 26 | 產業 ETF | XLY 非必需消費 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLY 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr-consumer-discr.-select-sector |
| 27 | 產業 ETF | XLC 通訊服務 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLC 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/communication-services-select-spdr |
| 28 | 產業 ETF | XLP 必需消費 | `#industry-bonds-fx-commodities .sector-list .sector-row（以內含 ticker XLP 的 a.tac-sector-link 識別）` | https://hk.investing.com/etfs/spdr---consumer-staples |
| 29 | 美債 | 2年期美債殖利率 | `#industry-bonds-fx-commodities #bonds .row a.global-index-link（卡片內第 1 筆）` | https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield |
| 30 | 美債 | 10年期美債殖利率 | `#industry-bonds-fx-commodities #bonds .row a.global-index-link（卡片內第 2 筆）` | https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield |
| 31 | 美債 | 30年期美債殖利率 | `#industry-bonds-fx-commodities #bonds .row a.global-index-link（卡片內第 3 筆）` | https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield |
| 32 | 外匯 | DXY 美元指數 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 1 筆）` | https://www.investing.com/indices/usdollar |
| 33 | 外匯 | USD/TWD 美元／新台幣 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 2 筆）` | https://hk.investing.com/currencies/usd-twd-historical-data |
| 34 | 外匯 | EUR/USD 歐元／美元 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 3 筆）` | https://hk.investing.com/currencies/eur-usd |
| 35 | 外匯 | GBP/USD 英鎊／美元 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 4 筆）` | https://hk.investing.com/currencies/gbp-usd |
| 36 | 外匯 | AUD/USD 澳幣／美元 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 5 筆）` | https://hk.investing.com/currencies/aud-usd |
| 37 | 外匯 | USD/JPY 美元／日圓 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 6 筆）` | https://hk.investing.com/currencies/usd-jpy |
| 38 | 商品 | WTI 原油期貨 | `#industry-bonds-fx-commodities #tac-assets-panel-3 .energy-card .row a.global-index-link（卡片內第 1 筆）` | https://hk.investing.com/commodities/crude-oil |
| 39 | 商品 | Brent 原油期貨 | `#industry-bonds-fx-commodities #tac-assets-panel-3 .energy-card .row a.global-index-link（卡片內第 2 筆）` | https://hk.investing.com/commodities/brent-oil |
| 40 | 商品 | 黃金期貨 GC | `#industry-bonds-fx-commodities #tac-assets-panel-4 .row a.global-index-link（卡片內第 1 筆）` | https://hk.investing.com/commodities/gold |
| 41 | 商品 | 白銀期貨 SI | `#industry-bonds-fx-commodities #tac-assets-panel-4 .row a.global-index-link（卡片內第 2 筆）` | https://hk.investing.com/commodities/silver |
| 42 | 風險情緒 | VIX | `#sentiment .sbox a[href="https://hk.investing.com/indices/volatility-s-p-500"]` | https://hk.investing.com/indices/volatility-s-p-500 |
| 43 | 風險情緒 | MOVE | `#sentiment .sbox a[href="https://hk.investing.com/indices/ice-bofaml-move"]` | https://hk.investing.com/indices/ice-bofaml-move |
| 44 | 風險情緒 | CNN Fear & Greed | `#sentiment .cnn-fg-preview`（卡片內 CNN 官方頁連結） | https://edition.cnn.com/markets/fear-and-greed |

**計數驗證：** 全球指數 17 + 產業 ETF 11 + 美債 3 + 外匯 6 + 商品 4 + 風險情緒 3 = **44**。FedWatch 位於獨立 Fed 區塊，不計入 44。ETF 顯示規則仍為僅顯示漲跌幅並依漲跌幅排序；兩份母版 11 檔 ticker 與 11 個唯一 href 完全一致，但示範排名順序不同，不得把母版示範排名當作每日排序。實際抽取確認：兩份母版各有 17 個全球市場 row、11 個唯一 ETF href、3 個債券 row、6 個 FX row、4 個商品 row，且 VIX／MOVE／CNN 三卡均存在；合計 44。

**限制：** 上表已抽取母版標籤、定位及固定 href；這不代表示範行情數值是當日行情，也不取代每日直接開啟歷史數據頁核對。表內第 n 筆定位是對應母版 SHA 下的 DOM row 順序索引，不是可跨版本沿用的 CSS nth-of-type；若 SHA 變更，先更新 Manifest 並重建欄位定位契約，否則 BLOCKED。

### A2. 指定來源
- SOX：Investing.com HK `https://hk.investing.com/indices/phlx-semiconductor-historical-data`；Yahoo `^SOX` 備援／交叉核對。
- VIX：Investing.com HK `https://hk.investing.com/indices/volatility-s-p-500`；Cboe `https://www.cboe.com/tradable_products/vix/vix_historical_data` 官方交叉核對；Yahoo `^VIX` 備援。
- MOVE：Investing.com HK `https://hk.investing.com/indices/ice-bofaml-move-historical-data`；TradingView ICE BofA MOVE 第二；Yahoo `^MOVE`、CNBC `.MOVE`、EODData `INDEX:MOVE` 後續備援。
- CNN：`https://edition.cnn.com/markets/fear-and-greed`；官方資料端點 `https://production.dataviz.cnn.io/index/fearandgreed/graphdata`；FGScore `https://fgscore.com/en/markets/sp500`；Financial Context `https://staging.fcontext.com/en/fear-and-greed`。
- FedWatch：Investing.com `https://www.investing.com/central-banks/fed-rate-monitor`；CME `https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool` 只作方法及交叉核對。
- **美國公債殖利率 2Y／10Y／30Y：Investing.com 對應歷史資料頁為第一優先來源**，必須直接讀取指定交易日期的 Close 欄：2Y 歷史資料頁 `https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield-historical-data`（商品主頁 `https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield`）；10Y 歷史資料頁 `https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data`（商品主頁 `https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield`）；30Y 歷史資料頁 `https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield-historical-data`（商品主頁 `https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield`）。三個期限各自獨立核對，不得合併 URL；必須使用相同資料日期並核對殖利率標的及 Close 欄位。美國財政部 Daily Treasury Par Yield Curve Rates `https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics` **僅供交叉核對，不得取代 Investing.com 成為第一順位來源**。頁面框架載入但歷史資料表／Close 欄無法讀取時標記 `TOOL_READ_FAILURE`，不得標記 `SOURCE_NO_DATA`；不得以 HTTP 200 或非歷史頁內容視為核驗完成。
- DXY：Investing.com `https://www.investing.com/indices/usdollar-historical-data`；不得誤用 DX 期貨。
- **USD/TWD 唯一行情來源為 Investing.com。** 第一順位使用 Investing.com HK 歷史資料頁 `https://hk.investing.com/currencies/usd-twd-historical-data`，直接讀取同一歷史資料列的收盤價與日漲跌幅，核對資料日期、USD/TWD 報價方向及現貨匯率標的。若香港站該日歷史列未更新或無法讀取，只能遞補至 Investing.com 其他站點的同標的歷史資料頁；不得改用其他平台。**禁止使用台灣央行／CBC 銀行間收盤、銀行牌告匯率或自行混合不同來源補值。** Investing.com 歷史列仍無法核實時，價格與漲跌幅均標示「待核實」，不得以其他口徑替代，也不得將市場報價稱為央行官方收盤。
- EUR/USD、GBP/USD、AUD/USD、USD/JPY：Investing.com 各自歷史資料頁；核對報價方向及各市場日界線。
- WTI：CME／NYMEX Daily Settlements `https://www.cmegroup.com/market-data/daily-settlements.html`；Investing.com 歷史頁備援。
- Brent：ICE `https://www.ice.com/products/219`；Investing.com 歷史頁備援。
- Gold GC、Silver SI：CME 指定交割月份歷史／結算資料；平台備援必須同交易所、同商品、同月份及同日期。
- 其他全球指數及 11 ETF：依核准母版各欄連結及指定 Investing.com HK 歷史頁；第一優先讀取其歷史資料頁，不以 CFD 替代現貨。具體網址應由母版固定連結讀取，不得猜造。
- 若母版 44 欄中的任何項目未被以上摘要列出，以母版實際欄位及其既有連結補齊來源登記；不得因此改變 44 項數量。

---

## 附錄 B｜財報比較與計算定義

- EPS 差額 = actual EPS − selected consensus EPS；負 EPS 按有號數值。
- Revenue 差額 = actual revenue − selected consensus revenue；先統一幣別與單位。
- 符合預期容忍區：`abs(actual-estimate) / abs(estimate) <= 1%`；estimate=0 時不計算百分比，使用來源精度及絕對差規則。
- 顯示狀態：優於預期、符合預期、低於預期、尚未公布／數值尚未齊備；資料不可比時標明原因，不虛構方向。
- Yahoo 與 Investing.com 來源各自保存；EPS／Revenue 可分別採不同來源。
- PIT snapshot 是可追溯證據，不是一般數值比較必要門檻。公告前聲明必須有 TAC 實際觀測時間及原始內容證據；不得把 observed_at 冒充 provider data_as_of。

---

## 附錄 C｜行事曆欄位及狀態
必須保存穩定 event_id、事件類型、國家／公司、原始日期時間、時區、台灣時間、發布時段、電話會議時間（如適用）、actual、forecast、previous、幣別／單位、來源 URL、發布狀態、TAC 星等、資料更新時間及 coverage。05:25 早報只讀取；不得回寫 JSON。

---

## 附錄 D｜DOM 與技術驗收
以 `simulation-lab/baseline/mother-template-qa-contract.md`（QA Contract v1.21，SIM-1.4 執行附件；目前 blob SHA `e4a11261fba37fbd9deee7c6b61c9dc29a1966d6`）作為唯一詳細 DOM／互動／視覺 QA 契約；其歷史修訂紀錄中的 DRAFT 字樣僅代表當時狀態，不覆蓋本次生效決議。契約涵蓋四種財報狀態、Yahoo → Investing → LSEG → FactSet 首筆採用來源順位、雙母版固定 DOM、Fed 官員行程、FedWatch 兩卡、商品短名稱、同合約歷史收市價與來源欄位、台灣截稿行事曆分類、TAC 漲跌配色及六視窗繁中字型驗收。另明確規定總結與五層分析不得顯示來源文字／連結／收折區，內部來源證據與 receipt 必須保留；其他報告區域來源標示不變。main `母版專區/母版結構驗收清單.md` 僅供正式資產歷史／交叉參考，不是第二份 simulation 每日 QA 清單。`scripts/tac_html_binding_map.json` 是舊版文字節點映射附件，不得視為目前 Builder 動態槽位的授權清單；在完成逐 selector 對照前，不作執行依據，也不得與本 QA Contract 並列裁決。任何契約與母版 SHA 不符即停止，不得自創 selector。

---

## 附錄 E｜SIM-1.3 → SIM-1.4 條文處置摘要

| SIM-1.3 原規則／新增要求 | SIM-1.4 主文去向 | 裁決 |
|---|---|---|
| 0、0.1、0.2、A、A1、A2 | 0、1、10、11 | 合併；權限、單一權威、修改閉環集中 |
| 0.5、0.6、C 第三步、H | 2、4、9 | 合併；行事曆資料庫 04:35 唯一寫入，05:25 早報唯讀 |
| 0.7、F2、F3、F4 | 4、5 | 重寫；保留行事曆分頁、財報卡及事件狀態規則 |
| 0.8 | 5.4 | 保留並集中 |
| 0.9、D2、D3、D2-補充、D4、D5 | 3、附錄 A | 合併；現貨與 CFD 矛盾裁決為 CFD 不得取代現貨 |
| C 六階段 | 2 | 重寫為單一流程，每階段有輸入、輸出、驗收及交接 |
| D1 44 項與 ETF | 3、附錄 A | 保留；以核准母版實際欄位鎖定，不臆測差額 |
| E 新聞 | 6 | 保留並集中 |
| F1–F4 | 4、5 | 合併；行事曆與財報分開資料契約 |
| F3-補充2、4–10 | 5、附錄 B | 衝突清理；Yahoo Finance 第一順位、Investing.com 第二順位、LSEG I/B/E/S 與 FactSet Estimates 依序遞補；EPS／Revenue 分開選源 |
| G1–G4、11/17、11/19 補充 | 7 | 合併；週一／平日總結分流、三區評論綁定 |
| H | 0、2、4、11 | 重寫；只保留 04:35 JSON 更新、05:25 唯讀、preview／首頁／封存分離 |
| I | 0、9、10 | 合併；狀態、恢復、計時及 QA 重跑規則集中 |
| 第五步 QA、A1 QA 指定 | 1、8、9、附錄 D | 重寫；流程 Gate 與 QA 檢查類型分開定義 |
| 第六步發布 | 0、9、11 | 重寫；定版綁定 SHA，QA 豁免不得偽裝通過 |
| J 與所有歷史補充條文 | 獨立歷史檔 | 移至 `simulation-lab/analysis/SIM-1.4_DRAFT_HISTORY.md`，不再混入有效規則 |
| B3.2–B3.6 母版視覺／互動規則 | 1.3、9.2 | 補回上漲紅／下跌綠、中文名稱／英文代碼層級、連結範圍、五星／四星顏色、禁止恢復已刪除膠囊、工具泡泡與呼吸燈分開驗收 |
| WTI／Brent／GC／SI 商品顯示、價格與連結 | 3.3、附錄 A | 短名稱不加月份；價格／漲跌幅須等於同合約、同日期歷史頁收市列；完整合約資料留來源說明；href 直開 Investing.com 歷史頁 |
| 行事曆台灣日期／截稿狀態 | 4.9–4.11、9.2 | 同日事件即使晚於截稿仍列今日；過期未證實者待核實；跨時區先轉 Asia/Taipei；延期／取消明確標示 |
| 財報 EPS／Revenue 雙卡母版版型 | 5.3、8.2、9.2 | 保留母版 DOM／CSS／欄數；不得重建或注入覆蓋樣式 |
| Builder 唯一入口、provenance 與 sidecar 狀態 | 8.1、9.1、9.3 | 技術 PASS 不等於核准；不同 SHA 的測試證據不得合併宣稱同版雙母版通過 |

完整逐條來源、條文對照及裁決依據見 `simulation-lab/analysis/SIM-1.3_to_SIM-1.4_clause_disposition.md`。目前實作狀態、最新 SHA 與未完成 Gate 以 Session State、Work Log 及 Builder 相容性稽核為準；本附錄不重複維護每日進度。

## 版本紀錄

- 2026-11-22｜QA Contract v1.19 曾完成歷史鎖定，SHA `d266e2074134824931561972709fc189869df98e`；後續 v1.20 取代之。
- 2026-11-22｜SIM-1.4 首次真實內容雙母版 E2E 驗收完成：GitHub Actions run `45016383014` completed／success；同一 active rules、核准 Builder `16254bfa249814ac75e62cf8acbad2828f366fe6`、Manifest、QA Contract v1.19 及雙 simulation mother SHA 綁定。真實 11/23 Monday Fixture 完成 Stage 2–5 組裝、輸入收據、Builder、內容／政治掃描、DOM／互動／來源連結、雙母版 synthetic candidate integration、六視窗 QA、QA sidecar seal、Simulation 封存及遠端回讀。44 項使用 Fixture 內既有完整瀏覽器觀察紀錄，本輪未重抓來源頁或獨立重核數值；此限制已在 receipt／sidecar 明示。QA_PASSED，但 W47 23 筆歷史財報共識及 W48 3 筆經濟預期缺少可採用公告前證據，`data_review_ready=false`、`review_ready=false`、`sim14_review_ready=false`；Stage 6 main delivery 正確 SKIPPED。此記錄證明 SIM-1.4 真實內容生產 E2E 技術路徑完成，不代表該份報告可交付，也不授權修改 main／正式首頁。

**文件狀態澄清：** 本文件標題及下方「SIM-1.4 正式生效紀錄」為現行狀態依據。版本紀錄中標示「當時 DRAFT／未生效」的段落，只記錄該次修訂提出時的歷史狀態；下方仍保留的三段 DRAFT 草案內容不構成獨立有效條文。其後已採納的規則以第 0–11 節現行主文及正式生效紀錄為準；未納入主文者不生效。不得將歷史 DRAFT 標籤解讀為目前 SIM-1.4 尚未生效。

- 2026-11-22｜文件狀態澄清：明確區分歷史草案狀態與 SIM-1.4 現行正式生效狀態；不變更任何操作條文或 Gate。
- 2026-11-22｜SIM-1.4 五層市場深度解析與政治／地緣政治分析修訂（依使用者明確授權）：將市場深度解析由四層改為五層，新增政治與地緣政治局勢、政策與產業鏈傳導、宏觀經濟傳導、金融市場定價、機構資金與投資策略的固定順序；新增六領域每日掃描、政策狀態分類、事件傳導鏈、情境分析及 QA sidecar 驗收欄位。雙母版、Manifest、QA Contract 與 Builder 已完成同步；候選 Builder 的 deterministic、雙母版完整組裝（TEST_ONLY 合成文章）、DOM preservation 及六視窗瀏覽器回歸通過。後續真實市場分析內容的每日 Stage 1–6 生產 E2E 仍須獨立驗收。

- 2026-11-22｜Stage 6 審核版交付修訂：simulation 完整 QA 通過後，以同一 HTML／QA sidecar bytes 原樣交付 main `preview/YYYY-MM-DD-review.*`；main 僅做 SHA／綁定／收據完整性檢查，不重跑完整 QA。main 寫入白名單限 HTML、QA sidecar、delivery receipt 三檔；`index.html`、母版、Manifest、正式行事曆及歷史報告仍禁止修改。


- 2026-11-22：依使用者指示，落實財報共識「首筆有效值即採用、停止該指標後續來源搜尋」：Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates；EPS／Revenue 獨立選源。PIT、分析師人數、完整方法論、raw archive 等可選欄位不再阻擋數值採用；QA Contract 更新為 v1.16 DRAFT。SIM-1.4 仍在 simulation 候選驗收階段。

- 2026-11-22：依使用者明確指示，財報共識來源採用順序統一為 Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates；EPS／Revenue 獨立選源，取得第一個符合期間的有效預估值即停止該指標搜尋。PIT、分析師人數及未揭露口徑不得阻擋已取得的有效數字；不做低順位來源交叉核對。

- 2026-11-21：SIM-1.4 首次整併草案；不生效、不覆寫 SIM-1.3。
- 2026-11-21：補入商品名稱／歷史頁連結、台灣截稿行事曆分類、財報母版雙卡及 B3 視覺／互動規則。
- 2026-11-21：歷史實證與過期 SHA 快照移至 `simulation-lab/analysis/SIM-1.4_DRAFT_HISTORY.md`；本檔只保留現行候選規則與簡要處置摘要。



- 2026-11-21：依使用者最新指示，統一財報共識來源順位為 Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates；同步 Stage 3、5.2 及條文處置摘要。該次提交時為 DRAFT；其後已由下方正式生效紀錄升格並納入現行主文。

- 2026-11-22：依使用者指示新增第 7.4 節「分析內容品質 Gate」；明定總結操作建議、評論因果鏈、區域正確性、避免行情重述、情緒分工及內容 QA sidecar。SIM-1.4 仍為 DRAFT，未生效。


## 2026-11-22 歷史修訂草案（當時未生效；後續採納內容以現行主文為準）

- 修正週二至週五摘要規格與核准平日母版的結構衝突：平日母版為五個原生摘要槽位，Fixture 必須提供五筆；不再強制套用週一三段標籤，也不得縮減成三筆或改造母版。
- 修正 Builder 核准流程的內部矛盾：核准前可在 simulation branch 進行完整候選 Builder 隔離測試，測試通過標示 CANDIDATE_VALIDATED；使用者核准指定路徑及 SHA 後，才可升格唯一生產 Builder 並標示 SIM-1.4 REVIEW_READY。
- 將操作建議驗收收斂為立場、可執行動作、條件／失效訊號；避免要求每篇總結機械列齊所有資產及所有操作條件。
- 本次僅修訂 SIM-1.4 DRAFT；SIM-1.3 仍是唯一有效規則，未修改 main、正式母版、Manifest、正式首頁或正式行事曆 JSON。


## 2026-11-22 歷史補充草案｜財報來源採用簡化與停止搜尋原則（不獨立生效；採納條文以 §5.2 現行主文為準）

- Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates。
- EPS 與 Revenue 各自獨立查找；第一個符合公司及財報期間的有效數值即採用，停止該指標其餘來源搜尋。
- 不要求 PIT 快照、分析師人數、完整 GAAP／Adjusted 或其他來源交叉核對作為數值採用門檻；缺少資訊僅作註記。

## 2026-11-22 歷史補充草案｜商品可見名稱與內部合約識別分離（不獨立生效；採納條文以 §3.3 現行主文為準）

- 商品行情列固定短名稱：WTI 原油期貨、Brent 原油期貨、黃金期貨、白銀期貨；不顯示 GC／SI 根代碼，也不顯示月份或月份合約代碼。
- 為兼容 SHA 鎖定母版的既有 anchor，黃金／白銀可保留內部 Fixture key「黃金期貨 GC」「白銀期貨 SI」，另以 `display_name` 輸出短名稱；Builder 僅替換既有 anchor 文字節點，保留 href、class、DOM 層級及互動。
- 完整合約識別（如 CLF27、LCOF7、GCZ6、SIZ6）、合約月份、交易所、資料日期、收市價、漲跌幅與報價口徑，集中列於收折來源說明。


## 2026-11-22｜SIM-1.4 正式生效紀錄

- 使用者已明確授權將現有 SIM-1.4 Draft 修訂後升格為正式規範。本文件由 `simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md` 升格至唯一有效路徑 `simulation-lab/TAC_WORK_RULES_SIM.md`。
- SIM-1.3 原文已完整封存至 `simulation-lab/archive/TAC_WORK_RULES_SIM_1.3_ARCHIVE.md`；不刪除、不與 SIM-1.4 並列有效。
- 財報共識採用順位統一為 Yahoo Finance Average Estimate → Investing.com → LSEG I/B/E/S → FactSet Estimates；EPS／Revenue 各自獨立選源，首筆同公司、同期間有效值即鎖定並停止該指標後續搜尋。舊 Session State 的相反順位屬過期紀錄，不構成規則。
- 本次生效不等於 Builder 已獲核准。候選 Builder 必須依第 8 章完成技術驗收，並由使用者明確核准指定路徑與 SHA 後，才可成為唯一正式生產入口。雙母版既有候選測試證據不得冒充 SIM-1.4 生效後的完整端到端驗收。
- 生效範圍僅限 `simulation/tac-process-lab-2026-11-06`；main、正式首頁、正式母版、正式 Manifest 及正式行事曆 JSON 均未授權修改。

- SIM-1.4 首次正式生效後端到端驗收目標：2026-11-23；本次以隔離 simulation workflow 執行，不得將既有 SIM-1.3 preview／QA sidecar 沿用為新規則驗收證據。


## 2026-11-22｜SIM-1.4 Builder 歷史核准與新版唯一入口

- **歷史核准（已被新版取代）：** `simulation-lab/runner/build_review_html.py`，blob SHA `40a3bc70a22bfd1aa4798149599fbd63a1f25efa`；原依 Monday run `44964279548` 與 Weekday run `44964439803` 通過當時雙母版驗收。該 SHA 不含五層文章槽位及政治掃描能力，自新版母版／Manifest 生效後不得再用於每日生產。
- **2026-11-23 Builder 核准狀態更新：已核准。** 唯一正式生產路徑 `simulation-lab/runner/build_review_html.py`，blob SHA `2cb0a90e53b10c31aca20503f93a5b324091c0a7`；僅限 simulation branch SIM-1.4。真實資料 E2E 與報告 QA 仍須獨立完成。
- 新版 Builder 核准只解除 Builder approval Gate；真實市場分析內容的 Stage 1–6 生產 E2E、資料／內容 Gate、完整互動與視覺 QA 仍須逐項完成，未通過前不得標示 REVIEW_READY 或交付。
- 本核准僅限 simulation branch 的 SIM-1.4 Builder 入口；不構成 main、正式首頁、正式母版、正式 Manifest、正式行事曆 JSON 或 Pages 部署授權。


## 2026-11-22｜Stage 1 基準重鎖與規範附件 SHA 修正

- 更新 Appendix A1.1 的 Manifest／週一母版／平日母版 SHA，與本分支目前實際 Blob SHA 一致；44 欄位定位仍由更新後雙母版回歸確認。
- 更新 Appendix D QA Contract 版本為 v1.17，記錄目前實際 Blob SHA。
- 2026-11-23 取得新 Builder 精確核准後，§1.1 與 §8.1 已更新；目前唯一核准 SHA 為 `2cb0a90e53b10c31aca20503f93a5b324091c0a7`，先前 `16254bfa249814ac75e62cf8acbad2828f366fe6` 僅保留為歷史核准。


### Stage 2 證據分類補充（SIM-1.4 修訂，2026-11-22）
- 數值核驗狀態與證據封存狀態分開管理。數值狀態：`VERIFIED`、`BACKUP_VERIFIED`、`TOOL_READ_FAILURE`、`SOURCE_NO_DATA`、`PENDING`。證據狀態：`BROWSER_OBSERVATION_SAVED`、`RAW_RESPONSE_SAVED`、`RAW_RESPONSE_UNAVAILABLE`。
- `raw_response_sha256` 可以為 null；其缺漏不得增加 Stage 2 blocker、不得將已核驗數值降級、不得令整體行情驗證由 PASS 變成 PARTIAL。
- 每筆 `BROWSER_OBSERVATION_SAVED` 必須保存 URL、標的／合約、交易日期、實際讀取欄位和值、漲跌欄位和值、查核時間、讀取方法；將這些欄位按固定鍵序標準化後計算 `observation_record_sha256`。此雜湊只證明保存的觀察紀錄未被改動，不代表供應商 HTTP response body 的雜湊。
- 只有缺少／不一致的觀察紀錄、來源標的／日期／報價口徑不符，或數值無法對應 Fixture，才可列入 Stage 2 blocker。已完整保存的瀏覽器歷史頁觀察足以支持數值核驗，不得為了取得 HTTP body 重抓已鎖定數值。


## 2026-11-22｜Stage 2–4 組裝前輸入收據修訂

- 新增唯一 pre-build input receipt，將 44 項行情觀察證據、同一 main commit 的當週／上週行事曆、新聞時間窗及五層／政治掃描輸入，綁定同一報告日期與 Workflow run／attempt。
- Builder 執行前必須取得 PASS 收據；QA sidecar 必須保存完整收據及 SHA，Simulation branch 封存與遠端回讀需驗證 SHA；明確 main preview 交付亦須驗證收據完整性。
- 原始 HTTP response body／raw_response_sha256 仍屬可選證據；此修訂不要求重抓已鎖定的 44 項行情，也不改變 Stage 2 數值核驗標準。
- 本次只更新 Simulation 分支 SIM-1.4 規範與對應驗收程式；不修改 main、正式首頁、正式母版或正式行事曆 JSON。


### 2026-11-22 本輪候選修訂紀錄（未核准 Builder）
- 規則已補入：分析品質與因果推論、AI 融資鏈信用傳導、總結／深度分析來源只保留內部證據而不顯示、總結／分析區塊局部更新原則。
- 來源顯示規則只限總結與五層分析；新聞、行情、商品、債券、匯率及行事曆的來源顯示不變。
- Builder 與局部更新器均會清除總結卡內的來源連結／收折元件，並以 summary_source_receipt 記錄清除結果；只作用於總結卡，不觸及其他區塊。
- 局部更新器新增 `simulation-lab/runner/patch_review_sections.py`；測試新增 `simulation-lab/runner/test_patch_review_sections.py`。測試尚待 CI 執行，不得先行標示 PASS。
- 11/23 Fixture 已加入 NVIDIA SEC 10-Q 與 Reuters 11/17、10/15 報導支持的 AI 融資鏈分析；具體區分 360 億美元 AI cloud agreements、初步第三方融資平台 MOU、NVIDIA 五大客戶約70%應收帳款集中、付款期限90天至一年、基礎設施融資商33億美元投資／47億美元最大損失曝險，以及 CoreWeave／Nebius 信用重新定價；不把信用重新定價寫成違約。
- Fed 官員行程 simulation 雙母版已將手機直向排列門檻由 360px 擴大至 412px；QA Contract v1.20 與 Manifest 同步更新。413px 以上維持桌面雙欄。
- 2026-11-22 候選驗收起始紀錄：Builder SHA `2cb0a90e53b10c31aca20503f93a5b324091c0a7`；Fixture SHA `bb7ab311a05d8ac3860f94fc6ecf10423e499bef`；Manifest SHA `d47d8abece4137884bda76d6a505ba4112904e0d`；QA Contract v1.20 SHA `ddaf719d22db66b7894a02683fc92d25d87da3af`。此處為當時基準，不覆蓋後續核准紀錄。
- Monday mother SHA：`0a7d5095aaa99c470e00e67f33567ff9f359d6ae`；weekday mother SHA：`3f4e65c1385532b0f0969fdc76caf2883a39e798`。
- 上述候選驗收起始紀錄當時尚未完成 CI／瀏覽器 QA；其後已於 2026-11-22 完成同一 SHA 的 run `45043061827`，並於 2026-11-23 取得使用者明確核准。
- QA Contract v1.20 已補入 A3.5 來源隱藏與局部 DOM 更新驗收條款；原 SHA `ddaf719d22db66b7894a02683fc92d25d87da3af` 為修訂前歷史值。

- QA Contract v1.20 A3.5 再補入 summary_source_receipt 與正式 CLI 路徑防護要求；本次同步後最新 SHA：`6af0a6cd9d9e37f19f7df70956f3bff54199cf99`。

- 11/23 summary risk observation 已補入已核實的台灣時間催化點：11/23 17:00 歐元區 Flash PMI、22:45 美國 Flash PMI；11/25 21:30 美國 GDP 第二次估值與 10 月 PCE。Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- 11/23 policy_industry 已恢復獨立 CoreWeave 融資結構段落，保留 Microsoft 約67%客戶集中、GPU／合約擔保貸款、私募信貸、銀行聯貸、公司債及可轉債；Fixture 最新 SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- NVIDIA SEC 文件期間已更正為 2027 會計年度第二季（截至 2026/07/26），避免誤寫成日曆年第二季；Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- 11/23 markets 段落已將制式「市場仍需分辨」改成可驗證條件：信用利差與GPU容量利用率是否同步惡化，以及主要客戶是否下修容量合約；Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- Builder summary cleanup 已擴大涵蓋 `.source`／`.source-list` 獨立來源容器，局部更新測試加入獨立來源文字案例；最新 Builder 候選 SHA：`2cb0a90e53b10c31aca20503f93a5b324091c0a7`，尚未核准。

- AI 融資鏈分析再補入 NVIDIA 對 SB Energy／OpenAI PORTS 園區最高 1,050 億美元有條件信用支持、約4.25GW／20年租約條件，以及2790億美元供應與產能承諾；明確區分專案保證上限與全體債務保證。Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- NVIDIA SEC 10-Q 對AI雲端業者融資能力的自我揭露已納入：需求存在但缺乏長期基礎設施合約與投資級融資能力，資本不足可能延後GPU採購；供應與產能承諾由前一季1,190億升至2,790億美元。Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- 11/23 AI融資鏈已改用最新 NVIDIA FY2027 Q3 CFO Commentary（11/17）：供應鏈採購承諾3900億（主要為多年度記憶體採購）、NVIDIA自身研發雲端／租賃承諾1020億、neocloud協議320億（須融資、部署及驗收才生效）、保證最大總曝險1180億（截至報告日尚未支付保證款）、應收帳款810億／DSO64天；Q2 10-Q僅保留為歷史補充，避免舊數據冒充最新。Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- Q3 1180億美元已明確標示為「保證最大總曝險」，避免讀者誤認為當期已支付或已形成同額現金負債；Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- 11/23分析補入NVIDIA Q3營收與資料中心成長（營收1158億、資料中心1076億、AI Clouds／Industrial & Enterprise平台475億、年增195%），以實際需求數據平衡融資風險判讀；Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。

- SB Energy／OpenAI信用支持補入首棟預計FY2029啟用及額外3.8GW分階段支持選項，明確區分目前1180億美元最大曝險與未來可能擴大的選項；Fixture SHA：`bb7ab311a05d8ac3860f94fc6ecf10423e499bef`。


## 2026-11-23｜使用者核准 SIM-1.4 Builder 精確 SHA

- 使用者明確核准唯一 Builder：`simulation-lab/runner/build_review_html.py`，Git blob SHA `2cb0a90e53b10c31aca20503f93a5b324091c0a7`。
- 核准前同一 SHA 的 GitHub Actions run `45043061827` completed／success；雙母版整合、五層分析來源隱藏、內部來源證據保留、局部更新及 320／360／390／412／768／1440px QA 均通過。
- 核准範圍僅限 simulation 分支 Builder 唯一入口；不授權 main、正式母版、Manifest、行事曆 JSON、首頁或 Pages 部署。
- 核准後下一步為 2026-11-23 真實 Fixture 完整 E2E；報告是否 REVIEW_READY 由實際資料／內容 Gate 與 QA 決定，不得由 Builder 核准推定。

- 2026-11-23 W48 最新主分支資料已修正 Williams 行程事件的 impact_judgment；Fixture 移除該筆已不再需要的 override，只保留四筆仍有來源網址誤置的事件修復。未修改 main。同步更新 fixture 測試與 preflight 預期修復數為4；最新 Fixture SHA：`58c2a0bd93d23af17b080ae0e3fcb4b162ecaa93`。W48 主分支 SHA：`9bb842ab475fa38ca6407304990d1cd3fae42c63`。

- 2026-11-23 W48 財報預估投影已依同一 main commit `f68b4d6d5ae3b5cf9dcf1c1cb49cc420f67176fb` 與 W48 blob `9bb842ab475fa38ca6407304990d1cd3fae42c63` 更新；11筆估值紀錄均與 authoritative W48 的 event_id、台灣時間 event_date 及 reporting_period 完全吻合。HPE 來源發布日期 11/23 轉為台灣電話會議時間 11/24 06:00；Deere 11/25 轉為台灣時間 11/25 23:00，原來源發布日期保留。Projection SHA：`8ddf96ab3c333d65e8e21386bcf052884efbb2d3`；新增 preflight 對 main commit／calendar SHA／event timestamp／reporting period 的逐筆核對。

- W48 consensus projection preflight 已改用標準 Python `assert` 執行 SHA／event_id／台灣時間 event_date／reporting_period 四項核對，避免引用未定義 helper；最新 preflight script SHA：`787cd06d05b3a93835a4d771092389baa8dffcbf`。


- 2026-11-23｜QA Contract v1.21 同步 A2.1 兩份 simulation mother SHA（Monday `0a7d5095aaa99c470e00e67f33567ff9f359d6ae`、Weekday `3f4e65c1385532b0f0969fdc76caf2883a39e798`），並明確加入總結／五層來源可見性與內部 evidence receipt 分離驗收；最新 QA Contract SHA：`e4a11261fba37fbd9deee7c6b61c9dc29a1966d6`。main 正式母版與首頁未修改。
- 2026-11-23 W47唯一五星NVDA財報卡的公告前Yahoo共識已載入report Fixture：EPS平均預估2.47121（43位分析師）、Revenue平均預估USD108.7319039B（45位分析師）；原始response SHA `5a20857e65c628b2ce0236b48a1414e8b361eef6e90c446a875b8ed1e3773a2a`、capture file blob SHA `46f9a7cc59b5fb6714219f053ce48b0da7dc9e52`。依報告日SIM-1.4來源順位Yahoo為第1順位，原始capture source_level=4保留為歷史順位。Fixture層的TAC 1.4比較結果為EPS數值高9.26%、Revenue數值高6.50%，但當時尚未整合至HTML；不可將Fixture有資料誤認為卡片已顯示。Main W47 JSON唯讀。此階段 Fixture SHA `c4f4a51e423b844bf799bbe488b74c8d678b6199`、test SHA `b55c6b016bddde98ccd61121aaa1320b5957343b` 為歷史值。

- 2026-11-23 Chart 3 ALFRED incremental maintenance已完成並更新main HEAD至`09e0e5fe64a781373464858fb70c800e4ffbf098`；W47／W48行事曆blob仍分別為`727ea2be1c04688d3c4f98d36c452561bbab6821`及`9bb842ab475fa38ca6407304990d1cd3fae42c63`，內容未變。W48 consensus projection main commit pin同步更新；最新 Projection SHA：`256c86a424b76e0b9cb4a85f915ea3ddac62f4b1`。Main全程唯讀，僅更新simulation投影的來源commit metadata。

- 2026-11-23｜QA Contract v1.21 已加入 W47 NVDA公告前共識局部overlay與receipt-to-final-HTML SHA gate；最新 SHA：`e4a11261fba37fbd9deee7c6b61c9dc29a1966d6`。
- 2026-11-23｜E2E run `45072970310` 雖技術 QA_PASSED，但實際 HTML 的 W47 NVDA 卡仍顯示「預期未取得」，未呈現Fixture已準備的Yahoo共識；該run及其review_ready sidecar正式標記為不可交付／失效，不得引用為完成。根因：Builder從main W47重新載入已公布事件，既有actuals overlay不套用Fixture共識欄位。
- 2026-11-23｜不修改已核准 Builder `2cb0a90e53b10c31aca20503f93a5b324091c0a7`；擴充 `patch_review_sections.py --section last_week_earnings`，於Builder之後只更新W47 NVDA五星卡，使用TAC 1.4判讀引擎、核對Yahoo原始capture與官方實績來源，保留-2.89%首個交易日價格反應，並產生獨立receipt。Patcher SHA：`e27901ce47f46a7f67b3b43065bc96162377ce15`；測試 SHA：`4229a82d1f414d84b8c6b85969b08916c695123b`。
- 2026-11-23｜11/23 Fixture補入NVIDIA官方Q3實績新聞稿來源，並移除歐洲市場判讀及Fed官員行程影響文字中的空泛「後續觀察」句型；Fixture SHA：`90d689feb5559f08c8de0e0837c1e4403a025645`；Fixture regression test SHA：`9ae4936f824c8c9e4c8911b741ec8ee0ea901a01`。
- 2026-11-23｜Simulation workflow新增Builder後W47 NVDA局部overlay步驟；QA sidecar必須核對overlay receipt SHA與最終HTML SHA，並檢查EPS／Revenue預估、優於預期狀態、非嚴格同口徑註記、官方實績及Yahoo共識連結。Workflow SHA：`97547723228ce44ca335ccdfd431fe6b38180961`。Main W47 JSON、main正式母版及首頁均未由本工作修改；未執行Stage 6 handoff。

- 2026-11-23｜W47 NVDA局部overlay最終實作：Builder仍寫入唯一核准的canonical preview路徑（保留 provenance mode=simulation-only）；複製Builder輸出至simulation-lab/output/candidate-validation，再由patch_review_sections.py以不同輸出路徑局部修改NVDA卡，最後回寫preview。Builder SHA保持`2cb0a90e53b10c31aca20503f93a5b324091c0a7`不變。最新patcher SHA：`e7677f0d39c438481f0ad534607fff2bbbc1301d`；patcher test SHA：`4229a82d1f414d84b8c6b85969b08916c695123b`；Fixture SHA：`90d689feb5559f08c8de0e0837c1e4403a025645`；Fixture test SHA：`9ae4936f824c8c9e4c8911b741ec8ee0ea901a01`；workflow SHA：`dd03a0abb3c5a8b280191ade3b80802987c46a48`；QA Contract v1.21 SHA：`e4a11261fba37fbd9deee7c6b61c9dc29a1966d6`。QA sidecar只有在receipt output SHA等於最終HTML SHA、且實際卡片顯示EPS／Revenue預估與來源時，才可標示review_ready。