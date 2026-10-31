# Repeat Group 控制規則草案 v1.1

狀態：測試專區草案，未經使用者核准，不構成正式 WR，也不授權每日自動寫入。

## 核心原則

**行事曆小卡數量是動態資料，不是母版固定規格。固定的是外層容器、分類與互動結構，以及每張小卡的設計骨架；不固定的是每週／每日實際需要呈現的小卡張數。**

經濟行事曆與財報行事曆須依當週實際事件動態增減。不得將鎖定母版當下的 12、16、3、7 等樣本張數視為每日或每週目標、下限、上限或驗收門檻。這些數字只供描述母版樣本及測試 selector 命中狀況。

## 群組類型

### 1. 固定筆數群組（fixed）

只有經產品規格明確定義為固定的群組，才限制筆數及順序。候選包括：
- 全球焦點新聞：5 則。
- 市場熱門頭條：10 則。
- 全球主要市場行情列：美國 5、亞洲 6、歐洲 3。
- 11 大產業 ETF：11 列。
- 美債：3 列；外匯：6 列。
- FedWatch 機率卡：2 張。
- 市場情緒四個 sbox：4 個；今日觀察三個 focus-panel：3 個。

以上仍須遵守各自資料更新規則；此清單不代表已授權寫入。

### 2. 動態筆數群組（content_variable）

以下群組筆數須依實際事件資料決定，不設母版樣本筆數的固定限制：
- 本週經濟事件卡。
- 本週財報卡。
- 週一上週經濟事件卡。
- 週一上週財報卡。

週一與週二至週五的外層分類、列表容器數量可能不同，必須分別依各自母版驗證；但各列表內的小卡數量仍然動態。

### 3. 模板限定結構（template_specific）

週一專屬的「上週經濟行事曆」與「上週財報行事曆」外層區塊，在平日模板中不存在，屬模板差異，不得當作缺漏。這是容器／功能存在與否的模板規格，不是卡片筆數限制。

## 允許的未來操作邊界（尚未啟用）

1. 重複群組外層容器、status group、tab radio、label、nav、panel、details/summary、紅圓加號、欄位標籤、來源收合、CSS 與 JS 一律固定。
2. 每個動態群組必須指定唯一的容器定位方式及子項 selector；同一面板有多個 status group／列表時，必須逐一對應，不得合併。
3. 新增子項只能以同一正式母版中已核准的完整子項骨架複製，不得自行拼裝 HTML 或從另一模板搬用。
4. 移除子項只限於資料核實後不應出現的事件卡；可以依實際事件數量增減，不得為了湊母版樣本張數而保留過期卡片或補造事件。
5. 每張子項的結構指紋必須一致；只允許核准資料欄位中的文字、連結與明確資料屬性變動。
6. 每張卡的收合控制、summary、欄位 label、來源區與 aria／互動屬性必須保留。
7. 動態筆數群組的卡片張數不設固定目標、上限或下限；但「列表與零卡片 empty-state 互換」屬另一種 status-group 變體。只有同一份正式母版、同一個行事曆區塊中，已存在實際 `.calendar-status-empty` HTML 節點作為原型時，才可由變體驗證器允許切換；僅有 CSS 樣式定義不算具備原型。現階段已驗證週一母版的本週經濟／財報 status group 可在既有列表與既有 empty-state 之間切換；平日母版本週經濟／財報區塊，以及週一母版的上週經濟／財報區塊，尚無同區塊 empty-state HTML 原型，必須拒絕自動轉換並停止處理，不得自行拼裝 empty-state 或留下空白列表。
8. 任何新增／移除導致固定祖先、同層非 repeat 子項、互動控制或 CSS/JS 改變，均視為失敗並停止。
9. 每次 repeat-group 數量變動都必須留下新增／移除項目清單、理由與資料來源；不可靜默調整。
10. 若母版 SHA 與 manifest 不一致，或模板結構指紋不符，立即停止，不得寫入或部署。

## Status-group 變體驗證補充

- 已新增 `scripts/tac_status_group_validator.py`，將每個 status group 的標題／外層結構視為固定，只允許該 group 內「一個已登記列表 wrapper」或「一個同模板、同區塊既有 `.calendar-status-empty` 節點」作為內容變體。
- 變體切換時，status group 數量、順序、標題元素與 class、列表 wrapper／卡片原型、文件其他固定 DOM、CSS／JS 及重複 ID 保護均須通過。
- 文字內容（包括日期、事件名稱及 empty-state 說明）可依資料更新；class、屬性與子元素骨架仍受保護。
- 此驗證不代表可以無事件就任意顯示 empty-state；事件是否應存在仍須先依正式資料來源核實。它只驗證結構轉換是否沿用同模板既有原型。

## 差異比對器設計要求

採「整份文件固定結構（排除已登記的動態卡片節點）+ 每個列表外框指紋 + 每張卡片骨架指紋」：
- 文件其餘結構、列表外框與固定控制完全相等。
- 只允許登記為 content_variable 的子項數量改變；不設固定張數上下限。
- 子項順序由資料層的日期／狀態排序規則驗證，不以 DOM 基線順序硬鎖。
- 每個新增或保留的子項，都必須與同一母版對應群組的卡片原型骨架相符。
- 每個列表 wrapper 的數量、順序、標題及狀態分類保持不變；週一／平日各自比較自己的母版。
- 不得把整個 calendar／earnings 容器或 status group 的 innerHTML 當作可替換資料。

## 明確禁止

- 不得將母版當下的行事曆卡片數量當作日常固定目標、上限或下限。
- 不得為了維持 12／16 張等樣本數而補造、保留過期或刪除有效事件。
- 不得以整個 calendar／earnings 容器 innerHTML 覆蓋方式更新。
- 不得將週一與平日母版合併成一套共用結構。
- 不得為了讓測試通過而修改正式母版、manifest、首頁或正式 WR。
- 本草案未經使用者核准與完整測試前，不得啟用 repeat-group 自動增刪、開發母版產生或每日更新。

## 母版 selector 定位（候選）

- 本週經濟列表外框：`#calendar .econ-event-list`；子項：`#calendar .econ-event-list > .econ-event`。
- 本週財報列表外框：`#earnings .earnings-accordion-list`；子項：`#earnings .earnings-accordion-list > .earnings-accordion`。
- 週一上週經濟列表外框：`#last-week-calendar .econ-event-list`；子項：`#last-week-calendar .econ-event-list > .econ-event`。
- 週一上週財報列表外框：`#last-week-earnings .earnings-accordion-list`；子項：`#last-week-earnings .earnings-accordion-list > .earnings-accordion`。
- 平日母版的本週財報有 3 個獨立列表 wrapper；必須逐一保留其 status group 與標題。母版樣本中各 wrapper 的卡片數量僅為觀察值。
- selector registry 的精確數量只用於確認「母版中的 selector 定位是否正確」，不是行事曆資料筆數的每日限制。

## 後續驗收門檻

- [ ] 每個 repeat-group wrapper selector 命中數與身份均可確認。
- [ ] 週一／平日分別建立 baseline；不得跨模板混用。
- [x] 測試動態新增、動態移除與已存在 empty-state 原型的 status-group 變體切換；無原型區塊拒絕轉換。
- [ ] 驗證事件日期排序及來源資料正確性（與結構骨架測試分開）。
- [ ] 測試 details/summary、紅圓加號、tabs、aria 與手機版互動未受影響。
- [ ] 瀏覽器 DOM 測試通過。
- [ ] 使用者明確核准後，才可考慮建立測試用開發母版。
