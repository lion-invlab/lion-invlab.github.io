# TAC 投資早報｜統一模擬工作規範 SIM-1.4（審核草案）

> **狀態：DRAFT／尚未生效。** 本文件供逐條審核及 2026-11-23（一）回歸測試使用。SIM-1.3 保留為歷史基準，不覆寫、不刪除。只有使用者明確核准 SIM-1.4 定版後，才可將本文件改名／替換為唯一有效規則檔。本草案不授權修改 main、正式母版、Manifest、正式首頁或正式行事曆 JSON。

- 專案：TAC 投資早報
- Repository：`lion-invlab/lion-invlab.github.io`
- 工作分支：`simulation/tac-process-lab-2026-11-06`
- 草案日期：2026-11-21
- 前版基準：`simulation-lab/TAC_WORK_RULES_SIM.md`（SIM-1.3）
- 時區：Asia/Taipei（UTC+8）

---

## 0. 核心原則、權限與狀態

### 0.1 規則優先權
1. 使用者當次明確指示優先；其次為經核准生效的 SIM-1.4；再其次為本文件明列的唯一技術契約及資料來源契約。
2. 助理建議、聊天摘要、舊交接、歷史版本、程式註解及自動化 prompt 均不得創造或覆寫規則。
3. SIM-1.3、SIM-1.2、v5.x 及補充條文在 SIM-1.4 生效後均為歷史資料，不再與 SIM-1.4 並列有效。
4. 發生本文件內部衝突時，先依本文件的專門章節優先於一般原則；仍無法裁決時標記 BLOCKED，不得自行猜測。

### 0.2 權限邊界
- 本次規則重整及回歸測試只可修改 simulation branch 的明確指定工作檔、測試報告及審核版輸出。
- main 原則唯讀。正式母版、main Manifest、main QA 附件、`index.html`、正式歷史報告及正式行事曆 JSON 均不得由本工作修改。
- main `data/calendar/weeks/YYYY-Www.json` 是早報唯一行事曆資料來源；工作日 04:35 專用排程是唯一寫入者。早報流程 05:25 嚴格唯讀。
- 審核版可依使用者對該次任務的明確授權，寫入指定日期的 simulation preview；GitHub 寫入不代表 Pages 已部署。
- 正式首頁只有使用者對已唯一識別的審核版 SHA 明確核准後才可更新。歷史封存只在正式發布後另行執行。
- simulation workflow 不得 deploy Pages、寫 main、使用 production secrets 或自動發布首頁。

### 0.3 保護與修改閉環
每次修改前取得目標檔案最新內容與 SHA；確認授權範圍；採最小必要差異；執行相應測試；寫入後回讀並核對 SHA、內容及未授權檔案未變。不得平行寫入同一路徑。遇到 SHA 競爭或更新失敗，重新讀取最新版本並重新比對，不得強制覆蓋。

### 0.4 狀態定義
- **BLOCKED**：關鍵基準錯誤／不存在、母版或日期情境錯誤、資料來源版本無法確認、組裝器無法安全定位、核心行情身分錯誤，或權限不符；不得交付審核版。
- **PARTIAL**：必要流程可繼續，部分非核心欄位待核實／暫缺／未測試；必須完整揭露，且不得標示 REVIEW_READY。
- **REVIEW_READY**：六階段必要輸入、完整內容、HTML 組裝及所有適用強制 QA 均通過；允許交付審核版，仍不代表正式發布。
- 資料狀態另使用 VERIFIED、BACKUP_VERIFIED、PENDING、MISSING、CLOSED、NOT_APPLICABLE、NOT_TESTED；不得把未測試或暫缺轉寫成通過。
- 單一非核心欄位缺漏不得停止無依賴的其他工作；BLOCKED 項目不得偽裝為 PARTIAL。

### 0.5 30 分鐘目標
30 分鐘是流程效率目標，不是資料正確性豁免。已取得且符合標的、日期、欄位、口徑及證據的資料立即鎖定，不再重抓；後續只處理待辦項目。超時必須記錄真正耗時與阻塞原因，不得為達標跳過來源讀取、Gate 或 QA。

---

## 1. 唯一權威資產與資料基準

### 1.1 唯一規則與技術附件
- 本草案若經核准，唯一工作規範路徑為 `simulation-lab/TAC_WORK_RULES_SIM.md`；草案核准前，SIM-1.3 仍是目前有效規則。 `scripts/tac_html_binding_map.json` 為歷史映射附件，除非本草案另列其 SHA、selector 與 Builder 對照並經核准，不構成額外 DOM 寫入授權。
- 母版選擇唯一依據：`simulation-lab/baseline/mother-template-manifest.json`。
- 核准母版結構、DOM、互動與視覺的唯一詳細 QA 契約：`simulation-lab/baseline/mother-template-qa-contract.md`。main 的 `母版專區/母版結構驗收清單.md` 是正式母版來源附件，不是 simulation 每日 QA 的第二份活動清單；其結構規格只有在與 simulation 契約一致且 SHA 基準相符時供來源追溯，不得兩份交替裁決。
- 正式行事曆資料：main `data/calendar/weeks/YYYY-Www.json`，無平行資料庫。
- Builder：本版不預先指定任何程式為唯一正式 Builder。候選程式必須通過第 8 章驗收後，才可由使用者核准列入生效版唯一入口。
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

六階段是唯一生產流程。開工前及每一階段開始前，執行者都必須重新讀取當前分支最新版本的 SIM-1.4 完整主文，核對 SHA，並依該階段條款執行；每階段完成後、進入下一階段前，再次完整重讀 SIM-1.4 並核對 SHA。不得只憑記憶、摘要或前一輪讀取繼續。每階段必須保存輸入、執行、輸出、驗收及下一階段交接；不另建第二套流程。

### Stage 1｜開工基準與母版鎖定
**輸入：** 本版規則、Manifest、QA Contract、雙母版、報告日期、main 行事曆 JSON。
**執行：** 確認台灣日期／星期、行情基準日、週一或平日情境、保護範圍、各基準 SHA；讀取當週 JSON，週一另讀上週 JSON。
**輸出：** 基準清單、來源 SHA 收據、日期／母版情境。
**驗收：** 必要路徑存在、SHA 相符、日期正確、main 保護範圍清楚。失敗為 BLOCKED。
**交接：** Stage 2 使用固定報告日期、行情基準日、核准母版欄位清單與來源規格。

### Stage 2｜44 項行情及獨立 FedWatch
**輸入：** Stage 1 基準、核准母版固定欄位、附錄 A 來源契約。
**執行：** 逐項直接讀取指定原始網頁；第一輪完整掃描。符合標的、交易日、報價欄位、口徑及證據的值立即鎖定。第二輪只刷新缺值／疑義項目；第三輪只改用同一來源系統歷史頁或日期查詢；其後才按該指標規定啟用備援。已鎖定值不得無理由重查或覆寫。
**輸出：** 44 項逐項行情台帳；每項含標的身分、數值／狀態、資料日期／時區、報價欄位、來源 URL、查核時間、來源角色、口徑、實際輪次及備援原因。FedWatch 獨立紀錄，不計入 44 項。
**驗收：** 44 項每項均有數值或明確狀態；任何已核實值均有足夠證據；未核實值不流入分析作為確定事實。
**交接：** 完整行情台帳及鎖定值提供 Stage 3–5；待核實狀態一併傳遞。

### Stage 3｜行事曆與財報事件
**輸入：** Stage 1 的 main JSON SHA；Stage 2 行情；附錄 C、D。
**執行：** 早報對 JSON 嚴格唯讀；逐筆核對事件 ID、日期／時區、公司／國家、狀態、實際值、預期值、來源、星等及分頁。財報共識由 Yahoo Finance Average Estimate 優先、Investing.com 第二順位，EPS／Revenue 各自選源。
**輸出：** 經濟與財報事件顯示資料、已公布實際值、共識來源與判讀、股價反應及待核實項目。
**驗收：** JSON SHA、事件 ID 唯一、日期／時區正確、已公布實際值有來源、EPS／Revenue 分開判讀、跨幣別比較有明確換算。
**交接：** 供 Stage 4 分析及 Stage 5 組裝；不得將早報查核結果寫回 JSON。

### Stage 4｜新聞與市場分析
**輸入：** 已鎖定行情、Stage 3 事件、新聞時間窗及來源契約。
**執行：** 讀取原始報導，核對發布時間／時區；撰寫總結、Market Sentiment、盤面觀察重點、區域與資產評論、今日觀察。
**輸出：** 5 則全球焦點新聞目標、10 則市場熱門頭條目標、完整分析文稿及來源證據。
**驗收：** 不灌水、不以報價冒充新聞、不重複新聞事件；事實、推論、策略分離；總結符合週一或平日格式。
**交接：** Stage 5 接收可直接組裝的完整內容與每則新聞原文 URL、時間、查核證據。

### Stage 5｜唯一 HTML Builder 組裝與 QA
**輸入：** 核准母版、Manifest、Fixture、Stage 2–4 成果、QA Contract。
**執行：** 只能使用經核准的唯一 Builder；DOM 更新只作用於核准槽位；產出指定日期 preview。執行第 9 章 Gate 與四類 QA。
**輸出：** 完整審核版 HTML、組裝收據、QA 報告、HTML SHA-256。
**驗收：** 組裝輸入完整、輸出有效、QA 全部適用強制項目通過。未經 Builder 核准或 QA 未通過不得標示 REVIEW_READY。
**交接：** Stage 6 接收 HTML 本體、SHA、QA 報告、來源與母版識別。

### Stage 6｜審核版交付
**輸入：** Stage 5 REVIEW_READY 證據與唯一 HTML SHA。
**執行：** 寫入當次明確授權的審核版路徑；回讀檔案、核對 SHA、實際開啟預覽網址（若 Pages 發布通道已授權且可用）。
**輸出：** 可預覽連結、回讀 SHA、部署狀態、QA 摘要及未結事項。
**驗收：** GitHub 寫入、回讀內容及 SHA 一致；Pages 可開啟才可稱預覽已上線。否則明確標示尚未部署／未驗證。
**權限：** 不修改 `index.html`；不做歷史封存；不視為使用者已核准正式發布。

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
- **商品可見名稱不得附加合約月份或合約代碼**，維持母版短名稱（例如「WTI 原油期貨」「黃金期貨 GC」「白銀期貨 SI」），避免擠壓行情欄位；合約月份、代碼、交易所、報價類型及結算／Close 口徑統一放在既有資料來源補充說明。
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
2. Yahoo Finance Average Estimate 第一順位；Investing.com 第二順位。Yahoo 該指標缺值、未提供或無法讀取，才改採 Investing.com 同一期間平均預期。
3. Yahoo 與 Investing.com 均有值但不同，仍以 Yahoo 為主判讀值；不得平均、擇高低或因數值偏好切換。保留第二來源作透明度交叉參考。
4. LSEG、FactSet、Visible Alpha、Reuters 等歷史條文所列來源不再構成一般 Beat/Miss 必查階梯；可以作獨立研究佐證，但不得覆寫已選定的 Yahoo／Investing.com 基準，也不得恢復舊順位。
5. 每一指標保存來源 URL、查核時間、資料／公告時間（若可得）、財報期間、estimate、幣別、單位、分析師數（若可得）、EPS methodology（若可得）、採用或跳過原因。
6. Yahoo observed_at 只代表 TAC 觀測時間，不得冒充供應商 data_as_of。PIT 原始回應、時間戳及 SHA 可作證據保存，但不再是一般數值判讀的先決門檻。

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

---

## 8. HTML 組裝契約

### 8.1 Builder 唯一入口核准程序
1. 唯一 Builder 尚未核准前，任何程式不得被宣稱為正式唯一入口；SIM-1.4 草案不得假設 `build_review_html.py` 已通過。
2. 候選 Builder 必須提交技術驗收報告，至少說明：CLI／API、必填輸入、Fixture schema、母版路徑與 SHA 驗證、行事曆唯讀及 Gate 0、財報判讀接線、DOM parser、可寫入 selector／槽位白名單、輸出路徑、錯誤處理、log／provenance、重跑冪等性。
3. 必須以核准週一與平日母版各執行至少一次；核對輸出完整保留原始 CSS／JS、DOM、互動、響應式行為；不得新增未授權 style/script、重建非授權 DOM 或把資料內容硬編碼於程式。
4. 必須測試缺少／錯誤 Fixture、Manifest SHA 不符、母版錨點缺失、main JSON 無效、JSON 版本變更、欄位缺漏、重複 ID、輸出路徑錯誤等負向案例。
5. 必須證明 Builder 不會寫 main JSON、母版、Manifest、正式首頁或其他保護檔案。
6. 通過以上測試後，提交候選 SHA、測試證據及差異報告，由使用者明確核准其路徑與 SHA。核准後 SIM-1.4 正式版只列該一個 Builder；任何其他組裝入口均禁止作每日生產路徑。
7. Builder 核准前，本次只能做靜態檢查與候選評估，不得以手工拼 HTML 冒充唯一組裝流程，不得宣稱回歸測試完整通過。

### 8.2 組裝限制
- 輸入必須包含核准母版、Manifest、Fixture、44 項行情、行事曆唯讀收據、財報判讀、新聞與分析內容。
- Builder 只能更新核准內容槽位；所有 selector 綁定母版 SHA。錨點缺失、重複或父子關係錯誤即停止該區塊，禁止 fallback。
- 重複事件卡以核准母版原始節點 clone；保留 details/summary、tabs、radio、ID 規則、CSS、JS、字體、互動及響應式結構。
- 不得在輸出後以 CSS／JS 追加修補來掩飾 DOM 組裝錯誤；新增任何樣式／腳本需使用者明確核准並同步母版基準。
- 輸出 HTML 必須包含來源／版本 provenance：報告日期、規則 SHA、Manifest SHA、母版 SHA、QA Contract SHA、Fixture SHA、main HEAD、週 JSON SHA、Builder SHA。

---

## 9. QA、Gate 與交付狀態

### 9.1 三道流程 Gate
- **Gate 0｜輸入與權限：** 報告日期、星期情境、規則版本、Manifest、母版 SHA、QA Contract、main JSON 路徑／SHA、Fixture schema 及權限均正確。失敗為 BLOCKED。
- **Gate 1｜資料與內容：** 44 項行情均有值或明確狀態；財報、行事曆、新聞及分析具來源與正確日期；關鍵商品身分錯誤不得放行。非核心資料缺漏可 PARTIAL，但不得 REVIEW_READY。
- **Gate 2｜HTML 與 QA：** Builder 唯一入口已核准；HTML 結構、互動、視覺及資料呈現適用項目全部通過。強制項目未通過不得 REVIEW_READY。
- QA sidecar 必須分開記錄 `QA_PASSED`（技術／結構／互動／視覺測試結果）、`data_review_ready`（資料與內容是否達截稿標準）、`sim14_builder_approval`（使用者是否核准指定 Builder 路徑及 SHA）及 `sim14_review_ready`（是否符合本版 Stage 5／6 的完整 REVIEW_READY）。`review_ready` 舊欄位只表示資料層狀態，不得單獨代表 SIM-1.4 REVIEW_READY；Builder 未核准時 `sim14_review_ready` 必須為 false。

### 9.2 四類 QA（檢查範圍，不是四道 Gate）
1. **資料與內容 QA：** 日期、行情基準日、44 項欄位、商品身分、來源、行事曆事件、財報實際／共識、新聞時間窗、數字與分析一致。
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
- 正式首頁僅在使用者明確核准指定審核版 SHA 後更新；發布後回讀首頁 SHA／內容並確認部署。歷史封存另行執行，只在正式發布後新增／核對 history，並驗證首頁未被封存流程修改。

---

## 10. 狀態管理、恢復與計時

### 10.1 Session State 與 Work Log 分工
- `TAC_SESSION_STATE.md`（Repository 根目錄）：當前活動任務的唯一狀態錨點。只保存目前報告日期、最後完成階段、輸入／輸出路徑及 SHA、各階段狀態、待處理項目、下一步及恢復位置。
- `TAC_WORK_LOG.md`（Repository 根目錄）：追加式重要證據紀錄。保存關鍵來源查核、重要裁決、修正、QA 結果、發布／交付回讀及時間紀錄；不複製整份 Session State。
- 本次實際核對確認上述兩檔均存在於 Repository 根目錄；本草案不得將它們誤報為 simulation-lab 子目錄檔案或缺檔。若未來路徑／檔案確實不存在，先列為 STATE_STORE_MISSING，核對 Git tree 後再依授權處理；不得虛報讀取或建立。
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
- Simulation Manifest：simulation-lab/baseline/mother-template-manifest.json，SHA `1496a510d144d340c41b642592675233d5bd2917`。
- Monday baseline：simulation-lab/baseline/monday-mother-template.html，SHA `36f29bcb37816348756f9233b60f0429d675a76e`。
- Weekday baseline：simulation-lab/baseline/weekday-mother-template.html，SHA `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。
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
| 33 | 外匯 | USD/TWD 美元／新台幣 | `#industry-bonds-fx-commodities #fx .row a.tac-market-link（卡片內第 2 筆）` | https://hk.investing.com/currencies/usd-twd |
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
- 美國公債 2Y／10Y／30Y：美國財政部 Daily Treasury Par Yield Curve Rates `https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics`；FRED DGS2、DGS10、DGS30 備援。三期限同資料日期。
- DXY：Investing.com `https://www.investing.com/indices/usdollar-historical-data`；不得誤用 DX 期貨。
- USD/TWD：台灣央行銀行間收盤匯率 `https://www.cbc.gov.tw/tw/lp-645-1-1-60.html`；Investing.com `https://hk.investing.com/currencies/usd-twd` 為市場報價備援，不得冒稱官方銀行間收盤。
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
以 `simulation-lab/baseline/mother-template-qa-contract.md`（QA Contract v1.11 DRAFT，blob SHA `f7c1d065c20d1d6fbc187525dbe98a58295b070f`）作為唯一詳細 DOM／互動／視覺 QA 契約；此附件與 SIM-1.4 均為候選草案，尚未生效。契約涵蓋四種財報狀態、Yahoo／Investing 共識來源順位、雙母版固定 DOM、Fed 官員行程、FedWatch 兩卡、商品合約連結、台灣截稿行事曆分類、TAC 漲跌配色及六視窗繁中字型驗收。main `母版專區/母版結構驗收清單.md` 僅供正式資產歷史／交叉參考，不是第二份 simulation 每日 QA 清單。`scripts/tac_html_binding_map.json` 是舊版文字節點映射附件，不得視為目前 Builder 動態槽位的授權清單；在完成逐 selector 對照前，不作執行依據，也不得與本 QA Contract 並列裁決。任何契約與母版 SHA 不符即停止，不得自創 selector。

---

## 附錄 E｜SIM-1.3 → SIM-1.4 條文處置摘要

| SIM-1.3 區段／規則 | SIM-1.4 去向 | 裁決 |
|---|---|---|
| 0、0.1、0.2、A、A1、A2 | 0、1、10、11 | 合併；權限、單一權威、修改閉環集中 |
| 0.5、0.6、C 第三步、H | 4、9 | 合併；04:35 唯一寫入、早報嚴格唯讀 |
| 0.7、F2、F3、F4 | 4、5 | 重寫；保留顯示與事件規則 |
| 0.8 | 5.4 | 保留並集中 |
| 0.9、D2、D3、D2-補充、D4、D5 | 3、附錄 A | 合併；現貨與 CFD 矛盾裁決為 CFD 不得取代現貨 |
| C 六階段 | 2 | 重寫為單一流程，每階段有 I/O／驗收／交接 |
| D1 44 項與 ETF | 3、附錄 A | 保留；以核准母版實際欄位鎖定，不臆測差額 |
| E 新聞 | 6 | 保留並集中 |
| F1–F4 | 4、5 | 合併；行事曆與財報分開資料契約 |
| F3-補充2、4–10 | 5、附錄 B | 衝突清理；Yahoo Finance Average Estimate 第一順位、Investing.com 第二順位；EPS／Revenue 分開選源；舊 LSEG 優先及 PIT 判讀門檻撤銷 |
| G1–G4、11/17、11/19 補充 | 7 | 合併；週一／平日總結分流、三區評論綁定 |
| H | 0、2、4、11 | 重寫；只保留 04:35 JSON 更新、05:25 唯讀、preview／首頁／封存分離 |
| I | 0、9、10 | 合併；狀態、恢復、計時及 QA 重跑規則集中 |
| 第五步 QA、A1 QA 指定 | 1、8、9、附錄 D | 重寫；三道流程 Gate 與四類 QA 分開定義 |
| 第六步發布 | 0、9、11 | 重寫；定版綁定 SHA，QA 豁免不得偽裝通過 |
| J 與所有歷史補充條文 | 本附錄 E／版本紀錄 | 移至歷史，不再當有效規則 |

### 歷史狀態紀錄（以下為後續實證前的歷史快照，不代表目前狀態）
1. 44 項母版欄位已依兩份 SHA 鎖定母版抽取名稱、定位及固定 href，詳見 A1.1；尚未完成的是每日 44 筆實際行情核對及現貨／CFD來源驗證。
2. Builder 唯一入口尚未核准；build_review_html.py 靜態稽核發現新增 CSS、重建 Fed 區塊、改寫週一收折 DOM，且行情來源檢查未拒絕 CFD quote_type 等不相容風險。GitHub Actions run 44897956591 的 Python compile、Node syntax checks 與 deterministic self-tests 已通過，但未執行 HTML build／DOM diff／Playwright；稽核報告：simulation-lab/analysis/SIM-1.4-builder-compatibility-audit.md。通過母版相容性測試及使用者核准前，不得作唯一入口。
3. QA Contract 與母版 SHA 的相容性已完成靜態對照；Manifest 正式 SHA 與 simulation SHA 均登記一致，QA Contract 已更新為 v1.5 DRAFT 並修正舊 SIM-1.2 引用。兩組母版 ID 集合、style/script 數量一致；DOM／視覺測試尚未執行。報告：simulation-lab/analysis/SIM-1.4-qa-contract-compatibility.md。
4. TAC_SESSION_STATE.md 與 TAC_WORK_LOG.md 均存在於 Repository 根目錄（不是 simulation-lab/ 子目錄）；本次已讀取並將更新本輪進度。11/23 fixture deterministic contract 已通過，但 6 筆 CFD 指數已改列待核實，情緒／FedWatch待刷新，HTML尚未組裝；不得引用先前不一致的「完成」標記。

---

## 版本紀錄
- SIM-1.4 DRAFT（2026-11-21）：首次整併草案；不生效、不覆寫 SIM-1.3。完成條文對照、實證及使用者核准後，才轉為唯一有效規範。


## 2026-11-21 實證更新（仍為 DRAFT）

- GitHub Actions run 44897956591，commit 384dab2fdfd498248f6911746db82f968bb8daf7，conclusion success；Python compile、Node --check（visual_regression.mjs／interaction_smoke.mjs）、11/23 fixture contract、44 欄計數、5+10 新聞、W47/W48 calendar projection、財報 schema／判讀等 deterministic tests 通過。該 push run 未觸發 build／QA-only 模式。
- 11/23 fixture 的六筆 CFD index reference 已由原始數值改為顯示「待核實」，原始參考值另存 rejected_reference；總結／區域評論不再引用這六筆 CFD 漲跌。Workflow 另加 build-level guard，禁止數字型 CFD 指數被渲染為現貨收盤。
- 仍未產生 11/23 審核版 HTML；未執行 Builder build、DOM 前後差異或 Playwright。市場現貨來源與 VIX／MOVE／CNN／FedWatch刷新仍是 review blockers。
- QA Contract v1.5 DRAFT 已鎖定 SHA 26bb1dc456185069753d1c6b9cfa038e97875913；320px 已加入視覺測試程式與 workflow evidence 尺寸清單，但尚無瀏覽器測試證據。


## 財報引擎 1.4.0 與 Renderer 相容性（2026-11-21）

- earnings_judgment.py 已更新為 Engine 1.4.0，公開狀態限制為 beat／miss／inline／pending；幣別、單位、期間明確不相容時映射 pending 並保留 comparison reason。Schema const 已同步 1.4.0。
- 共識快照來源層級已調整為 Yahoo Finance=1、Investing.com=2、LSEG=3、FactSet=4；W47 Yahoo projection 改用 source_level=1。
- Builder 檔案依交接保護範圍未修改，仍保留 legacy incomparable／consensus_divergent label 分支，且無法將「數值存在但不可比」顯示為「比較資料尚未齊備」。因此財報 renderer Gate 仍為 BLOCKED；visual regression 已改成只接受四種狀態並會檢出該標籤錯置。


- 最新 GitHub Actions run 44897956591（commit 384dab2fdfd498248f6911746db82f968bb8daf7）conclusion success；Python compile、Node --check（visual_regression.mjs／interaction_smoke.mjs）及 deterministic self-tests 均通過。此 run 未執行 HTML build、DOM diff 或 Playwright。


## 逐條台帳與財報引擎實作同步（2026-11-21）

- SIM-1.3 逐條處置台帳已補齊 E、F1–F4、F3-補充4–10、G1–G4、H、I，以及 C 第五／六步 Gate 的細項；最新台帳 SHA：1ec0936a6640ffb70b0af94c08b85ca96e903d87。逐條台帳另含 D2、D2-補充、D3.1–D3.17、D4、D5。
- 財報判讀引擎 earnings_judgment.py 1.4.0 SHA：62148064ad08efe72bc5a107a4142d32dffc6c7c；公開狀態固定 beat／miss／inline／pending。共識來源層級 Yahoo Finance=1、Investing.com=2、LSEG=3、FactSet=4。schema 與 deterministic tests 已同步。
- 最新財報引擎 deterministic regression：run 44897795972 success，四狀態判讀、snapshot store 23 tests、schema audit、report-layer status 及 11/23 fixture contract 通過。
- 最新 Node／Python 語法及 deterministic regression：run 44897956591 success。workflow YAML 縮排問題曾造成 run 44897899979 failure，已修正並由 44897956591 驗證成功。
- **明確未完成：** 未執行 build mode／QA-only mode；未產出 11/23 HTML；未完成雙母版 DOM diff、Playwright 互動／視覺回歸；Builder 的 legacy 財報狀態 renderer 仍 BLOCKED，且本輪遵守保護限制未修改 Builder。SIM-1.4 仍是 DRAFT，不得啟用。

## 2026-11-21 晚間實作與測試狀態（DRAFT，尚未生效）

- Builder 已新增 CFD index reference fail-closed guard，並將財報 renderer 狀態收斂為 beat／miss／inline／pending；回歸測試 `test_quote_type_guard.py` 已加入 simulation workflow。
- 11/23 真正 build／DOM artifact validation／Playwright／六種 viewport QA 已由 GitHub Actions run `44899645332` 觸發；記錄時仍 pending，未宣稱通過。
- Builder 仍有已知母版零退化阻塞：額外注入 CSS、重建週一收折 summary DOM、重建 Fed 區塊，以及未完成雙母版逐節點 DOM diff。故目前不得宣告 REVIEW_READY、不得核准 Builder 唯一入口，SIM-1.4 仍維持 DRAFT。
- main、正式母版、Manifest、正式首頁與正式行事曆 JSON 未修改。


## 2026-11-21｜Fed 官員週行程固定槽位修復（尚待 CI／Build QA）

- 使用者明確要求保留 Fed 官員行程功能；因此不刪除功能，而是修復 Builder 與母版脫節問題。
- 週一母版新增固定 `#fed .fc-fomc-weekly-events` 外層、標題、清單、事件原型及空狀態槽位；平日母版同步相同契約。事件原型固定含日期、名稱、影響說明、官方來源連結欄位。Builder 僅深複製母版原型並填入欄位，不再清空／重建外層容器或整張卡片。
- Manifest 已更新 simulation 母版 SHA：Monday `36f29bcb37816348756f9233b60f0429d675a76e`；Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。QA Contract 已新增 Fed 行程槽位及保留結構驗收條款。
- Builder 修正 `normalize_market_label` 的 regex typo：原始 `r"\\s+"` 只會匹配反斜線與 s 字元，無法移除空白；已改為 `r"\\s+"` 的 Python 正確空白 regex（實際原始碼為單一反斜線），並補全形空白測試。
- `test_quote_type_guard.py` 已擴充：兩份母版均需驗證 Fed 行程槽位存在且唯一、已發表／預定事件能顯示、空週顯示明確空狀態、外層節點與事件原型不被破壞。該測試已在 workflow 原有 deterministic self-test step 中執行。
- Builder 修復 commit：`7e9a4fe524880a993f7a15988776627e96e4cc0a`；測試 commit：`1ca9b8da23ce9105c7cf2b04408ca50f0d008ef1`；雙母版與 Manifest／QA Contract 已分別提交。
- 仍未通過 CI 前，不宣稱測試成功；仍須跑真正 Monday／weekday HTML build、DOM 零退化、artifact validation、Playwright 桌面／手機與六 viewport 視覺 QA。SIM-1.4 維持 DRAFT，main／正式首頁未修改。


## 2026-11-21｜母版零退化與 FedWatch 版型邊界修正

- Builder 不再每日追加 summary heading、週一 disclosure、側欄 layout、能源報價、財報卡片及市場名稱字體 CSS；不再清空重建週一上週收折 summary。保留使用者曾核准的單次突發專題 `special_focus` 條件式呈現及其專屬樣式，未寫回母版。
- FedWatch 嚴格沿用母版 2 卡／2 分布段／2 圖例，不再 clone 第三卡、不再以固定 hold/+25bp/+50bp 寫死。超出兩卡可表達的情境數量／類型時，兩卡標待核實、隱藏不完整分布，完整情境保留在既有快照收折區。
- 最新 QA Contract SHA：`26bb1dc456185069753d1c6b9cfa038e97875913`。這些修正仍須經實際 Monday／weekday build、DOM 零退化、Playwright 與六 viewport 視覺驗收；SIM-1.4 仍為 DRAFT。


## 2026-11-21｜Builder 相容性修正進度（仍待 build QA）

- 最新 Manifest SHA：`1496a510d144d340c41b642592675233d5bd2917`；QA Contract SHA：`26bb1dc456185069753d1c6b9cfa038e97875913`。
- Fed 官員行程固定槽位已納入週一／平日 simulation 母版；Builder 以母版事件原型填資料。FedWatch 保留母版兩卡結構，多情境不符合時 fail closed 並在既有快照說明列出完整機率。
- 移除每日 CSS 注入與週一收折 summary 重建；保留 2026-11-11 已核准的單次 `special_focus` 條件式功能作為明確例外。
- CI run `44900780456`（母版 SHA／Fed agenda slot）及 `44900949612`（FedWatch 雙卡與 Builder CSS 清理）success；以上僅為 smoke／deterministic self-tests，不代表 HTML build、DOM diff、Playwright 或視覺 QA 通過。


- 2026-11-21 build request: 使用當前 2026-11-23 Monday fixture，以最新 simulation Builder／母版／Manifest／QA Contract 執行完整 build mode；此為測試請求，不代表 QA 通過或 SIM-1.4 生效。


- 2026-11-21 build retry: run `44901082368` 已通過前置及 deterministic tests，組裝 11/23 Monday fixture 時發現 `observation` 為結構物件（heading/text），Builder 原以字串判斷而中止。已修正 `set_market_observation` 支援字串與結構物件，最終 Gate 亦改比較 `observation.text`；新增 regression test，現觸發完整 build 重跑。此錯誤修正尚待 CI 與 build 結果驗證。


- 2026-11-21 第二輪 build 修正：run `44901183828` 發現 FOMC 活頁中尚有一段舊程式會把母版原有 `.fc-fomc-observation` 清空、改名並重建成第二個 `.fc-fomc-weekly-events`，導致固定槽位檢查出現不完整／重複結構。已移除該舊重建分支，保留母版原有 observation 節點；Fed 官員行程只在固定母版槽位呈現。新增測試確認 observation 節點前後不變。另將槽位缺漏檢查改為明確 None 檢查並回報缺漏名稱。重新觸發 11/23 Monday build。


- 2026-11-21 新聞來源 Gate 修正：上一輪 HTML 組裝成功，但 Playwright interaction smoke 因 Global Focus News 來源網域不符規範而停止。原 fixture 混有 Reuters 直連及 www.investing.com 美站網址，與既定 HK Investing.com／鉅亨網來源契約不符。已以可核對的 HK Investing.com 與鉅亨網文章替換五則新聞，保留 11/20 12:00 之後的時間窗、更新發佈時間與摘要，並按時間排序；此為 simulation fixture 修正，尚待完整 build／互動／視覺驗收。


- 2026-11-21 視覺 QA 修正：run `44901460631` 已通過 HTML build、互動 smoke 與新聞來源 Gate，但視覺回歸發現舊 QA 契約仍要求三張 FedWatch 卡（與母版兩卡相衝突）、舊財報 pending 標籤，以及總結標題字級不一致；另 11/23 Fixture 的核心觀察 heading 寫成「下週」但報告週是本週。已將兩份 simulation 母版既有 CSS 的總結／市場情緒標題統一為 21px（不新增 style 節點、不修改 main），將視覺 QA 改為兩卡／兩分布段／兩圖例及 fail-closed 驗收，更新財報 pending 標籤預期，並修正 fixture heading 為「本週三大觀察焦點」。最新 simulation 母版 SHA：Monday `36f29bcb37816348756f9233b60f0429d675a76e`；Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`；Manifest `1496a510d144d340c41b642592675233d5bd2917`。以上修正尚待下一輪六 viewport QA。


- 2026-11-21 Summary 標題字級第二次修正：前次 21px 規則選錯 selector（誤用 `#overview>.title`，實際母版標題位於 `#overview > section > article.card.bluf > .title`），因此 1440px 計算字級仍為 26px。已改在兩份母版既有最後一個 style block 的精確 selector 設定 21px，沒有新增 style 節點；Manifest 已同步。待重新跑六 viewport。


- 2026-11-21 六項指數來源修正：Investing.com HK 六個同名頁面均標示「即時差價合約」，不可因為有歷史數據表就誤認為現貨。已改用 Investing.com 全球指數歷史頁（Real-time derived）及 DAX Xetra 頁，六筆 quote_type 改為 `cash_index_close`；FTSE 100 11/20 收盤修正為 10,346.34（-1.02%），其餘五項依全球頁歷史列核對。Fixture SHA：`8ecaf343336aac51e76a0958784ea69aada346d6`。新增回歸測試驗證六筆均不再觸發 CFD guard。過期「HTML尚未產出」阻塞已移除；只保留 VIX／MOVE／CNN Fear & Greed／FedWatch 於 11/23 05:25 前刷新一項阻塞。現觸發重新 build 與完整 QA。


- 2026-11-21 Fixture Gate 測試同步：舊 `test_1123_fixture.py` 仍把「六項 CFD／三個 blocker／HTML未產出」當成預期，與已修正 fixture 衝突。已改為驗證六項均為 `cash_index_close`、六組數字與歷史頁來源正確、沒有 CFD rejected_reference，且只剩 VIX／MOVE／CNN Fear & Greed／FedWatch 一項截稿前刷新阻塞。現再次觸發 Monday build。


- 2026-11-21 Weekday full-build regression request: workflow push trigger now accepts `[build-tac-report:YYYY-MM-DD]` to select an exact dated fixture without changing or moving any fixture. Request `[build-tac-report:2026-11-20]` will exercise the 2026-11-20 weekday mother using its date-matched fixture; this is a regression test only, not a new production report.


- 2026-11-21 Weekday regression build follow-up: the 2026-11-20 fixture reached Builder assembly and exposed three missing FactSet fields (`mag7_eps_growth`, `other_493_eps_growth`, `source_url`). The 11/13 FactSet source does not provide a verifiable Mag 7／Other 493 split, so the fixture now marks both split values `待核實` and links the exact 11/13 FactSet PDF; it does not backfill the later 11/20 values. Added a regression test for this pending-state behavior. Re-run weekday build.


- 2026-11-21 Weekday visual QA 修正：2026-11-20 舊 fixture 原本 `key_levels.items=[]`，因此今日觀察第三活頁沒有五檔現金指數 OHLC、支撐／壓力及來源日期，六視窗視覺驗收合理地失敗。已按該報告基準日 2026-11-19 逐筆核對 Yahoo Finance 現金指數歷史頁，補入 Dow／S&P 500／Nasdaq Composite／SOX／Russell 2000 五檔 OHLC，並按同一公式重算 S2/S1/P/R1/R2；新增測試驗證日期一致、來源 URL 與公式結果。沒有沿用 11/20 週一 fixture 的 11/20 OHLC。重新執行 weekday full build。

## 2026-11-21｜完整 build／QA 實證更新（SIM-1.4 仍為 DRAFT）
- 週一 2026-11-23 fixture 已由 run 44904316843 完成真實 HTML build；母版結構比較、獨立 artifact／provenance、44項／行事曆／新聞契約、Playwright 互動與六視窗視覺 QA 全部通過。QA_PASSED，但 review_ready=false，唯一 blocker 為 VIX／MOVE／CNN Fear & Greed／FedWatch須在報告截稿前刷新。審核 HTML blob SHA e6ea8ca01e38e68cc34fe4d74874f1b915e994d6，QA sidecar SHA f7ccad8ea44c578f3a620bf17b79e2c8be347c92。
- 平日 2026-11-20 fixture 已由 run 44902986319 完成真實 HTML build；母版結構比較、artifact／provenance、44項／行事曆／新聞契約、Playwright 互動與六視窗視覺 QA 全部通過；QA_PASSED 且 review_ready=true。審核 HTML blob SHA 0597447d59563d459fc4c913639a07d7ecfcdbbf，QA sidecar SHA 0d18025b4a2a197b1c6c6877ff93b9d6bd8d4bf6。
- 因兩個完整 build 均通過，前文「尚未完成 build／DOM diff／Playwright／六 viewport」僅是當時歷史狀態，不再代表最新狀態。Builder 已具備兩種母版的實際組裝與 QA 證據；但尚未完成報告截稿前情緒／FedWatch刷新，因此不可把週一審核版標為 REVIEW_READY。
- 2026-11-21 20:33 Asia/Taipei 重新讀取 VIX／MOVE／FGScore CNN Provider Index／Investing.com Fed Rate Monitor，數值與來源時間未見更新：VIX 35.89、MOVE 106.31（均為11/20收盤）；FGScore CNN Provider Index 10（as of 11/20 UTC）；FedWatch 12/09/2026 hold 13.6%、升息25bp 86.4%，Updated Nov 21 00:35 EST（台灣13:35）。最後截稿刷新仍待11/23 05:25前執行。
- main首頁、正式母版及正式行事曆JSON保持唯讀；SIM-1.4仍是DRAFT，未生效。


## 2026-11-21｜完整雙母版 Build 後的規則一致性稽核（仍為 DRAFT）

### 已由後續實證更新的歷史狀態
- 本文前段及舊紀錄中「尚未執行 HTML build／DOM／Playwright／六視窗 QA」均是當時狀態，已由 2026-11-21 20:33 的兩次完整 build 更新，不得再當成目前狀態。
- Monday 2026-11-23：Actions run 44904316843 success；HTML build、母版結構契約、artifact/provenance、44 項／行事曆／新聞契約、Playwright interaction smoke、1440／768／412／390／360／320 六視窗視覺 QA 通過。QA_PASSED；review_ready=false，僅剩 VIX／MOVE／CNN Fear & Greed／FedWatch 截稿前刷新。
- Weekday 2026-11-20：Actions run 44902986319 success；相同類別 build／QA 通過。QA_PASSED；sidecar 的資料型 review_ready=true。
- 上述 build 已證明候選 Builder 可在週一及平日 fixture 產生 HTML；不等於候選 Builder 已依本章 8.1 取得「唯一 Builder」核准，也不等於 SIM-1.4 已生效。

### 最新規則／資產 SHA
- SIM-1.3（目前有效規則）blob SHA：`679eae7ba7a40dbad64d15bb448fe53db7d67e09`。
- 本草案 SIM-1.4 blob SHA：以本次 commit 回讀值為準。
- Simulation Manifest SHA：`1496a510d144d340c41b642592675233d5bd2917`。
- QA Contract v1.6 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- Monday simulation mother SHA：`36f29bcb37816348756f9233b60f0429d675a76e`；Weekday：`19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。附錄 A1.1 與 QA Contract A2.1 已同步這兩個目前 SHA；正式母版 SHA 仍各自獨立，不得混用。

### 仍未通過的 SIM-1.4 規則／技術 Gate
1. **Builder 尚未取得唯一入口核准。** 目前候選檔為 `simulation-lab/runner/build_review_html.py`，blob SHA `b36ae1ba2b3fd3dfbde577fb6df6ea926333b3fc`。兩種母版 build 通過只是技術實證；依 8.1，仍須完整提交差異白名單、負向案例、CLI／副作用報告，並由使用者明確核准此路徑與 SHA。
2. **Build provenance 尚未滿足 8.2。** 現行 `TAC_BUILD_PROVENANCE` 有 report date、build commit、template、fixture、builder、calendar SHA，但未記錄 Manifest SHA、QA Contract SHA、SIM-1.3 active rules SHA 及 SIM-1.4 candidate rules SHA；`validate_review_artifact.py` 亦未驗證這四項。現有 build 不可宣稱已通過完整規則／資產 provenance Gate。
3. **Sidecar 的 review_ready 定義尚未與 SIM-1.4 對齊。** workflow 目前主要依 fixture 的 `review_ready_blockers` 計算布林值；它沒有納入 Builder 唯一入口核准狀態。因此 weekday sidecar 的資料型 `review_ready=true` 不可直接解讀為 SIM-1.4 Stage 5／Stage 6 的 REVIEW_READY。
4. **DOM 比對範圍必須精確命名。** `validate_mother_dom_contract.py` 目前逐項比對 style／script 節點與內容、ID inventory，以及總結段落、FOMC observation、Fed agenda wrapper、工具欄、週一收折 summary 等指定穩定節點；它不是全頁逐節點完整 DOM diff。六視窗視覺與 Playwright 通過不會自動補足未比較的 DOM 範圍。
5. **DOM 寫入白名單仍需補齊。** `scripts/tac_html_binding_map.json` 宣告 `mutate_only_text_nodes=true`、`preserve_element_tree=true`、`preserve_attributes=true`；候選 Builder 實際包含清空／重建部分內容節點、來源欄位子節點重建、事件原型 clone、排序與動態卡片產生。必須逐 selector 說明哪些是核准動態槽位、哪些操作合法，並裁決 binding map 是需同步更新的有效契約或已退役的舊附件；不可讓兩份契約互相矛盾。
6. **Fed 官員行程必須保留。** 候選 Builder 現在使用母版既有 `.fc-fomc-weekly-event-template` clone，更新既有 list，保留外層 wrapper／title／empty-state；此項有兩種母版 build 與 DOM contract 測試證據。後續修正不得移除 Fed 官員週行程，也不得清空重建 Fed 外層區塊。
7. **週一上週收折外層必須保留。** 動態事件清單可依核准槽位更新，但 `details.last-week-calendar-collapse`、`details.last-week-earnings-collapse` 及其 summary 必須保持母版結構與預設收折狀態。

### 下一個實作順序
1. 先補 Builder 的 provenance 欄位及獨立 validator：Manifest、QA Contract、active SIM-1.3、candidate SIM-1.4 的路徑／blob SHA 必須從 build commit 讀回核對。
2. 再補完整 DOM write allowlist／契約一致性測試，明確界定動態卡片及來源連結槽位；擴充 DOM validator 的檢查範圍或明確限定其名稱與驗收聲明。
3. 修正 sidecar 狀態欄位，分開 `QA_PASSED`、資料完整度、`SIM14_BUILDER_APPROVED`、`SIM14_REVIEW_READY`；Builder 未獲使用者核准前不得標示 SIM-1.4 REVIEW_READY。
4. 兩種母版重新跑完整 build／artifact validation／Playwright／六視窗 QA；完成後提交候選 Builder SHA 與證據，等待使用者核准。SIM-1.3 持續有效，SIM-1.4 持續 DRAFT。


## 2026-11-21｜S&P 500 Dashboard 與市場情緒 DOM 保留修正（待 CI）

- 再次檢查兩份實際母版後，確認舊 Builder 曾對 `#sp500-earnings-health` 執行 `health.clear()`，再以六張固定卡及 inline style 重建；這違反 QA Contract F 的母版 Dashboard 保留要求。現已改為只更新母版既有文字槽位，週一保留 4 張卡、平日保留 3 張卡，並保留原有容器、卡片、排列、欄數及 inline style。
- 舊 Builder 對市場情緒最後一張核心解讀卡執行 `interpretation.clear()`，會移除原有 body wrapper 與 inline style。現改為只更新既有 body text node，保留 label／body wrapper。
- `validate_mother_dom_contract.py` 現已將 `#sp500-earnings-health` 與 `#sentiment .sent > .sbox:last-child` 納入穩定 DOM 比對，並比較兩區 inline style；新增雙母版回歸測試 `test_earnings_health_dom_preservation.py`，已接入 workflow。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`8757c7dc3f218908a8d314156d2d6f06406e12ca`；雙母版 regression test SHA：`d66f50ef5ce3fd3ab3c8edecdecb23be9e3843aa`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`。
- 以上為程式修改已提交，尚未有這一版 Builder／validator／test 的完整 CI 結果。下一次完整 build 必須同時驗證 Monday 4 卡、Weekday 3 卡、兩區 DOM／inline style 不變、來源連結與日期更新，並通過 provenance validator、互動及六視窗視覺 QA。
- 此修正不代表 Builder 已取得唯一入口核准；SIM-1.4 仍是 DRAFT，SIM-1.3 仍有效。


## 2026-11-21｜Dashboard 資料欄位回歸修正（待重跑）

- 首次執行新 DOM 保留版本的 run 44905304475：雙母版 Dashboard／市場情緒 DOM-preservation deterministic tests 均通過；真正 Monday build 在最後 FactSet 資料 Gate 失敗，因新 renderer 未將 fixture 的 Mag 7／Other 493 成長值寫入現有分析文字槽位。
- 同一 Gate 原先要求 `.factset-source-link` class，但 Weekday 核准母版的來源連結沒有該 class；此要求會迫使 Builder 改寫母版 class，與零退化原則衝突。
- 已修正：Monday 既有「正面」文字槽位加入 Mag 7／其他 493 數值；FactSet 來源驗收改檢查母版既有 `details a` 連結及其 href，不要求新增 class。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`。以上修正尚未經新一輪完整 build 驗證；run 44905304475 保留為失敗歷史證據，不可改稱通過。


## 2026-11-21｜市場評論與 FactSet 欄位保留修正（待完整重跑）

- run 44905304475 在新 Dashboard DOM-preservation deterministic tests 通過後，於最後 FactSet Gate 失敗：Mag 7／Other 493 數值尚未寫入保留的母版文字槽位。後續已在既有 Monday／Weekday「正面／保留」文字槽位補入 Mag 7、Other 493 及 Forward 12M P/E，不增加卡片、不改變欄位排列。
- FactSet 來源連結 Gate 改為驗證母版既有 `details a` 的 href；不再要求平日母版原本不存在的 `.factset-source-link` class，避免為通過 Gate 而改寫母版屬性。
- `set_market_observation` 已由清空重建改為只更新母版既有直接子節點 `b／br／text`；移除前置的冗餘 destructive `set_text(reason,...)`。DOM validator 現比對所有 `.market-reason` 子樹及 inline style；雙母版回歸測試亦涵蓋市場評論槽位。
- QA Contract 已更新為 v1.7 DRAFT，新增市場評論、Market Sentiment 核心解讀及 S&P 500 盈餘 Dashboard 的 DOM／inline style 保護條款。QA Contract SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；Manifest SHA 仍為 `1496a510d144d340c41b642592675233d5bd2917`；雙母版 SHA 仍為 Monday `36f29bcb37816348756f9233b60f0429d675a76e`／Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`52404ce2dc6881566ea998cc84e7af030dff43ba`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；雙母版 DOM regression test SHA：`6ab733532893a17faf8814d677e11d81fa08e6fe`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`。
- 上述修改仍須在同一個最新 build commit 重新跑 Monday 與 Weekday；不得引用早一版 run 的成功作為本版通過證據。SIM-1.4 仍為 DRAFT，候選 Builder 尚未取得唯一入口核准。

## 2026-11-21｜Builder 母版零退化修正與回歸狀態（持續 DRAFT）

### 已完成的程式修正
- Fed 官員週行程功能明確保留。週一／平日母版均有固定外層、標題、清單、原型及空狀態槽位；Builder 只複製原型並填入事件，不清空重建外層。
- FedWatch 保留母版兩張機率卡、兩段分布及兩個圖例；多情境或不符合兩卡規格時 fail closed，完整情境保留在既有快照說明，不 clone 第三張卡。
- 移除 Builder 的每日版面 CSS 注入；summary 總結改為填入原有粗體標籤／換行／文字槽位，槽位數不符即停止，不再 clear 後重建。
- S&P 500 盈餘健康度 Dashboard 改為更新母版既有文字槽位，週一維持 4 張卡、平日 3 張卡；市場情緒解讀保留原有 label/body wrapper 與 inline style。
- 市場評論改為更新母版既有直接子節點（粗體標題、換行、文字），不清空重建；缺少既有槽位即停止。
- CFD quote_type 防錯保留；已修正空白正規化雙重跳脫錯誤。

### 最新程式與契約版本
- Builder：simulation-lab/runner/build_review_html.py，目前 blob SHA e03e4af65007a6cfdd3c241a1219ea28d42cbabf。
- DOM validator：simulation-lab/runner/validate_mother_dom_contract.py，目前 blob SHA 52404ce2dc6881566ea998cc84e7af030dff43ba。
- FactSet／市場情緒 DOM regression：simulation-lab/runner/test_earnings_health_dom_preservation.py，目前 blob SHA 6ab733532893a17faf8814d677e11d81fa08e6fe。
- QA Contract：版本 1.7 DRAFT，blob SHA f6848d21286f63c4eef11682eedd8825b5fd3aad；Manifest 已登記兩份 simulation 母版 SHA，未修改 main 正式母版。

### 實際驗收紀錄與未完成項
- 2026-11-23 Monday build run 44905408554 曾完成 HTML 組裝、deterministic tests、Playwright 互動、六種 viewport（1440／768／412／390／360／320）、artifact validation、44 項行情結構驗收及母版 DOM 比對；該次 QA sidecar 為 QA_PASSED。
- 該次 sidecar 的 review_ready=false：VIX、MOVE、CNN Fear & Greed、FedWatch 快照仍早於 2026-11-21 17:57:31；必須在 2026-11-23 05:25 截稿前重新讀取並更新時間，不能把結構 QA 通過當成資料完整。
- 上述 run 使用 Builder SHA 45bafe4c8e346fe1c51d1eb342c114d8009fc43c；其後又新增市場評論 DOM 保留修正，故目前最新 Builder SHA 尚須重新跑 Monday／weekday 完整 build 與 DOM validator。
- 2026-11-20 weekday 曾有完整 build／六視窗 QA 通過紀錄，但後續增加固定 DOM validator、FactSet 欄位顯示與市場評論 DOM 保護；最新 Builder／validator 組合的 weekday 完整回歸仍待重跑。
- SIM-1.4 不得標示完成或啟用；SIM-1.3 仍為唯一有效規範。正式首頁、main、正式母版及正式行事曆 JSON 均未修改。


## 2026-11-21｜市場評論槽位與 CNN 分數 DOM 保護（待最新 CI）

- 舊通用 `set_text()` 會直接 `node.clear()`，若目標有子元素便可能刪除母版 DOM。現已改為 fail-closed：遇到子元素即拒絕破壞性寫入；資料更新必須明確定位 leaf text node。
- CNN Fear & Greed 分數原先寫入父層 `.fg6-score`，會移除 `.fg6-score-main` 與固定 `.fg6-outof`（/100）子節點。現改為只更新 `.fg6-score-main`；validator 比對分數 wrapper 結構與 inline style。
- 市場評論 helper 已改為保留母版直接子節點 `b／br／text`；測試範圍限定為 Builder 真正會更新的三區市場評論、產業／債券／匯率／商品評論，以及今日市場觀點槽位。validator 仍比對全頁所有 `.market-reason` 的結構與 inline style。
- run 44905555873（commit cebd527）在 deterministic tests 階段失敗：測試曾過度涵蓋所有 `.market-reason`，包含 Builder 不會寫入的舊節點。已將測試範圍收斂至 Builder 實際寫入的母版槽位；該 run 不可算通過。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`86ad959871e9e9ecfbfd32644b06d3f34d2e05ae`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；DOM regression test SHA：`70cb06d15ed736bb7dc31b4b42455937d1566f6a`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 44905408554 曾在較早版本通過完整 Monday build，但該版本未包含後續市場評論與 fail-closed CNN 更新；本版仍須以最新 commit 重跑 Monday／Weekday，不得沿用舊 run 當成最終驗收。


## 2026-11-21｜最新測試修正與完整回歸待辦

- run 44905688058 的雙母版 Dashboard／情緒 DOM 測試已通過；失敗點是另一支 quote-type regression test 使用了不符合母版的簡化 `<div><span>` 節點，卻要求 updater 自動建立 `b`。已將該測試改為使用核准母版的 `b／br／text` 結構，並加入非母版結構必須 fail-closed 的負向案例。
- 市場評論回歸測試已限定於 Builder 真正會更新的區塊；對沒有粗體標題、但有既有文字槽位的合法評論節點，依現有 DOM 更新文字而不新增標籤。DOM validator 比對所有 `.market-reason` 的子樹與 inline style；重複的同一比對區塊已合併。
- Builder 通用 `set_text` 現在遇到子元素即拒絕清空；CNN 分數只更新 `.fg6-score-main`，保留 `/100`；市場觀察、Market Sentiment、S&P 500 Dashboard 均只更新既有節點。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；Dashboard／評論 DOM test SHA：`f4b2be83bd6efb0eeb93f9b08bf2f43f3c2d33ab`；quote-type test SHA：`e83ca9011ec6a03672b18eb2522ee633b6fc74ab`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 本版仍需重新跑 deterministic tests、Monday build、Weekday build、母版 DOM、provenance、Playwright、六視窗 QA。任何一項失敗均不可標示 QA_PASSED／SIM-1.4 REVIEW_READY；SIM-1.4 仍未生效。


## 2026-11-21｜來源揭露連結保留修正（待最新完整 CI）

- run 44905791885 已通過 deterministic tests，進入 HTML build；在更新市場行情來源揭露時，fail-closed `set_text` 正確阻止清空含有來源連結的 `.source` 容器。這證明 guard 有效，也暴露一個原先未列入白名單的來源文字槽位。
- Builder 已改用 `set_text_preserving_child_elements` 更新來源說明文字，保留母版既有 anchor／href／子元素；新增回歸測試確認來源連結仍存在且 DOM／樣式不變。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；Dashboard／市場評論／來源連結 regression test SHA：`b0fc64650be06d2a4f64435e2d7c9930f4852391`；quote-type test SHA：`4aa2214f175cd2a8bb1970a648fc8512f0c527a2`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 本次修改尚未完整驗收。最新 build 必須確認 fail-closed guard 不再阻止合法的來源揭露文字更新，同時不刪除既有連結；再完成 Monday／Weekday build、DOM、provenance、Playwright、六視窗 QA。


## 2026-11-21｜來源揭露文字節點保留的第二次修正（待重跑）

- run 44905957224 在來源連結 regression test 失敗：當時版本雖保留 anchor，但將來源容器內其他直接文字節點改成空字串，仍改變 DOM text-node 結構。
- 最新 helper 已改為只更新第一個核准文字槽位，保留後續所有文字節點及所有 child elements；不再移除或清空其餘文字節點。回歸測試同時比對 DOM skeleton 與來源 anchor href。
- 本次為 fail-closed／DOM-preservation 原則的修正，不可只因 anchor 仍存在就判定結構完整。必須在最新 commit 重新執行 regression tests 與完整 HTML build。


## 2026-11-21｜來源尾端文字節點測試口徑修正（待重跑）

- run 44906001227 的來源 helper 回歸測試失敗，原因是測試仍期待舊尾端文字被刪除；最新規則是保留全部既有文字節點與 anchor，故實際輸出應保留「舊尾註」尾端文字。已修正測試預期值，不再要求移除尾端節點。
- 最新 quote-type regression test SHA：`bf13d2b86dd1119132bcf214daf4bc57e0b5e415`；候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`。本次修正仍需重新跑 deterministic tests 及完整 build。


## 2026-11-21｜空白來源槽位的非破壞式補入（待最新 CI）

- run 44906103379 的 deterministic tests 已通過，HTML assemble 階段發現部分母版 `.source` 容器只有既有 anchor，沒有直接文字節點。fail-closed helper 正確拒絕破壞式覆寫，但原先沒有處理「空白文字槽位、子元素仍存在」的情況。
- 最新 helper 若有直接文字節點，只更新第一個並保留其他文字節點／子元素；若容器只有 anchor、沒有獨立文字槽位，則回傳 False 並完全不改動，不新增節點、不覆蓋來源連結。
- 新增「只有既有來源 anchor」的回歸案例，驗證說明文字插入後連結仍保留。最新 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；DOM regression test SHA：`61a969a8504aa7e219ac3f98d2614bba7f92cf81`；quote-type test SHA：`bf13d2b86dd1119132bcf214daf4bc57e0b5e415`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`。
- 此修正尚未經新一輪 build；必須確認 source-only／source-with-link／empty-source-with-link 三種情況皆通過，然後才可繼續後續 DOM／視覺 Gate。


## 2026-11-21｜link-only source disclosure 最終口徑（待最新 CI）

- run 44906194763 顯示 link-only source regression test 不應要求 Builder 新增文字節點。母版若只有來源 anchor 而沒有獨立文字槽位，Builder 必須完全不動該容器；報告日期由既有 `.tab-panel-meta` 提供，來源 anchor 仍保留原 href／label。
- 最新 `set_text_preserving_child_elements` 採此口徑：有直接文字槽位才更新；只有 anchor 時回傳 False 並保持 DOM 完全不變。雙母版 regression test 與 quote-type test 已同步。
- 最新候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；Dashboard／市場評論／來源 regression test SHA：`07a5f8a05a0b8518223fc79fe507a4a70cfe3111`；quote-type test SHA：`a3569c0355c29278bddc0bc9ec551471036cf586`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 上述最新 SHA 尚未取得完整 Monday／Weekday CI 通過證據。SIM-1.4 仍為 DRAFT，Builder 未獲唯一入口核准。


## 2026-11-21｜最後一處 market-reason 破壞性寫入修正（待重跑）

- run 44906262981 的 deterministic tests 通過，HTML assemble 在 global market panel 的另一處舊程式碼失敗：仍以 `set_text(reason,...)` 清空 `.market-reason`，觸發 fail-closed guard。
- 最新 Builder 已將此最後一處寫入改為 `set_market_observation(reason, "", ...)`，只更新既有市場評論標題／文字槽位，不清空節點。
- 最新 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；quote-type test SHA：`a3569c0355c29278bddc0bc9ec551471036cf586`；Dashboard／市場評論／來源 regression test SHA：`07a5f8a05a0b8518223fc79fe507a4a70cfe3111`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`。
- 本版尚未完成 Monday／Weekday build；須再執行全套 deterministic tests 與 HTML assemble，確認不再有未核准的 destructive text write。

## 2026-11-21｜最新 Builder SHA 完整 Monday 驗收（weekday 待驗）

- 最新 Builder SHA：c4c24c03625b3532f48362d7235755a8fa55850f。
- 最新 DOM validator SHA：e202923cb0d31a8381c238884203599a2937de77。
- 最新 FactSet／情緒 DOM regression SHA：07a5f8a05a0b8518223fc79fe507a4a70cfe3111。
- 最新 CFD／Fed／summary／市場評論 regression SHA：a3569c0355c29278bddc0bc9ec551471036cf586。
- 2026-11-23 Monday 完整 run 44906325728 已成功：deterministic tests、HTML assemble、Playwright 互動、approved-mother visual regression、DOM contract、artifact provenance、44 項行情／新聞結構 Gate、QA-passed HTML persist 均 PASS；六視窗為 1440／768／412／390／360／320。
- 11/23 sidecar QA_PASSED、review_ready=false；VIX、MOVE、CNN Fear & Greed、FedWatch 的來源快照仍須在報告截稿前刷新。這是資料 freshness Gate，不是 Builder／DOM Gate 失敗。
- 現在只剩最新同一組 Builder／DOM validator SHA 的 weekday 完整 build 尚未重跑；本次狀態更新將觸發 2026-11-20 weekday regression。
- SIM-1.4 仍是 DRAFT，SIM-1.3 仍有效；不得部署、不得修改 main／正式首頁／正式母版／正式行事曆 JSON。


## 2026-11-21｜繁中字型視覺 Gate（QA Contract v1.8 DRAFT）

- 先前 run 44906329420 的技術組裝、母版 DOM、互動及六視窗比較已通過，但實際 screenshot 中繁體中文字形呈方框；因此該輪視覺結果不可作最終視覺驗收，且推送審核版時遇到 simulation branch concurrent push race，未寫回 preview。
- QA Contract 更新至 v1.8 DRAFT，要求 CI 安裝 Noto CJK、確認 `fc-match "Noto Sans TC"` 解析至 Noto Sans CJK，Playwright 等待 `document.fonts.ready` 並用 `document.fonts.check` 驗證繁中字型可用；缺字即視覺 QA 失敗。
- Workflow 已加入 `fonts-noto-cjk` 安裝與 fontconfig 檢查；`visual_regression.mjs` 已加入字型檢查及 font audit 輸出。
- QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；DOM regression test SHA：`07a5f8a05a0b8518223fc79fe507a4a70cfe3111`；quote-type test SHA：`dc115b0638f3f6772eac7b28ca32a8fed867b020`；visual regression SHA：`d9712593f49dc712d248d262a0e6bff92fdd4720`；workflow SHA：`eb95ab66db37dded42d49d3e82386223b6d27265`。
- 此版尚未執行完整 Monday／Weekday build；字型 Gate 與新版本 provenance 必須以最新 build commit 驗證。SIM-1.4 仍是 DRAFT，Builder 未獲唯一入口核准。


## 2026-11-21｜Noto Sans TC fontconfig alias 修正（待重跑）

- run 44906661785 確認 `fonts-noto-cjk` 已安裝，但 Ubuntu fontconfig 的 `Noto Sans TC` family name 未自動 alias，`fc-match "Noto Sans TC"` 回退為 DejaVu Sans，因此字型 Gate 正確失敗。
- Workflow 現改為先確認 `Noto Sans CJK TC` 字型存在，再寫入 user-level fontconfig alias：`Noto Sans TC → Noto Sans CJK TC`，重建 cache 後再次驗證 `fc-match`。Playwright 仍需通過 `document.fonts.check` 才可截圖。
- 最新 workflow SHA：`eb95ab66db37dded42d49d3e82386223b6d27265`；QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`。
- 本次 alias 修正尚未經 CI 驗證；在 fontconfig、Playwright 字型檢查及六視窗截圖全部確認正常前，不得宣稱視覺 QA 通過。


## 2026-11-21｜Weekday 母版檔名映射修正（待重跑）

- run 44906846280 的 Weekday fixture 已完成 HTML assemble、Playwright interaction 與六視窗視覺／字型測試；母版 DOM 驗收未能開始，因 workflow 將 `TEMPLATE_KEY=weekdays` 直接拼成 `weekdays-mother-template.html`，但 manifest materializer 實際輸出檔名是單數 `weekday-mother-template.html`。
- 已在 build 與 qa-only 兩條路徑新增明確映射：`monday → monday-mother-template.html`；`weekdays → weekday-mother-template.html`，並以 `MOTHER_FILE` 傳給 DOM validator。這是路徑錯誤修正，不是 DOM mismatch 通過證據。
- 最新 workflow SHA：`eb95ab66db37dded42d49d3e82386223b6d27265`；候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- Weekday 母版必須在此映射修正後重新跑完整流程；不得沿用 44906846280 的失敗 run 當成通過。


## 2026-11-21｜雙母版實證後的規則一致性修訂（仍為 DRAFT）

1. **實際雙母版 build 已通過，但版本基準尚需統一重跑。** Monday run 44906803821 使用 candidate rules blob `9d0b2fed694ffe09724f310514f3a4f759b9b956`；Weekday run 44907253127 使用較新的 candidate rules blob `1b808c093bfd6186febdca58021589026ef23700`。兩者 Builder／Manifest／QA Contract 相同，但規則 SHA 不同，因此不可宣稱是同一個規則版本的雙母版驗收。凍結本次草案內容後，必須以同一 candidate rules SHA 重跑 Monday 與 Weekday。
2. **Provenance 四項規則／資產 SHA 已實際驗證。** `validate_review_artifact.py` 會從不可變 build commit 讀回並驗證 Manifest、QA Contract、active SIM-1.3、candidate SIM-1.4 的路徑與 blob SHA；sidecar 也分別記錄四項 SHA。舊稽核中「缺少四項 provenance」已過時。
3. **狀態欄位已分層。** Sidecar 同時記錄 `status`、`review_ready`、`data_review_ready`、`sim14_builder_approval`、`sim14_review_ready`。其中舊 `review_ready` 是資料型 readiness，不是 SIM-1.4 完整交付狀態；Builder 未經使用者核准時，`sim14_review_ready=false`。第 9.1 已補上定義。
4. **DOM validator 的聲明範圍須精確。** 現有 validator 驗證 CSS／JS、ID inventory 及列明的穩定母版結構，不是全頁每一個動態子節點的 byte-for-byte DOM diff。每日動態事件卡／財報卡／行事曆清單只可在核准槽位內更新；外層 wrapper、prototype、details／summary、來源連結及母版互動節點必須保留。
5. **舊 `tac_html_binding_map.json` 不再作活動授權。** 其 `mutate_only_text_nodes=true` 與目前經 QA Contract 定義的受控動態卡片 clone／list item refresh 並不完全相容。現階段將它標為歷史映射，不得單獨授權 Builder 寫入；若未來要恢復使用，必須先逐 selector 同步更新並納入同一 QA Contract。
6. **六視窗與字型條件一致。** 本文第 9.2 已補入 320px，並要求實際驗證繁體中文字型；QA Contract v1.8 DRAFT 同樣要求 Noto Sans CJK TC／fontconfig alias 與 Playwright 字型檢查。
7. **Fed 官員週行程不得刪除。** Builder 使用母版固定 wrapper、title、list、prototype、empty-state；只替換動態 event instances 並填入官方來源連結。FedWatch 仍固定兩卡兩段，不得擅自改回三卡。
8. **核准狀態不變。** SIM-1.3 仍為唯一現行有效規則；SIM-1.4 仍為 DRAFT。候選 Builder 尚未獲使用者明確核准為唯一入口；本修訂不授權 main、正式首頁、正式母版或正式行事曆 JSON 的修改。


## 2026-11-21｜凍結候選規則版本後的雙母版同版重跑

- 本次一致性修訂已完成；以本 commit 的 candidate SIM-1.4 blob SHA 作為雙母版同版回歸基準。
- 先跑 Monday 2026-11-23，再跑 Weekday 2026-11-20；兩次 build 必須讀取同一 candidate rules SHA、Builder SHA、Manifest SHA、QA Contract SHA。若任一規則／技術資產在兩次 run 之間變更，先停止並重新凍結版本，不得把不同 SHA 的 run 合併宣稱為同版雙母版驗收。
- 本節只規定 simulation branch 的回歸順序，不授權 SIM-1.4 生效或正式資產修改。## 附錄 E｜SIM-1.3 → SIM-1.4 條文處置摘要

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
| F3-補充2、4–10 | 5、附錄 B | 衝突清理；Yahoo Finance Average Estimate 第一順位、Investing.com 第二順位；EPS／Revenue 分開選源 |
| G1–G4、11/17、11/19 補充 | 7 | 合併；週一／平日總結分流、三區評論綁定 |
| H | 0、2、4、11 | 重寫；只保留 04:35 JSON 更新、05:25 唯讀、preview／首頁／封存分離 |
| I | 0、9、10 | 合併；狀態、恢復、計時及 QA 重跑規則集中 |
| 第五步 QA、A1 QA 指定 | 1、8、9、附錄 D | 重寫；流程 Gate 與 QA 檢查類型分開定義 |
| 第六步發布 | 0、9、11 | 重寫；定版綁定 SHA，QA 豁免不得偽裝通過 |
| J 與所有歷史補充條文 | 獨立歷史檔 | 移至 `simulation-lab/analysis/SIM-1.4_DRAFT_HISTORY.md`，不再混入有效規則 |
| B3.2–B3.6 母版視覺／互動規則 | 1.3、9.2 | 補回上漲紅／下跌綠、中文名稱／英文代碼層級、連結範圍、五星／四星顏色、禁止恢復已刪除膠囊、工具泡泡與呼吸燈分開驗收 |
| WTI／Brent／GC／SI 商品顯示及連結 | 3.3、附錄 A | 可見名稱不加合約月份；合約資料留來源說明；href 直接開啟並核對 Investing.com 對應歷史頁 |
| 行事曆台灣日期／截稿狀態 | 4.9–4.11、9.2 | 同日事件即使晚於截稿仍列今日；過期未證實者待核實；跨時區先轉 Asia/Taipei；延期／取消明確標示 |
| 財報 EPS／Revenue 雙卡母版版型 | 5.3、8.2、9.2 | 保留母版 DOM／CSS／欄數；不得重建或注入覆蓋樣式 |
| Builder 唯一入口、provenance 與 sidecar 狀態 | 8.1、9.1、9.3 | 技術 PASS 不等於核准；不同 SHA 的測試證據不得合併宣稱同版雙母版通過 |

完整逐條來源、條文對照及裁決依據見 `simulation-lab/analysis/SIM-1.3_to_SIM-1.4_clause_disposition.md`。目前實作狀態、最新 SHA 與未完成 Gate 以 Session State、Work Log 及 Builder 相容性稽核為準；本附錄不重複維護每日進度。

## 版本紀錄

- 2026-11-21：SIM-1.4 首次整併草案；不生效、不覆寫 SIM-1.3。
- 2026-11-21：補入商品名稱／歷史頁連結、台灣截稿行事曆分類、財報母版雙卡及 B3 視覺／互動規則。
- 2026-11-21：歷史實證與過期 SHA 快照移至 `simulation-lab/analysis/SIM-1.4_DRAFT_HISTORY.md`；本檔只保留現行候選規則與簡要處置摘要。

