# 動態插槽候選節點 v1.1

本清單區分「資料內容容器」與「互動控制」。只有資料內容容器可以進一步拆分為插槽；radio input、label、tab-nav、details/summary、卡片外框均屬固定結構，禁止清空或替換。

## 新聞
- `tac-news-panel-0`：全球焦點新聞分頁內容容器；內層 `global-focus` 為卡片容器，須逐則定位新聞資料節點。
- `tac-news-panel-1`：市場熱門頭條分頁內容容器；逐則定位新聞資料節點。
- `tac-news-0`、`tac-news-1` 是 radio input ID，僅供分頁互動，絕不可當成資料插槽。

## 全球市場
- `global-markets`：全球主要股市分頁組件外框，固定。
- `tac-global-panel-0`、`tac-global-panel-1`、`tac-global-panel-2`：美國、亞洲、歐洲市場資料面板；只允許更新各行情列的資料值，不得替換面板或列結構。
- `tac-global-0`、`tac-global-1`、`tac-global-2` 是 radio input ID，僅供分頁互動，絕不可當成資料插槽。

## 產業、債券、匯率與商品
- `industry-bonds-fx-commodities`：整體分頁外框，固定。
- `bonds`：美債殖利率卡片；只更新日期、殖利率及變動值。
- `fx`：外匯卡片；只更新固定六項報價的日期、數值及變動值。
- 產業 ETF 與商品面板仍須定位其實際面板 ID 及逐列資料節點後，才能列入可寫入清單。

## 行事曆與財報
- `last-week-calendar`、`last-week-earnings`：週一專屬整體區塊。外層、details、summary、卡片與欄位骨架固定；只允許逐張資料卡內容更新。
- `calendar`：本週經濟行事曆。tabs、radio、紅圓加號、details 與卡片骨架固定；只允許逐張資料卡的日期、事件、實際值、預期值、前值、重要性與評論更新。
- `earnings`：本週財報行事曆。tabs、卡片骨架、欄位與收合控制固定；只允許逐張財報卡資料更新。

## Fed
- `fed`：Fed 限時動態卡片。外框、tabs、分頁控制固定；只更新 FedWatch 機率、會議日期與對應資料文字。

## 固定區域
頁首、導航、總結與盤面觀察重點版面、市場情緒視覺結構、全部卡片外框、欄位標籤、收合按鈕、分頁控制、CSS、JavaScript、手機響應式規則。

## 注意
以上仍是容器層級候選定位，不是已完成的逐欄位 selector。下一階段需解析各面板內部 DOM，建立精確資料節點 allowlist，才可製作清空資料的開發母版及自動化更新器。