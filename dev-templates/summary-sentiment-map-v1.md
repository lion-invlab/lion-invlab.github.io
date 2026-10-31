# 總結與市場情緒節點盤點 v1

來源：週一正式母版 main，blob SHA 176eb7c686f9e0de9216eb57e144eeebaaf75f9b。此盤點先定義可寫入內容區，保留卡片、版面、資料來源收合及互動骨架。

## 總結
- 容器：第一個總結區塊為 section.grid.two，其內 article.card.bluf。
- 可更新內容：article.card.bluf > h1（總結主標）；article.card.bluf > p（總結正文）。
- 固定內容：section、article、title 標題容器、卡片 class 與 CSS。不得替換整個總結卡。
- 正文包含上週回顧、本週展望、投資應對三個語意段落；更新時須維持三段順序與標籤結構。

## 市場情緒
- 容器：#sentiment；內層 .sent 是固定排版容器。
- VIX：#sentiment .sent > .sbox:nth-child(1)。可更新 strong 數值、緊鄰的漲跌 span、source-details .source；名稱及連結固定。
- MOVE：#sentiment .sent > .sbox:nth-child(2)。可更新 strong 數值、緊鄰的漲跌 span、source-details .source；名稱及連結固定。
- CNN Fear & Greed：#sentiment .cnn-fg-preview。可更新 .fg6-date、.fg6-score-main、.fg6-status 的文字、.fg6-marker 的 left 百分比及 aria-label、source-details .source。刻度色帶、標籤、容器及收合控制固定。
- 核心解讀：#sentiment .sent > .sbox:last-child（第四張 sbox）；可更新內層解讀文字，不可移除 label、卡片或改變其位置。
- .sbox 數量固定為 4；三個指標卡及一個核心解讀卡的順序固定。

## 今日觀察重點
- 容器：#view；tabs、radio、label、focus-panels 與 focus-panel 固定。
- 市場觀點：#view .focus-panel.focus-market .key 文字可更新。
- 今日關鍵價位：#view .focus-panel.focus-levels .key 內的指數名稱、支撐／中樞／壓力數值可更新；內部 details/summary 與計算方式、來源收合結構固定。不得刪除計算方式與來源收合區。
- 今日核心觀察：#view .focus-panel.focus-core .callout 內主評論可更新；其內 compact-disclosure 收合區需保留並依規則更新。
- 三個 focus-panel 的順序及 tab 關係固定；不可把 radio input 或 label 當資料插槽。

## 尚待完成
- KPI 區塊在這份母版中尚未定位出穩定的專屬容器 ID；須由頁首 DOM 階層及標籤語意再定位，禁止使用全頁通用 .value/.chg 等 selector。
- 以上 selector 尚未經瀏覽器 DOM 唯一性及手機版視覺驗收；仍屬候選 allowlist。