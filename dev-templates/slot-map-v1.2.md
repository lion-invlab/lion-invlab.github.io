# 動態資料節點精確定位 v1.2

本版根據正式雙母版原始碼盤點，將外層容器細化至可限定範圍的資料元素。此為候選 allowlist，正式啟用前仍須以 DOM parser 與瀏覽器測試驗證唯一性、元素數量及父子關係。

## 寫入原則
- 所有 selector 必須以容器 ID 限定；禁止全頁操作 .row、.r、.newsitem 等泛用 class。
- radio、label、tab nav、tab panel 外框、article/card 外框、details/summary、紅圓加號、欄位標籤、CSS、JS 均為固定結構。
- 未列入本文件的節點一律不得由每日更新器寫入。
- 行情與事件資料完成核實後，才更新觀察、評論、摘要；來源連結與資料須一對一。

## A. 新聞
- 全球焦點：容器 #tac-news-panel-0 #global-focus；每則 #global-focus .newsitem。
- 熱門頭條：容器 #tac-news-panel-1 #headlines；每則 #headlines .newsitem。
- 每則可更新 h3（標題序號）、p（摘要）、.newsmeta a（來源顯示文字及 href）。
- 容器層級 .tab-panel-meta 與時間窗提示另行更新，不得混入單則新聞。

## B. 全球主要市場
- 美國、亞洲、歐洲面板依序為 #tac-global-panel-0、#tac-global-panel-1、#tac-global-panel-2。
- 行情列限定在各面板第一個 article.card 內的 .row；欄位為 .row b a、.row > span.r 及其 up/down/flat 狀態。
- 日期口徑為面板內 .tab-panel-meta；觀察為 .market-reason；來源為 .source-details 內連結與文字。
- 禁止全頁 .row 或 .r 寫入，因其跨元件重複。

## C. 產業、債券、匯率、商品
- 外框 #industry-bonds-fx-commodities 固定，tab radio、nav 與 panel 外框固定。
- 11 大產業 ETF：面板 #tac-assets-panel-0、卡片 #us、資料列 #us .sector-list > .sector-row；可更新 .rank、.sector-label 內名稱/連結、列內 .r 與 up/down/flat 狀態。固定 11 列、依漲跌幅排序，只顯示 ETF 漲跌幅。sector-collapse、summary、audit-content 固定。
- 美債：卡片 #bonds（#tac-assets-panel-1）；行情列 #bonds > .row，固定 2Y/10Y/30Y 三列；日期口徑 .tab-panel-meta，觀察 .market-reason，來源 .source-details。
- 外匯：卡片 #fx（#tac-assets-panel-2）；行情列 #fx > .row，固定 DXY、USD/TWD、EUR/USD、GBP/USD、AUD/USD、USD/JPY 六列；日期口徑 .tab-panel-meta，觀察 .market-reason，來源 .source-details。
- 商品：面板 #tac-assets-panel-3，卡片 .energy-card。WTI、Brent、Gold、Silver 的精確行情列尚未定位，暫不納入自動寫入 allowlist。

## D. 經濟行事曆
- 容器 #calendar；每張事件卡 #calendar .econ-event。
- 摘要欄位 .econ-date、.econ-time、.econ-country、.econ-name、.econ-stars。
- 展開欄位 .econ-details .econ-field；label 固定，.econ-value 可更新。
- tabs、radio、label、紅圓加號/收合控制、details/summary、卡片骨架固定。
- 週一另有 #last-week-calendar，需再做專屬內層盤點。

## E. 財報行事曆
- 容器 #earnings；每張卡 #earnings .earnings-accordion。
- 摘要欄位 .earnings-us-date、.earnings-tw-date、.earnings-company-name、.earnings-company-sub、.earnings-stars。
- 展開欄位 .earnings-accordion-details .earnings-detail-field；label 固定，.earnings-detail-value 可更新。
- tabs、radio、label、details/summary、展開按鈕與欄位骨架固定。
- 週一另有 #last-week-earnings，需再做專屬內層盤點。

## F. Fed
- 容器 #fed；FedWatch 區 #fed .fed-live-watch；FOMC 區 #fed .fed-live-fomc。
- FedWatch 可更新 .fc-prob 內機率與利率區間、.fc-split-head 快照時間、.fc-split-bar 比例與 aria-label、圖例數值、資料時間說明及來源文字。
- FOMC 內層節點尚未完成定位，不加入完整 allowlist。tabs、比例條外框、details/summary 與來源區固定。

## 尚未完成精確定位（禁止自動寫入）
- 頁首 KPI、總結、盤面觀察重點、市場情緒的獨立資料節點。
- 商品卡四個行情列。
- 週一上週經濟與財報區塊的完整欄位。
- Fed FOMC 會議區。
- SOX、VIX、MOVE、CNN Fear & Greed 等分散卡片的精確節點。

## 既存結構差異與風險
- 週一版有 #last-week-calendar、#last-week-earnings；週二至週五版沒有。
- 週一版既存重複 ID：tac-toolbar-bubble-preview-v1、tac-toolbar-bubble-preview-v1-js；週二至週五版既存重複 ID：tac-toolbar-bubble-preview-v1-js。未經核准不得修正。
- tac-news-0/1、tac-global-0/1/2 是 radio input，只供互動控制，不是資料插槽。
- 此版仍是候選 allowlist；未完成 DOM parser 與瀏覽器驗收前，不得啟用每日自動寫入。