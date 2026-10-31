# 週一專屬、商品與 FOMC 節點補充 v1

來源：週一正式母版 main，blob SHA 176eb7c686f9e0de9216eb57e144eeebaaf75f9b。

## 商品
- 原油面板 #tac-assets-panel-3，卡片 .energy-card；WTI 與 Brent 兩筆行情列為 #tac-assets-panel-3 .energy-card > .row（預期數量 2）。
- 貴金屬面板 #tac-assets-panel-4，卡片內兩筆行情列為 #tac-assets-panel-4 article.card > .row（預期數量 2），分別為 Gold 與 Silver。
- 各卡片 .tab-panel-meta 是日期與合約口徑；.market-reason 是觀察文字；.source-details 內來源文字與連結可隨資料更新。
- 原油與貴金屬是兩個不同 tab panel，不能合併成同一張卡片或跨面板更新。外框、tab、radio、收合控制固定。

## 週一上週經濟行事曆
- 容器 #last-week-calendar；外層 .last-week-calendar-collapse、summary、calendar-status-group、econ-event-list 與每張 details.econ-event 都是固定骨架。
- 每張事件卡摘要欄位 .econ-date、.econ-time、.econ-country、.econ-name、.econ-stars 可更新。
- 展開欄位限定在 .econ-details .econ-field；label 固定，.econ-value 可更新，來源連結屬資料內容。
- 目前母版樣本有 3 張事件卡；實際每週依 WR 只保留重要性五星事件，數量不固定。清空資料時必須保留所需空卡骨架，不得刪除整個收合元件。

## 週一上週財報行事曆
- 容器 #last-week-earnings；外層 .last-week-earnings-collapse、summary、calendar-status-group、.earnings-accordion-list 與每張 .earnings-accordion 固定。
- 摘要欄位沿用 .earnings-summary-dates、.earnings-us-date、.earnings-tw-date、.earnings-company-name、.earnings-company-sub、.earnings-stars。
- 已公布財報有專屬結果卡 .earnings-results-grid、.earnings-actual-card、.earnings-actual-line、.earnings-actual-status；EPS、營收實際與預期、優於/低於預期狀態均屬資料內容。
- 其他分析欄位限定在 .earnings-detail-field 與 .earnings-detail-value；label 固定，value 可更新。
- 來源連結與股價公布後表現是資料內容；卡片展開控制與欄位骨架固定。
- 樣本有 7 張卡，但每週實際張數不固定；不得把 7 寫死為固定數量。

## FOMC 會議
- 容器 #fed .fed-live-fomc；內層 .fc-fomc 固定。
- 會議日期：.fc-fomc-meeting 內 span 為固定標籤，b 為可更新日期。
- 記者會時間：.fc-fomc-press 內 span 固定，b 可更新。
- 目前目標利率：.fc-fomc-rate 內 span 固定，b 與 small 可更新。
- 核心觀察：.fc-fomc-observation 內 span 固定，b 可更新。
- 說明段落 p 可更新；tab radio、tab label、panel 與 .fc-fomc 外框固定。

## 驗收限制
- 本文件定位的是現有母版中的實際 class 與面板，不代表 selector 已通過瀏覽器測試。
- 商品原油、貴金屬面板的列數各為 2；若正式母版日後改變，必須先重新比對正式母版 SHA 與 DOM，再更新規格。
- 週一上週事件與財報張數依內容變化，不可將當前樣本張數作為硬性固定值。