# SIM-1.4｜Builder Selector／DOM 寫入清單（第一輪）

日期：2026-11-21  
工作分支：simulation/tac-process-lab-2026-11-06  
Builder：simulation-lab/runner/build_review_html.py  
Builder blob SHA：c4c24c03625b3532f48362d7235755a8fa55850f  
Manifest SHA：1496a510d144d340c41b642592675233d5bd2917  
Monday simulation mother SHA：36f29bcb37816348756f9233b60f0429d675a76e  
Weekday simulation mother SHA：19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96  
狀態：第一輪靜態盤點；尚未核准 Builder。

## 1. 本輪結論

兩份母版在同一凍結候選版本下均已實際 build 並通過 workflow QA，但 Builder 仍有多個容器層級 destructive writes。QA_PASSED 不等於所有寫入均符合母版零結構變更契約。本文件先列出可由原始碼直接確認的高風險位置；未完成逐 selector 白名單前，不得核准為 SIM-1.4 唯一 Builder。

Manifest 對兩份母版均明載「Summary and Market Sentiment section headings ... in existing mother CSS; no Builder CSS injection」。因此任何可執行路徑在未取得明確授權前，不得向 head/body 追加 CSS 或建立新版位。

## 2. 目前已確認的保護

| 區域 | Builder 位置 | 現況 | 判定 |
|---|---:|---|---|
| FedWatch | 29–80 | 強制兩個機率列、兩段 bar、兩個 legend；只更新既有 slot | PASS（需保留負向測試） |
| Fed 官員行程 | 89–151 | 固定 wrapper/title/list/prototype/empty slot；只移除 list 直屬已渲染 event instances，再由固定 prototype 複製 | 條件式 PASS（確認母版槽位後可接受） |
| 純文字 leaf | 185–195 | set_text 遇到子元素即拒絕，不清除巢狀 DOM | PASS（僅涵蓋經此函式的寫入） |
| Summary headline | 約 1300 | 更新既有 h1 leaf | PASS（summary points helper 仍需獨立核查） |
| CFD 防錯 | 約 160–183 | cfd_index_reference_series 被拒絕，不當現貨收盤渲染 | PASS（保留負向測試） |

## 3. 已確認的高風險 destructive writes

| Builder 行 | 目標／操作 | 實際影響 | 目前判定 |
|---:|---|---|---|
| 1197 | 移除 meta[name=tac-correction-test] | 刪除母版 head 節點 | 需證明該節點為明確可移除的測試殘留；否則 BLOCK |
| 1201、約 2550 | head_node.append(Comment(...))、soup.head.append(provenance_comment) | 在 head 新增兩個 provenance comments | 與母版 byte-identical 不同；需由 QA 契約明確允許 |
| 1240–1291 | special_focus 分支建立新 section、inline style、子節點並 append responsive style | 插入非母版區塊並改 head CSS；即使目前 fixture 未觸發，程式仍存在此路徑 | BLOCK，除非有明確授權的可選版位規格 |
| 1832 | panels.clear()，目標 .week-econ-panels | 清空整個經濟行事曆 panels 容器，再重建三個狀態 group | BLOCK，除非確認此容器是明確核准的 dynamic collection 且保留必要固定 wrapper／controls |
| 1839 | 每個 .econ-event-list.clear() | 清空卡片列表後重新插入卡片 | 條件式；須逐一核對清單本身是否核准為動態子集合 |
| 1866 | ep.clear()，目標 .week-earnings-panels | 清空整個財報 panels 容器，再重建 group | BLOCK，須先證明不會刪除母版固定 accordion／summary／控制 |
| 1882 | .earnings-accordion-list.clear() | 清空財報卡片列表 | 條件式；需確認固定容器與互動節點完整保留 |
| 1924、2005 | earnings card .earnings-accordion-details.clear() | 清空卡片詳情，再生成新的 results grid／detail fields | BLOCK，需確認母版本身是否已有同一結構及哪些子槽可重建 |
| 2012、2164、2170 | value_node／value.clear() | 清除財報欄位內容（部分再建 source link） | 條件式；來源連結與既有子節點須列入白名單 |
| 2083、2115 | Monday last-week economic／earnings list clear() | 清空上週卡片列表後重建 | 條件式；須核對母版收折外殼、summary、list wrapper 未被清除 |
| 2129 | grid.clear() | 清空 earnings health grid | BLOCK，需核對 grid 是否動態卡片槽或固定版面 |
| 2207 | fed_source.clear() | 清空 Fed source disclosure 子節點，再重新建立來源連結 | 條件式；需證明 .fc-source 是允許替換的動態來源槽 |
| 2264、2307 | source_detail/source.clear() | 清空來源揭露內容並重建 | 條件式；不能刪除母版內固定連結／提示節點 |
| 2316 | market_tab_label.clear() | 清空盤面觀察 tab label | BLOCK，應只更新既有文字節點 |
| 2328–2329 | disclosure.extract()、levels_box.clear() | 移除既有 disclosure，再清空整個 key-level content 容器 | BLOCK，可能刪除固定 details/summary 或其他母版內容 |
| 2366 | detail_body.clear() | 清空 key-level disclosure body | 條件式；只允許替換明確資料槽，不應任意移除內部結構 |
| 2383–2398 | disclosure.extract()、callout.clear()、detail_nodes[0].clear()、stale_detail.decompose() | 移除 disclosure、重建 callout、清空／刪除既有 detail nodes | BLOCK，需保留母版原有收折控制與子結構 |

註：上表不是說每一個 clear 都必然造成使用者可見錯誤，而是這些操作會移除既有節點；必須先證明目標是核准動態內容槽，且固定 wrapper、summary、控制、source link、ID、ARIA 與事件監聽結構不會被刪除。現有 QA 只能證明其測試所覆蓋的結構與互動結果通過，不能替代寫入授權清單。

## 4. 必須特別修正的設計原則

1. 不得以「重建後畫面看起來正確」作為清空母版容器的授權。
2. 動態卡片應以母版固定 wrapper + 固定 prototype + 明確 list slot 為邊界；只清空核准 list slot 的直屬 dynamic instances，不得清空整個 section/panels。
3. 如果母版沒有可供更新的必要子槽，應回報母版／資料契約不相容，不能在 Builder 補造新 DOM 或 CSS。
4. 來源揭露應優先更新既有文字節點及既有 anchor href；不可無條件清空整個 disclosure。
5. special_focus 應移出每日 Builder，或先由使用者核准兩母版固定槽位與 CSS；未核准時遇到 special_focus 必須 fail closed。
6. Fed 官員行程 wrapper、prototype、empty state 與 FedWatch 兩卡兩段是固定要求，不得因本輪重構而刪除。
7. Summary、Market Sentiment、Fed 官員行程、FedWatch、行事曆收折控制、來源連結及既有互動均須有獨立負向測試。

## 5. 尚未完成

- [ ] 將所有 451 個 selector/find/mutation 命中逐函式分類，產生完整 allowlist。
- [ ] 對照兩份母版的實際 DOM parent path、元素數量、子節點、屬性與固定互動。
- [ ] 確認 .week-econ-panels、.week-earnings-panels、.earnings-accordion-details、earnings health grid、key-level content 等是否在 QA Contract 中明確授權為動態槽。
- [ ] 為所有 destructive writes 加入缺失／重複 selector、缺失 wrapper、缺失 prototype、既有 source link 被移除、details/summary 被移除等負向測試。
- [ ] 移除或隔離未經授權的 special_focus 新增 DOM/CSS 路徑。
- [ ] 對同一凍結版本執行 DOM before/after structural diff；若修改 Builder 或 QA Contract，必須重新凍結並重跑 Monday + Weekday。
- [ ] 完成後再決定是否提交 SIM-1.4 核准；在使用者明確核准前，SIM-1.3 仍為有效規範。

## 6. 當前狀態

- 雙母版同 SHA build：PASS。
- 六視窗繁中字型與互動 QA：PASS。
- Builder 完整 selector/write allowlist：未完成。
- 容器層級 destructive writes：仍有 BLOCK／條件式項目。
- SIM-1.4：DRAFT，未生效。
- SIM-1.3：仍為唯一有效規範。
- main、正式首頁、正式母版：未修改。
