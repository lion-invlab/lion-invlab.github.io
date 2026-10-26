# TAC CSS 相依盤點｜2026-10-26

## 範圍與基線

本盤點直接讀取隔離分支目前的 `legacy-cascade.css` 與 `design-system.css`，目的是找出「已加上新元件 class、但仍依賴舊 selector 提供結構或互動樣式」的部分。它不是完整 CSS parser 的語意等價證明；出現次數是文字命中數，不代表獨立規則數。

- 舊 CSS：188,986 字元、1,995 個 `!important`。
- 設計系統 CSS：40,768 字元、263 個 `!important`。
- 候選建置仍將兩份 CSS 合併；因此目前仍是漸進遷移，尚未達到舊 CSS 可移除的乾淨架構。
- 本次沒有修改正式首頁、正式母版、JSON 資料或排程。

## 元件相依命中數

| 舊／現有元件識別字 | legacy CSS 命中 | design-system CSS 命中 | 判讀 |
|---|---:|---:|---|
| `.newsitem` | 8 | 2 | 舊 CSS 仍提供卡片邊線、最後一張卡規則與轉場；不能整批刪除。 |
| `.tac-tab-nav` | 53 | 18 | 高度相依；舊 CSS 包含選取狀態、產業頁籤排列與多個窄螢幕變體。暫不刪除。 |
| `.tac-section-heading` | 12 | 8 | 舊 CSS 仍提供標題容器與部分結構；需要先確認 DOM 結構及偽元素責任。 |
| `.econ-event` | 39 | 1 | 新系統主要接管外框，事件內部欄位、星號與展開符號仍由舊 CSS 負責。 |
| `.earnings-accordion` | 49 | 1 | 新系統主要接管外框；摘要列、公司名稱、財報內容與展開控制仍依賴舊 CSS。 |
| `.source-details` | 22 | 5 | 新系統接管共用外觀，但舊 CSS 仍有來源箭頭、內文及不同區塊變體。 |
| `.sector-row` | 10 | 10 | 舊 CSS 仍定義 grid 欄位、間距與手機尺寸；新系統部分接管外觀與字體。 |
| `.last-week-calendar-collapse` | 2 | 9 | 舊版容器和摘要樣式仍是刻意保留的相容層，避免窄螢幕高度回歸。 |
| `.last-week-earnings-collapse` | 5 | 9 | 舊版容器和摘要樣式仍是刻意保留的相容層，避免窄螢幕高度回歸。 |

## 重構決策

### 先做「新聞卡」元件的完整接管盤點，不直接刪除整組舊規則

舊 CSS 中新聞卡相關規則分散在基礎樣式、卡片背景和手機 padding。新系統目前接管標題、內文、來源文字及主要卡片外觀，但仍有舊規則提供邊線、最後一張卡的邊線移除與轉場。因此，若下一階段要移除舊規則，應先把仍需要的行為正式納入 `.tac-ds-card--news`，再在隔離分支逐條移除已被接管的舊規則。

### 頁籤、經濟事件、財報手風琴暫不批次清理

這三組舊規則仍包含互動選取狀態、內部欄位排版、展開圖示和響應式差異。僅以 selector 命中數判定「重複」會造成錯誤刪除。應先把內部結構與互動責任明確分層，再做元件級遷移。

## 驗收門檻

每次遷移後，繼續使用 1440、390、320px 三種視窗驗收；包含水平溢出、重複／缺少 ID、瀏覽器錯誤、頁籤切換、來源 disclosure 開合、行事曆開合、五星紅字數量，以及全球股市和產業／債匯商品名稱字體一致性。只有這些檢查通過，才可移除相對應的舊 CSS。

## 狀態

本文件是下一輪遷移的相依性依據，不代表舊 CSS 已被刪除。正式首頁和正式母版維持不變。

## 2026-10-26 遷移紀錄：新聞卡片（第一組完成）

- 設計系統 commit：`582a02eebf484ca2d0be9aae1df5c4ee3415d91f`；新聞卡片的背景轉場已移入 `.tac-ds-panel--tabbed .tac-ds-card--news` 正式定義。
- 舊 CSS commit：`97ae9c8c42b98c202d76d99516f9406cf55b8345`；移除已被新元件接管的新聞卡片基礎內距、底線、標題／內文樣式、偶數／奇數背景與手機內距。通用 `.newsmeta` 規則保留，因為其他元件仍可能使用。
- 驗收 run：`40256737803`，結果 `success`。實際下載並檢查 `results.json` 與 `summary.md`，不是只看 workflow 狀態。
- 1440、390、320px 均無水平溢出、缺少面板、重複 ID、未匹配導覽連結或新增瀏覽器錯誤。
- 三種尺寸五星紅字皆為 16；全球市場與產業商品名稱字體皆為 16px；15 張新聞卡仍由新元件識別，來源 disclosure 與行事曆／財報展開互動通過。
- 桌面整頁高度由 5147px 變為 5156px（+9px）；手機與窄手機畫布尺寸維持不變。此變化已記錄，不代表所有像素差異都等於錯誤；後續仍應逐組檢查差異圖。
- 目前只完成新聞卡片這一組的舊規則清理。其他元件仍依賴 legacy CSS，不能宣告整體架構重建完成。

## 2026-10-26 遷移紀錄：產業資料列（第二組，已驗收；詳細結果見下節）

- 舊 CSS commit：`8904b7d91be62648211b19377ec4de196c068253`；從 legacy 檔移除 10 條通用 `.sector-row`／`.sector-label` 規則。候選建置已將這 11 列全部標記為 `.tac-ds-data-row--sector`，且設計系統內已有專屬 grid 欄位、間距、rank、label、報酬率及手機版規則。
- 這次只移除候選版中已由專屬元件覆蓋的通用規則，未移除同一區塊其他仍使用的 legacy selector。
- 回歸測試 run：`40259133152` 已完成且成功；實際報告顯示基本互動與結構契約通過。視覺高度差異已另行記錄，仍需在後續整體視覺驗收時核對。
- 若驗收發現列寬、字體、圓角或手機版高度偏移，先修正新元件的正式規則並重跑；必要時回復移除的 legacy 規則。驗收通過後再更新本節狀態。


## 產業資料列（第二組：已通過瀏覽器驗收）
- 變更：移除 legacy cascade 中 10 組與 sector row 重複／互相覆蓋的規則；由 `.tac-ds-data-row--sector` 作為候選版產業資料列的唯一主要樣式來源。
- 相關提交：legacy 清理 `8904b7d91be62648211b19377ec4de196c068253`；驗收觸發 `289f6aca450cb751cad5c7d63231c38e9e24cdb6`。
- GitHub Actions： [run 40259133152](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40259133152) **completed / success**；已檢查 artifact `12623601255` 的 `results.json` 與 `summary.md`。
- 桌面 1440、手機 390、窄手機 320：均無水平溢出、缺失面板、重複 ID、未匹配導覽連結或新增瀏覽器錯誤；紅色五星計數均為 16；全球主要股市與產業商品名稱字級均為 16px；11 筆產業列均存在，桌機圓角 12px、手機圓角 10px、背景白色；產業分頁及收折互動均通過。
- 需留意的版面差異：桌機產業債匯商品面板高度由 380px 變為 332px（-48px）；手機由 448px 變為 439px（-9px）。這可能是清除多層重複 padding/min-height 後的緊縮，但目前 smoke test 只證明功能與基本樣式契約通過，未等於已完成逐像素視覺核可。正式首頁未修改。


## 2026-10-26 遷移紀錄：產業資料列通用規則合併（第三組，已驗收）
- 設計系統提交：`b10b6f78fdc3768fd1bf13a4b0cb38e1aecb172f`。移除 `design-system.css` 中一組 1,261 字元的泛用 sector row 樣式區塊；這些外觀設定已由後方更具體的 `.sector-row.tac-ds-data-row--sector` 元件規則完整接管，保留後方元件規則不動。
- 驗收 run： [40260066596](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40260066596)，狀態 `completed / success`；已下載檢查 artifact `12624641053` 的 `results.json` 與 `summary.md`。
- 1440、390、320px 均通過：沒有水平溢出、缺失面板、重複 ID、未匹配導覽或新增瀏覽器錯誤；紅色五星皆為 16；市場／產業商品名稱皆為 16px；11 筆 sector rows 存在，桌機圓角 12px、手機 10px、白色背景；分頁與收折互動通過。
- 面板高度與上一輪相同（桌機 332px、手機 439px），未因本次刪除重複元件規則再產生高度變化。與原始 baseline 的高度差仍記錄於第二組驗收節，不應解讀為逐像素視覺核可。
- 正式首頁、正式母版、JSON 資料與排程均未修改。


## 2026-10-26 遷移紀錄：市場情緒來源收折（第四組驗證完成）

- 舊 CSS commit：`0fb8c2517ae4d86ae2dad0249aeb0ffe1fa2ea5c`；移除 `#sentiment .source-details` 專屬的外距、摘要列排版、加／減號偽元素與來源內文樣式，並移除對應手機字級覆寫。市場情緒卡片本身的指標字級與手機排版保留。
- 驗收 run：`40260346513`，結果 `success`；已下載並檢查 artifact `12623797578` 的 `results.json` 與 `summary.md`。
- 1440、390、320px 均無水平溢出、缺少面板、重複 ID、未匹配導覽連結或新增瀏覽器錯誤；三種視窗五星紅字均為 16，全球股市與產業商品名稱字級均為 16px。
- 來源收折開啟／關閉測試通過，箭頭標記為 `▸`；暗色來源元件共 3 個，元件仍套用深色背景層次。整體瀏覽器錯誤為空。
- 本次是元件責任移交的回歸測試，不代表所有來源類 selector 都已清除；日曆來源、區域／產業來源與共用 `.source` 仍需逐一核對，不能批次刪除。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 遷移紀錄：來源摘要列舊式箭頭覆寫移除（第五組驗證完成）

- 舊 CSS commit：`01511a57c958771dd9edca0e9b8fee51d393574a`；從共用標記規則中移除已由 `.tac-ds-disclosure` 接管的 `details.source-details > summary` selector；日曆來源與尚未分類的 inline-style disclosure 仍保留舊式相容規則。
- 驗收 run：`40260907282`，結果 `success`；已下載並檢查 artifact `12624214179` 的 `results.json` 與 `summary.md`。
- 1440、390、320px 均無水平溢出、缺少面板、重複 ID、未匹配導覽或新增瀏覽器錯誤；來源收折開／關均為 true，標記為 `▸`；暗色來源 disclosure 3 個，新聞卡 15 張；五星紅字 16，全球與產業商品名稱字級皆為 16px。
- 桌機／手機幾何差異與前一輪一致；產業面板桌機仍較 baseline 短 48px，窄手機短 44px，列為既有視覺差異，不能視為逐像素核可。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 遷移紀錄：方法說明 disclosure 元件接管（第六組驗收完成）

- 設計系統 commit：`16fe3782e9b8005b777de0e8eebb9f4c46dd4b2a`；`.tac-ds-disclosure--method` 現在完整定義外距、透明容器、摘要列、`▸` 箭頭與展開狀態、內文字級及間距。
- 舊 CSS commit：`518240818ca717637c81a83c1c01352eee125f0b`；移除約 1,627 字元的舊式 compact disclosure 視覺規則，改以註解標示由新元件負責。
- 驗收 run：`40261098609`，結果 `completed / success`；已實際下載並檢查 artifact `12623494663` 的 `results.json` 與 `summary.md`。
- 桌面 1440、手機 390、窄手機 320px 均無水平溢出、缺少面板、重複 ID、未匹配導覽或新增瀏覽器錯誤；來源 disclosure 開／關均通過，標記仍為 `▸`，暗色 disclosure 3 個，新聞卡 15 張，五星紅字 16，全球／產業商品名稱字級皆為 16px。
- 既有幾何差異仍存在：產業債匯商品面板桌機高度 332px，相較 baseline 380px 少 48px；窄手機相較 baseline 少 44px。這是先前遷移留下的差異，不是本次方法說明遷移新增的回歸，也尚未獲逐像素視覺核可。
- 正式首頁、正式母版、JSON 資料與排程未修改。

## 2026-10-26 清理紀錄：無對應 DOM 的日曆來源 selector（回歸測試待完成）

- 候選建置檢查：`source-baseline-2026-10-26.html` 中沒有任何 `details.calendar-source-collapse` 或 `details.tac-ds-disclosure--calendar-source` 元素；該舊 selector 不應被計為一個已完成的元件遷移。
- 清理提交：legacy 註解更新 `d1e921c8e2c6d14fb74b5be5b7a73e5c3cb64230`；移除未被使用的設計系統元件區塊 `7586b65931c4cedbdca31effcee3a05c2d8ce91b`。仍有實際用途的 inline-style disclosure 相容 selector 保留。
- 驗收觸發提交：`fe1657eeca7a8ed411802bba859dab250f3308cb`；GitHub Actions [run 40261938319](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40261938319)。最近查詢仍停在 Install Playwright，尚未執行候選建置與瀏覽器測試；因此本項只記錄清理依據，不能標記為回歸驗收通過。
- 正式首頁、正式母版、JSON 資料與排程未修改。

### 回歸結果補記：無對應 DOM 的日曆來源 selector 清理

- GitHub Actions [run 40261938319](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40261938319) 已完成 `success`；artifact `12625051399` 的 `results.json` 與 `summary.md` 已下載並實際檢查。
- 桌面 1440px、手機 390px、窄手機 320px：`errors=[]`；三種視窗均無水平溢出、重複 ID、缺少面板、未匹配導覽連結或新增瀏覽器錯誤；來源 disclosure 開／關通過、標記 `▸`；五星紅字 16；全球股市與產業商品名稱均為 16px；新聞卡 15 張；事件卡 12 張、財報手風琴 22 張、產業資料列 11 列及既有互動均通過。
- 因候選 DOM 沒有 `.calendar-source-collapse` 對應元素，這次通過代表刪除未使用的元件 CSS、清理註解後整體回歸正常，不代表日曆來源元件遷移已完成。
- 既有視覺差異仍需單獨核對：產業債匯商品面板桌機 332px（baseline 380px，-48px）、手機 439px（baseline 448px，-9px）；另有其他面板幾何差異，功能 smoke test 不等於逐像素視覺核可。
- 正式首頁、正式母版、JSON 資料與排程未修改。

## 2026-10-26 遷移紀錄：四個方法／資料口徑 disclosure 統一接管（第七組，驗收待執行）

- 候選基線 DOM 有 4 個 `details[style*="margin-top:8px"]`：其中 2 個原本已使用 `compact-disclosure`，另外 2 個是未分類的純 inline-style disclosure；摘要分別為「資料來源與統計口徑」、「資料時間與快照口徑」、「價位計算方式與資料來源」、「核心觀察更新與失敗處理」。
- 候選建置器提交 `1dc581ae1846adc11fb3a3b3f5247fb3d0526ef8`：把四個元素統一標記為 `tac-ds-disclosure tac-ds-disclosure--method`，移除這四個元素上的 inline style，並要求匹配數必須恰好為 4，否則建置失敗。
- 舊 CSS 清理提交 `9968a4eb72a8272c68e07d37e5bc04831cb6bf03`：移除只服務於這四個 inline-style disclosure 的舊摘要列／箭頭規則；新元件已定義外距、摘要字級／顏色、箭頭與內容樣式。
- 回歸測試提交 `f84aad1019d10c656380c9bb654283a078bc335c`：新增硬性驗收條件，要求每個視窗恰有 4 個 `.tac-ds-disclosure--method`，且 0 個仍帶 `margin-top:8px` inline style 的該元件。
- GitHub Actions [run 40262457451](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40262457451) 已觸發，目前為 queued；在下載並檢查 artifact 前，不將此組標記為驗收通過。
- 正式首頁、正式母版、JSON 資料與排程未修改。

### 建置排錯紀錄：第七組首次驗收未進入瀏覽器測試

- 首次 run `40262457451` 的 Install Playwright 成功，但候選建置因 selector 正規表示式多了一層跳脫，回報 `expected 4 inline-style method disclosures, found 0`，未執行瀏覽器測試。此結果不是功能驗收失敗，而是建置器檢查條件沒有匹配到原始 HTML。
- 修正提交 `b26a58d817c92d9cc5a9051c8fc335daf3fa70be`：改為對完整 disclosure 區塊做正規化，將元素、summary 與內容 div 的 inline style 移交給元件樣式；保留內容與連結。
- 為避免外觀漂移，設計系統提交 `fd4db5d5ed404fe5bcf1fb5b85fac68da8cd8d90` 將 summary 字級、字重與箭頭大小調回舊規則的 12px／650／12px，並由元件接管 cursor。已重新觸發回歸測試，等待新的 run 結果。

### 第七組驗收補記：四個方法／資料口徑 disclosure 遷移成功

- 第二輪 GitHub Actions [run 40262568254](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40262568254) `completed / success`；已下載並實際檢查 artifact `12625520536` 的 `results.json`、`summary.md` 與候選 HTML。
- 1440、390、320px 三種視窗 `errors=[]`，均無水平溢出、重複 ID、缺少面板、未匹配導覽或新增瀏覽器錯誤；每個視窗均恰有 4 個 `.tac-ds-disclosure--method`，且 0 個該元件仍保留 `margin-top:8px` inline style。候選 HTML 的 `details[style*="margin-top:8px"]` 數量也為 0。
- 摘要列箭頭 `▸`，來源 disclosure 開／關通過；五星紅字 16；全球市場與產業商品名稱字級均為 16px；新聞卡 15、經濟事件 12、財報手風琴 22、產業資料列 11，相關既有互動均通過。
- 舊規則清理 commit `9968a4eb72a8272c68e07d37e5bc04831cb6bf03`；候選建置修正 commit `b26a58d817c92d9cc5a9051c8fc335daf3fa70be`；設計系統摘要列規格修正 commit `fd4db5d5ed404fe5bcf1fb5b85fac68da8cd8d90`。
- 視覺差異仍需逐項審視，不能把功能測試成功等同逐像素核可。已知產業債匯商品面板桌機 332px（baseline 380px，-48px）、手機 439px（baseline 448px，-9px）、窄手機 458px（baseline 502px，-44px）；窄手機總覽面板亦短 97px，S&P 500 財報健康面板短 34px，需保留在整體視覺驗收清單。
- 正式首頁、正式母版、JSON 資料與排程未修改。

## 2026-10-26 遷移紀錄：區域／產業來源摘要列（第八組，驗收待執行）

- 候選 DOM 中有 3 個 `details.region-source` 與 1 個 `details.sector-source`；它們已具有 `.tac-ds-disclosure--source`，但摘要字體／顏色／內距仍由 legacy selector 以 `!important` 提供。
- 設計系統提交 `3cfa4e705a6ceaa226f66a0de7f5855ff66e80e2` 新增 `.tac-ds-disclosure--source.region-source` 與 `.tac-ds-disclosure--source.sector-source` 摘要列樣式；舊 CSS 提交 `e5e88f866f10e819d4a03a2130a425827f8c018a` 移除兩組 legacy summary／marker 規則。保留原本實際計算樣式：11px、font-weight 400、`#9CA3AF`、padding `2px 0`。
- 測試提交 `5a7a5b05ad189e0287a5a678002ebe0011940c7e` 新增四個摘要列的硬性樣式驗收（字級、字重、顏色、padding），回歸觸發提交 `e642c7b7f700cba5d5009046b68b5ba74a1cba86`。等待 GitHub Actions 完成並檢查 artifact 後，才可將本組標記為通過。
- 正式首頁、正式母版、JSON 資料與排程未修改。

## 2026-10-26 遷移紀錄：Sentiment 深色來源 disclosure 色彩（第九組，等待前一輪後驗收）

- 候選建置器會將 sentiment 的 `details.source-details` 標記為 `.tac-ds-disclosure--dark`；設計系統已負責摘要文字、箭頭與 `.source` 內容色彩，但 legacy cascade 仍有多處 `#sentiment .source-details` 顏色覆寫。
- 舊 CSS 清理提交 `0db5a015ebd02f7b469760d7f31d487c05a2f498` 移除 5 條重複／覆寫色彩規則，保留設計系統既有色彩：摘要 `#AEBBC8`、箭頭 `#E2B84D`、來源文字 `#C2CCD6`。
- 測試提交 `42722d67efa6ede9360f25537efd699c6bc30740` 新增三個深色 disclosure 的計算樣式斷言。因第八組 run `40262905487` 尚在執行，尚未觸發新 workflow，避免併發設定取消前一輪。第九組尚未驗收。
- 正式首頁、正式母版、JSON 資料與排程未修改。


### 第八、九組合併驗收補記：通過（2026-10-26）

- 第八組首次 run `40262905487` 因 Playwright 安裝階段長時間停滯而被替代，不列為通過或失敗；替代 run `40263157833` 已進入瀏覽器測試，但測試斷言把計算後的 padding 字串預期寫成 `2px 0`，瀏覽器實際回傳 `2px 0px`，因此非版面問題而中止。
- 測試斷言修正 commit `40d143c624518a0f3b3356b2bb6d43f5adb9a6d3`：將預期正規化為瀏覽器實際的 `2px 0px`；重新觸發 commit `bf0c5f4d9622f503cbdd52fc590a64cf023ebb3e`。
- 最終驗收 GitHub Actions [run 40263417258](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40263417258) 為 `completed / success`；artifact `12625238188` 已下載並檢查 `results.json`、`summary.md` 與候選 HTML。
- 1440、390、320px 三種視窗均 `errors=[]`；無水平溢出、缺少面板、重複 ID、未匹配導覽或新增瀏覽器錯誤。第八組四個摘要列均為 11px、字重 400、`rgb(156, 163, 175)`、padding `2px 0px`；第九組三個 sentiment 深色來源 disclosure 均為摘要 `rgb(174, 187, 200)`、箭頭 `rgb(226, 184, 77)`、來源文字 `rgb(194, 204, 214)`。
- 方法 disclosure 仍恰為 4 個且 inline style 數量為 0；三種視窗五星紅字均 16，全球／產業商品名稱字級一致為 16px；共用 tabs 21、news cards 15、sector rows 11，相關既有互動通過。
- **保留的視覺驗收事項：**產業面板高度桌機 332px（baseline 380px，-48px）、手機 439px（baseline 448px，-9px）、窄手機 458px（baseline 502px，-44px）；窄手機 overview 面板短 97px，S&P 500 財報健康面板短 34px。這些幾何差異沒有在本輪修正，不能宣稱逐像素視覺核可。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 幾何差異診斷補記：配對基準／候選內部元素量測（Run 131）

- GitHub Actions [run 40265412091](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40265412091) 已 completed / success；artifact 12625823663 已下載，檢查 results.json 的 baselineDetailedGeometry 與 detailedGeometry。三種 viewport 的 errors=[]，無水平溢出、缺少面板、重複 ID、未匹配導覽或新增瀏覽器錯誤。這代表 smoke assertions 通過，不代表像素相同。
- 配對內部量測確認：產業資產 tabs 的導覽列在桌機由基準版 display:grid、高度 96px 變為候選版 display:flex、高度 40px（少 56px）；窄手機由 89px 變為 35px（少 54px）。這是候選 tabs 元件規格的明確幾何變動，並非外層面板 padding 單一造成。全球市場 tabs 在窄手機亦由 48px 變為 34px。
- 11 個產業資料列的量測顯示：桌機多數列由 73px 變 62px（約 -11px／列）；窄手機多數列由 68px 變 56px（約 -12px／列），較長文字列另有差異。這與設計系統元件的 min-height、padding 與 grid 配置相符，是產業面板高度差的重要來源。尚未確認所有差異是否符合原設計意圖，因此不直接把舊高度硬塞回去。
- 新聞卡在候選版大多維持原高度或增加約 2–3px；窄手機多數卡片約 -9px，但個別長文字卡因換行增加高度。S&P 500 財報健康區的主要內層區塊桌機高度相同；窄手機有一個 grid 區塊由 266px 變 235px（-31px），其餘多數內層高度相同。這些項目應分開檢查內容換行與容器寬度，不能只用整頁高度推斷。
- 本輪只增加並驗證量測工具，未修改任何 CSS；目前尚未批准或實施幾何回復。下一步先讀取候選版與 frozen baseline 對應的 tabs／sector-row 原始 computed-style 及 CSS 規則，判定哪些變動是預期的元件標準化、哪些是真正非預期漂移，再逐元件做最小修正及回歸。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 產業頁籤幾何修正回合（Run 132 失敗，已修正並重跑）

- Run 132 [40266019186](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40266019186) completed / failure。artifact `12626188393` 已檢查：瀏覽器無新增 JS error，其他互動多數通過；硬性驗收失敗項為 desktop 的 16 個紅色五星 glyph 計數回傳 0（手機與窄手機均為 16），此項與產業頁籤 CSS 改動沒有已知直接關聯，須以重跑確認是否為測試波動或穩定問題。
- 同一 artifact 的幾何數據顯示前一輪 CSS 改動並未完全恢復基準：桌面頁籤列 84px（baseline 96px），390px 為 70px（baseline 89px），320px 仍錯誤落入 `display:flex`、35px。檢查 CSS 後發現更新時 media rule 的 selector 區塊被不完整替換，造成窄螢幕規則不完整；已修復整段 CSS 區塊，改為明確的 grid selector，並設定頁籤最小高度 44px。
- 修正提交 `15cb57b2f669d3d80e4890aedb72276f3a558982`；回歸觸發提交 `fd0bb5b14f3a324ca5ab802774ccda5371ff8a20`。新 run `40266309905` 已排入隊列，尚未驗收。不得把 Run 132 標記為通過。
- 正式首頁、正式母版、JSON 資料與排程未修改。
