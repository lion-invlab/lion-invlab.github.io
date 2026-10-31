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

