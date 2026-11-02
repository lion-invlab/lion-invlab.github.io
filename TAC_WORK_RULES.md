# TAC 投資早報｜正式工作規則

版本：4.0（2026-11-02｜單一流程與責任整併版）
建立日期：2026-10-28
本次整併日期：2026-11-02
適用範圍：TAC 投資早報資料蒐集、分析、每日審核版、版面更新、品質驗收及正式發布。

## A. 規則權威、責任與基本原則

### A1. 唯一權威來源
1. 本檔（GitHub main 根目錄 `TAC_WORK_RULES.md`）是唯一正式工作規則。每次工作開始前必須重新讀取 main 最新內容，不得以聊天記憶、舊交接摘要、舊版副本或其他同名檔案取代。
2. 使用者最新明確指示優先於本檔；但不得把一般討論、假設或助理建議視為已核准變更。若明確指示改變長期規則，先更新本檔並記錄，再依新規則執行。
3. `母版專區/mother-template-manifest.json` 是核准母版路徑與 SHA 的唯一登記來源；本檔定義製作規則，Manifest 定義實際核准檔案。兩者不一致時停止母版渲染，不得自行猜選或更新 SHA。
4. `母版專區/母版結構驗收清單.md` 是每日 HTML 結構、功能與視覺 QA 的唯一詳細執行清單。它是技術驗收附件，不是第二份 Work Rules；本檔只定義 QA Gate、通過門檻及權責，不重複抄錄清單。
5. 行事曆資料庫的 schema、事件欄位與更新紀錄以 repo 中正式資料及其維護規則為準；不得另建平行資料庫或替代路徑。

### A2. 不可妥協的原則
- 先核實，再呈現；不猜值、不捏造新聞、不用舊快照冒充最新資料。
- 每一筆行情均須可辨識標的、資料日期／時間、時區、價格口徑及來源。
- 版面只更新內容，不重建、不簡化、不重新設計核准母版。
- 先產出獨立審核版；使用者明確核准後才可發布至正式首頁。
- 計畫、資料取得、檔案寫入、commit、Pages 部署、內容驗收是不同狀態，不得混稱完成。
- 工作應在授權範圍內自主連續執行，不要求使用者逐步輸入「繼續」；只在需要使用者決策、權限或無法安全推斷時暫停該項，其餘工作繼續。
- 不以流程文件存在、測試程式存在或 GitHub Actions 綠燈，推定自動化或資料品質已完成。

## B. 唯一核准母版與保護範圍

### B1. 雙母版
每日依台灣報告日期選擇唯一母版，並以 Manifest 的精確路徑及 blob SHA 驗證：
- 週一：`母版專區/TAC_母版_週一_2026-10-28_最終定版.html`
- 週二至週五：`母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html`

週一版保留「上週經濟行事曆」「上週財報行事曆」及導航；週二至週五版不得出現這兩個區塊及導航。其他共用版型、CSS、JavaScript、Dashboard、欄位、連結與互動均依各自核准母版完整保留。

若 Manifest 缺失、母版不存在、SHA 不符、星期情境不符或必要結構驗證失敗，停止渲染並回報；不得 fallback 至首頁、歷史報告、preview、其他分支或自行重建的 HTML。只有使用者明確核准母版變更後，才可更新母版及 Manifest。

### B2. 保護檔案與允許修改範圍
未取得使用者明確授權，不得修改：
- 正式首頁 `index.html`
- 雙母版及 `母版專區/mother-template-manifest.json`
- `refactor-work/design-system.css`、`refactor-work/source-baseline-2026-10-26.html` 等獨立設計重構資產
- 既有歷史報告及非本次指定的資料檔

每日審核版只允許更新核准母版中當日日期、行情數值、新聞、行事曆資料、分析文字、來源及必要連結等內容；不得刪除、重排、縮減、改名、改樣式或改變任何既有元件與互動。Renderer 若未經測試驗證，只能視為未完成工具，不得用它重建頁面。

### B3. 固定版面與視覺規則
必須保留核准母版既有的頁首、日期、狀態列、導航、總結、Market Sentiment、新聞、全球市場、產業／債匯商品、適用的上週與本週行事曆、今日關鍵價位、今日觀察、資料來源、頁尾及全部 CSS／JavaScript／tabs／收折功能。
- 上漲紅、下跌綠；同類漲跌數字的字級、粗細、行高與對齊一致。
- 中文名稱在上、英文代碼小字在下，不加括號；沿用母版既有字體與版面。
- 行情卡只連結名稱或代碼，不把點位、漲跌幅及評論包入連結。
- 行事曆重要性採 TAC 自主五星制；完整顯示五格星等。五星事件標題使用 TAC 紅色，四星沿用核准母版樣式。
- 不得重新加入使用者已要求刪除的總結區下方「關鍵重點」膠囊。
- 工具欄說明泡泡須在使用者首次捲動／觸控移動時立即提前消失，不等待原定 6.5 秒；泡泡消失不得連帶移除工具欄呼吸燈／高亮提示，呼吸燈仍依原定時間持續（除非使用者點擊或母版原始行為另有定義）。此行為若存在於所選母版，須在預覽中保留並分別驗收泡泡及呼吸燈；未實測不得宣稱實機通過。
- 不得以 CSS 臨時覆蓋掩飾 DOM 缺失，不得為統一 selector 重寫母版原有不同實作。

## C. 每日唯一生產流程（六步驟）

這是每日唯一主流程。其他章節只提供各步驟需要遵循的內容規格，不另形成第二套流程。

### 第一步｜讀取規則、日期與母版
1. 讀取 main 最新版本檔及 Manifest。
2. 確認報告日期、Asia/Taipei（UTC+8）、星期情境、美東 EDT／EST 狀態、目標產出時間、最近一個已完成的美股交易日及預覽路徑。
3. 依 Manifest 讀取唯一對應母版，核對實際 SHA、必要區塊及星期情境。
4. 列明本次輸出檔案與保護檔案。以上任何必要條件不符，停止母版製作並回報，不得自行替換來源。

### 第二步｜蒐集並核實市場行情
1. 依 D 節固定清單及個別指標的來源優先序，更新全球市場、產業 ETF、債券、外匯、能源、貴金屬及風險情緒指標。不得漏掉核准母版中的固定欄位；本產品行情資料集以 44 項固定市場指標及 11 大產業 ETF 為完整更新目標。
2. 一般指數與行情依各指標指定來源讀取；SOX、VIX、MOVE 等優先依 D 節指定 Investing.com 香港站頁面。Fed 利率機率必須在本次製作當下直接讀取 Investing.com Fed Rate Monitor 動態頁，記錄台灣時間及目標會議。
3. 逐項確認標的身分、資料日期／更新時間、時區、正式收盤／結算／盤中、現貨／期貨、合約月份、報價方向與單位。交易所指數採最近一個已完成交易日正式收盤；即時更新型指標記錄實際更新時間，不假裝是收盤值。
4. 每項資料採「優先來源一次讀取 → 失敗時以不同方法重試同一優先來源一次 → 仍失敗才查既定備援」的單項流程。不得重複同一失效動作；不得為了完成形式而對全資料集再做一輪無差別重抓。
5. 優先來源有可核實且符合欄位口徑的資料時採用，不因備援數字略有不同任意切換。來源差異先核對標的、日期、時間、口徑及修訂；無法解釋則標示待核實，不取平均、不猜值。
6. 每項狀態記為「主要來源已核實」「備援來源已核實」「待核實」「暫缺」「不適用／休市」之一，並保留來源網址、日期／時間、讀取方式及必要口徑。不得將技術性讀取失敗誤判為市場無報價。
7. 個別項目完成處理後即進入下一項，不讓單一失敗中斷整批工作。所有項目各自處理一次後，僅針對仍待處理項目做一次清單式總檢查；已完成且無新證據的項目不必重抓。
8. 無法核實的項目在主畫面標示「待核實」或「暫缺」，不得留白造成零值誤解；分析文字不可把未核實數字寫成確定事實。

### 第三步｜讀取行事曆資料庫並核實事件
1. 唯一資料路徑為 `data/calendar/weeks/YYYY-Www.json`（ISO week）。禁止使用 `data/calendar/weekly/` 或其他替代路徑。讀取 main 分支本週 JSON；週一另讀取必要的上週 JSON。
2. **責任分工：** 每日 03:30 行事曆資料庫排程是週資料庫的例行維護者／寫入者；每日早報流程原則上只讀取資料庫、核實當日必要事件並將資料呈現到審核版，不重建週資料、不另開平行資料庫、不與維護排程並行寫入。若早報時發現資料庫需要修正，記錄具體缺漏並透過資料庫維護工作處理；不得為了完成早報而私自重寫資料庫。
3. `coverage.economic`／`coverage.earnings` 的 `incomplete` 是動態進行中狀態，可能因事件尚未發生、實際值尚未公布而正常存在；不得單憑 incomplete 判定故障或阻止當日早報。未到公布時間的 actual=null 屬正常，不得預填或推估。只有檔案不存在、JSON/schema 損壞、核心事件集合明顯缺失、來源／更新資訊異常或當日必要事件無法可靠呈現，才列為資料問題。
4. 逐筆核對報告日期、事件識別碼、原始發布日期時間、台灣時間、國家／公司、事件類型、發布狀態、實際值、預期值、前值（適用時）、來源及目標分頁。已公布事件核對實際值；未來事件核對日期、時間、預期值及來源。
5. 依 TAC 星等與星期情境篩選：本週經濟／財報行事曆只呈現 TAC 四星、五星；週一上週兩區只呈現五星。所有國家／經濟體同一標準，不得機械換算外部一至三星。
6. 事件狀態依實際發布情況分為「已公布／已發布」「今日公布」「即將公布」及適用的延期、取消、待核實。已公布事件移入正確分頁，原分頁不得殘留過期卡；沿用穩定事件 ID，避免重複或遺失。排序以台灣時間為準：今日公布由早到晚、即將公布由近到遠、已公布由新到舊；時間待核實者放該分頁待核實區，不猜時間。
7. 已公布且資料完整、來源可追溯、狀態正確的卡片採保留制；只補缺漏或修正已知錯誤，不為例行更新無必要重抓完整卡片。

### 第四步｜新聞蒐集與市場分析
1. 依 E 節的台灣時間窗口蒐集新聞。新聞卡必須連至真實存在、可直接開啟的原始報導；先讀原文再摘要，核對原始發布時間、時區及連結。
2. 全球焦點新聞目標 5 則，以鉅亨網、Investing.com 的宏觀重要新聞為主；重大國際事件可使用 Reuters、AP 等可靠原始報導。市場熱門頭條目標 10 則，內容可涵蓋總經、市場、企業重大消息、個股異動、財報、併購、AI、半導體等。
3. 不得把行情數據、報價頁、殖利率或 FedWatch 機率包裝成新聞。兩區避免重複同一事件；合格新聞不足時減少則數並說明，不得杜撰或灌水。
4. 依最終已核實行情、新聞及行事曆撰寫總結、盤面觀察重點、Market Sentiment、今日觀察重點、關鍵價位及必要的產業／跨資產分析。
5. 所有分析區塊依 F 節分工；資料修正後只檢查並更新受影響區塊，不要求每一筆資料都無差別重寫全篇。

### 第五步｜母版內容更新與單一 QA Gate
1. 從第一步通過 SHA 驗證的母版完整複製，產生獨立日期審核版。只替換允許更新的內容槽位；不得重建 DOM、重排元件、重設 CSS／JavaScript 或變更互動。
2. 完成資料、新聞、行事曆及分析內容更新後，執行一次整體 QA Gate。詳細檢查只依 `母版專區/母版結構驗收清單.md`，不得再另外執行第 8、16、24、25 節等重複版本的清單。
3. QA Gate 分為四類，並在交付回報分別列示：
   - **資料與內容：** 日期、行情基準日、來源、欄位、新聞時間窗、事件分頁／星等、分析與數字一致。
   - **母版結構：** 來源 SHA、必要區塊、DOM／ID／錨點、卡片欄位、超連結及與母版差異。
   - **互動功能：** tabs、導航、紅色圓形「＋」收折控制、details／summary、資料來源展開／收折及行情連結。
   - **視覺回歸：** 桌面、手機常見寬度及至少 320px；檢查字級、間距、卡片欄位、顏色、排序、對齊與溢位。
4. 靜態檢查、原始碼存在或自動化測試通過，不得冒稱已完成瀏覽器、iPhone 或實機測試。不能實際執行的項目標示「未測試」。
5. 任一強制項目未通過，該版不得標示「可審核完成」。停止在錯誤結構上繼續補資料；保留已核實內容，回到正確母版修復後，重跑受影響測試及完整 QA Gate。
6. QA 清單中已完整且無需更新的內容，採保留制；不為了形式重複重抓或重製。

### 第六步｜交付審核版與正式發布
1. 審核版固定寫入 `preview/YYYY-MM-DD.html`。若同日檔案已存在，先回讀後更新同一路徑，不另造多份同日副本。
2. 首選預覽網址：`https://lion-invlab.github.io/preview/YYYY-MM-DD.html`。不得以 GitHub /blob/ 原始碼頁代替。GitHub 寫入成功不等於 Pages 已部署或可開啟。
3. 寫入後重新 fetch 回讀審核版，核對檔案路徑、日期、內容、commit／blob SHA、母版來源及保護檔案未被修改；並實際開啟 Pages 網址確認載入正常 HTML。無法確認部署時明確標示「已寫入 GitHub，Pages 尚未驗證」。
4. 回報資料基準日、來源、完成項目、待核實／暫缺項目、QA 四類狀態、GitHub 寫入狀態及 Pages 部署狀態。不得將未測試項目寫成通過。
5. **正式發布閘門：** 只有使用者明確核准該份審核版後，才可更新正式首頁 `index.html`。核准只適用該份指定審核版，不自動授權修改母版、Manifest、設計系統或其他資產。
6. 正式發布後回讀首頁，核對 commit、部署狀態與線上內容；若無法確認，明確標示未完成。

## D. 市場資料範圍、來源與口徑

### D1. 固定更新範圍
- 全球主要市場：道瓊、S&P 500、Nasdaq Composite、Russell 2000、SOX、Nikkei 225、KOSPI、台灣加權、Singapore STI、S&P/ASX 200、上海綜合、深證成指、Hang Seng、FTSE 100、DAX、CAC 40、STOXX Europe 600；以及核准母版固定列出的其他市場項目。不得刪除固定欄位。
- S&P 500 十一大產業 ETF：XLE、XLF、XLK、XLI、XLY、XLP、XLU、XLV、XLB、XLRE、XLC。只呈現各 ETF 漲跌幅，依當日漲跌幅排序；不得改變母版活頁及欄位配置。
- 債券：美國 2 年、10 年、30 年公債殖利率。
- 外匯：DXY、USD/TWD、EUR/USD、GBP/USD、AUD/USD、USD/JPY。
- 能源與貴金屬：WTI、Brent、黃金 GC、白銀 SI。
- 風險／情緒：SOX、VIX、MOVE、CNN Fear & Greed、FedWatch。
- 全部固定行情項目逐項登記狀態；資料缺漏時保留欄位並顯示待核實／暫缺，不得刪欄或猜值。

### D2. 通用資料裁決
1. 優先來源可取得、日期口徑正確且可確認為最新時，採用優先來源；只有缺值、過期、未更新、必要欄位缺失或標的／日期／口徑無法核實時，才啟用備援。
2. 先確認標的身分，再確認資料日期、時區、更新時間、正式收盤／盤中／結算、現貨／期貨、合約月份及單位，最後依該指標指定來源順序裁決。
3. 不同來源時間或口徑不同，不可直接視為數值衝突；先查明差異。無法解釋時標示待核實，不取平均、不猜測、不沿用舊值。
4. 技術口徑、擷取時間、合約代碼、來源及備援原因放在既有收折式「資料來源／計算方式」區；主畫面只放必要的最短限制提示。
5. 空值不得當作零。若無任何可核實報價，主畫面標示「暫缺」或「待核實」。

### D3. 指標專屬來源與口徑
- **SOX：** 優先 Investing.com 香港站歷史資料 `https://hk.investing.com/indices/phlx-semiconductor-historical-data`，採最近已完成交易日正式收盤及日漲跌幅；核對日期、指數名稱與延遲標記。Yahoo Finance `^SOX` 僅作備援／交叉核對。
- **VIX：** 優先 Investing.com 香港站 `https://hk.investing.com/indices/volatility-s-p-500`，採最近已完成交易日正式收盤；Cboe 歷史資料 `https://www.cboe.com/tradable_products/vix/vix_historical_data` 作官方交叉核對，Yahoo Finance `^VIX` 作備援。
- **MOVE：** 優先 Investing.com 香港站歷史資料 `https://hk.investing.com/indices/ice-bofaml-move-historical-data`。必須確認確為 ICE BofA MOVE Index 及同一交易日；不得只因 Yahoo `^MOVE` 有數字就採用，無法確認標的身分即待核實。
- **CNN Fear & Greed：** 優先 CNN Business `https://www.cnn.com/markets/fear-and-greed`；頁面無法讀取時，嘗試 CNN 頁面使用的資料端點 `https://production.dataviz.cnn.io/index/fearandgreed/graphdata`。記錄分數、評級、資料日期與實際更新時間；端點非有公開穩定性保證的正式 API。官方來源皆不可用時才使用 FGScore、Fear & Greed Tracker 等第三方備援，並保留網址及時間戳。
- **FedWatch：** 日常讀取優先使用 Investing.com Fed Rate Monitor `https://www.investing.com/central-banks/fed-rate-monitor`，必須在本次製作當下讀取，記錄台灣時間、目標 FOMC 會議日期、各目標利率區間機率及頁面可得的期貨價格／比較欄位。CME 官方工具 `https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool` 僅作方法與交叉核對，不得把 Investing.com 數據稱為 CME 官方數據。機率合計與卡片／長條圖須一致；無法取得動態機率或更新時間時標示待核實，不用舊快照或自行推算填補。
- **美國公債殖利率 2Y／10Y／30Y：** 優先美國財政部 Daily Treasury Par Yield Curve Rates `https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics`，三個期限採同一資料日期的 CMT／par yield。備援 FRED：`https://fred.stlouisfed.org/series/DGS2`、`https://fred.stlouisfed.org/series/DGS10`、`https://fred.stlouisfed.org/series/DGS30`。不得混用個別債券即時殖利率或不同日期。
- **DXY：** 使用美元指數現貨／CFD 序列，不得誤用美元指數期貨 DX。Investing.com 歷史頁 `https://www.investing.com/indices/usdollar-historical-data`。
- **USD/TWD：** 若欄位標示台北外匯／銀行間官方收盤，優先中央銀行「新臺幣／美元銀行間收盤匯率」`https://www.cbc.gov.tw/tw/lp-645-1-1-60.html`，核對官方 NTD/USD 原始方向及資料日期；如轉成 USD/TWD 必須明確換算。Investing.com `https://hk.investing.com/currencies/usd-twd` 只作市場報價序列備援，不得冒稱銀行間官方收盤。銀行牌告買賣價不可替代銀行間收盤。
- **EUR/USD、GBP/USD、AUD/USD、USD/JPY：** 優先 Investing.com 歷史頁：`https://www.investing.com/currencies/eur-usd-historical-data`、`https://www.investing.com/currencies/gbp-usd-historical-data`、`https://www.investing.com/currencies/aud-usd-historical-data`、`https://www.investing.com/currencies/usd-jpy-historical-data`。備援須核對相同貨幣對、日期、報價方向及時間；Fed H.10 是紐約中午買入匯率且按週發布，不可直接替代日收盤。各貨幣市場日界線不同，不得假設六項匯率同時收盤。
- **WTI：** 欄位採期貨結算價，優先 CME／NYMEX Daily Settlements `https://www.cmegroup.com/market-data/daily-settlements.html`；備援 Investing.com `https://www.investing.com/commodities/crude-oil-historical-data`。不得用 EIA 現貨價替代。
- **Brent：** 優先 ICE Brent 官方產品／結算資訊 `https://www.ice.com/products/219`；備援 Investing.com `https://www.investing.com/commodities/brent-oil-historical-data`。核對合約月份、日期及結算口徑。
- **黃金 GC、白銀 SI：** 優先 CME／COMEX Daily Settlements `https://www.cmegroup.com/market-data/daily-settlements.html`；備援 Investing.com 黃金 `https://www.investing.com/commodities/gold-historical-data`、白銀 `https://www.investing.com/commodities/silver-historical-data`。不得以 XAU/USD、XAG/USD 現貨或 LBMA／ICE IBA 定盤價替代期貨欄位。
- **期貨換月：** 記錄標的、合約月份、交易日期、settlement／close 欄位及來源。Investing.com 連續期貨序列不得冒稱特定交易所合約官方結算價；換月日若不可比，不自行計算漲跌幅，標示待核實。
- **其他全球指數與 11 大產業 ETF：** 依核准母版指定的 Investing.com 香港站對應標的頁讀取；核對標的、交易日、正式收盤及漲跌幅。不得以相似代碼或不同市場標的代替。

### D4. 關鍵價位
- 以同一基準交易日、同一標的且已核實的 OHLC 計算，標示基準日期；公式與來源放既有收折區。
- GitHub Actions「TAC Daily Key Levels」若為當日正式流程的一部分，冬令早報 05:25 前應確認該工作完成並讀取本次執行結果／產物。工作流程成功不等於 OHLC 或價位正確，仍須核對該工作定義的五項指數資料日期一致性及 OHLC 合理性。夏令／冬令對應時間依 America/New_York 實際 DST 狀態判定。
- 關鍵價位驗收與 FedWatch 驗收分開；其中一項失敗不得冒充另一項成功。
- 若無法確認來源、OHLC 或基準日期，標示待核實，不得使用舊快照冒充最新價位。

### D5. 標準行情超連結
以下網址是讀者點擊目的頁規範，不會自動取代 D3 的數據來源／結算口徑。只連結名稱或代碼；一般行情連結新分頁並設 `rel="noopener"`。CNN Fear & Greed 是唯一固定同頁開啟例外。
- 全球指數：道瓊 `https://hk.investing.com/indices/us-30`；S&P 500 `https://hk.investing.com/indices/us-spx-500`；Nasdaq Composite `https://hk.investing.com/indices/nasdaq-composite`；Russell 2000 `https://hk.investing.com/indices/smallcap-2000`；SOX `https://hk.investing.com/indices/phlx-semiconductor`；Hang Seng `https://hk.investing.com/indices/hang-sen-40`；上海綜合 `https://hk.investing.com/indices/shanghai-composite`；深證成指 `https://hk.investing.com/indices/szse-component`；Nikkei 225 `https://hk.investing.com/indices/japan-ni225`；KOSPI `https://hk.investing.com/indices/kospi`；台灣加權 `https://hk.investing.com/indices/taiwan-weighted`；STI `https://hk.investing.com/indices/singapore-straits-time`；S&P/ASX 200 `https://hk.investing.com/indices/aus-200-historical-data`；FTSE 100 `https://hk.investing.com/indices/uk-100`；DAX `https://hk.investing.com/indices/germany-30`；CAC 40 `https://hk.investing.com/indices/france-40`；STOXX Europe 600 `https://hk.investing.com/indices/stoxx-600`。
- 風險／情緒：VIX `https://hk.investing.com/indices/volatility-s-p-500`；MOVE `https://hk.investing.com/indices/ice-bofaml-move`；CNN Fear & Greed `https://edition.cnn.com/markets/fear-and-greed`（同頁開啟）。
- 殖利率：美國 2 年 `https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield`；10 年 `https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield`；30 年 `https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield`。
- 外匯／商品：DXY `https://www.investing.com/indices/usdollar`；USD/TWD `https://hk.investing.com/currencies/usd-twd`；EUR/USD `https://hk.investing.com/currencies/eur-usd`；GBP/USD `https://hk.investing.com/currencies/gbp-usd`；AUD/USD `https://hk.investing.com/currencies/aud-usd`；USD/JPY `https://hk.investing.com/currencies/usd-jpy`；WTI `https://hk.investing.com/commodities/crude-oil`；Brent `https://hk.investing.com/commodities/brent-oil`；黃金 `https://hk.investing.com/commodities/gold`；白銀 `https://hk.investing.com/commodities/silver`。
- 11 大產業 ETF：XLE `https://hk.investing.com/etfs/spdr-energy-select-sector-fund`；XLF `https://hk.investing.com/etfs/financial-select-sector-spdr-fund`；XLK `https://hk.investing.com/etfs/spdr-select-sector---technology`；XLI `https://hk.investing.com/etfs/industrial-sector-spdr-trust`；XLY `https://hk.investing.com/etfs/spdr-consumer-discr.-select-sector`；XLP `https://hk.investing.com/etfs/spdr---consumer-staples`；XLU `https://hk.investing.com/etfs/spdr-select-sector---utilities`；XLV `https://hk.investing.com/etfs/spdr---health-care`；XLB `https://hk.investing.com/etfs/spdr-materials-select-sector-etf`；XLRE `https://hk.investing.com/etfs/real-estate-select-sector-spdr?cid=959413`；XLC `https://hk.investing.com/etfs/communication-services-select-spdr`。
- 同一指數在不同頁籤重複出現時，href 必須一致；連結不可包住數值、漲跌幅或評論。連結目的頁驗收只確認連結與標的相符，不代表行情數據已核實。

## E. 新聞規格
1. 新聞時間窗口均採台灣時間與原始發布時間：
   - 週一：前一個美股交易日台灣時間 12:00 起，至本次實際截稿時間。
   - 週二至週五：前一日台灣時間 12:00 起，至本次實際截稿時間。
2. 優先來源為鉅亨網、Investing.com；國際重大事件可用 Reuters、AP 等可信原始報導交叉核對。
3. 每則新聞必須有真實存在且可直接開啟的原始報導連結。先閱讀原文，核對原始發布時間、時區、最後更新時間，再忠實摘要事件、背景、影響與分析。
4. 搜尋排序時間、爬取時間或最後更新時間不得代替原始發布時間。原始發布時間無法確認時標示待核實或剔除。
5. 不得把指數／商品報價、漲跌幅、FedWatch 機率、行情快訊或數據儀表板包裝成新聞。行情數據只能作為原文支持的背景，不能單獨構成新聞。
6. 全球焦點新聞目標 5 則，以宏觀事件為主；市場熱門頭條目標 10 則，涵蓋總經、市場、企業重大消息、個股異動、財報／併購／AI／半導體等。兩區應有不同功能並避免同一事件重複。
7. 合格新聞不足時減少則數並註明，不得杜撰標題、內容、時間、連結或為湊數灌水。新聞摘要直接描述事件，不用「依據某媒體報導」等贅語開頭；來源列在卡片下方。

## F. 行事曆評級、卡片及分析規格

### F1. TAC 五星評級
- 經濟與財報事件均採 TAC 自主五星制，顯示完整刻度 ★☆☆☆☆ 至 ★★★★★；不得直接複製或機械換算外部一至三星評級。
- 本週經濟與財報行事曆只收錄四星、五星；週一上週經濟與財報行事曆只收錄五星。適用所有國家／經濟體。
- 五星代表可能造成全球／主要市場政策轉折、重大定價重估或跨資產顯著波動；四星代表對主要經濟體、重要區域、關鍵產業或大型權值企業具明顯市場影響；一至三星不納入早報精選。
- 評級須依事件本身的市場影響獨立判斷。證據不足標示「評級待核實」並暫不列入已確認四／五星清單；不得以外部星等補值。

### F2. 經濟事件
已公布經濟事件依適用性呈現事件名稱、國家／經濟體、期間、台灣公布時間、實際值、預期值、前值、結果比較、影響解讀及可追溯來源。無可比值或不適用欄位須明確標示，不得捏造。高於預期不必然利多、低於預期不必然利空，須結合指標方向、政策背景、前值修正及市場定價解讀。

### F3. 財報公司範圍與已公布卡
- 美國公司依 TAC 重要性評級納入。非美國公司只有在 NYSE、Nasdaq、NYSE American 等美國證券交易所正式掛牌的普通股、ADR 或 ADS 才可納入；OTC／OTCQX 或只在美國以外掛牌者不納入。須以公司 IR、交易所、SEC 或存託機構資料核實市場及代碼；無法核實先排除並標示待核實。
- 財報時間優先依公司 IR 公告，區分美股盤前／盤後及台灣日期。正式季度／年度財報、自結／初步數字、月營收及其他公告不得互相冒充。
- 已公布財報必須使用核准母版專用版型：EPS 與營收兩張實績卡並列，分別呈現實際、預期、幣別／單位、EPS GAAP／調整後口徑及各自的高於／符合／低於預期狀態；無可比共識明確標示。兩卡下方保留全寬詳細資訊區，包含公布時段、EPS／營收比較、財報判讀、股價反應與來源。
- 桌面與手機均維持兩欄並列；不得改成單卡、純文字或上下堆疊。缺欄時標示未取得／待核實，保留版型，不得猜值。
- 股價反應必須標示觀察時間及盤前／正常交易／盤後時段；不可用前一日收盤冒充財報公布後反應。財報優於預期不代表股價必漲，低於預期不代表必跌。

### F4. 事件保留、搬移與排序
- 已公布且欄位完整、來源可追溯、狀態正確的卡片採保留制；有新修正、已知錯誤或欄位缺漏才重新查證／更新。
- 更新事件優先沿用穩定識別碼，移動完整卡片；不得新增重複卡而保留舊卡。狀態搬移後檢查原分頁無殘留、目的分頁正確、事件無遺失／重複。
- 今日公布依台灣預定時間由早到晚；即將公布依時間由近到遠；已公布依實際日期時間由新到舊。只有日期無精確時間時不可捏造同日先後；時間待核實者集中於該分頁末端待核實區。
- 延期、取消、實際值未取得或來源狀態不明時如實標示，不得僅因預定時間已過就推定已公布。

## G. 分析與文字規格

### G1. 總結（市場判斷）
- 原則上 4–5 個重點，每點 1–2 句。先結論，再說明有來源支持的原因、主要風險及後續觀察條件。
- 回答市場主軸、漲勢廣度、跨市場同步性、主要風險及可能改變判斷的事件。
- 不複製行情表，不逐項重抄點位與漲跌幅；只有論證必要時引用最少量數字。
- 提出條件式投資應對，不把單日走勢說成趨勢確立，不使用空泛警語取代分析。

### G2. Market Sentiment（市場情緒）
- 只判讀投資氛圍、風險偏好、情緒指標一致性及情緒改善／惡化／轉折是否獲得確認。
- 不重複總結中的事件、產業原因或部位策略；不堆疊 VIX、MOVE、CNN 等已顯示數字。
- 指標互相矛盾時如實指出訊號分歧，不硬套單一情緒標籤；不強制提供買賣策略。

### G3. 盤面觀察重點與 📌 評論
- 盤面觀察重點及各市場／產業／債匯商品圖釘評論，應說明該市場專屬現象、已核實的可能驅動因素、意義、後續驗證條件、風險及審慎應對。
- 分清事實、來源報導與推論；不得把相關性直接說成因果。證據不足時明確標示待確認。
- 股市評論聚焦市場廣度、權值集中及區域分化；產業談輪動；債市談期限結構與利率預期；匯率談貨幣對差異與利差；原油談供需及供應風險；貴金屬談美元、實質利率、避險與工業需求。
- 每則評論以精煉一段為原則，不重複行情數字、不套用通用套話、不為形式完整硬湊原因或預測。

### G4. 資料變動後的分析同步
每次資料補入或修正後，只針對受影響訊號，搜尋並核對總結、Market Sentiment、盤面觀察重點、📌評論、今日觀察各分頁及相關活頁。每個受影響區塊回報「已同步更新」「核對後無須修改」或「仍待核實」。不需要對無關區塊重寫，也不得跳過受影響區塊的核對。

## H. 排程與自動化能力邊界
- 行事曆資料庫排程目標：台灣時間每日 03:30，僅維護週資料庫，不製作早報、不修改 HTML。
- 夏令時間（America/New_York 為 EDT）：工作日早報審核版目標 05:00；冬令時間（EST）：工作日目標 05:25。必須以時區實際 DST 狀態判定；非適用季節的排程不得執行。
- 排程時間是目標，不是資料品質保證。來源延遲、必要資料待核實或 QA 未通過時，寧可如實標示，不可為趕時間猜值。
- GitHub Actions 擷取器、關鍵價位工作、Renderer、Orchestrator 只有在實際整合測試、正反向測試及完整產出驗收通過後，才可稱為已完成。Capture-only／source-probe 或測試分支結果不能直接當正式生產資料。
- 工作流程成功只代表程式工作結束；必須另驗證標的、日期、口徑及數值。若無法觸發 workflow_dispatch，須明確說明未觸發，不得冒稱已執行。

## I. 工作狀態、錯誤處理與規則變更
1. 進度回報只列真實狀態：已完成、進行中、待核實、未測試、未通過。可列完成數／待處理數，但不得用估計進度冒充實際進度。
2. 讀取失敗要區分技術錯誤、來源無資料、休市／不適用及口徑不符。按 C 第二步處理一次替代讀取與既定備援；無法解決即標示待核實，不讓單項錯誤中斷整批工作。
3. 發現母版來源錯誤、結構缺失、互動遺失、數據基準錯誤或保護檔案被改動時，停止擴大修改，回到正確基礎修復。修正前後比較差異，只改授權範圍。
4. 同一路徑不可並行寫入。更新前先回讀當前版本與 SHA；更新後重新 fetch 回讀，核對內容、commit／blob SHA 及未授權檔案未變更。
5. 長期規則變更須記錄日期、舊規則、新規則、適用範圍與原因；只更新本檔，不另建第二份 Work Rules。每次規則變更後做章節編號、內部引用、連結、重複條文與必要需求保留檢查。

## J. 版本 4.0 整併紀錄（2026-11-02）
本版依使用者明確授權，整併原 WR v3.13。保留原有市場資料來源與口徑、TAC 五星評級、新聞真實性、行事曆事件狀態與已公布財報雙卡、分析分工、雙母版鎖定、預覽路徑、使用者發布授權、排程及未完成自動化能力的誠實標示。

主要整併：
- 原第 0、9、10、12、17 節：合併為 A、B、I 的權威來源、開工檢查與錯誤處理。
- 原第 1、2、15、24 節：合併為 B；母版 SHA 與保護範圍仍以 Manifest 為準。
- 原第 4、13、18、21 節：合併為 D；保留指標專屬來源、備援與行情連結，不再把 Actions 擷取流程設為與網頁讀取並列的主要資料入口。
- 原第 5 節：整併為 E，保留新聞真實性及時間窗。
- 原第 6、16、20、21（行事曆排序）節：整併為 F，保留 TAC 五星、非美國公司掛牌範圍、事件搬移、排序及已公布財報雙卡。
- 原第 11、19、22、23 節：整併為 G，保留總結、情緒、圖釘評論分工及受影響區塊同步核對。
- 原第 8、15.2、24、26 節：整併為 C 第五、六步，並指定結構驗收清單為唯一詳細 QA 清單。
- 原第 25 節的無差別第二輪補漏改為單項替代讀取、備援與一次待處理清單總檢查，避免全資料集重複重抓。
- 原第 26 節保留為唯一每日六步驟；自動化尚未實測完成的部分明確標示為未完成能力。

本版只授權更新本規則檔，不代表母版、Manifest、首頁、資料庫、排程、Renderer 或 Orchestrator 已被修改或驗收。
