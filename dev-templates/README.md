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
- 已新增對兩份唯讀正式母版的真實 DOM 複製測試，模擬每個列表新增同骨架卡片及移除部分卡片，均通過。尚未做瀏覽器互動、手機版及 empty-state 變體驗收，故尚不能啟用開發母版產生、每日自動增刪或部署。
- 以上全部僅在 `tac-template-architecture` 測試分支。正式 WR、兩份正式母版、manifest、首頁及 11/02 預覽均保持不變。
