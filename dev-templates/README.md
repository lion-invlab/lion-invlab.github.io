# TAC 動靜態分離母版架構（TAC Template Architecture）

專案代號：TAC-Template-Architecture

目的：分離 TAC 投資早報的固定版面與每日資料，避免每日更新時反覆核對整份母版，並防止改動卡片、欄位、互動、CSS 與響應式結構。

## 三層架構
1. 正式母版：唯讀，唯一來源仍是母版專區/mother-template-manifest.json 指定的週一與週二至週五母版。
2. 開發母版：從正式母版複製，保留完整元件骨架；動態資料以插槽表示。清空資料不等於刪除卡片、欄位、按鈕或收合功能。
3. 每日資料更新：只允許更新明確列入插槽清單的資料節點，不得整段替換固定元件。

## 驗收原則
- 先核對正式母版路徑與 blob SHA，不符即停止。
- 更新後比對固定 ID、DOM 階層、class、卡片骨架、收合控制、CSS/JS 與週別專屬區塊。
- 固定結構有任何非授權變動即驗收失敗，不得部署。
- 行情、新聞、日曆、財報、摘要與評論仍須按正式 WR 逐項核實。
- 使用者核准後才可部署首頁。

## 保護範圍
本專案不修改 index.html、TAC_WORK_RULES.md、兩份正式母版、正式母版 manifest，也不覆寫既有 11/02 預覽。此分支所有文件與程式均為測試用途，不構成正式 WR 或生產規則。

## 階段進度
- [x] 建立獨立開發分支
- [x] 讀取雙母版與正式 manifest
- [x] 建立第一版架構規格
- [~] 完成主要區塊候選節點定位 v1.2；總結／情緒／今日觀察另有 v1 盤點；KPI、週一上週區塊等需進一步由正式母版逐項核實
- [x] 完成雙母版主要重複資料節點數量盤點 v1
- [ ] 產生週一與週二至週五開發母版
- [x] 結構指紋改採 HTML5 browser-normalized DOM，避免以簡易堆疊解析器誤判瀏覽器可修復的標籤
- [x] 單元測試已由 GitHub Actions 執行；首輪 6 項通過，後續增加重複 ID 次數與事件處理器測試
- [x] 雙母版結構基準解析及正式 SHA 鎖定檢查已通過 CI（Run 41170389474）
- [x] 定義動態 repeat-group 規則；經濟／財報卡片筆數依實際事件增減，不以母版樣本張數作限制
- [x] 使用 Playwright／Chromium 驗證 tabs、details/summary 與 320px 手機列表幾何；紅圓加號視覺與點擊仍待專項驗收
- [ ] 使用 11/02 預覽進行非破壞性測試（須待前述結構驗收通過後）

目前狀態：尚未產生開發母版；slot map 仍為候選 allowlist。CI 已確認週一母版 HTML5 正規化後為 1,976 個節點、4 個 parser 診斷；週二至週五母版為 1,902 個節點、3 個 parser 診斷。這些 parser 診斷是 HTML5 parser 對原始標記的修復提示，不代表瀏覽器 DOM 無法建立。已完成真實雙母版 repeat-group 新增／移除模擬、Playwright 瀏覽器 tabs/details 測試及 320px 手機列表幾何測試。已完成週一母版本週經濟／財報 status-group 的既有列表與 empty-state 互換驗證；平日母版本週區塊及週一上週區塊沒有同區塊 empty-state HTML 原型，故明確拒絕自動轉換。正式母版既有重複 ID 已在 dom-count-audit-v1.md 記錄並鎖定；新增卡片不得引入新的重複 ID。仍未建立開發母版，不得啟用每日自動寫入，不得視為可採用或可部署。

## Selector 命中數驗證補充
- 已建立 `selector-registry-v1.json` 與 `scripts/audit_tac_template_selectors.py`，在 CI 以 HTML5 DOM + CSS selector 引擎驗證週一／平日候選節點命中數。
- 首輪 15 個候選定位均通過（Run 41170538336）。
- 擴充總結／情緒／今日觀察定位後，Run 41170577276 如實失敗：平日 CNN 日期節點不存在；關鍵價位只有一個 `.key` 容器而非預設 3 個。已更正為平日 CNN 日期預期 0、關鍵價位容器預期 1，並將含有收合來源內容的關鍵價位／核心觀察容器標記為 `protected_container_only`，不得整段覆寫。
- 正式雙母版的 `<main id="overview">` 均由總結區開始，沒有獨立 KPI 區塊；KPI 插槽不建立、不新增版面。
- 目前已擴充至 31 個候選 selector；Run 41171589227 已通過雙母版所有 31 個定位稽核。

## Repeat-group 架構草案
- 早期 `repeat-group-policy-v1.md` 已由 `repeat-group-policy-v1.1.md` 取代。新版明確規定經濟／財報小卡筆數為內容動態群組；母版 12／16／3／7 張僅是樣本數，不是目標、上限、下限或驗收門檻。
- 已建立 `scripts/tac_repeat_group_validator.py`、合成測試及真實雙母版整合測試。驗證器保護所有非 repeat DOM 屬性（卡片內僅允許 href 更新）、卡片完整骨架、CSS／JS、外層 wrapper 及重複 ID 數量；新增／移除只改變登記列表內的卡片數量。
- 新增 `scripts/tac_status_group_validator.py` 與 `scripts/test_tac_status_group_validator.py`，驗證 status-group 固定外框下的列表／empty-state 變體切換。只允許沿用同模板、同區塊實際存在的 `.calendar-status-empty` 節點原型；單有 CSS class 定義不算。
- 最新 CI Run **41171589227** 成功：22 項單元／整合測試通過，涵蓋兩份真實母版的合法新增與移除模擬、卡片 class／style／固定連結變更拒絕、卡片 href 允許更新、重複 ID 保護、空列表拒絕、SHA 鎖定、HTML5 結構解析與 31 個 selector 稽核。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41171589227
- 已新增 Playwright／Chromium 真實瀏覽器測試。Run **41172036125** 通過 22 項結構／repeat-group 測試及 3 項瀏覽器測試：週一／平日經濟與財報 tabs 切換、卡片 details 開合、320px 手機寬度列表不溢出。瀏覽器測試會先關閉母版原有的 Q4 基金提醒對話框，再操作行事曆；未修改母版內容。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41172036125
- Empty-state 驗證界線：週一母版本週經濟與財報區塊已通過列表↔既有 empty-state 雙向切換；平日母版本週區塊及週一上週區塊沒有實際 empty-state 節點原型，測試確認會拒絕轉換。不得跨模板搬用空狀態節點。
- 修正後 selector CI（Run 41170745808）已通過：母版 SHA 鎖定、8 項結構指紋測試、雙母版 HTML5 解析與候選 selector 命中數檢查均成功。此 run 驗證的是修正後 registry；新增 repeat-group 草案本身尚未進入該 run。

## 2026-10-31 動態行事曆數量修正與 Repeat Group 驗證進度（以本節為準）

- 使用者已明確確認：**經濟行事曆與財報行事曆的小卡數量不固定，依每週／每日實際事件動態調整。** 母版目前的 12／16／3／7 張僅為樣本命中數，不是目標數、上下限或驗收門檻。
- 固定的是各模板的外層容器、status group、標題、欄位、卡片骨架、details/summary、紅圓加號、來源收合、CSS／JS 與互動；動態的是每個列表內的事件卡張數。
- 新版測試草案：`repeat-group-policy-v1.1.md`。舊版 `repeat-group-policy-v1.md` 已標記為被取代，避免誤讀。
- 新增 `scripts/tac_repeat_group_validator.py`、合成測試及真實雙母版整合測試。驗證器允許登記的動態子項增減，逐張核對卡片完整骨架，並保護列表外框及文件其他固定結構。
- 新增 `scripts/test_tac_template_browser.py`，使用 Playwright／Chromium 驗證 tabs、卡片開合與 320px 行動版列表幾何。
- Repeat Group 測試涵蓋：合法新增、合法移除、零卡片列表拒絕、卡片 class／style 非法變更、固定連結變更、卡片來源 href 更新、重複 ID、wrapper 變更、固定同層控制變更、wrapper 數量變更及非動態群組筆數變更。Status-group 測試另涵蓋雙向空狀態切換、無原型拒絕、標題 class 保護及固定 DOM 保護。
- 最新 CI Run **41172663405** 已完成成功：31 項結構／repeat-group／status-group 單元與整合測試、3 項 Chromium 瀏覽器測試、雙母版 SHA 鎖定、HTML5 結構解析、31 個候選 selector 命中數稽核及報告上傳全部通過。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41172663405
- 已新增對兩份唯讀正式母版的真實 DOM 複製測試，模擬每個列表新增同骨架卡片及移除部分卡片，均通過。Playwright 瀏覽器互動、320px 手機列表幾何及週一本週區塊 empty-state 雙向切換也已通過 CI；紅圓加號視覺／點擊、日期排序資料層與 11/02 預覽非破壞性測試仍待完成。開發母版尚未產生，故不得啟用每日自動增刪或部署。
- 以上全部僅在 `tac-template-architecture` 測試分支。正式 WR、兩份正式母版、manifest、首頁及 11/02 預覽均保持不變。


## 2026-10-31 Gate A 雙母版插槽盤點更新（本節優先）

- 新增整合文件：[`slot-map-v1.4.md`](slot-map-v1.4.md)。此版統整 `slot-map-v1.2.md`、`summary-sentiment-map-v1.md`、`weekly-commodities-fomc-map-v1.md`、selector registry 與 Repeat Group 規則，作為目前雙母版欄位盤點入口。
- v1.3 已確認週一／平日正式母版檔案及 SHA，並明確標記所有欄位仍屬候選定位，未授權每日寫入。
- v1.3 補齊了先前進度文字尚未整合的專項定位：能源 WTI／Brent、貴金屬 Gold／Silver、FOMC 會議欄位，以及週一上週經濟／財報欄位。這些仍需加入 selector registry 並完成逐欄位正反向測試，不能誤報為已通過 CI。
- 總結正文、核心情緒解讀、今日觀察三個 panel 均採「容器保護」；不得以整段 textContent／innerHTML 覆寫。KPI 不存在獨立版面，不建立 KPI 插槽。
- 舊進度段落中「KPI、週一上週區塊、商品、FOMC 尚未定位」是 v1.3 前的盤點狀態；自本節起以 v1.3 的細項狀態為準。定位完成不等於寫入驗收完成。
- 最新 WR 文件：`TAC_TEMPLATE_ARCHITECTURE_WR_v1.0.md`，狀態仍為 DRAFT。WR 測試 Run 41174832080 成功，但僅驗證工作流程，不代表 Gate A 完成。
- 本次盤點文件 commit：`8935c428f6c6754d17debd17b1f5c6252e3a1fd9`。仍不得建立或啟用每日自動寫入，直到 Gate A 欄位級驗證、Gate B 開發母版、瀏覽器驗收與使用者核准完成。

## 2026-10-31 Run #73｜紅圓加號逐卡測試與週一母版缺口揭露（最新）

- 測試程式修正 commit：`3f380f3df64539bfac0128db905d2da144d37168`；僅修改 `dev-templates/scripts/test_tac_template_browser.py`。
- GitHub Actions Run **#73（41176059854）成功**：31 項結構／Repeat Group／Status Group 單元與整合測試通過；5 項 Chromium 瀏覽器測試通過；雙母版 SHA 鎖定、HTML5 結構指紋解析、現有 31 個候選 Selector cardinality 稽核及報告上傳全部成功。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176059854
- 本次逐卡測試依實際 DOM 區分三種控制：
  - 週二至週五「本週經濟」：`.econ-toggle`，16 個事件卡。
  - 週一「上週經濟」：`.econ-event-toggle`，3 個事件卡。
  - 週一／平日財報卡：`.earnings-accordion-toggle`，依母版實際卡片逐張測試。
- **已確認的正式母版缺口（未修母版）：週一「本週經濟」卡片目前 12 張皆沒有加號控制節點。** 其 `details.econ-event > summary` 內沒有 `.econ-toggle`；CSS 雖有相關樣式，HTML 並未提供控制節點。測試已新增明確診斷項，確認這個缺口仍存在；不得把它誤報為 32px 控制已驗收。
- 週一「上週經濟」的 `.econ-event-toggle` 與週一／平日財報卡的 `.earnings-accordion-toggle` 已逐張驗證 32×32px、圓形、TAC 紅色、展開減號／深色狀態及收合；週二至週五本週經濟卡亦逐張完成相同控制檢查。
- 本次沒有修改正式雙母版、正式首頁、manifest 或根目錄 WR v3.4。若要補上週一「本週經濟」的控制節點，必須另行取得正式母版修改授權；在此之前，該項仍是 Gate D 的未結缺口。
- Run #73 成功只代表目前測試套件及既有 selector registry 通過；**不代表 Gate A 已完成、所有欄位已獲寫入授權、實際部署視覺驗收完成或可正式採用**。

## 2026-10-31 Run #74｜商品／FOMC／週一上週卡欄位級 Selector 盤點

- Selector Registry 擴充 commit：`8f34f52776c5544c34a05148b34266745f69108e`；新增 30 個欄位／保護容器候選 selector，總數由 31 增至 **61**。
- 新增盤點範圍：
  - WTI／Brent：行情列、商品名稱、報價值、日期／口徑文字、觀察容器與來源收合容器。
  - Gold／Silver：行情列、商品名稱、報價值、日期／合約口徑文字、觀察容器與來源收合容器。
  - FOMC：會議日期、政策聲明／記者會時間、目標利率、利率快照日期、核心觀察及說明段落。
  - 週一上週經濟：日期、時間、國家、事件名稱、星級、欄位 label 與欄位值。
  - 週一上週財報：美股公布日期、台灣時間、公司名稱、產業副標、星級。
- GitHub Actions Run **#74（41176143602）成功**：31 項結構／Repeat Group／Status Group 測試、5 項 Chromium 瀏覽器測試、雙母版 SHA 鎖定、HTML5 指紋解析、**61 個 selector 的週一／平日命中數稽核**及報告上傳全部通過。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176143602
- 這次通過的是 selector 命中數與 cardinality，不等於所有欄位已獲每日寫入授權。商品觀察／來源容器仍標記為 protected；FOMC 說明段落也先列為保護範圍。欄位正向寫入與負向結構保護測試仍待建立。
- 週一上週財報目前只完成摘要欄位定位；EPS／營收實際值、預期值、優劣狀態、分析、股價表現及來源欄位仍需逐欄位盤點，不能因公司卡片摘要 selector 通過就視為財報卡完整定位。
- 本次仍只修改測試分支中的 registry；正式首頁、雙母版、manifest 與正式 WR v3.4 均未修改。



## Gate A 盤點文件入口更新

- 目前最新雙母版插槽盤點入口為 [`slot-map-v1.4.md`](slot-map-v1.4.md)，承接 v1.3 並記錄 Run #74 的 61 個候選 selector cardinality 結果。
- v1.3 保留作為前一版盤點紀錄；不得再將其中「商品／FOMC／週一上週卡尚未納入 registry」的舊狀態當作目前進度。

## 2026-10-31 Run #84｜葉節點寫入防護正反向測試通過

- 新增測試防護模組：`scripts/tac_field_write_guard.py`；僅供測試驗證，不是每日生產更新器。
- 新增 `scripts/test_tac_field_write_guard.py`，並納入 CI。Run **#84（41176330236）成功**：
  - 38 項結構／Repeat Group／Status Group／欄位寫入防護單元與整合測試通過。
  - 5 項 Chromium 瀏覽器測試通過。
  - 雙母版 SHA 鎖定、HTML5 結構指紋及 61 個候選 selector cardinality 稽核通過。
  - 欄位防護測試涵蓋：已登記葉節點正向更新、週一經濟日期葉節點更新、商品觀察容器拒絕、固定欄位 label 拒絕、toggle／未知 selector 拒絕，以及即使 selector 被登記但目標含子元素仍拒絕更新。
- Registry 已將能源／貴金屬商品名稱精確收斂至連結葉節點；週一上週經濟的混合內容值容器改列 protected，避免寫入時覆蓋來源連結。
- Run 連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176330236
- 最新盤點文件：[`slot-map-v1.4.md`](slot-map-v1.4.md)。Gate A 仍未完成：週一上週財報 EPS／營收實際與預期、優劣狀態、分析、股價表現及來源欄位尚未完整定位；總結／情緒／今日觀察的複合文字也尚未拆成安全葉節點。
- 本次所有程式、registry、WR 草案與盤點文件都只在 `tac-template-architecture` 測試分支；正式首頁、雙母版、manifest、根目錄 WR v3.4 均未修改。未取得正式採用核准，不啟用每日寫入或部署。

## 2026-10-31 Run #88｜日期排序規則測試通過

- 新增 `scripts/tac_calendar_sort.py` 與 `scripts/test_tac_calendar_sort.py`，建立經濟事件與財報事件的正規化排序資料層。
- 經濟事件依 ISO 日期及報告時區時間排序；未知時間排在同日已知時間之後。財報事件依美國公告日期、盤前／盤中／盤後時段及可確認時間排序；台灣顯示日期不取代美國公告日期。
- Run **#88（41176456247）成功**：43 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA 鎖定、HTML5 DOM 指紋、61 個 selector cardinality 稽核與報告上傳全部通過。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176456247
- 此排序層尚未接入每日資料整理／更新器，亦未用實際行事曆資料完成端到端排序驗收；目前只代表排序規則與邊界測試通過。

## 2026-10-31 Run #93｜週一上週財報結果欄位定位

- Selector Registry 擴充至 **68 項**，新增 7 個週一上週財報結果 selector。
- 已定位可安全更新的 leaf：EPS／營收實際與預期值 28 個、優劣狀態 14 個、補充註記 14 個。卡片標題與欄位 label 固定不得寫入；21 個分析值容器含複合文字／連結風險，先列 protected。
- Run **#93（41176580490）成功**：44 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、HTML5 DOM 指紋及 68 個 selector cardinality 稽核全部通過。連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176580490
- 仍待定位：週一上週財報的股價當日表現與來源連結安全葉節點，以及分析文字的細部拆分；Gate A 尚未完成。

## 2026-10-31 Run #99–#100｜來源連結安全更新測試

- Selector Registry 擴充至 **72 項**。週一上週財報的來源容器仍列為 protected；另獨立定位 13 個來源 anchor leaf（平日母版 0 個，符合模板差異）。
- 新增 `update_registered_source_links()`：僅能逐一更新已登記 anchor 的 `href` 與 label；URL 僅允許絕對 HTTP(S)，拒絕 javascript:、無 host、帳密 URL、控制字元；更新數量必須與 anchor 命中數完全一致。既有 `target`、`rel` 屬性保留。
- Run **#99（41176987923）** 與 **#100（41176996598）** 均成功。兩次各通過 46 項單元／整合測試、5 項 Chromium 瀏覽器測試及 72 項 selector cardinality；雙母版 SHA 與 DOM 指紋檢查通過。
- 這是測試分支的安全更新函式，尚未接入每日資料流程或 Repeat Group updater，不代表正式早報已啟用自動來源更新。
- Run #99：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176987923
- Run #100：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41176996598

## 2026-10-31 Run #101｜來源連結正反向測試完成

- Run **#101（41177005842）成功**：48 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、DOM 指紋、72 項 selector cardinality 全部通過。
- 新增測試驗證來源連結更新器可逐一更新 13 個 anchor 的 href／label，同時保留 target／rel；拒絕 javascript: URL、錯誤 selector 與更新筆數不符。
- Run #101 是來源連結功能的完整測試閉環；Run #99/#100 為 selector 與函式本體的前置驗證。
- 來源連結更新器仍未接入正式資料匯入與 repeat-group updater。
- 連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177005842

## 2026-10-31 Run #112｜市場情緒與總結欄位測試通過

- Selector Registry 擴充至 **77 項**。新增 VIX／MOVE 漲跌幅、CNN 英文／中文狀態及市場情緒核心解讀 5 個可更新 leaf。
- VIX 漲跌幅 selector 改以 strong 後方相鄰 span 定位，避免依賴 `.warn`／`.down` 顏色 class；週一與平日母版皆命中 1 個節點。
- 總結標題 leaf 可更新；總結正文因含粗體標籤、換行及複合文字，改列 protected。今日市場觀點、CNN 狀態父容器及 marker style 亦維持 protected。
- Run **#112（41177327390）成功**：51 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、DOM 指紋與 77 項 selector cardinality 全部通過。
- Run 連結：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41177327390
- Gate A 尚未完成，尚未啟用每日資料更新或正式寫入。

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



## 2026-10-31 Run #41180947602｜行事曆標準資料契約層與 CI 驗收

- 新增 `scripts/tac_calendar_dataset.py`：建立經濟／財報行事曆共用的資料集入口契約，先驗證再排序；不抓取資料、不推測缺值、不修改 HTML，也不代表已授權每日寫入。
- 經濟事件必須具備唯一 event_id、ISO 事件日期、事件時區、國家、事件名稱、1–5 星重要性及至少一筆來源紀錄；財報事件另保留美國公告日期、台灣顯示日期、公司名稱、副標題及公告時段。美國公告日期是排序依據，台灣顯示日期僅供顯示，不可混用。
- 每筆來源紀錄必須具備來源名稱、顯示標籤、絕對 HTTP(S) URL、含時區 offset 的查證時間；不安全網址、無時區查證時間、重複事件 ID、錯誤日期／時間及欄位型別錯誤均拒絕。
- 經濟事件依事件當地日期／時間排序；財報依美國公告日期、盤前／盤中／盤後時段及可用時間排序。未知時間排在同日已知時間後；原始輸入不被改寫。
- 新增 `scripts/test_tac_calendar_dataset.py`，15 項測試全數通過。第一次 CI 提交雖通過既有測試，但日誌檢查發現新測試未列入明確測試清單；已修正 workflow，將資料集測試正式加入每次 CI。
- 最終 Run #41180947602 完整成功：**78 項單元／整合測試、5 項 Chromium 瀏覽器測試**；正式雙母版 SHA、DOM 結構指紋、94 個候選 selector cardinality 及稽核報告上傳均通過。
- 重要界線：本次只完成資料契約與排序入口，尚未接入真實資料蒐集、來源 Mapping、Repeat Group 卡片新增／移除、DOM 寫入或每日產製。Gate A 仍未完成，Gate B–D 未完成，Gate E 未核准。
- 最終驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41180947602


## 2026-10-31 Run #41181717574｜狀態群組原型盤點與 Repeat Group dry-run planner

- 新增 `scripts/tac_calendar_group_inventory.py`，對兩份正式鎖定母版只讀盤點本週／上週經濟及財報 status group，記錄可見 heading、語意狀態、既有列表／empty-state、卡片張數及同群組原型是否存在。CI 另輸出 `calendar-group-inventory.json` 稽核報告。
- 狀態分類不能只依 CSS class：週一母版「今日公布」標題的 CSS class 可能仍是 `upcoming`。盤點器改以 heading 可見文字辨識 today／upcoming／published／prior_week_published，CSS class 僅作結構資訊保留。
- 正式母版樣本盤點結果（張數僅為當前樣本，不是動態筆數限制）：
  - 週一本週經濟：今日公布 0 張、即將公布 12 張、已公布 0 張；只有即將公布群組有同群組卡片原型。
  - 週一本週財報：今日公布 0 張、即將公布 16 張、已公布 0 張；只有即將公布群組有同群組卡片原型。
  - 週一上週經濟／財報：各有 3／7 張，兩組均有同群組原型。
  - 週二至週五本週經濟：今日／即將／已公布為 2／8／6 張；財報為 4／7／5 張，六個狀態群組均有同群組原型。
- 週一本週經濟／財報的今日與已公布群組雖有同區塊 empty-state 原型，但沒有卡片原型；目前 repeat-group policy 不允許跨狀態群組借用卡片。因此若當週資料要求在這些群組新增卡片，planner 必須阻擋。週一上週群組有卡片原型但沒有同區塊 empty-state；若事件集為零，也必須阻擋自動清空。平日各群組沒有同區塊 empty-state；若某狀態群組事件為零，同樣不得自行拼裝空狀態。
- 新增 `scripts/tac_calendar_repeat_plan.py`：以標準資料集與母版 inventory 產生 dry-run 計畫；逐群組判斷 render_list、keep_empty_state、switch_to_existing_empty_state、not_applicable 或 blocked。它不修改 HTML，遇到原型缺失、狀態群組缺漏或模板不符即明確阻擋。
- 行事曆資料契約補充 `status_group`，並將週一專屬的 `prior_week_economic_events`／`prior_week_earnings_events` 與本週資料分開；平日資料集不得含上週事件。週一上週事件使用 `prior_week_published` 狀態。
- 新增 8 項 repeat-plan 測試，覆蓋週一今日／已公布新增阻擋、上週原型可用、無 empty-state 不可清空、平日三群組更新及模板不匹配。
- Run #41181717574 完整成功：**100 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 selector cardinality、calendar group inventory 報告及測試報告上傳成功。
- 本階段仍未建立真正的卡片複製／新增／刪除與欄位填入器，也未接入實際資料匯入；planner 僅為寫入前安全閘門。Gate A 尚未完成，Gate B–D 未完成，Gate E 未核准。
- 驗收紀錄：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41181717574


## 2026-10-31 Run #41181918499｜行事曆資料契約型別與時區強化

- 行事曆事件的 `event_timezone` 不再只檢查非空字串，改以 Python `zoneinfo` 驗證有效 IANA 時區；錯誤時區名稱直接拒絕。
- `status_group`、`release_session`、`template` 均增加字串型別檢查，避免 list／dict 等錯誤型別造成未預期例外或被誤認為合法值。
- 新增 3 項負向測試：無效 IANA 時區、非字串狀態群組、非字串財報公告時段。
- Run #41181918499 完整成功：**103 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 selector cardinality、calendar group inventory 及稽核報告上傳均通過。
- 目前資料契約仍屬測試用標準化入口；未連接資料抓取、正式來源 mapping、Repeat Group DOM 寫入或每日生產。
- 驗收紀錄：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41181918499


## 2026-10-31 Run #41182239153｜行事曆欄位 Mapping 與台灣時間換算

- 新增 `scripts/tac_calendar_field_mapper.py`，把已通過資料契約的事件轉成明確的 per-card payload：摘要欄位、detail label/value、來源欄位 anchor 清單及獨立 provenance；不查資料、不修改 DOM。
- 來源紀錄新增必填 `field_label`，用來對應母版中的固定來源欄位 label（例如「資料來源」或「來源」）；`label` 是 anchor 顯示文字，`url` 是來源 href，`accessed_at` 保留查證時間。來源資料不能只靠網址猜測要寫入哪個欄位。
- 經濟事件的 event_date／event_time 定義為已換算後的台灣顯示日期／時間，event_timezone 必須是 `Asia/Taipei`；未知時間只映射成「待核實」，不推測。
- 財報事件保留美國公告日期／當地時間／IANA 時區，使用 ZoneInfo 換算台灣時間；若有精確公告時間，換算後日期必須與明確提供的 taiwan_display_date 一致，否則拒絕。沒有精確時間時只顯示已核實的台灣日期，不自行補時刻。
- mapper 統一產生中文星期、月／日、五星字元及盤前／盤中／盤後標示；detail 欄位與來源欄位保持獨立，不會把來源 anchor 當成一般文字。
- 新增 8 項 mapper 測試，覆蓋日期／星級格式、經濟摘要、未知時間、財報跨日換算、來源欄位 mapping、資料集分群及輸入不變性。
- Run #41182239153 完整成功：**115 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 selector cardinality、calendar group inventory 及稽核報告上傳均成功。
- 現在已具備「資料契約驗證 → 排序 → 狀態群組規劃 → per-card payload mapping」測試層；尚未執行 Repeat Group DOM 複製／增刪／寫入，也未接入實際資料來源蒐集。Gate A 尚未完成，Gate B–D 未完成，Gate E 未核准。
- 驗收紀錄：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41182239153


## 2026-10-31 Run #41182431871｜行事曆資料準備流程閉環（尚未寫入 DOM）

- 新增 `scripts/tac_calendar_prepare.py`，把既有資料契約驗證、日期／時區排序、模板 status-group 原型 dry-run 與 per-card payload mapper 串成單一準備流程。
- 執行順序：驗證資料集 → 依狀態分組排序 → 對照指定週一／平日正式母版 inventory → 檢查各群組是否具備合法卡片／empty-state 原型 → 產生摘要／detail／來源 anchor payload。
- 只要任一狀態群組為 blocked，流程會回傳 `ready=false`、`stage=blocked_before_dom_write`，並將全部 `payloads` 設為 null；不允許只寫入部分群組或忽略阻擋項目。
- 全部通過時才回傳 `ready=true` 與 `validated_payload_ready`；此狀態只代表資料 payload 可供後續 DOM updater 使用，並不代表已修改 HTML。
- 新增 5 項 preparation 整合測試：週一合法群組、週一缺少卡片原型時整批阻擋、平日三狀態群組完整準備、平日缺少 empty-state 時整批阻擋、輸入資料不變。
- Run #41182431871 完整成功：**120 項單元／整合測試、5 項 Chromium 瀏覽器測試**通過；雙母版 SHA、DOM 結構指紋、94 selector cardinality、calendar inventory 及稽核報告上傳均通過。
- 目前已完成「資料契約 → 排序 → 狀態群組安全規劃 → per-card Mapping → 寫入前整批準備閘門」。尚未實作 DOM Repeat Group 新增／刪除／替換、欄位實際寫入或瀏覽器端到端資料更新。Gate A 尚未完成，Gate B–D 未完成，Gate E 未核准。
- 驗收紀錄：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41182431871
