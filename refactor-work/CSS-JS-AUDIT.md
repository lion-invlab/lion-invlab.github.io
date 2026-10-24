# TAC CSS／JavaScript 依賴盤點 v1

基準：`refactor-work/source-baseline-2026-10-26.html`  
基準 SHA：`8e905bb16e6ea1575fded3b781b86597241ffd9d`  
樣式來源：`refactor-work/legacy-cascade.css`（由 95 個原始 style 區塊依原順序抽取）  
盤點日期：2026-10-24（台灣時間）

## 1. 靜態盤點指標

| 項目 | 統計 | 說明 |
|---|---:|---|
| 原始 style 區塊 | 95 | 已抽取，但目前大部分 legacy 規則仍保留 |
| Legacy CSS 字元 | 190,090 | 不是檔案大小或 selector 數的替代值 |
| CSS selector 近似項目 | 1,783 | 簡化掃描估算；含逗號 selector 拆分，不等於瀏覽器 CSSOM 規則數 |
| 重複出現的 selector 字串 | 365 | 多輪覆蓋與修補的重要風險訊號；重複不代表每條都能安全刪除 |
| `!important` 出現次數 | 2,000 | 高密度強制覆蓋；需按元件與優先級逐步整理 |
| `@media` 區塊 | 118 | 響應式規則散落在多個版本區塊 |
| `@keyframes` | 3 | 動畫名稱與觸發時序需保留 |
| 含 ID 的 selector | 652 | 高特異性規則，尤其要檢查是否與新元件規則互相競爭 |
| JavaScript 區塊 | 10 | 第一輪建置保留原始區塊與順序 |
| JavaScript 字元 | 16,486 | 仍需逐函式追蹤資料與 DOM 依賴 |
| function 宣告 | 14 | 靜態掃描結果 |
| `addEventListener` | 20 | 綁定點數量；需檢查重複綁定與目標節點 |
| `getElementById` | 15 | 包含非字串變數參數，不全是固定 ID |
| `querySelector/All` | 26 | 需核對 selector 是否依賴舊 DOM 結構 |
| Inline handlers | 6 | HTML 內仍有 inline 事件處理器 |
| `fetch()` | 1 | 不代表頁面沒有外部 iframe／第三方資料來源 |
| timer 呼叫 | 4 | 動畫與提示時序不能在整理時誤刪 |
| local/session storage | 0 | 目前靜態掃描未找到引用 |

## 2. 重複 selector 高頻清單

以下是字串重複次數，不是刪除清單。任何 selector 必須先確認 cascade 的最後有效值與其覆蓋範圍。

- `#sentiment>.title` — 9 次
- `#sentiment .sent` — 9 次
- `.fund-report-title` — 8 次
- `#sentiment .sent>section.sbox.cnn-fg-preview>.fg6-title` — 8 次
- `.history-panel>.title` — 7 次
- `.tac-tools-hint` — 7 次
- `html body .fed-compact-preview .fed-live-panel.fed-live-fomc .fc-fomc>.fc-fomc-observation` — 7 次
- `.history-box` — 6 次
- `.history-btn` — 6 次
- `html body #sentiment .sent > section.sbox.cnn-fg-preview > .fg6-title` — 6 次
- `html body #sentiment .sent > section.sbox.cnn-fg-preview > .fg6-title .label-en` — 6 次
- `html body #sentiment .sent > section.sbox.cnn-fg-preview > .fg6-title .label-zh` — 6 次
- `.fed-compact-preview .fc-fomc` — 6 次
- `html body .fed-compact-preview .fed-live-panel.fed-live-fomc .fc-fomc>.fc-fomc-meeting` — 6 次
- `#sentiment .sbox` — 6 次
- `.nav` — 5 次
- `.wrap` — 5 次
- `.fund-names` — 5 次
- `.fund-status` — 5 次
- `.history-field` — 5 次

## 3. JavaScript 函式清單（靜態掃描）

- `historyPath()`
- `historyMove()`
- `updateHistoryStatus()`
- `goLatestReport()`
- `openHistoryReport()`
- `syncHomeFundUpcoming()`
- `tacHistoryShift()`
- `tacOpenHistory()`
- `render()`
- `setup()`
- `stopAndRemove()`
- `findToolbar()`
- `move()`
- `applyFiveStarRules()`

## 4. 已辨識的 script ID

- `tac-layout-hint-v9-script`
- `tac-layout-v10-script`
- `tac-sidebar-tools-script-v2`
- `tac-sidebar-tools-script-v4`
- `tac-sidebar-tools-v6-note-script`
- `tac-fund-popup-v7-js`
- `tac-toolbar-hand-target-v15-js`
- `tac-verify-five-star-color-rule`

## 5. 代表性事件綁定片段

- `document.addEventListener('DOMContentLoaded',function(){  const header=document.querySelector('header');  if(!header)return;  const title=header`
- `document.addEventListener('DOMContentLoaded',function(){  const hint=document.querySelector('.tac-tools-hint');  const main=document.querySelect`
- `document.addEventListener('DOMContentLoaded',()=>{   const input=document.getElementById('historyDate');   if(input) input.addEventListener('cha`
- `document.addEventListener('DOMContentLoaded',function(){  const a=document.getElementById('tac-history-shortcut');  if(a)a.addEventListener('cli`
- ` document.addEventListener('keydown',function(e){if(e.key==='Escape')document.body.classList.remove('tac-side-open')}); });   document.a`
- `document.addEventListener('DOMContentLoaded',function(){  const nav=document.querySelector('nav.nav');  if(!nav||document.getElementById('tac-to`
- ` document.addEventListener('DOMContentLoaded',function(){   render();root.hidden=false;document.body.style.overflow='hidden';   document.getEleme`
- `ntById('tfn-ack').addEventListener('change',function(){if(this.checked)close()});   document.getElementById('tfn-close').addEventListener('clic`
- `  root.addEventListener('click',function(e){if(e.target===root)close()});   document.addEventListener('keydown',function(e){if(e.ke`
- `  move();window.addEventListener('resize',move,{passive:true});window.addEventListener('scroll',move,{passive:true});window.addEventListener('orientationchange',function(){if(!expi`
- `move,250)},{passive:true});window.addEventListener('pageshow',move);setTimeout(move,400);setTimeout(move,1200);  }  if(document.readyState==='loading')document.a`
- `  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',applyFiveStarRules);   else applyFiveStarRules(); })(); `

## 6. 安全移轉順序

1. **不得先大規模刪 CSS。** 重複 selector 與高密度 `!important` 顯示存在大量覆蓋依賴；先記錄元件的有效樣式，再逐元件搬移。
2. 已完成的 panel shell 與 radio tabs 是第一個試點；後續每一個元件需有「舊 selector → 新 component class → 視覺差異 → 互動測試」對照。
3. 先盤點事件處理器及其依賴的 DOM IDs；所有 script 區塊目前保留原順序。除非有獨立測試，不合併、不重排、不刪除。
4. 原生 radio/label 的頁籤切換依賴 DOM 順序及 `:checked ~ sibling` 選擇器；修改包裝層或新增 wrapper 時必須重新跑測試。
5. 先凍結固定／動態／條件式資料契約，再遷移內層卡片／收折；最後才逐批刪除已證明無引用的 legacy selector。
6. 此為靜態盤點，不能單獨證明所有 selector 或事件都在 runtime 有效；瀏覽器回歸仍是必須閘門。
