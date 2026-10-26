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


## 2026-10-26 產業頁籤 CSS 再修正（Run 133 失敗，修正後待驗收）

- Run 133 [40266309905](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40266309905) completed / failure。artifact `12626700849` 已檢查；三個 viewport 的紅色五星均為 16，瀏覽器新增錯誤為 0，主要互動正常。失敗原因是產業頁籤的規則與其他主頁籤規格不一致（桌機產業頁籤 min-height 44px，而新聞／全球市場為 28px），且 320px 的舊窄螢幕規則仍將產業頁籤導覽列覆寫成 flex，實際高度 35px，未恢復 frozen baseline 的兩列 grid。
- 已在設計系統 CSS 移除產業 tab 專屬 44px 最小高度，提升 mobile grid selector specificity，並移除 320px 舊 flex 覆寫，保留窄螢幕字體／padding 設定。修正提交 `62d350c567c854f9d8bc7cd849a5e71f253fa6f1`。此修正目標是讓三種寬度都維持兩列 grid，並使桌機主頁籤尺寸斷言一致；尚未以新 artifact 證實。
- 下一步觸發完整瀏覽器驗收，檢查三個 viewport 的 tabs display／高度、桌機三組主頁籤樣式一致性、紅色五星數與所有既有互動。若仍失敗，依新 artifact 繼續修正，不將任何未驗收的 CSS 當作完成。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 產業頁籤回歸驗收（Run 134 通過；剩餘幾何差異保留）

- Run 134 [40266693614](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40266693614) completed / success；artifact `12626339205` 已下載並檢查 `results.json` 與 `summary.md`。三種 viewport 均 `errors=[]`、新增瀏覽器錯誤為 0；16 個五星紅色 glyph 全部符合，桌機新聞／全球市場／產業三組主頁籤樣式一致，產業頁籤三種寬度皆為 grid，tab 與 disclosure 互動正常。
- 修正已解決 320px 被舊 flex 規則覆寫的問題：候選窄手機導覽列現在為 grid、70px，而非上一輪 flex、35px。桌機導覽列 72px（baseline 96px），390px 70px（baseline 89px），320px 70px（baseline 89px）。因此目前已恢復 grid 排列及通過硬性回歸，但高度仍比基準短 19–24px，尚不能標記為幾何完全一致。
- 產業整體面板高度目前桌機 396px（baseline 380px，+16）、手機 471px（baseline 448px，+23）、窄手機 458px（baseline 502px，-44）。差異同時受頁籤列與資料列高度影響；不以加大 tab 高度破壞三組主頁籤一致性，也不盲目增加間距。下一步應單獨對照 baseline／candidate 的產業 tab padding、row-gap 與 sector-row 內部文字換行，先確認最小可逆調整，再做下一輪驗收。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 產業資料列高度校準（待回歸驗收）

- Run 134 artifact 的 baselineDetailedGeometry 與 candidate detailedGeometry 逐列比對後，確認產業資料列高度差是主要可控差異：桌機基準列 73px、候選列 62px；390px 基準列 68px、候選列 56px；320px 基準列多為 68px、長文字列 83px，候選列多為 56px、長文字列 70px。文字字級／行高相同，候選設計系統的 min-height 是主要固定高度差來源。
- 已把 .sector-row.tac-ds-data-row--sector 桌機 min-height 由 62px 調回 73px，mobile 由 56px 調回 68px；保留原有 grid 欄位、padding、字體和互動，不另加間距。提交 9fbdf35f20239f5c71ea3ecbfb17981186529316。這是針對已量測差異的單元調整，尚待完整三視窗驗收，尤其需核對 320px 長文字列與整體 panel 高度。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 產業資料列高度校準驗收（Run 135 通過）

- GitHub Actions [run 40267253701](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40267253701) completed / success；artifact 12627420407 已檢查。三個 viewport 均 errors=[]、新增瀏覽器錯誤 0、水平溢出 false、導航錨點通過、五星紅色 glyph 各 16。
- 產業資料列高度現已與基準一致：桌機 11 列均 73px；390px 11 列均 68px；320px 多數 68px、長文字列 70px（基準長文字列為 83px，仍有局部換行／欄寬差異）。面板高度改善為桌機 364px（基準 380，-16）、390px 439px（基準 448，-9）、320px 493px（基準 502，-9）。
- 目前主要剩餘幾何差異是產業頁籤列：桌機候選 72px 對基準 96px；手機與窄手機候選 70px 對基準 89px。由於其餘主頁籤需維持一致樣式，下一步先檢查基準與候選的 tab label 計算高度、padding、grid row sizing，然後只修正產業兩列 tab 的內部尺寸；不改動資料列、不以面板固定高度補差。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 產業資料列高度校準回歸（Run 135 通過）

- GitHub Actions [run 40267253701](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40267253701) completed / success；artifact `12627420407` 已下載並檢查 results.json。三種 viewport errors=[]、16 個五星紅色標記全數符合，無新增瀏覽器錯誤，既有互動通過。
- 產業資料列 min-height 回復後，桌機 11 列均為 73px、390px 多數列 68px、320px 多數列 68px；長文字列依換行自然增高（baseline 83px、candidate 70px），沒有硬塞固定高度。相較 Run 134，產業面板高度改善為桌機 364px（baseline 380，-16）、手機 439px（baseline 448，-9）、窄手機 493px（baseline 502，-9）。
- 目前剩餘最明確的差異是 tabs 導覽列：桌機候選 72px／baseline 96px；手機與窄手機候選 70px／baseline 89px。資料列的主要固定高度差已處理；下一步針對 tabs 的行高、padding、grid row sizing 做配對檢查，避免直接加高整個導覽列或破壞其他兩組主頁籤的視覺一致性。
- 正式首頁、正式母版、JSON 資料與排程未修改。


## 2026-10-26 產業資料列高度校準驗收（Run 135 通過）

- GitHub Actions [run 40267253701](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40267253701) completed / success；artifact `12627420407` 已下載檢查。三種 viewport 的 `errors=[]`、16 個五星紅色標記均通過，沒有水平溢出、缺少面板、重複 ID、未匹配導覽或新增瀏覽器錯誤；三組主頁籤計算樣式一致，產業頁籤／收折互動正常。
- 將 sector row min-height 桌機 62→73px、mobile 56→68px 後，產業面板高度：桌機 364px（baseline 380，-16）、390px 439px（baseline 448，-9）、320px 待依 summary 後段完整核對。桌機面板比前一輪 396px 減少 32px，表示這個修正確實改善高度偏差，但未完全回到 baseline；手機仍差 9px。桌機 tabs 仍 72px（baseline 96px），390／320 tabs 70px（baseline 89px），頁籤列仍有 19–24px 的基準差異。不要以整體面板高度判斷單一元件，下一輪應檢查候選／基準 tabs 的 padding、grid row-gap 和行高，尋找不影響三組主頁籤一致性的最小調整。
- 其他主要面板差異：桌機 overview +52px、S&P 500 財報健康 +27px、Fed +17px、View +15px；手機 overview -1px、S&P 500 財報健康 +8px、calendar +4px。窄手機的差異仍需從 results.json 的 paired detailed geometry 逐項定位，不能只依整頁差值直接修改。
- 稽核紀錄已更新。正式首頁、正式母版、JSON 資料與排程未修改。

## 2026-10-26 幾何校準紀錄：產業頁籤高度試驗（Run 136，失敗並已回退）

- 試驗提交：`f453ac83a2e6dc57cde2319736e49a33c0a2c1f1`；測試：[Run 136](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40268935934)，結論 `failure`。
- 已下載並檢查 Artifact `12626853953` 的 `results.json`、`summary.md`。三種視窗均無新增瀏覽器錯誤、水平溢出、缺失面板、重複 ID 或未匹配導覽；五星紅字均為 16。
- 失敗原因：桌機主頁籤計算樣式簽章不一致，因試驗將產業頁籤設為 14px／48px，而新聞與全球市場頁籤維持 13px／28px。違反三組主頁籤一致性門檻。
- 試驗的產業頁籤列高度：桌機 98px、390px 94px、320px 94px；對比基準版 96px／89px／89px。產業面板總高度則為桌機 +10px、390px +15px、320px +15px，故試驗不接受。
- 已回退該試驗專屬覆寫：`47ad8ade5f0c2727d2285f633d34008e65b3f396`。回歸驗證 Run 137 已觸發，待結果確認回退後的樣式一致性。
- 後續不得再用不同字級或最小高度強行補足。應先逐標籤量測 baseline/candidate 的 bounding box 與實際 grid row 軌跡；目標是在保留三組主頁籤共同計算樣式簽章的前提下，定位原始差異究竟是 grid row 分配、label 基礎規則，或容器 padding/margin。不得只比較外層總高度。


## 2026-10-26 產業頁籤幾何診斷與修正（Run 137–139）

- Run 137（回退後回歸測試：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40269193751）通過：原先頁籤樣式簽章恢復一致，但產業面板仍比基準短 16px／9px／9px。
- Run 138（新增逐標籤幾何量測：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40269414654）通過。Artifact 12627098634 的 results.json 顯示差異源頭是 grid 兩列高度：基準桌機 nav 96px、候選 72px；390px 與 320px 基準 89px、候選 70px。候選 label 的計算樣式仍須與另外兩組主要頁籤相同，不能直接提高 label 的 min-height、字級或 padding。
- Run 139（產業頁籤列高校準：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40269619720）通過。只調整產業頁籤 grid row tracks，不改共用 label 樣式：桌機 rows 36px + 36px，手機 rows 32px + 33px。結果產業面板高度與基準完全一致：桌機 380px、390px 448px、320px 502px；三種 viewport 無新增瀏覽器錯誤、無水平溢出、無缺少面板、重複 ID 或未匹配導覽；三組主要頁籤樣式簽章保持一致。這是通過的局部幾何修正，不代表其他面板差異已完成。
- Run 139 同時確認：產業 nav 實際高度桌機 88px、手機／窄手機 79px；雖低於基準 96px／89px，但由於候選面板其餘內容的內部間距略高，整體面板高度已與基準相符。保留這種以 grid row track 校準而不破壞共同 label 樣式的做法。
- 下一項定位目標不是「overview 面板」本身，而是整頁總高度／累積差異：桌機頁面總高度約 +68px、390px 約 +8px、320px 約 -53px；個別剩餘差異集中在 S&P 500 財報健康（桌機 +27px、手機 +8px）、Fed（桌機 +17px）、View（桌機 +15px）、calendar（手機 +4px）等。下一輪逐項比對這些面板的可見子元件 bounding boxes，不以整頁總高度作單一元件的判斷。
- 本輪只改動隔離分支的設計系統 CSS、瀏覽器測試診斷與觸發紀錄；正式首頁、正式母版、JSON 資料與排程均未修改。


## 2026-10-26 S&P 500 財報健康面板幾何校準（Run 140 通過）

- 測試：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40269870772；Artifact 12627054382 已下載並檢查。
- 以基準的實際子元件數據定位到三個來源：桌機外框 padding 候選 22px、基準 16px；標題候選高度 35px、基準 33px（含 padding／margin 差）；資料來源 summary 候選 24px、基準 17px。390px 也有相同的標題與 summary 差異，但外框 padding 候選為 14px、基準 16px。
- 在 381px 以上恢復面板 padding 16px、標題 padding 0／margin-bottom 11px，並將該面板方法摘要恢復為緊湊的原生 summary 樣式。驗收結果：桌機 583→582px（-1），390px 809→807px（-2）；無新增瀏覽器錯誤、水平溢出或頁籤簽章不一致。
- 320px 仍維持既有窄版規則（外框 padding 10px、標題緊縮、卡片內距縮小），面板為 909px、比基準 943px 短 34px。此差異尚未驗收，不應宣稱全尺寸幾何一致；後續若處理，須逐卡片比較換行與內容完整性，不能只強行加高面板。
- 下一步加入 Fed、View、Calendar、Earnings 面板的子元件幾何診斷，逐項確認剩餘差異（Fed 桌機 +17px、View 桌機 +15px、Calendar 手機 +4px），再做最小範圍修正。


## 2026-10-26 Fed／View 面板幾何校準（Run 141–143）

- Run 141（https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40270054416）與 Run 142（https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40270212742）通過；擴大 paired detailed geometry，確認 Fed／View 桌機高度差主要來自外框 padding、標題 padding／margin，而不是內容資料。
- Run 142 的量測：Fed 桌機候選外框 padding 22px、基準 16px；標題 35px／基準 33px、標題下距 16px／基準 10px；Fed 內容容器 343px／基準 346px。View 桌機外框 padding 22px／基準 16px；標題 35px／基準 33px、標題下距 16px／基準 11px；focus-tabs 163px／基準 167px。標準手機也呈現同方向差異，窄手機則有獨立緊縮規則。
- Run 143（https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40270454570）通過。381px 以上恢復 Fed／View 外框 padding 16px、標題 padding 0 與基準標題下距，並將 Fed 內容容器及 View focus-tabs 的自然高度底線恢復至基準。結果：Fed 桌機 422→423px（+1）、390px 416→416px（0）；View 桌機 244→245px（+1）、390px 320→320px（0）。無新增瀏覽器錯誤、水平溢出或主頁籤樣式簽章問題。
- 窄手機保留現有緊縮規則：Fed 411px（基準 416，-5）、View 372px（基準 368，+4）；暫不改動，需與其他窄版差異一併評估。
- 剩餘明確項目：經濟行事曆手機 +4px／窄手機 +7px；財報行事曆手機 +1px／窄手機 +2px。下一步補量測兩種行事曆內部標籤列、面板區域與上下 margin，避免以整體面板高度反推錯誤的 CSS 修正。


## 2026-10-26 行事曆內部幾何診斷（Run 144 通過）

- Run 144：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40270640388，Artifact 12628701038 已檢查；所有 viewport 無新增瀏覽器錯誤或水平溢出。
- 經濟行事曆與財報行事曆面板外框差異，主要落在 tab label row 與內容區高度互相抵銷。經濟 tab labels：桌機基準 56px、候選 46px；390／320 基準 58px、候選 46px。經濟 panels 區：桌機基準 98px、候選 109px；390 基準 133px、候選 149px；320 基準 151px、候選 170px。
- 財報行事曆亦有相同方向：labels 基準 56／58px，候選 46px；panels 區桌機基準 98px、候選 109px，390px 基準 115px、候選 129px，320px 基準 115px、候選 129px。這表示差異不能單靠 tab row 高度解決，需繼續比較 panels 內部事件群組、空狀態、事件卡與列表的實際高度。
- 下一步為測試診斷擴充，量測 calendar-status-group／heading／empty、econ-event-list、earnings-accordion-list 與各事件卡的 bounding box。尚未修改行事曆版面 CSS。


## 2026-10-26 行事曆高度差根因定位（Run 145 通過）

- Run 145：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40270815531，Artifact 12627996963 已檢查；所有 viewport 無新增瀏覽器錯誤或水平溢出。
- 經濟與財報行事曆的空狀態元件是可確認的主要差異：基準桌機 44px、候選 51px；390px 基準經濟 80px／財報 62px，候選 92px／72px；320px 基準經濟 98px／財報 62px，候選 113px／72px。候選空狀態套用了 14px padding（基準垂直 padding 12px），額外 margin-top:4px（基準 0），且字級／行高與基準不同；造成內容區多出 11–19px。
- tab label row 也比基準短：桌機 46px 對 56px，手機／窄手機 46px 對 58px。這是共享樣式遷移後的計算高度差，不應以面板固定高度補償。
- 下一輪採用兩個局部修正：行事曆 tab label 容器恢復基準 row footprint（56px 桌機、58px 手機），但保留共用 label 計算樣式；只在兩種行事曆內將空狀態的 padding、margin、字級與行高恢復為基準幾何。修正後再驗證整體面板與所有既有互動。


## 2026-10-26 行事曆幾何校準驗收（Run 146–147）

- Run 146（https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40271325462）通過，但首次空狀態覆寫在 320px 把經濟行事曆壓短 15px；該試驗不作為驗收。
- Run 147（https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40271499577）改回基準空狀態字級 13px、line-height normal，保留基準 padding 12px 14px、margin-top 0；並保留基準 label row footprint（桌機 56px、手機 58px）。已檢查 Artifact 12628857195，空狀態高度與基準在所有 viewport 完全一致，行事曆面板高度也完全一致：經濟桌機／手機／窄手機 305／399／417px；財報 305／412／427px。
- Run 147 三種 viewport 均無新增瀏覽器錯誤、水平溢出、缺少面板、重複 ID 或未匹配導覽；三組主要頁籤的樣式簽章一致。行事曆幾何項目驗收完成。
- 後續剩餘差異：桌機新聞掃描 -7px、全球市場 -4px；手機新聞掃描 -3px；窄手機新聞掃描 -25px、S&P 500 財報健康 -34px、Fed -5px、View +4px。窄手機的新聞卡片內距與 S&P 卡片間距有既有緊縮規則，應先標註為有意的窄版差異，再針對桌機／標準手機的微小差異逐項判斷是否值得修正。


## 2026-10-26 新聞掃描／全球市場幾何校準（Run 148 通過）

- Run 148：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40271691503；Artifact 12628882653 已下載檢查。
- 新聞掃描與全球市場面板：桌機新聞 807→807px、全球市場 477→477px；390px 新聞 1360→1360px、全球市場 578→578px，均與基準一致。主頁籤 label 的字級、min-height、padding、圓角、white-space 簽章仍一致，無新增瀏覽器錯誤、水平溢出、缺少面板、重複 ID 或未匹配導覽。
- 修正方式只提高兩個 nav 容器的 grid/flex footprint，不修改共用 label 規則：新聞掃描桌機 min-height 39px、390px min-height 35px；全球市場桌機 min-height 40px。窄手機新聞掃描仍比基準短 25px，這是既有 320px 卡片內距緊縮規則造成，暫保留。
- 桌機總內容高度相較基準約 +18px，主要由最上方主標題與 source disclosure 遷移樣式等累積，不再是新聞／全球市場面板高度造成。下一步應決定這些頂部共用元件差異是否屬預期設計更新；320px 的 -62px 則主要來自已知的新聞卡片緊縮（-25）、S&P 500 面板緊縮（-34）、Fed（-5）與 View（+4），不以整頁高度直接加補償。


## 2026-10-26 經濟事件卡片外框責任移交（Run 149 通過）

- 設計系統提交：9f564fb22748e727d1cb714563b9f37b2f7c9b85；legacy 清理提交：c89bae602cb7bf520eb97fad2a3701d71c53b9da；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40272039894。
- 候選建置的 12 張經濟事件卡均有 tac-ds-event，沒有仍依賴舊外框 selector 的未標記卡片。已將 min-width、transition 與 open 狀態外框陰影／邊線納入設計系統，並從 legacy 移除通用 econ-event 外框、背景、margin、摘要列 padding／背景等重複 selector；保留事件內部欄位與互動規則。
- Artifact 12629027417 已下載檢查：1440／390／320px 的 errors=[]、無水平溢出、缺少面板、重複 ID或未匹配導覽；經濟事件卡 12 張、財報卡 22 張、五星紅字 16；事件卡開啟／關閉與來源 disclosure 開啟／關閉皆通過。外框圓角桌機 12px、手機與窄手機 10px，與設計系統預期一致。
- 本組只完成事件卡外框與 open 狀態的責任移交；事件摘要列、meta/name/stars、內部欄位 grid 仍保留在 legacy。下一步可先移交摘要列與 metadata 版型，保留資料欄位與星號規則，逐步減少 legacy 相依，不批次刪除整個 econ-event 區塊。


## 2026-10-26 經濟事件卡片 metadata 樣式移交（Run 150 通過）

- 設計系統提交：69483016df3161795be2677fd39ef7fd7e486b0e；legacy 清理提交：f68bb42134ee6083c4d84423b0e789c77dcca5cf；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40272285720。
- 將 econ-meta、econ-country、econ-name、econ-stars 的 grid／字級／色彩與 mobile metadata 規則移入設計系統，並把已驗證的五星紅字規則改由 tac-ds-event.star-verified-five 負責；從 legacy 移除對應樣式與重複的名稱顏色覆寫。事件摘要列的結構與詳細欄位樣式仍留在 legacy，避免一次移動過多責任。
- Artifact 12628928450 已檢查：三種 viewport 均 errors=[]、無水平溢出、缺少面板、重複 ID或未匹配導覽；經濟事件 12 張、財報卡 22 張、五星紅字 16；事件卡開啟／關閉、來源 disclosure 開／關通過；外框圓角桌機 12px、手機／窄手機 10px。面板幾何與 Run 149 一致，未新增視覺高度回歸。
- 下一步可將 econ-details／econ-field／label／value 的內部欄位排版與響應式規則移入設計系統，並從 legacy 移除精確對應規則；不移動事件資料、DOM 結構或互動控制。


## 2026-10-26 經濟事件卡片內部欄位移交（Run 151 通過）

- 設計系統提交：6121ad130c44ffab42b7df4f43a17b36e2b971f4；legacy 清理提交：ce2ca88d7ce887c3e2620a188171ef137e8ce56b；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40272510059。
- 將 econ-details、econ-field、欄位 label/value、wide 欄位及手機版內距／字級規則移入 .tac-ds-event；從 legacy 移除 9 條精確對應規則。沒有改動 DOM、事件資料或互動控制。
- Artifact 12628682831 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；事件卡 12 張、財報卡 22 張、五星紅字 16；事件卡開／關、來源 disclosure 開／關均通過；桌機外框 12px、手機／窄手機 10px。主要面板幾何與 Run 150 一致，沒有新增高度回歸。
- 下一步將事件 summary 的 marker suppression、grid layout 與 meta 佈局責任進一步收斂到 .tac-ds-event；保留尚未驗證的 toggle pseudo-element 規則，先檢查 DOM 確認是否有實際 .econ-toggle 元素，再決定清理範圍。


## 2026-10-26 經濟事件摘要列移交（Run 152 通過）

- 設計系統提交：e0c7e8e93b4064e12cf2b4604514ff0d5a29f0ce；legacy 清理提交：4ffb5232f7eaafe5fcf2681a1da90b789cf010cd；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40272700767。
- 將事件 summary 的 list marker suppression、grid 列配置、cursor、gap 與 padding 移入 .tac-ds-event；檢查候選 DOM 後確認沒有任何 .econ-toggle 元素，故同步移除 6 組只作用於不存在 toggle 元素的舊 CSS selector。未改變 summary 的 DOM 結構，也未新增 toggle 元素。
- Artifact 12628564839 已檢查：桌面／手機／窄手機 errors=[]、無水平溢出、缺少面板、重複 ID；事件卡 12 張、財報卡 22 張、五星紅字 16；事件卡開／關、來源 disclosure 開／關通過；圓角仍為桌機 12px、手機／窄手機 10px；版面幾何與 Run 151 一致。
- 下一步可把 .econ-event-list 容器的 grid／gap／margin 移入設計系統，移除 legacy 的單一通用 wrapper rule；其後再評估事件卡內部剩餘相依與財報手風琴。


## 2026-10-26 經濟事件列表容器移交（Run 153 通過）

- 設計系統提交：57b1d929a08fa7fa8806849fb3b9014bb247e64d；legacy 清理提交：0a6d535d0a322b17ae350f8182ff6f0fed742830；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40272897835。
- 將 econ-event-list 的 grid、gap 與 margin 移入設計系統，從 legacy 移除原本單一通用 wrapper 規則。
- Artifact 12628914680 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；事件卡 12 張、財報卡 22 張、五星紅字 16；事件開／關與來源 disclosure 開／關通過；外框圓角桌機 12px、手機／窄手機 10px，面板幾何與 Run 152 一致。
- 盤點確認 legacy-cascade.css 中已沒有 econ-event、econ-meta、econ-name、econ-details、econ-field、econ-toggle 或 econ-event-list selector 命中；經濟事件卡的外框、summary、metadata、內部欄位與列表容器已由 design-system.css 接管。這代表經濟事件元件的舊 selector 相依已清零；不等於整份 legacy CSS 可以移除，其他元件仍有大量相依。
- 下一個候選是 earnings-accordion（舊 CSS 仍有大量 selector 命中、設計系統目前主要接管外框）；先量出其內部結構／樣式責任與候選 DOM 覆蓋率，再逐步移交。


## 2026-10-26 財報手風琴外框責任移交（Run 154 通過）

- 設計系統提交：c76a62a0abe06b298300298a8ef213fe5762939c；legacy 清理提交：480e4860e4790bc32a8e4e79444eb6d18cc2b80f；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40273144948。
- 已確認候選 DOM 22 張 earnings-accordion 全部帶有 tac-ds-earnings-card。將 min-width、transition 與 open 狀態外框邊線／陰影納入設計系統，從 legacy 移除舊外框規則及已被新元件覆蓋的 margin／摘要背景覆寫；保留摘要列 toggle、公司名稱、詳細欄位、結果 grid 等內部規則。
- Artifact 12627899961 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；經濟事件卡 12 張、財報卡 22 張、五星紅字 16；財報手風琴開／關、來源 disclosure 開／關通過；外框圓角桌機 12px、手機／窄手機 10px；面板幾何未變。
- 下一步先移交 earnings-accordion-list 容器的 grid／gap／margin，之後再處理摘要列與 toggle 控制。財報卡的內部欄位和結果 grid 有多層 legacy override，未完成逐條盤點前不批次清除。


## 2026-10-26 財報手風琴列表容器移交（Run 155 通過）

- 設計系統提交：347f4b89a10f1bf78ca3871636adac8adea2e80d；legacy 清理提交：a231a699455dcecc319b21c3a68991d2586b006f；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40273362678。
- 將 earnings-accordion-list 的 display:grid、gap、margin 與 min-width 移入設計系統，從 legacy 移除單一通用 wrapper rule。
- Artifact 12628169478 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；經濟事件卡 12 張、財報卡 22 張、五星紅字 16；財報手風琴開／關、來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；面板幾何未變。
- 下一步應先以計算樣式診斷確認財報摘要列與圓形 toggle 在桌機／手機的最終有效規則，再將最終樣式集中到 tac-ds-earnings-card，避免直接刪除目前多層 legacy !important 覆寫。


## 2026-10-26 財報手風琴摘要列計算樣式診斷（Run 156）

- Run 156：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40273584504，Artifact 12628384615 已檢查。
- 兩個容器的摘要列計算樣式：桌機 padding 13px 14px、gap 12px；手機 padding 12px 11px；#earnings 的手機 gap 8px，#last-week-earnings 保持 12px。摘要列目前 display:flex、align-items:center、justify-content:space-between、min-width:0、list-style:none、cursor:pointer。
- 候選 DOM 中 .earnings-accordion-toggle 元素數為 0；因此 legacy 中所有只針對此 toggle class 的圓形按鈕尺寸、背景、偽元素加減號規則皆未匹配任何 DOM，屬死規則。不要在這次 CSS-only 遷移中新增按鈕 DOM；只移除死規則，保持目前實際呈現與 summary 開／關行為。
- 下一步將摘要列本身的 flex／padding／marker 樣式移入 tac-ds-earnings-card，並移除死 toggle selector；保留 last-week earnings 的 summary visibility 規則與卡片內容／結果 grid 覆寫。


## 2026-10-26 財報手風琴摘要列移交（Run 157 通過）

- 設計系統提交：0f5f153765059b381d5e5b3546512c4f65ad6343；legacy 清理提交：a316001481737787fb2edc7825c8429f1651f58c；後續 mobile gap 清理：61b65d0e3f4c6268d15ef639161d78bb388400a5；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40273905318。
- 將摘要列 list-style、cursor、flex 排版、padding、min-width 與響應式 gap 移入 tac-ds-earnings-card；移除舊摘要列樣式與所有僅針對 .earnings-accordion-toggle 的死規則。DOM 檢查確認該 toggle class 在候選 HTML 中為 0 個，沒有新增任何按鈕或改動 DOM。
- Artifact 12629636532 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；財報卡 22 張、經濟事件卡 12 張、五星紅字 16；財報手風琴開／關、來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；面板幾何與 Run 156 一致。
- 計算樣式一致：桌機摘要 padding 13px 14px、gap 12px；手機摘要 padding 12px 11px；#earnings 手機 gap 8px、#last-week-earnings 手機 gap 12px。摘要高度診斷命中的是隱藏分頁／折疊內的卡片，因此高度值為 0；padding、display、gap 等計算樣式仍有效，但後續若需比較實際高度，需先打開父層收折與對應 tab。
- 下一步移交公司日期／名稱／產業副標／星號文字樣式；保留 .earnings-accordion-details、earnings-detail-field 與結果 grid 的 legacy 覆寫，直到完成相依性盤點。


## 2026-10-26 財報摘要文字樣式移交（Run 158 通過）

- 設計系統提交：9ccbb330a769dc97a502d5491a2825a38c441a5c；legacy 清理提交：33db11f0ed50a894d1e44b716287201d5521db00；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40274163205。
- 將日期列、公司名稱、副標與星號文字樣式移入 tac-ds-earnings-card，並把名稱顏色規則集中為：一般名稱黑色，只有 star-verified-five 的公司名稱紅色；保留設計系統已接管的五星星號紅色規則。從 legacy 移除 11 條對應文字／顏色規則。
- Artifact 12629082564 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；財報卡 22 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；面板幾何與 Run 157 一致。
- 下一步是財報卡內部詳細欄位的基礎樣式移交；先保留 last-week-earnings 的高優先級結果 grid 與容器覆寫，只移動沒有被特定面板覆寫的通用規則。


## 2026-10-26 財報手風琴內部欄位基礎樣式移交（Run 159 通過）

- 設計系統提交：dd26192ae49903c6bb2c1e256e65efd058dfbd4c；legacy 清理提交：35dee602788efe3d62091e2889fc865f69647f89；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40274386745。
- 將 earnings-accordion-details、earnings-detail-field、wide 欄位、label 與 detail-value 的基礎樣式及 640px 響應式規則移入 tac-ds-earnings-card；移除 6 條通用 legacy 規則。
- 保留 #last-week-earnings 的高優先級 display:flex、padding/gap、結果 grid 欄位規則與 wide 欄位覆寫，避免破壞上週財報的特殊內容結構。
- Artifact 12629791115 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；財報卡 22 張、結果卡 14 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；面板幾何未變。
- 財報手風琴通用 summary、日期／名稱／副標／星號與詳細欄位基礎樣式已移交；剩餘主要相依集中在上週財報專用的結果 grid 與寬欄位外觀。下一步先盤點這些規則與已存在的 tac-ds-earnings-actual-card 元件，不批次移除 #last-week-earnings 的 !important 覆寫。


## 2026-10-26 財報手風琴 detail-field 基礎規則移交（Run 159 通過）

- 設計系統提交：dd26192ae49903c6bb2c1e256e65efd058dfbd4c；legacy 清理提交：35dee602788efe3d62091e2889fc865f69647f89；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40274386745。
- 將 earnings-accordion-details、earnings-detail-field、wide 欄位、label 與 detail-value 的通用基礎樣式及 640px 響應式規則移入 tac-ds-earnings-card，保留 #last-week-earnings 的高優先級結果 grid 與 wide 欄位覆寫。
- Artifact 12629791115 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；財報卡 22 張、結果卡 14 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；面板幾何未變。
- 下一步盤點已存在的 tac-ds-earnings-actual-card 與 legacy 通用 .earnings-results-grid／.earnings-actual-card 規則，確認它們是否都只作用於已標記的上週財報卡，再移除重複基礎規則；保留 #last-week-earnings 的特殊 !important 覆寫。


## 2026-10-26 財報實際結果卡通用規則清理（Run 160 通過）

- legacy 清理提交：ef014ecca036ed68121e7ca56186dc56bbd9048a；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40274674877。
- 候選 DOM 結構檢查：7 個 earnings-results-grid、14 張 earnings-actual-card 全部位於 #last-week-earnings，14 張都帶 tac-ds-earnings-actual-card，沒有未標記卡片。
- 從 legacy 移除 7 條通用 results-grid／actual-card 規則（含重複的 mobile 規則及 grid child sizing）；保留 #last-week-earnings 的高優先級 !important 覆寫，因為它們仍控制實際結果 grid 的兩欄寬度、卡片間距、欄位順序與響應式行為。
- Artifact 12630085862 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；結果卡 14 張、財報手風琴 22 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；面板幾何與 Run 159 一致。
- 下一步需將 #last-week-earnings 的特殊 results-grid／actual-card 覆寫按責任分組；先搬移能由設計系統元件 selector 等價表達的部分，逐條驗收，不批次刪除整組 !important 規則。


## 2026-10-26 上週實際財報卡內部樣式移交（Run 161 通過）

- 設計系統提交：e906e684bc2e52353a24c1c1eba06fa75c9a651e；legacy 清理提交：e817ac5fbd6668ff9305916b20e8cfd52e39c7cc；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40274922465。
- 將實際財報卡的 border、title、EPS／營收列、status pill、note 的基礎樣式與手機變體集中於 tac-ds-earnings-actual-card，從 legacy 移除通用規則及最終外觀重複覆寫；保留上週結果 grid 的寬度／欄位結構覆寫與 detail-field.wide 專用樣式。
- Artifact 12630111168 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；結果卡 14 張、財報手風琴 22 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；幾何與 Run 160 一致。
- 下一步只處理 #last-week-earnings 的結果 grid 佈局：先將目前散落於 FIX v2/v3 與 approved-preview 區塊的有效規則整理成一組設計系統 scoped rule，逐條移除 legacy 重複覆寫；不得更動財報資料或結果卡 DOM。


## 2026-10-26 上週財報結果 grid 移交（Run 162 通過）

- 設計系統提交：33be9f30f7bfa005b4fb8c769269ebf1177583f8；legacy 清理提交：17919573a7b12501481d4fce82c8893022e60369；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40275159788。
- 將 #last-week-earnings 的 detail 容器方向、結果 grid 兩欄、gap、透明背景／零 padding、寬度／min-width、卡片 sizing 與手機 gap 收斂為設計系統 scoped rule；從 legacy 移除 8 條 FIX v2/v3／approved-preview 的重複結果 grid 覆寫。
- Artifact 12629703653 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；結果卡 14 張、財報手風琴 22 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；圓角桌機 12px、手機／窄手機 10px；面板幾何與 Run 161 一致。
- 剩餘 #last-week-earnings 專用 legacy 規則主要是 detail-field.wide 外觀與一條 summary visibility 修正；下一步移交 wide 欄位樣式，summary visibility 先保留直到確認它沒有遮蔽其他狀態。


## 2026-10-26 上週財報 wide detail-field 移交（Run 163 通過）

- 設計系統提交：51112026165ef685ad71985fbe92c2353022dc91；legacy 清理提交：3610b4ab17ecd1c4a2d54548bddcb7e5c3742b40；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40275372651。
- 將 #last-week-earnings 專用 wide detail-field 的 border、radius、padding、background、label 字級／字重／色彩與 value 字級／行高移入設計系統，從 legacy 移除 3 條精確覆寫。
- Artifact 12629303192 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；結果卡 14 張、財報手風琴 22 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；面板幾何與 Run 162 一致。
- 財報元件剩餘 #last-week-earnings legacy 例外只剩 summary 的 display／visibility 保險規則及其他非元件級的來源／內容樣式；下一步先核對這條保險規則是否有其他 display:none／visibility:hidden 對手，再移除或記錄保留原因。


## 2026-10-26 財報摘要 visibility 保險規則清理（Run 164 通過）

- 設計系統提交：d1ec1349853454f88c60c9afd96a5e9a33262385；legacy 清理提交：04829b97d9ec141770adb30a10f523bb2fc15a40；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40275596611。
- 診斷確認 legacy 中唯一 #last-week-earnings summary visibility 保險規則沒有相反的 display:none／visibility:hidden 對手；已把 visibility:visible 納入設計系統摘要列並移除 legacy 的 display:flex!important／visibility:visible!important 重複規則。
- Artifact 12630435447 已檢查：三種 viewport errors=[]、無水平溢出、缺少面板、重複 ID；結果卡 14 張、財報手風琴 22 張、經濟事件卡 12 張、五星紅字 16；手風琴開／關與來源 disclosure 開／關通過；面板幾何與 Run 163 一致。
- 財報手風琴元件相關 legacy 覆寫已大幅清理；接下來盤點非元件級規則與 CSS 依賴總表，避免為了清理而改動其他面板。


## 2026-10-26 依賴總盤點（Run 164 驗收後）

- 已由 design-system.css 接管：經濟事件元件完整外觀與 metadata／detail fields／summary／list wrapper；財報手風琴外框、列表容器、摘要列、日期／公司名稱／副標／星號、詳細欄位基礎樣式、實際財報卡外觀、上週財報結果 grid 與 wide 欄位變體。
- legacy selector 命中盤點：econ-event、econ-meta、econ-details、econ-field、econ-toggle、econ-event-list、earnings-actual、earnings-detail-field 的元件舊規則已清零；earnings-accordion 字樣剩餘 2 次，但不代表一定是 selector（需逐行檢查是否註解或非元件規則）。
- 已完成的驗收鏈：Run 150–164（含 Run 156 樣式診斷）均通過；每次 artifact 已確認 errors=[]、沒有水平溢出／缺少面板／重複 ID，並核對事件卡、財報卡、結果卡數量及互動。
- 下一步不應繼續大批刪 CSS；先列出 legacy 剩餘 2 條 earnings-accordion 命中與相鄰規則，確認語義後再處理。然後更新母版／工作規範中的依賴圖與目前驗收基準；仍只在隔離分支工作，不碰正式首頁、正式母版、JSON 或排程。


## 2026-10-26 財報手風琴收合保險規則移交（Run 165 通過）

- 設計系統提交：f30508a0c8f15bb77a6a52f76b48f7d84a6eab24；legacy 清理提交：2388a5e87e995ac0db6556f8003b9237a4d5d92b；驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40278522753。
- 將原本唯一的 legacy 規則 `#last-week-earnings details.earnings-accordion:not([open]) > .earnings-accordion-details{display:none!important}` 移入 design-system.css，改以 `#last-week-earnings details.tac-ds-earnings-card:not([open]) > .earnings-accordion-details` 精確限定已標記的設計系統財報卡；legacy 只留說明註解。22 張財報卡已確認皆是共用元件，因此不擴大或縮小實際元件範圍。
- Artifact 12631860073（`run165-results.zip`）已下載並檢查 `results.json` 與 `summary.md`：頂層 errors=[]；桌機 1440px、手機 390px、窄手機 320px 均無水平溢出、缺少面板、重複 ID 或新增瀏覽器錯誤；每個 viewport 都有財報卡 22 張、實際結果卡 14 張、五星紅字 16；財報手風琴開／關、上週財報收合與展開、經濟行事曆收合與展開、來源 disclosure 開／關均通過。面板幾何與基準大致一致；窄手機部分非目標面板有像素差異，屬 CSS 抽取基準既有差異，這次僅移動收合規則，未見目標元件或互動退化。
- 修正前盤點：`earnings-accordion` 字樣實際只剩 1 條有效 legacy 選擇器（不是 2 條）；其餘命中來自不同搜尋／統計口徑。移交後 legacy 中 `earnings-accordion` 有效選擇器為 0，經濟事件與財報元件舊規則清零的盤點不變。
- 下一步：開始整理非元件級 legacy 依賴地圖，先按區域／元件家族列出仍由 legacy 控制的規則、DOM 範圍與 !important 風險；優先選可驗收的單一元件簇，不批次刪除，也不碰正式首頁、正式母版、JSON 或排程。


## Run 165 後：剩餘 legacy 依賴風險分層（盤點，不代表已移除）

### 已核對的候選區塊

1. **主面板結構／間距（legacy 約 2693–2739 行）— 高風險，暫不移除。** `main.wrap` 的 flex/contents、主面板 display、新聞面板 overflow、`#calendar/#earnings` 外框正規化及間距互相依賴；任何單條刪除都可能改變導航錨點與整頁幾何。需先逐 selector 對照設計系統及 viewport geometry，再逐條遷移。
2. **主標題顏色／字級（約 2768–2848 行）— 高風險，暫不合併。** 有多組不同 specificity 的 `!important` 規則，市場情緒標題白色是刻意例外，其他主面板標題酒紅。須以 computed style 和 DOM 範圍證明等價後才能整理。
3. **市場情緒面板外觀（約 2427–2628 行）— 高風險，先維持。** 深色漸層、軌道偽元素、CNN 卡片玻璃效果及窄螢幕變體分散在多個版本區塊；現有驗收包含特殊背景與偽元素診斷，應先把有效規則歸納成來源矩陣，不可直接批次刪除舊版本。
4. **債／匯／能源／貴金屬商品列（約 1481–1580、2663–2679 行）— 有衝突，不可只按 selector 重複就刪。** 原始 block 47 的字級為 14px、block 48 改為 16px/1.5，後續 block 91 又針對特定商品名稱設定 16px/1.35。design-system.css 已有債券／商品名稱 16px/1.35 規則，但它不能單獨取代整個 legacy 區塊；匯率、能源、貴金屬的部分名稱沒有 `instrument-name` class，必須保留其覆蓋範圍。
5. **工具列提示／動態手指（約 2630–2691 行）— 中高風險，暫不動。** 桌機與窄螢幕有不同顯示條件，且動畫位置使用 CSS 變數與 fixed positioning；不屬於目前已驗收的財報／經濟元件範圍。

### 下一步執行順序

- 優先建立「主標題規則來源表」：逐條記錄 selector、媒體條件、specificity、最後生效值與例外，不先改 CSS。
- 接著選擇一條已被 design-system 等價接管且可證明沒有其他責任的規則做小步移交；每次只改一個責任簇，觸發桌機／手機／窄手機回歸，檢查 artifact 後再更新本表。
- 保持隔離分支；不更動正式首頁、正式母版、JSON、排程或任何資料／DOM。


### 主標題 cascade 來源表（Run 165 後盤點）

| Legacy 區段 | Selector 責任 | 宣告 | 目前判斷 |
|---|---|---|---|
| 約 2768–2777 | BLUF 標題字級／行高／字重；手機重申字級 | `font-size: clamp(21px,2.4vw,26px)`、`line-height:1.25`、`font-weight:900` | 與下一段共用變數重疊，但 BLUF 的 selector 更具體；先確認 design-system 是否覆蓋同一節點。 |
| 約 2779–2790 | 多種主面板標題字級統一 | `--tac-main-heading-size`、`line-height:1.25`、`font-weight:900` | 是目前共用字級來源之一；不可只刪變數宣告，因為多個 selector 直接引用。 |
| 約 2793–2797 | 市場情緒漲跌色 | up 酒紅、down 綠、warn 金色 | 與標題顏色不是同一責任，先保留。 |
| 約 2800–2812（block 93） | 多種主標題酒紅；市場情緒標題白色 | `#a92332!important`；情緒標題白色 | 與 block 94/95 有重疊，但覆蓋面不同。不能整塊移除。 |
| 約 2822–2837（block 94） | article/card/tabset 標題酒紅；情緒標題白色例外 | `#b42332!important`；情緒標題白色 | 範圍較廣，可能涵蓋巢狀卡片；需先用 DOM selector 命中清單確認，不與 block 93 視為完全重複。 |
| 約 2841–2848（block 95） | overview、兩個上週面板、calendar、earnings 的標題與情緒標題 | `#b42332!important`；情緒標題白色 | 對指定主面板是較晚的明確終局規則；但不取代 block 94 對其他卡片的涵蓋。 |

**目前安全結論：**主面板常見標題最終顏色是 `#b42332`，市場情緒主標題刻意為白色；主標題字級統一規則與顏色規則分開。此表只記錄來源與重疊，不視為完成移除。下一個實際 CSS 變更前，需在瀏覽器測試輸出中補一份各 viewport 的主標題 computed-style／命中節點診斷，才可判斷哪些舊規則真正無效。


## 2026-10-26 主標題 cascade 診斷與冗餘規則清理（Run 168–170）

- Run 168 診斷驗收：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40281696736；Run 169：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40281912199；Run 170：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40282162154。
- 已將主標題診斷加入 `visual-smoke-test.mjs`：逐 viewport 擷取 12 個主面板標題的 computed color/font-size/line-height/font-weight，並列出實際匹配的 CSS selector、媒體條件及宣告。Run 166/167 的 CSSOM walker 仍未能列出匹配規則，已在 Run 168 修正遞迴條件；Run 168 artifact 已確認命中清單正常。
- Run 169 移除 legacy block 95 最末端的低 specificity `#sentiment > .title { color:#fff!important; }` 重複宣告；Run 170 再移除較早的 `body #sentiment > .title { color:#fff!important; }`。兩條皆由後續更高 specificity 的白色例外覆蓋，逐條回歸後未改變 computed style。
- Run 170 artifact 12632971133 已檢查：頂層 errors=[]；桌機、390px 手機、320px 窄手機均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；三種 viewport 的市場情緒標題 computed color 均為白色 `rgb(255,255,255)`，財報／經濟元件數量及開關互動維持正常。
- 下一步：在市場情緒標題區繼續依診斷清單逐條核對剩餘低 specificity／重複白色宣告，先確認其後是否存在更強、同值的覆蓋；每次最多清理一條或一個已證明等價的最小規則群。避免觸及市場情緒深色背景、軌道偽元素與卡片玻璃效果，除非另行建立專項視覺驗收。


## 2026-10-26 市場情緒標題重複色彩宣告清理（Run 169–171 通過）

- Run 169：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40281912199；Run 170：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40282162154；Run 171：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40282383260。
- 依 Run 168 的 CSSOM 命中診斷，逐條移除三條低 specificity、同為白色的市場情緒標題重複宣告：block 95 尾端 `#sentiment > .title { color:#fff!important; }`、block 62 的 `body #sentiment > .title { color:#fff!important; }`、block 61 的 `main.wrap #sentiment > .title { color:#fff!important; }`。後續仍有更高 specificity 的白色例外，逐次測試未改變最終樣式。
- Run 171 artifact 12632966536 已檢查：errors=[]；桌機、390px 手機、320px 窄手機均無水平溢出、缺少面板、重複 ID；三種 viewport 市場情緒標題 computed color 都是 `rgb(255,255,255)`，命中規則清單仍可讀取。前一輪 Run 170 的財報卡／經濟事件卡數量、手風琴與 disclosure 互動均正常；Run 171 完整回歸也通過。
- 目前不是把市場情緒標題白色規則整組刪除；剩餘白色宣告仍需逐條比較 specificity、順序與媒體條件。下一步可檢查 `body main.wrap #sentiment > .title { color:#fff!important; }` 是否仍被後面的更強白色例外完全覆蓋，再做一條一驗收；不觸碰背景、軌道偽元素、卡片玻璃效果。


## Run 172 驗收與下一條白色例外判斷

- Run 172：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40282957469；artifact 12633027611 已解壓檢查 `results.json` 與 `summary.md`。三種 viewport 均無水平溢出、缺少面板、重複 ID、未匹配導覽連結或新增瀏覽器錯誤；市場情緒標題在桌機、手機、窄手機 computed color 都維持 `rgb(255,255,255)`；22 張財報卡、12 張經濟事件卡與相關開關互動正常。
- Run 172 移除 block 93 中 `#sentiment > .title { color:#fff!important; }`。後續 block 94 的 `main.wrap #sentiment > .title, main.wrap #sentiment .title:first-child { color:#fff!important; }` 仍接管該標題，驗收確認結果未變。
- 注意：剩餘 `body main.wrap #sentiment > .title { color:#fff!important; }` 的 specificity 高於 block 94 第一個 selector，但低於第二個 `main.wrap #sentiment .title:first-child`（前提是標題維持 section 第一子元素）；在目前 HTML 中它確實命中同一標題。可用一條獨立回歸驗證移除後 computed color 仍白色。若結果有差異立即回復，不動背景、偽元素或其他 sentiment 視覺規則。


## Run 173 驗收：移除 sentiment 標題重複白色規則

- Run 173：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40283172062；artifact 12632498799 已檢查 `results.json` 與 `summary.md`。
- 移除 `body main.wrap #sentiment > .title { color:#fff!important; }`。後續 block 94 的 `main.wrap #sentiment .title:first-child { color:#fff!important; }` specificity 更高，且命中同一個第一子元素標題。
- 驗收：`errors=[]`；desktop 1440、mobile 390、narrow-mobile 320 全部 `horizontalOverflow=false`、`missingPanels=[]`、`duplicateIds=[]`；三個 viewport sentiment 標題 computed color 都是 `rgb(255,255,255)`。桌機／手機版面主要幾何與 Run 172 相同，財報與經濟行事曆互動維持正常。
- 下一個最小候選：移除較早的 `#sentiment > .title{color:var(--red)!important}` 中僅有衝突的 color 宣告，保留同一段的 up/down/warn 顏色慣例；後續 block 94 的白色例外才是標題最終規則。須再做一次全 viewport 回歸。


## Run 174 驗收：移除 sentiment 標題衝突的紅色宣告

- Run 174：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40283400842；artifact 12633022160 的 `results.json` 與 `summary.md` 已檢查。
- 從 legacy 的市場情緒顏色慣例區移除 `#sentiment > .title{color:var(--red)!important}`，保留同區的 `.sbox .up/.down/.warn` 顏色規則。標題最終白色由後續高 specificity 的白色例外負責。
- 驗收：`errors=[]`；1440、390、320 viewport 均無水平溢出、缺少面板或重複 ID；三種 viewport 的 sentiment 標題 computed color 全為 `rgb(255,255,255)`。財報 22 張、經濟事件 12 張、開／關操作維持正常。
- 下一個候選：block 66 的 `#sentiment>.title{color:#fff!important;font-size:21px!important;font-weight:950!important}` 可只移除 color 宣告、保留字級與字重；後續更高 specificity 的白色例外已驗收為最終色彩來源。


## Run 175 驗收：只移除 sentiment 標題重複 color，保留字級／字重

- Run 175：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40283616490；artifact 12633346770 已解壓檢查。
- 將 `#sentiment>.title{color:#fff!important;font-size:21px!important;font-weight:950!important}` 收斂為只保留 `font-size:21px!important;font-weight:950!important`，移除重複 color 宣告。
- 驗收 `errors=[]`；desktop 1440、mobile 390、narrow-mobile 320 均無水平溢出、缺少面板或重複 ID；三個 viewport sentiment 標題 computed color 均為白色 `rgb(255,255,255)`，新增瀏覽器錯誤 0。
- 診斷同時顯示 source-baseline 仍包含早期 `#sentiment > .title` 顏色宣告（紅色／淺色），而後續 block 94 的高 specificity 例外才決定最終白色。source-baseline 是比較基準，不直接修改；未來若要把它併入元件樣式，需另做來源責任與 cascade 遷移，不可把基準檔的命中誤判成剛移除的 legacy 規則仍存在。
- 主標題這個最小清理簇先告一段落。下一步回到稽核表中「商品列字級」依賴：先盤點 legacy block 47/48/91 與 design-system 的命中範圍、實際生效字級、selector specificity，再挑一條確定重複且不改變能源／匯率／貴金屬範圍的規則進行單條移交。


## Run 176 驗收：清除被 block 48 完整覆蓋的商品列舊字級

- Run 176：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40283852851；artifact 12632763016 已檢查。
- 將 legacy block 47 中商品列的 align/font-size/line-height/font-weight/letter-spacing/數字對齊與手機覆寫移除；保留只由 block 47 負責的 `.tab-panel-meta` 與 `.title small` 字級規則。後續 block 48 使用相同範圍的 row selectors，且同樣含有手機媒體條件，原先較早的列字級宣告均被後續規則覆蓋。
- 驗收：`errors=[]`；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；三種 viewport 商品名稱仍維持 16px，與全球主要股市商品名稱字級一致；財報 22 張、經濟事件 12 張與相關互動正常。
- 下一步盤點 block 48 與 block 91 的關係：block 48 控制所有 tab-panel row 的 16px/1.5 排版，block 91 對債券、匯率、能源、貴金屬的特定 `b` 標籤強制 16px/1.35。兩者 line-height 不同且命中範圍不同，不能直接刪 block 48；先用 computed-style 診斷把四個分頁各種 row 的 line-height、font-size 與 selector 命中記錄出來。


## Run 178 驗收：移除 block 95 重複主標題顏色升級規則

- Run 178：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40284368436；artifact 12634030221 的 `results.json` 與 `summary.md` 已解壓檢查。
- 移除 block 95 對 overview、上週經濟行事曆、上週財報、calendar、earnings 五個標題的高 specificity 酒紅色重複宣告。block 94 的一般標題規則仍命中全部五個目標，computed color 沒有改變。
- 驗收：頂層 errors=[]；桌機 1440、手機 390、窄手機 320 均 `horizontalOverflow=false`、`missingPanels=[]`、`duplicateIds=[]`、`newErrors=[]`；12 個主標題診斷可正常輸出，五個目標標題三種 viewport 均為酒紅 `rgb(180,35,50)`，市場情緒標題均為白色。財報 22 張、經濟事件 12 張、實際財報卡 14 張；財報手風琴開／關正常。
- Pixel diff 存在，但與先前設計系統抽取分支的既有差異一致；本次只刪除 color escalation，主面板幾何無顯著變動，沒有新的瀏覽器錯誤。
- 下一個最小候選：block 91 的 `#industry-bonds-fx-commodities #bonds .row>b` 及其手機覆寫，與 design-system.css 中 `#industry-bonds-fx-commodities #bonds .row b` 同樣指定 16px/1.35；只考慮從 block 91 的 selector group 移除債券這一項，保留匯率、能源、貴金屬選擇器，並用 Run 179 驗證各分頁 computed style。


## Run 179 驗收：block 91 債券名稱字級規則交由設計系統負責

- Run 179：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40284829306；artifact 12633323212 的 `results.json` 與 `summary.md` 已檢查。
- 從 legacy block 91 的桌機及手機 selector group 移除兩條 `#industry-bonds-fx-commodities #bonds .row>b`，由 design-system.css 的 `#industry-bonds-fx-commodities #bonds .row b` 接管。其他匯率、能源、貴金屬 selector 仍保留。
- 驗收：頂層 errors=[]；1440、390、320 三種 viewport 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；債券名稱仍為 16px/21.6px，與設計系統值一致；全球主要股市與產業商品名稱仍均為 16px。匯率、能源、貴金屬的字級與行高維持原樣。
- 下一個最小候選：block 91 的 `#industry-bonds-fx-commodities #fx .row>b) 目前命中的名稱是 `.instrument-name`，design-system.css 已以 `#industry-bonds-fx-commodities .row .instrument-name` 指定相同 16px/1.35；可只移除 FX selector，保留能源與貴金屬的裸 `b` selector。


## Run 180–181 驗收與 FX selector 回退結論

- Run 180：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40285081581；artifact 12633473023 已檢查。此輪嘗試移除 block 91 的 FX 名稱 selector 後，CI 失敗；不是頁面錯誤，而是測試的商品名稱字級契約被破壞：FX 在手機／窄手機從 16px 降為 15px，因 legacy block 48 的高 specificity 手機規則仍勝過 design-system 的 `.instrument-name` 規則。此變更不可接受。
- 已恢復 block 91 的 `#industry-bonds-fx-commodities #fx .row>b` 桌機與手機 selector；保留前一輪成功移交的 bonds selector，並保留 energy、precious metals selector。
- Run 181：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40285303903；artifact 12632879644 已解壓檢查。errors=[]；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；四個商品區域字級符合契約：bonds 16px/21.6px、FX 16px/21.6px、energy 名稱桌機 16px/24px、手機 15px/22.5px（這是既有窄螢幕規則）、precious-metal 名稱 16px/21.6px；industryInstrumentFontSizes 三種 viewport 均只有 16px。
- **結論：** block 91 的 FX selector 目前仍有責任，不能單獨刪除。若未來要將 FX 完全移交 design-system，必須先處理 block 48 手機字級規則與 specificity，並同時驗證能源與貴金屬範圍；在此之前保留此 legacy selector。
- 下一步：停止針對 block 91 做更多 selector 刪除；先盤點 block 48 的手機 `font-size:15px!important` 覆蓋究竟是刻意例外還是舊版通用規則，逐項記錄它對債券、匯率、能源、貴金屬名稱／數值的實際命中，再決定是否拆分為明確元件變體。不得以改變測試預期的方式掩蓋樣式退化。


## Run 182 驗收：能源商品名稱字級在手機統一為 16px

- Run 182：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40285541946；artifact 12634196406 已檢查。
- 在 design-system.css 新增高 specificity 的能源商品名稱規則 `html body #industry-bonds-fx-commodities .tac-tab-panel .energy-card .row > b`，固定名稱為 16px/1.35。這是針對診斷發現的既有缺口：舊 block 48 的手機 15px 通用列規則 specificity 高於原 block 91 的能源名稱規則，導致能源名稱在手機仍為 15px，未達與全球主要股市商品名稱一致的 16px 契約。
- 驗收：errors=[]；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；能源名稱三種 viewport 均為 16px/21.6px，報價數值手機仍維持原本 15px/22.5px，其他債券、匯率與貴金屬名稱維持 16px。
- 下一個最小候選：現在 design-system.css 的能源名稱規則已用更高 specificity 固定相同 16px/1.35，可移除 block 91 的能源 `.energy-card .row>b` selector（桌機及手機兩處），但保留貴金屬 selector；再用 Run 183 驗證所有分頁。


## Run 183 驗收：能源名稱字級規則由 design-system 接管

- Run 183：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40285790317；artifact 12634455252 已檢查。
- 移除 legacy block 91 的能源 `.energy-card .row>b` 桌機與手機 selector，保留貴金屬裸 `b` selector。新的 design-system 規則已覆蓋能源名稱並以更高 specificity 壓過 block 48 的舊手機規則。
- 驗收：errors=[]；1440、390、320 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；能源名稱三種 viewport 均為 16px/21.6px，貴金屬名稱也維持 16px/21.6px；商品名稱尺寸契約在三種 viewport 均只出現 16px。
- 下一個最小候選：block 48 手機 media group 中的 `html body #industry-bonds-fx-commodities .tac-tab-panel .row b` 15px selector，對四個主要商品區的裸 `b` 名稱都已被更具體的 bonds／energy design-system 與 FX／貴金屬保留規則覆蓋。可只從手機 selector group 移除這一項，保留 `.row .name`、`.row .label` 與報價數字的 15px 緊湊規則，再驗收。


## Run 184 驗收：清除 block 48 通用手機裸 b 字級規則

- Run 184：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40286029448；artifact 12633948352 已檢查。
- 只從 block 48 的 `@media(max-width:600px)` selector group 移除 `html body #industry-bonds-fx-commodities .tac-tab-panel .row b` 的 15px 規則；保留 `.row .name`、`.row .label`、報價 `.r` 與漲跌幅 `.up/.down` 的手機 15px 規則。
- 驗收：errors=[]；1440、390、320 三種 viewport 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；債券、FX、能源、貴金屬名稱皆維持 16px/21.6px，手機報價仍為 15px/22.5px，符合既有緊湊數值排版。
- 下一個最小候選：將 block 91 的 `#tac-assets-panel-4 .row>b`（貴金屬名稱）兩處規則移到 design-system.css，建立比 block 48 更具體的元件規則，再逐條移除 legacy selector。保留能源與 FX 的已驗收狀態。


## Run 184 驗收：移除 block 48 手機版通用 row b 字級 selector

- Run 184：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40286029448；artifact 12633948352 已下載解壓並檢查 `results.json` 與 `summary.md`。
- 從 block 48 的 `@media(max-width:600px)` selector group 移除 `html body #industry-bonds-fx-commodities .tac-tab-panel .row b`，保留 `.row .name`、`.row .label`、`.row .r`、`span.r`、inline font-weight、`.up`、`.down` 的 15px 手機緊湊字級規則。桌機通用 `row b` 規則未變更；FX 與貴金屬 block 91 selector 也未變更。
- 驗收：頂層 `errors=[]`；desktop 1440、mobile 390、narrow-mobile 320 均 `horizontalOverflow=false`、`missingPanels=[]`、`duplicateIds=[]`、`newErrors=[]`、`pageErrors=[]`。三種 viewport 的全球主要股市與產業商品名稱字級診斷均為 16px。
- computed style 抽查：債券、匯率、能源、貴金屬名稱三種 viewport 均為 16px/21.6px；手機與窄手機的報價數值仍為 15px/22.5px；桌機報價數值維持 16px/24px。財報 22 張、經濟事件 12 張、實際財報卡 14 張；財報手風琴、經濟事件開關、商品分頁與 disclosure 互動均正常。
- 版面幾何：1440 與 390px 的主要商品面板高度一致；320px 所有面板仍存在且無溢出。窄手機 overview/news/標普財報等區域仍有既存 baseline-to-candidate 高度差，需在後續獨立幾何追蹤中處理，不應誤歸因於本次只涉及商品名稱字級的 selector。
- 下一步：先盤點 block 48 桌機通用 `row b/.row .name/.row .label` 與 design-system.css 的重疊範圍、實際 DOM 命中及 computed-style；不要直接刪除桌機 selector 或手機 `.name/.label` 規則。每次只移除一個已證明冗餘的 selector，再做全 viewport 回歸。


## Run 186 驗收：貴金屬名稱設計系統規則已驗證

- Run 186：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40286310013；artifact 12634201852 已檢查。原本命名為 Run 185 的工作流程被併發執行取消；Run 186 的候選版本已包含本次 design-system 規則，故以此實際 artifact 驗收，不把已取消的 Run 185 當成通過。
- design-system.css 已新增 `#industry-bonds-fx-commodities #tac-assets-panel-4 .row > b`，對貴金屬名稱設定 16px/1.35，specificity 足以壓過 block 48 通用手機 15px 規則。
- 驗收：errors=[]；桌機、手機、窄手機均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；能源與貴金屬名稱三種 viewport 均為 16px/21.6px，商品名稱字級契約只出現 16px。
- 下一步：從 block 91 桌機與手機兩處 selector group 移除 `#tac-assets-panel-4 .row>b`，由 design-system 規則接管，保留 FX 及其他仍有責任的 selector，然後用新 run 驗收。


## Run 188 驗收：貴金屬名稱規則移交設計系統

- Run 187 因 block 91 selector group 移除最後一個 selector 後留下逗號，執行期間被新的修復流程取消；不把它當成驗收。Run 188 修正 selector 語法並完成回歸：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40286978576；artifact 12634741349 已解壓檢查。
- block 91 的貴金屬 `#tac-assets-panel-4 .row>b` 桌機／手機規則已移除，改由 design-system.css 的 ID-scoped selector 負責。block 91 現在只保留 FX 名稱 selector；它不能直接刪除，因為 Run 180 已證明手機時 block 48 的 15px 規則會勝出。
- Run 188 驗收：errors=[]；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；債券、FX、能源、貴金屬名稱全部為 16px/21.6px，商品名稱尺寸契約在三種 viewport 都只有 16px。手機報價仍保留原本 15px 緊湊數值排版。
- 下一步：block 91 只剩 FX selector，且已證明受 block 48 高 specificity 手機規則影響。不要單獨刪除；若要移交，需先把 block 48 的 FX 名稱手機規則改成明確的設計系統變體，再逐步移除 FX legacy selector。接下來先盤點 block 48 的 `.row .name/.label` 以及數值 `.r/.up/.down` 命中範圍，建立哪些 selector 實際被 DOM 使用的清單，再決定下一個最小可安全遷移單位。


## Run 189 結果與修復：block 48 selector 語法

- Run 189：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40287322663；artifact 12634457375 已檢查 `results.json` 與 `summary.md`。errors=[]；1440/390/320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；三種 viewport 的商品名稱診斷均為 16px，互動測試通過。
- 但人工檢查 legacy-cascade.css 發現先前移除 `.row .name` 與 `.row .label` 後，桌機 selector group 的 `.row b,` 留下懸空逗號。瀏覽器 smoke test 未直接檢查 CSS selector 語法，因此 Run 189 只能作為版面/互動結果，不能單獨完成本次驗收。
- 已修正該 group 為 `.row b{...}`，其餘規則與移除範圍不變。Run 190 將重新建置並驗收，確認 selector 語法修復後商品名稱、數值與所有 viewport 行為仍符合契約。

## Run 189 驗收：移除 block 48 未使用的 .name/.label selector

- Run 189：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40287322663；artifact 12634457375 已檢查。
- DOM inventory（run188 candidate-build.html）確認 `.tac-tab-panel .row .name` 與 `.tac-tab-panel .row .label` 命中數均為 0，因此從 block 48 桌機／手機 selector group 移除這兩個未使用 selector；保留實際存在的 `b`、`.r`、`span.r`、內嵌字重 span、`.up/.down` 規則。
- 驗收：errors=[]；1440、390、320 均無水平溢出、缺少面板、重複 ID或新增瀏覽器錯誤；商品名稱字級契約三種 viewport 都只有 16px，導航錨點通過。
- 下一步候選：block 47 殘留的 `.tab-panel .title small` selector 在 baseline DOM 命中 0 次，而同組的 `.tab-panel-meta` 命中 5 次；可只移除未使用的 `.title small` selector，保留實際使用的 metadata 字級。


## Run 191 驗收：修正 block 48 selector 並移除 block 47 dead selector

- Run 191：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40287599181；artifact 12635136644 已檢查 `results.json` 與 `summary.md`。errors=[]；1440/390/320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽錨點、7 組分頁、來源 disclosure、經濟事件與財報收合互動通過；商品名稱三種 viewport 均為 16px。
- 本輪候選包含 block 48 的 `.row b{...}` 懸空逗號修復，以及 block 47 移除零命中的 `.tab-panel .title small`，保留命中 5 次的 `.tab-panel-meta`。兩項均經 Run 191 完整 workflow 與 artifact 驗收。
- DOM inventory（Run 191 candidate-build.html）：商品列共 13 列；`.row .name`=0、`.row .label`=0、`.row .up`=7，且 `.up:not(.r)`=0；7 個 `.up` 全部同時符合 `.r`，因此 block 48 的 `.row .up` 是 `.row .r` 已覆蓋的重複 selector。下一輪只移除 `.row .up`，保留 `.row .down` 及 `.r` 數值規則。

## Run 192 驗收：移除重複的 block 48 .row .up selector

- Run 192：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40287962596；artifact 12634537877 已檢查 `results.json` 與 `summary.md`。workflow success；errors=[]；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽錨點、分頁、來源 disclosure、事件／財報收合、商品分頁與商品收合互動均通過。
- 本輪只從 block 48 桌機與手機 selector groups 移除 `.row .up`。DOM inventory 顯示 7 個 `.up` 全部同時符合 `.r`，`.up:not(.r)`=0；移除後商品名稱仍為 16px，其他商品值與互動契約維持。
- Run 192 DOM inventory 也確認 `.row .r` 命中 26 次，`span.r` 同樣命中 26 次，`.r:not(span)`=0；因此 `html body #industry-bonds-fx-commodities .tac-tab-panel .row span.r` 是 `.row .r` 的完全重複 selector。下一輪只移除這個 `span.r` selector，保留 `.row .r` 與內嵌字重 span 規則。

## Run 193 驗收：移除重複的 block 48 span.r selector

- Run 193：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40288194007；artifact 12635400543 已檢查 `results.json` 與 `summary.md`。workflow success；errors=[]；1440/390/320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽錨點、分頁、來源 disclosure、經濟事件與財報收合、商品分頁與商品收合互動均通過。
- 本輪只從 block 48 桌機與手機 selector groups 移除 `span.r`。DOM inventory 顯示 `.row .r`=26、`span.r`=26、`.r:not(span)`=0，兩 selector 命中完全相同；商品名稱三種 viewport 均維持 16px。
- DOM inventory 顯示 `span[style*="font-weight"]` 命中 3 次，且 `span[style*="font-weight"]:not(.r)`=0，這三個 inline-font-weight span 也全部被 `.row .r` 覆蓋。下一輪只移除該 inline-style selector，保留 `.row .r` 與 `.row .down`。

## Run 194 驗收：移除 block 48 inline-font-weight selector

- Run 194：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40288410778；artifact 12634823806 已檢查 `results.json` 與 `summary.md`。workflow success；errors=[]；1440/390/320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽、分頁與各 disclosure/accordion 互動均通過，商品名稱字級仍為 16px。
- 本輪只移除 block 48 的 `span[style*="font-weight"]` selector。DOM inventory 顯示其 3 次命中全部也是 `.r`（`span[style*="font-weight"]:not(.r)`=0），因此由 `.row .r` 接管；數值與名稱樣式未退化。
- 下一個候選：`.row .down` 命中 6 次且 `.down:not(.r)`=0，全部已由 `.row .r` 命中；桌機 `.row .down` 的字級／行高／字重／nowrap 與 `.row .r` 相同，手機規則也只重複設定 15px。下一輪只移除 `.row .down`，保留 `.row .r`。

## Run 195 狀態：安裝步驟停滯，未形成驗收結果

- Run 195：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40288608489 在 `Install Playwright` 持續停留，建置與瀏覽器測試尚未開始，沒有 artifact 可檢查。此 run 不算通過，也不能用來判定 CSS 變更。
- 為避免無效等待，Run 196 對同一隔離分支版本重新執行完整 workflow；Run 195 隨新觸發取消，僅記錄為基礎設施重試，不算 CSS 驗收失敗或成功。


## Run 196 驗收：重試並驗收 block 48 .row .down 清理

- Run 196：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40288906883；artifact 12635333220 已檢查 `results.json` 與 `summary.md`。workflow success；errors=[]；1440、390、320 三種 viewport 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽錨點、分頁、來源 disclosure、事件／財報收合與商品分頁／收合互動通過。
- 本輪驗收 block 48 的 `.row .down` 清理：DOM 中 6 個 `.down` 全部同時符合 `.row .r`，移除後全球股市與產業商品名稱三種 viewport 仍為 16px，報價維持桌機 16px、手機 15px。
- 下一候選是 block 48 的通用 `.row b` 規則。DOM inventory 顯示 13 個商品名稱分別由債券（3）、FX 的 `.instrument-name`（6）、能源（2）及貴金屬（2）組成，皆已有更具體的名稱字級規則；目前 computed style 亦顯示字重為 700、字距為 normal。下一輪僅移除這條通用 `.row b` 規則作驗證，保留通用 `.row` 與數值 `.row .r`，檢查所有名稱的字級、行高、字重、字距及三種 viewport；若任何樣式偏移即恢復。


## Run 196 驗收：移除重複的 block 48 .row .down selector

- Run 195 因 Install Playwright 未完成而被 Run 196 取代，Run 195 不算通過。Run 196 完整成功：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40288906883；artifact 12635333220 已下載並檢查 `results.json` 與 `summary.md`。
- Run 196 的 errors=[]；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導航錨點、分頁、來源 disclosure、經濟事件／財報收合與商品分頁／收合互動通過。全球股市與產業債匯商品名稱在三種 viewport 均為 16px。
- 本輪只移除 block 48 的 `.row .down` selector。candidate DOM 有 6 個 `.down`，且 `.down:not(.r)`=0；因此數值的既有 `.row .r` 規則已完整覆蓋，移除沒有造成版面或互動回歸。
- Run 196 candidate DOM 的 13 個商品名稱分布為債券 3、FX 6、能源 2、貴金屬 2。design-system.css 已分別以 `#bonds .row b`、`.row .instrument-name`、`.energy-card .row > b`、`#tac-assets-panel-4 .row > b` 覆蓋這 13 個名稱的 16px 字級；下一輪只移除 block 48 `.row b` 的 `font-size:16px!important` 宣告，保留 `line-height:1.5`、字重與 letter-spacing，避免一次改動行高幾何。


## Run 197 結果：通用 .row b 整條移除會改變能源名稱字距

- Run 197：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40289217514；artifact 12635378540 已檢查。workflow success；errors=[]；1440、390、320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤，導覽錨點與主要互動通過。
- 但 computed-style 對比發現能源商品名稱的 letter-spacing 從 Run 196 的 `normal` 變為桌機 `-0.35px`、手機／窄手機 `-0.4px`。因此「整條移除」不符合保留現有樣式的要求，不把這項移除視為可接受的清理。
- 修正策略：保留 block 48 的 `.row b` 規則，只先移除其中已由 bonds／FX／energy／metals 具體 selector 覆蓋的 `font-size:16px!important`；保留 `line-height`、`font-weight` 與 `letter-spacing` 宣告。Run 198 將驗收這個更小範圍的變更；若 computed styles 有任何其他偏移，回復。


## Run 197 驗收：移除 block 48 通用商品名稱規則

- Run 197：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40289217514；artifact 12635378540 已下載並檢查 results.json 與 summary.md。
- workflow success；errors=[]；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽錨點、7 組分頁、來源 disclosure、經濟事件／財報收合與商品分頁／收合互動通過。
- 本輪移除 block 48 的通用 .row b 規則（font-size、line-height、font-weight、letter-spacing）。設計系統與原有特定名稱規則仍使債券、FX、能源、貴金屬名稱三種 viewport 均為 16px／21.6px／700；FX 名稱保持 normal 字距，能源名稱仍保留 -0.4px 字距與 nowrap；商品數值桌機 16px／24px、手機 15px／22.5px，tabular-nums 與 nowrap 不變。所有 4 組 row typography 診斷一致，商品名稱契約通過。
- 下一步不直接刪除 block 48 通用 .row 規則：它還控制 align-items、font-size、line-height，可能影響未被名稱／數值專屬 selector 覆蓋的後代。先盤點 13 個商品列的 direct children 及其 computed styles，確認 .row 規則對哪些元素仍有實際作用，再挑選最小安全遷移單位。


## Run 199 驗收：商品名稱字級宣告移交後的回歸與 direct-child inventory

- Run 198 在測試步驟與 artifact 上傳完成後，因 Run 199 新觸發而被取消；Run 198 artifact 12635466184 的 `results.json` 已檢查，但不把該 workflow 標為 success。Run 199 完整成功：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40289625295；artifact 12636345240 已檢查。
- Run 199 errors=[]；1440、390、320 三種 viewport 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導航、7 組分頁、來源 disclosure、事件／財報收合、商品分頁與收合互動通過。債券、FX、能源、貴金屬名稱皆為 16px／21.6px／700，字距與 Run 196 的基線一致；報價桌機 16px、手機 15px。
- Run 199 candidate-build.html 的 DOM inventory：產業商品區共 13 列，每列只有 3 個 direct children：1 個 `b` 名稱與 2 個 `.r` 報價／漲跌元素；沒有其他直接子元素依賴 row 的繼承字級。13 個名稱由具體 bonds／FX／energy／metals selector 覆蓋；26 個數值由 `.row .r` 覆蓋。
- 下一個最小候選：只移除 block 48 通用 `.row` 的 `font-size:16px!important`，保留 `align-items:center` 與 `line-height:1.5`。直接子元素都有各自的字級規則；Run 200 將檢查所有 computed styles、列高、幾何及互動，若任何繼承樣式變動即恢復。


## Run 200 驗收：移除通用 .row 字級宣告

- Run 200：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40290055427；artifact 12635786678 已下載並檢查 `results.json`、`summary.md`。workflow success，`errors=[]`；桌機 1440、手機 390、窄手機 320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤，主要導航錨點及互動測試通過。
- 本輪只移除 block 48 通用 `.row` 的 `font-size:16px!important`。13 個名稱仍由專屬規則呈現 16px／21.6px／700；26 個數值桌機 16px／24px、手機 15px／22.5px；四組商品列 computed typography 一致，三種 viewport 的產業商品面板高度與前輪相同。
- 下一候選：移除通用 `.row` 的 `line-height:1.5!important`，保留 `align-items:center!important`。DOM inventory 中 13 個名稱由專屬 `b` 規則提供 21.6px 行高，26 個數值由 `.row .r` 提供 24px／22.5px 行高；下一輪需再核對每一種 viewport 的直接子元素行高、列高、面板幾何與互動，若有變化即恢復。


## Run 201 驗收：移除通用商品列 line-height

- Run 201：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40290286474；artifact 12636475788 已檢查 `results.json` 與 `summary.md`。workflow success；errors=[]；1440、390、320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤，主要導覽與互動測試通過。
- 本輪只移除 block 48 通用 `.row` 的 `line-height:1.5!important`。row 容器的 computed line-height 變為 `normal`，但 13 個名稱仍為 21.6px，26 個數值仍為桌機 24px／手機 22.5px；產業商品面板高度與 Run 200 相同（桌機 380px、手機 448px、窄手機 502px），無幾何回歸。
- 下一個候選：移除 block 48 剩餘的 `align-items:center!important`。舊 CSS 的基礎 `.row` 已定義 `align-items:center`，13 個商品列的專屬規則只改欄寬／間距，未覆寫對齊；Run 202 將驗證移除高 specificity 宣告後，實際對齊、列高、面板幾何及互動是否不變。


## Run 202 驗收：移除通用商品列 align-items 覆寫

- Run 202：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40290579471；artifact 12636356546 已檢查 `results.json` 與 `summary.md`。workflow success；errors=[]；1440、390、320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤，導覽與主要互動通過。
- 本輪只移除 block 48 通用 `.row` 的 `align-items:center!important`。原始基礎 `.row` 的 `align-items:center` 接手後，三種 viewport 的商品列／面板幾何與 Run 201 相同；名稱 16px／21.6px，報價桌機 16px／24px、手機 15px／22.5px。
- 下一候選：移除 block 48 的 `.row b` 通用 `line-height:1.5!important`。13 個商品名稱均由更具體的 bonds／FX／energy／metals 規則提供 21.6px 行高；下一輪只移除此一宣告，保留字重與字距，驗收 computed typography 及三種 viewport 幾何。


## Run 203 驗收：移除商品名稱通用行高宣告

- Run 203：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40290849446；artifact 12636627348 已下載並檢查 `results.json`、`summary.md`。workflow success；`errors=[]`；1440、390、320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤，導航、7 組分頁與 disclosure／事件／財報／商品互動均通過。
- 本輪只移除 block 48 的通用 `.row b` 行高宣告。債券、FX、能源、貴金屬名稱仍為 16px／21.6px／700，字距保持 normal；報價桌機 16px／24px、手機 15px／22.5px。產業商品面板高度仍為桌機 380px、手機 448px、窄手機 502px。
- 下一候選：只移除同一規則中的 `font-weight:700!important`，保留 `letter-spacing:0!important`。名稱元素都是 `b`，且目前 computed font-weight 為 700；Run 204 將確認移除重要性宣告後，四類名稱仍是 700、字距不變且沒有版面／互動回歸。若有任何名稱字重改變，立即恢復。


## Run 204 驗收：移除通用商品名稱字重宣告

- Run 204：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40291119029；artifact 12636446632 已下載並檢查 `results.json`。workflow success；`errors=[]`；1440、390、320 三種 viewport 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；7 組分頁、來源 disclosure、經濟事件、財報收合及商品分頁／收合通過。
- 本輪只移除 block 48 通用名稱規則的 `font-weight:700!important`。四類名稱仍由語意元素 `b` 呈現 700 字重，字距維持 normal，名稱字級／行高仍是 16px／21.6px；報價桌機 16px／24px、手機 15px／22.5px，版面幾何不變。
- 下一步：把最後剩餘的 `letter-spacing:0!important` 從 legacy block 48 移入 design-system.css，保留完全相同 selector 與重要性。Run 197 已證明這個字距重設不能直接刪除；Run 205 會驗證遷移後四類名稱的 computed letter-spacing、字級／行高、三種 viewport 幾何與互動。若能源名稱再度出現負字距，立即回復。


## Run 205 狀態：Playwright 安裝停滯，尚無驗收結果

- Run 205：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40291363732 在 `Install Playwright` 超過兩分鐘仍未完成，候選建置與瀏覽器測試未開始，尚無 artifact。此 run 不算通過，也不能判斷 letter-spacing 遷移結果。
- Run 206 將在不改動 CSS 的情況下重跑同一隔離分支版本；若 Run 205 被新觸發取消，只記錄為基礎設施重試。


## Run 206 驗收：將商品名稱字距規則遷移至 design-system.css

- Run 205 在 Playwright 安裝階段停滯並被 Run 206 取代，不算通過。Run 206 完整成功：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40291703706；artifact 12636569083 已檢查 `results.json` 與 `summary.md`。
- Run 206 errors=[]；1440、390、320 三種 viewport 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；7 組分頁、來源 disclosure、經濟事件、財報收合與商品分頁／收合通過。四類商品名稱均為 16px／21.6px／700、letter-spacing normal；面板高度維持 380px／448px／502px。
- 本輪把 `letter-spacing:0!important` 從 legacy block 48 移入 design-system.css 的相同 ID／元件範圍 selector，移除 legacy 名稱規則後，computed style 與 Run 204 完全一致。
- 下一候選：移除 block 48 數值規則中的 `font-variant-numeric:tabular-nums!important`。原始通用 `.r` 規則已設 `font-variant-numeric:tabular-nums`，債券列也有專屬 tabular-nums；Run 207 將檢查 26 個報價／漲跌值在三種 viewport 仍保有 tabular-nums，且不影響其他數值樣式。


## Run 206 驗收：字距規則移至 design-system.css

- Run 206：https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40291703706；artifact 12636569083 已檢查 `results.json` 與 `summary.md`。workflow success；`errors=[]`；1440、390、320 均無水平溢出、缺失面板、重複 ID或新增瀏覽器錯誤；導覽錨點、7 組主要分頁、來源 disclosure、事件／財報收合、商品分頁與收合互動通過。
- 產業商品面板高度維持桌機 380px、手機 448px、窄手機 502px；商品名稱仍為 16px／21.6px／700，報價桌機 16px／24px、手機 15px／22.5px。CSS 規則已在 `design-system.css`，legacy block 48 不再保留名稱字距宣告。
- 注意：此輪的報告記錄四類名稱 computed `letter-spacing: normal`；版面與互動無回歸，但尚未證明這條新規則實際命中所有商品列。不得把「規則搬移」視為字距行為已被完整驗收。後續需先查清 DOM／selector 命中原因，補上明確的字距 assertion，再做其他名稱規則清理。
