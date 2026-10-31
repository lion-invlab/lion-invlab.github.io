# TAC 動靜分離｜雙母版動態插槽盤點 v1.4

狀態：Gate A 工作底稿（61 個候選 selector 已完成雙模板 cardinality 稽核；葉節點正反向寫入測試未完成；未授權每日自動寫入）
分支：`tac-template-architecture`
依據：正式雙母版 manifest／SHA、`slot-map-v1.2.md`、`selector-registry-v1.json`、`summary-sentiment-map-v1.md`、`weekly-commodities-fomc-map-v1.md`、`repeat-group-policy-v1.1.md`。

## 0. 本版目的與規格優先序

本文件將既有分散盤點合併成一份雙母版欄位清冊，處理舊文件間「已定位／未定位」狀態不一致的問題。它只定義候選節點、模板差異及下一輪驗證工作，不會自行授予寫入權。

規格優先序：
1. 正式母版 manifest 與實際 HTML DOM（唯讀基準）。
2. 本文件 v1.3 的雙母版盤點狀態。
3. 各專項 map／selector registry／repeat-group policy（作為證據與測試資料）。
4. 舊版 README 的進度敘述；若與本文件不一致，須回頭更新 README，不得沿用過期狀態。

任何正式母版 SHA、manifest 或 DOM 指紋不符，立即停止。

## 1. 正式母版基準（唯讀）

| 模板 | 正式檔案 | Blob SHA |
|---|---|---|
| 週一 | `母版專區/TAC_母版_週一_2026-10-28_最終定版.html` | `776f778b895c6da781348bcf8fefc1d4719ed4ce` |
| 週二至週五 | `母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html` | `ab3286750a64aa0fc9fc01af51f819024526a4ba` |

上述檔案只供讀取與比對。本分支不得修改正式母版、manifest、首頁 `index.html`、根目錄 `TAC_WORK_RULES.md` v3.4，亦不得覆寫既有 11/02 預覽。

## 2. 欄位狀態定義

- **已定位（候選）**：DOM 中找到具體容器與子節點，且既有 selector cardinality audit 有相應記錄；仍不代表已授權寫入。
- **專項定位（候選）**：專項 map 已指出具體子節點，但尚須補 selector registry／逐欄位 DOM 驗證。
- **容器保護**：只用於限定範圍與比對，不得整段覆寫其文字或 innerHTML。
- **未定位／禁止**：不得建立 selector、不得寫入；先完成結構盤點。
- **固定結構**：不得由每日資料更新器更動，包括 wrapper、卡片骨架、tab/radio/label、details/summary、按鈕、欄位標籤、CSS、JS、aria／互動骨架等。

## 3. 雙模板共用欄位清冊

| 區塊 | 容器／候選定位 | 資料節點候選 | 筆數規則 | 目前狀態 |
|---|---|---|---|---|
| 全球焦點新聞 | `#global-focus` | `#global-focus .newsitem`；卡內 `h3`、`p`、`.newsmeta a` | 固定 5 則 | 已定位（候選）；卡片骨架固定 |
| 市場熱門頭條 | `#headlines` | `#headlines .newsitem`；卡內 `h3`、`p`、`.newsmeta a` | 固定 10 則 | 已定位（候選）；卡片骨架固定 |
| 全球主要市場－美國 | `#tac-global-panel-0` | 面板內第一個 `article.card .row`；名稱連結、行情值、漲跌狀態；`.tab-panel-meta`、`.market-reason`、`.source-details` | 5 列 | 已定位（候選） |
| 全球主要市場－亞洲 | `#tac-global-panel-1` | 同上，僅限本面板 | 6 列 | 已定位（候選） |
| 全球主要市場－歐洲 | `#tac-global-panel-2` | 同上，僅限本面板 | 3 列 | 已定位（候選） |
| 11 大產業 ETF | `#tac-assets-panel-0 #us` | `.sector-list > .sector-row`；`.rank`、`.sector-label`、`.r` 及漲跌 class | 固定 11 列；依漲跌幅排序 | 已定位（候選）；僅 ETF 漲跌幅，不得增加其他欄位 |
| 美債殖利率 | `#bonds` | `#bonds > .row`；2Y／10Y／30Y 行情值與漲跌狀態 | 固定 3 列 | 已定位（候選） |
| 外匯 | `#fx` | `#fx > .row`；DXY、USD/TWD、EUR/USD、GBP/USD、AUD/USD、USD/JPY | 固定 6 列 | 已定位（候選） |
| 本週經濟行事曆 | `#calendar` | `#calendar .econ-event`；摘要欄位及 `.econ-details .econ-field .econ-value` | 動態；依實際事件 | 已定位（候選）；Repeat Group |
| 本週財報行事曆 | `#earnings` | `#earnings .earnings-accordion`；摘要欄位及 `.earnings-detail-field .earnings-detail-value` | 動態；依實際事件 | 已定位（候選）；Repeat Group |
| FedWatch | `#fed .fed-live-watch` | `.fc-prob`、`.fc-split-head`、`.fc-split-bar`、圖例數值及 aria-label | 目前 2 個機率情境卡；依實際資料結構核對 | 已定位（候選）；比例外框固定 |
| 市場情緒 VIX／MOVE | `#sentiment` | 第 1、2 個 `.sbox` 的 `strong`、緊鄰漲跌 span、各自 `.source-details .source` | 固定 4 個 sbox 中的前 2 個 | 專項定位（候選）；只改葉節點 |
| CNN Fear & Greed | `#sentiment .cnn-fg-preview` | `.fg6-score-main`、`.fg6-status`、`.fg6-marker` 的 left／aria-label、來源文字；週一另有 `.fg6-date` | 固定 1 區 | 專項定位（候選）；日期為模板差異 |
| 市場情緒核心解讀 | `#sentiment .sent > .sbox:last-child` | 卡內解讀文字節點 | 固定 1 卡 | 容器保護；須先拆出不破壞 label／骨架的原子文字節點 |
| 總結 | `section.grid.two article.card.bluf` | `h1` 與 `p` 命中各 1 | 固定 1 卡 | 容器已定位；正文含多個語意段與標籤，整個 `p` 不得直接替換 |
| 今日觀察－市場觀點 | `#view .focus-panel.focus-market` | `.key` 內各段落／文字 | 固定 1 panel | 容器保護；須逐段／逐文字節點定位 |
| 今日觀察－關鍵價位 | `#view .focus-panel.focus-levels` | `.key` 內指數段落；來源收合區獨立保留 | 固定 1 panel | 容器保護；不得覆寫整個 `.key` |
| 今日觀察－核心觀察 | `#view .focus-panel.focus-core` | `.callout` 內評論文字 | 固定 1 panel | 容器保護；週一含 compact-disclosure，須逐節點處理 |

注意：候選 selector 的命中數是母版結構定位測試，不是每日內容筆數目標。全球行情列與產業／債匯欄位的具體子節點仍須由資料更新器以精確子 selector 寫入，禁止全頁泛用 class 查找。

## 4. 商品與 FOMC 專項欄位

| 區塊 | 模板 | 容器／候選定位 | 資料節點候選 | 狀態 |
|---|---|---|---|---|
| WTI／Brent | 雙模板 | `#tac-assets-panel-3 .energy-card` | `.energy-card > .row` 兩列；`.tab-panel-meta`、`.market-reason`、`.source-details` | 欄位 selector 已納入 registry，Run #74 雙模板 cardinality 通過；正反向寫入安全測試待完成 |
| Gold／Silver | 雙模板 | `#tac-assets-panel-4 article.card` | `article.card > .row` 兩列；日期／合約口徑、觀察、來源 | 欄位 selector 已納入 registry，Run #74 雙模板 cardinality 通過；正反向寫入安全測試待完成 |
| FOMC 會議 | 雙模板 | `#fed .fed-live-fomc .fc-fomc` | `.fc-fomc-meeting b`、`.fc-fomc-press b`、`.fc-fomc-rate b`／`small`、`.fc-fomc-observation b`、說明段落 | 欄位 selector 已納入 registry，Run #74 雙模板 cardinality 通過；正反向寫入安全測試待完成 |

商品的能源與貴金屬是不同 tab panel，不可合併或跨面板寫入。日期／合約口徑與來源文字雖屬資料內容，仍須按各自行情資料來源逐筆對應。

## 5. 週一專屬欄位

| 區塊 | 容器／候選定位 | 資料節點候選 | 筆數規則 | 狀態 |
|---|---|---|---|---|
| 上週經濟行事曆 | `#last-week-calendar` → `.last-week-calendar-collapse` → `.calendar-status-group` → `.econ-event-list` | 每張 `.econ-event` 的 `.econ-date`、`.econ-time`、`.econ-country`、`.econ-name`、`.econ-stars`；展開欄位 `.econ-details .econ-field .econ-value` | 動態；依 WR 重要性五星事件 | 摘要欄位 selector 已納入 registry，Run #74 cardinality 通過；經濟欄位 leaf 正反向測試待完成 |
| 上週財報行事曆 | `#last-week-earnings` → `.last-week-earnings-collapse` → `.calendar-status-group` → `.earnings-accordion-list` | 每張 `.earnings-accordion` 的日期、公司、產業、星級；EPS／營收卡標題與實際／預期 label 固定；28 個實際／預期值 leaf、14 個優劣狀態 leaf、14 個補充註記 leaf；21 個分析值容器保護 | 動態；依 WR 篩選重要財報 | EPS／營收結果、財報判讀及股價表現 leaf selector 已納入 registry；來源容器保護，另以 13 個 anchor leaf selector 定位；Run #100 selector cardinality 通過，Run #101 寫入測試待結果 |

上週經濟／財報外層收合、status group、列表 wrapper、卡片骨架與欄位 label 固定。不得把目前樣本 3 張／7 張寫死。這兩個區塊只存在於週一模板，平日模板沒有它們是正常模板差異，不是缺漏。

## 6. 明確禁止建立或寫入的區域

1. **獨立 KPI 區**：雙母版的 `<main id="overview">` 均由總結區開始，沒有獨立 KPI grid／卡片。不得新增 KPI 區或自行建立 KPI 插槽。
2. **整段覆寫容器**：總結正文、核心情緒解讀、今日市場觀點、關鍵價位、核心觀察等複合內容，不能以整個父容器的 `textContent`／`innerHTML` 替換。
3. **跨模板借用**：週一上週行事曆節點不得複製到平日模板；週一 CNN 日期節點不得假設平日也存在。
4. **泛用 selector**：禁止全頁 `.row`、`.r`、`.value`、`.chg` 等查找；每個 selector 必須以唯一模板容器限定。
5. **未登記區塊**：SOX、VIX、MOVE 等分散行情卡的完整行情欄位尚未全部納入本版 allowlist；不得因已有來源連結或文字就推定可寫入。

## 7. Repeat Group 與 empty-state 界線

- 動態群組：本週經濟卡、本週財報卡、週一上週經濟卡、週一上週財報卡。張數依實際事件，不設樣本數上下限。
- 固定群組：全球焦點 5、熱門頭條 10、全球市場列、11 大產業 11、美債 3、外匯 6、情緒 4 個 sbox、今日觀察 3 個 panel 等。
- 週一／平日各自以自己的正式母版作骨架，不得跨模板複製卡片原型。
- 只有同一模板、同一區塊實際存在的 empty-state HTML 原型才可進行列表／empty-state 變體切換。現有測試僅確認週一本週經濟／財報區塊具備可用原型；平日本週及週一上週區塊無同區塊原型，必須拒絕自動轉換。
- 每次增刪均須記錄事件名稱、日期、來源、增刪理由與結果；不得靜默增刪。

## 8. Gate A 尚需完成的工作

- [ ] 為商品 WTI／Brent、Gold／Silver 與 FOMC 葉節點建立正向／負向寫入安全測試；觀察、來源與說明容器維持 protected。
- [ ] 補完週一上週財報股價表現與來源欄位定位，並將分析文字拆成安全葉節點；為週一上週經濟／財報完成逐欄位正反向測試。
- [ ] 將總結、情緒、今日觀察的複合欄位拆成可安全更新的葉節點；對含有來源收合、計算方式、標籤的容器明確設為 protected。
- [ ] 對所有「專項定位」欄位建立正向／反向測試：允許資料葉節點變更，拒絕父容器、label、class、style、aria、details/summary、CSS／JS 變更。
- [ ] 產出週一與平日兩份欄位層級驗證報告；兩版不得合併成單一假設。
- [ ] Gate A 通過後，才進入開發母版產生；開發母版仍只存在測試分支，不能自動成為正式生產母版。

## 9. 寫入權限聲明

本文件不是每日更新器的寫入授權清單。所有狀態目前均為候選定位。只有完成 selector registry、欄位級 diff、正反向測試、雙模板瀏覽器驗證，並經專案驗收與使用者明確核准後，才可將指定葉節點升級為可寫入欄位。根目錄 WR v3.4 仍是正式早報內容與資料品質規則的唯一權威。

## 10. 2026-10-31 Run #74 欄位 Selector cardinality 結果

- `selector-registry-v1.json` 由 31 項擴充至 61 項，新增 30 項 selector，包含能源、貴金屬、FOMC、週一上週經濟卡及週一上週財報摘要欄位。
- GitHub Actions Run #74（41176143602）已通過雙模板 selector cardinality 稽核；兩份母版均以實際 HTML5 DOM 命中數核對 registry 預期值。
- 本次結果只證明 selector 命中位置與數量符合盤點，不授予資料寫入權。商品觀察與來源容器、FOMC 說明段落仍屬 protected；欄位 label、固定結構、互動控制、ARIA、CSS／JS 不得寫入。
- 週一上週財報目前只定位日期／公司／產業／星級摘要；EPS、營收實際與預期、優劣狀態、財報判讀、股價表現及來源等欄位尚未完成欄位級盤點。
- Gate A 下一步：建立葉節點 allowlist 與正向／負向測試；正向只允許指定資料 leaf 更新，負向必須拒絕父容器、label、summary/details、toggle、來源收合、ARIA、class、style、CSS／JS 等結構變更。完成後再分別產出週一／平日驗證報告。

## 11. 2026-10-31 Run #88｜日期排序資料層（測試通過，尚未接入更新器）

- 新增 `scripts/tac_calendar_sort.py` 與 `scripts/test_tac_calendar_sort.py`，以正規化事件資料排序，不依賴卡片目前的 DOM 順序或顯示字串排序。
- 經濟事件資料欄位：`event_date`（ISO `YYYY-MM-DD`，採報告顯示時區日期）、`event_time`（同一時區的 `HH:MM[:SS]`，未知值為 null）。排序依日期、時間；未知時間排在同日已知時間之後；相同排序鍵保持來源順序。
- 財報事件資料欄位：`event_date`（美股公司公告的美國當地日期）、`release_session`（`pre_market`／`during_market`／`after_market`／`unspecified`）、`event_time`（可選美東當地時間）。台灣時間顯示欄位另行保留，不作為排序日期。排序依美國公布日期、時段、已知時間；未知時段／時間不臆測，排在同日可確認時段之後。
- Run #88（41176456247）通過 43 項單元／整合測試與 5 項瀏覽器測試，並通過 SHA、DOM 指紋與 61 個 selector 稽核。排序測試包含跨日／跨年、同日時間、盤前／盤後順序、未知時間穩定排序、輸入資料不變及錯誤日期／時間拒絕。
- **重要界線：** 排序函式目前只對正規化測試資料執行，尚未接入每日資料整理流程、repeat-group 更新器或正式母版 DOM；也尚未以實際行事曆資料完成端到端日期排序驗收。不得宣稱每日行事曆已自動排序完成。

## 12. 2026-10-31 Run #93｜週一上週財報結果欄位

- Registry 擴充至 **68 個候選 selector**，新增 7 個週一上週財報結果欄位 selector：EPS／營收卡片標題、實際／預期標籤、實際／預期數值、優劣狀態、補充註記、分析 label、分析值容器。
- 可更新 leaf：實際／預期數值 28 個、優劣狀態 14 個、補充註記 14 個；固定標籤 14+28+21 個不得更新；分析值容器 21 個因可能包含連結／複合內容，暫列 protected。
- Run #93（41176580490）通過 44 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、HTML5 DOM 指紋及 68 個 selector cardinality 稽核。
- 本次仍未定位財報卡「股價當日表現」的安全葉節點與來源連結欄位；分析值容器尚未拆解，不能整段覆寫。Gate A 未完成。



## 13. 2026-10-31 Run #100｜來源連結獨立葉節點與安全更新器

- Registry 擴充至 **72 個候選 selector**。週一上週財報來源欄位仍保留 7 個 protected container；另新增來源 anchor 葉節點 selector，雙母版實測命中：週一 13 個、週二至週五 0 個。
- 新增 `update_registered_source_links()`，只接受明確登記的 `source_link_leaf` selector，逐一更新 anchor 的 `href` 與文字 label；要求更新筆數與 DOM anchor 數一致、目標必須是無子節點的 anchor、URL 必須為絕對 HTTP(S) URL，拒絕 javascript:、缺少 host、帳密 URL 及控制字元。
- 更新時保留既有 `target`、`rel` 等 anchor 屬性；不替換來源容器、不建立或刪除 anchor、不變更 DOM 層級。
- Run #99（41176987923）通過 46 項單元／整合測試、5 項瀏覽器測試、雙母版 SHA、DOM 指紋及 72 項 selector cardinality。
- Run #100（41176996598）通過 46 項單元／整合測試、5 項瀏覽器測試及 72 項 selector cardinality；安全來源連結更新器已在測試分支完成正向／負向驗證。
- 本功能仍是測試用參考 guard，尚未接入每日資料匯入器或 Repeat Group 寫入流程。不能宣稱正式早報已可自動更新來源連結。


## 14. 2026-10-31 Run #112｜市場情緒與總結欄位安全定位

- Registry 擴充至 **77 個候選 selector**，新增 5 個市場情緒 leaf：VIX 漲跌幅、MOVE 漲跌幅、CNN 英文狀態、CNN 中文狀態、核心解讀文字。
- VIX 漲跌幅 selector 採 `strong + span` 結構定位，不依賴方向色 class；因週一 VIX 變動 class 為 `.warn`，平日樣板可能為 `.down`，更新文字不得改動方向 class。
- CNN 狀態父容器 `.fg6-status`、恐懼貪婪 marker（含 style 定位）、今日市場觀點複合容器、總結複合段落均列為 protected。只允許更新 CNN 英文／中文狀態 leaf；marker 的 style left 不允許寫入。
- 總結標題 `summary_title` 是純文字 leaf，可獨立更新；總結正文含粗體標籤、換行及多段文字，整個 `summary_body` 列為 protected，避免覆蓋固定格式。
- Run #112（41177327390）通過 **51 項單元／整合測試、5 項 Chromium 瀏覽器測試、雙母版 SHA、HTML5 DOM 指紋及 77 項 selector cardinality**。包含市場情緒 leaf 正向更新、複合容器拒絕更新、總結標題可寫／正文不可整段覆寫。
- 今日觀察重點三個 panel 仍維持 protected：市場觀點、關鍵價位、核心觀察都含多層標籤、details 或複合內容；在不調整母版結構的前提下，不能安全以單一 selector 覆寫。
- Gate A 尚未完成：仍須處理 11 大產業／市場行情各欄位、商品及 FOMC 的完整葉節點測試、週一上週經濟欄位正反向測試、兩版總結／觀察完整 mapping 報告。

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
