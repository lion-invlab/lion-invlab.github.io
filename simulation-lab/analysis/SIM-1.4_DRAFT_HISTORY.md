# TAC 投資早報｜SIM-1.4 DRAFT 歷史實證與版本變更紀錄

> 本檔僅保存草案形成期間的歷史 build、QA、測試失敗、修正與版本快照。歷史 SHA／狀態可能已被後續版本取代；不得視為現行規則或最新驗收結論。現況以 `TAC_SESSION_STATE.md`、`TAC_WORK_LOG.md`、最新 Builder 相容性稽核及最新 workflow sidecar 為準。SIM-1.3 在使用者核准 SIM-1.4 前仍是唯一有效規範。

---

### 歷史狀態紀錄（以下為後續實證前的歷史快照，不代表目前狀態）
1. 44 項母版欄位已依兩份 SHA 鎖定母版抽取名稱、定位及固定 href，詳見 A1.1；尚未完成的是每日 44 筆實際行情核對及現貨／CFD來源驗證。
2. Builder 唯一入口尚未核准；build_review_html.py 靜態稽核發現新增 CSS、重建 Fed 區塊、改寫週一收折 DOM，且行情來源檢查未拒絕 CFD quote_type 等不相容風險。GitHub Actions run 44897956591 的 Python compile、Node syntax checks 與 deterministic self-tests 已通過，但未執行 HTML build／DOM diff／Playwright；稽核報告：simulation-lab/analysis/SIM-1.4-builder-compatibility-audit.md。通過母版相容性測試及使用者核准前，不得作唯一入口。
3. QA Contract 與母版 SHA 的相容性已完成靜態對照；Manifest 正式 SHA 與 simulation SHA 均登記一致，QA Contract 已更新為 v1.5 DRAFT 並修正舊 SIM-1.2 引用。兩組母版 ID 集合、style/script 數量一致；DOM／視覺測試尚未執行。報告：simulation-lab/analysis/SIM-1.4-qa-contract-compatibility.md。
4. TAC_SESSION_STATE.md 與 TAC_WORK_LOG.md 均存在於 Repository 根目錄（不是 simulation-lab/ 子目錄）；本次已讀取並將更新本輪進度。11/23 fixture deterministic contract 已通過，但 6 筆 CFD 指數已改列待核實，情緒／FedWatch待刷新，HTML尚未組裝；不得引用先前不一致的「完成」標記。

---

## 版本紀錄
- SIM-1.4 DRAFT（2026-11-21）：首次整併草案；不生效、不覆寫 SIM-1.3。完成條文對照、實證及使用者核准後，才轉為唯一有效規範。


## 2026-11-21 實證更新（仍為 DRAFT）

- GitHub Actions run 44897956591，commit 384dab2fdfd498248f6911746db82f968bb8daf7，conclusion success；Python compile、Node --check（visual_regression.mjs／interaction_smoke.mjs）、11/23 fixture contract、44 欄計數、5+10 新聞、W47/W48 calendar projection、財報 schema／判讀等 deterministic tests 通過。該 push run 未觸發 build／QA-only 模式。
- 11/23 fixture 的六筆 CFD index reference 已由原始數值改為顯示「待核實」，原始參考值另存 rejected_reference；總結／區域評論不再引用這六筆 CFD 漲跌。Workflow 另加 build-level guard，禁止數字型 CFD 指數被渲染為現貨收盤。
- 仍未產生 11/23 審核版 HTML；未執行 Builder build、DOM 前後差異或 Playwright。市場現貨來源與 VIX／MOVE／CNN／FedWatch刷新仍是 review blockers。
- QA Contract v1.5 DRAFT 已鎖定 SHA 26bb1dc456185069753d1c6b9cfa038e97875913；320px 已加入視覺測試程式與 workflow evidence 尺寸清單，但尚無瀏覽器測試證據。


## 財報引擎 1.4.0 與 Renderer 相容性（2026-11-21）

- earnings_judgment.py 已更新為 Engine 1.4.0，公開狀態限制為 beat／miss／inline／pending；幣別、單位、期間明確不相容時映射 pending 並保留 comparison reason。Schema const 已同步 1.4.0。
- 共識快照來源層級已調整為 Yahoo Finance=1、Investing.com=2、LSEG=3、FactSet=4；W47 Yahoo projection 改用 source_level=1。
- Builder 檔案依交接保護範圍未修改，仍保留 legacy incomparable／consensus_divergent label 分支，且無法將「數值存在但不可比」顯示為「比較資料尚未齊備」。因此財報 renderer Gate 仍為 BLOCKED；visual regression 已改成只接受四種狀態並會檢出該標籤錯置。


- 最新 GitHub Actions run 44897956591（commit 384dab2fdfd498248f6911746db82f968bb8daf7）conclusion success；Python compile、Node --check（visual_regression.mjs／interaction_smoke.mjs）及 deterministic self-tests 均通過。此 run 未執行 HTML build、DOM diff 或 Playwright。


## 逐條台帳與財報引擎實作同步（2026-11-21）

- SIM-1.3 逐條處置台帳已補齊 E、F1–F4、F3-補充4–10、G1–G4、H、I，以及 C 第五／六步 Gate 的細項；最新台帳 SHA：1ec0936a6640ffb70b0af94c08b85ca96e903d87。逐條台帳另含 D2、D2-補充、D3.1–D3.17、D4、D5。
- 財報判讀引擎 earnings_judgment.py 1.4.0 SHA：62148064ad08efe72bc5a107a4142d32dffc6c7c；公開狀態固定 beat／miss／inline／pending。共識來源層級 Yahoo Finance=1、Investing.com=2、LSEG=3、FactSet=4。schema 與 deterministic tests 已同步。
- 最新財報引擎 deterministic regression：run 44897795972 success，四狀態判讀、snapshot store 23 tests、schema audit、report-layer status 及 11/23 fixture contract 通過。
- 最新 Node／Python 語法及 deterministic regression：run 44897956591 success。workflow YAML 縮排問題曾造成 run 44897899979 failure，已修正並由 44897956591 驗證成功。
- **明確未完成：** 未執行 build mode／QA-only mode；未產出 11/23 HTML；未完成雙母版 DOM diff、Playwright 互動／視覺回歸；Builder 的 legacy 財報狀態 renderer 仍 BLOCKED，且本輪遵守保護限制未修改 Builder。SIM-1.4 仍是 DRAFT，不得啟用。

## 2026-11-21 晚間實作與測試狀態（DRAFT，尚未生效）

- Builder 已新增 CFD index reference fail-closed guard，並將財報 renderer 狀態收斂為 beat／miss／inline／pending；回歸測試 `test_quote_type_guard.py` 已加入 simulation workflow。
- 11/23 真正 build／DOM artifact validation／Playwright／六種 viewport QA 已由 GitHub Actions run `44899645332` 觸發；記錄時仍 pending，未宣稱通過。
- Builder 仍有已知母版零退化阻塞：額外注入 CSS、重建週一收折 summary DOM、重建 Fed 區塊，以及未完成雙母版逐節點 DOM diff。故目前不得宣告 REVIEW_READY、不得核准 Builder 唯一入口，SIM-1.4 仍維持 DRAFT。
- main、正式母版、Manifest、正式首頁與正式行事曆 JSON 未修改。


## 2026-11-21｜Fed 官員週行程固定槽位修復（尚待 CI／Build QA）

- 使用者明確要求保留 Fed 官員行程功能；因此不刪除功能，而是修復 Builder 與母版脫節問題。
- 週一母版新增固定 `#fed .fc-fomc-weekly-events` 外層、標題、清單、事件原型及空狀態槽位；平日母版同步相同契約。事件原型固定含日期、名稱、影響說明、官方來源連結欄位。Builder 僅深複製母版原型並填入欄位，不再清空／重建外層容器或整張卡片。
- Manifest 已更新 simulation 母版 SHA：Monday `36f29bcb37816348756f9233b60f0429d675a76e`；Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。QA Contract 已新增 Fed 行程槽位及保留結構驗收條款。
- Builder 修正 `normalize_market_label` 的 regex typo：原始 `r"\\s+"` 只會匹配反斜線與 s 字元，無法移除空白；已改為 `r"\\s+"` 的 Python 正確空白 regex（實際原始碼為單一反斜線），並補全形空白測試。
- `test_quote_type_guard.py` 已擴充：兩份母版均需驗證 Fed 行程槽位存在且唯一、已發表／預定事件能顯示、空週顯示明確空狀態、外層節點與事件原型不被破壞。該測試已在 workflow 原有 deterministic self-test step 中執行。
- Builder 修復 commit：`7e9a4fe524880a993f7a15988776627e96e4cc0a`；測試 commit：`1ca9b8da23ce9105c7cf2b04408ca50f0d008ef1`；雙母版與 Manifest／QA Contract 已分別提交。
- 仍未通過 CI 前，不宣稱測試成功；仍須跑真正 Monday／weekday HTML build、DOM 零退化、artifact validation、Playwright 桌面／手機與六 viewport 視覺 QA。SIM-1.4 維持 DRAFT，main／正式首頁未修改。


## 2026-11-21｜母版零退化與 FedWatch 版型邊界修正

- Builder 不再每日追加 summary heading、週一 disclosure、側欄 layout、能源報價、財報卡片及市場名稱字體 CSS；不再清空重建週一上週收折 summary。保留使用者曾核准的單次突發專題 `special_focus` 條件式呈現及其專屬樣式，未寫回母版。
- FedWatch 嚴格沿用母版 2 卡／2 分布段／2 圖例，不再 clone 第三卡、不再以固定 hold/+25bp/+50bp 寫死。超出兩卡可表達的情境數量／類型時，兩卡標待核實、隱藏不完整分布，完整情境保留在既有快照收折區。
- 最新 QA Contract SHA：`26bb1dc456185069753d1c6b9cfa038e97875913`。這些修正仍須經實際 Monday／weekday build、DOM 零退化、Playwright 與六 viewport 視覺驗收；SIM-1.4 仍為 DRAFT。


## 2026-11-21｜Builder 相容性修正進度（仍待 build QA）

- 最新 Manifest SHA：`1496a510d144d340c41b642592675233d5bd2917`；QA Contract SHA：`26bb1dc456185069753d1c6b9cfa038e97875913`。
- Fed 官員行程固定槽位已納入週一／平日 simulation 母版；Builder 以母版事件原型填資料。FedWatch 保留母版兩卡結構，多情境不符合時 fail closed 並在既有快照說明列出完整機率。
- 移除每日 CSS 注入與週一收折 summary 重建；保留 2026-11-11 已核准的單次 `special_focus` 條件式功能作為明確例外。
- CI run `44900780456`（母版 SHA／Fed agenda slot）及 `44900949612`（FedWatch 雙卡與 Builder CSS 清理）success；以上僅為 smoke／deterministic self-tests，不代表 HTML build、DOM diff、Playwright 或視覺 QA 通過。


- 2026-11-21 build request: 使用當前 2026-11-23 Monday fixture，以最新 simulation Builder／母版／Manifest／QA Contract 執行完整 build mode；此為測試請求，不代表 QA 通過或 SIM-1.4 生效。


- 2026-11-21 build retry: run `44901082368` 已通過前置及 deterministic tests，組裝 11/23 Monday fixture 時發現 `observation` 為結構物件（heading/text），Builder 原以字串判斷而中止。已修正 `set_market_observation` 支援字串與結構物件，最終 Gate 亦改比較 `observation.text`；新增 regression test，現觸發完整 build 重跑。此錯誤修正尚待 CI 與 build 結果驗證。


- 2026-11-21 第二輪 build 修正：run `44901183828` 發現 FOMC 活頁中尚有一段舊程式會把母版原有 `.fc-fomc-observation` 清空、改名並重建成第二個 `.fc-fomc-weekly-events`，導致固定槽位檢查出現不完整／重複結構。已移除該舊重建分支，保留母版原有 observation 節點；Fed 官員行程只在固定母版槽位呈現。新增測試確認 observation 節點前後不變。另將槽位缺漏檢查改為明確 None 檢查並回報缺漏名稱。重新觸發 11/23 Monday build。


- 2026-11-21 新聞來源 Gate 修正：上一輪 HTML 組裝成功，但 Playwright interaction smoke 因 Global Focus News 來源網域不符規範而停止。原 fixture 混有 Reuters 直連及 www.investing.com 美站網址，與既定 HK Investing.com／鉅亨網來源契約不符。已以可核對的 HK Investing.com 與鉅亨網文章替換五則新聞，保留 11/20 12:00 之後的時間窗、更新發佈時間與摘要，並按時間排序；此為 simulation fixture 修正，尚待完整 build／互動／視覺驗收。


- 2026-11-21 視覺 QA 修正：run `44901460631` 已通過 HTML build、互動 smoke 與新聞來源 Gate，但視覺回歸發現舊 QA 契約仍要求三張 FedWatch 卡（與母版兩卡相衝突）、舊財報 pending 標籤，以及總結標題字級不一致；另 11/23 Fixture 的核心觀察 heading 寫成「下週」但報告週是本週。已將兩份 simulation 母版既有 CSS 的總結／市場情緒標題統一為 21px（不新增 style 節點、不修改 main），將視覺 QA 改為兩卡／兩分布段／兩圖例及 fail-closed 驗收，更新財報 pending 標籤預期，並修正 fixture heading 為「本週三大觀察焦點」。最新 simulation 母版 SHA：Monday `36f29bcb37816348756f9233b60f0429d675a76e`；Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`；Manifest `1496a510d144d340c41b642592675233d5bd2917`。以上修正尚待下一輪六 viewport QA。


- 2026-11-21 Summary 標題字級第二次修正：前次 21px 規則選錯 selector（誤用 `#overview>.title`，實際母版標題位於 `#overview > section > article.card.bluf > .title`），因此 1440px 計算字級仍為 26px。已改在兩份母版既有最後一個 style block 的精確 selector 設定 21px，沒有新增 style 節點；Manifest 已同步。待重新跑六 viewport。


- 2026-11-21 六項指數來源修正：Investing.com HK 六個同名頁面均標示「即時差價合約」，不可因為有歷史數據表就誤認為現貨。已改用 Investing.com 全球指數歷史頁（Real-time derived）及 DAX Xetra 頁，六筆 quote_type 改為 `cash_index_close`；FTSE 100 11/20 收盤修正為 10,346.34（-1.02%），其餘五項依全球頁歷史列核對。Fixture SHA：`8ecaf343336aac51e76a0958784ea69aada346d6`。新增回歸測試驗證六筆均不再觸發 CFD guard。過期「HTML尚未產出」阻塞已移除；只保留 VIX／MOVE／CNN Fear & Greed／FedWatch 於 11/23 05:25 前刷新一項阻塞。現觸發重新 build 與完整 QA。


- 2026-11-21 Fixture Gate 測試同步：舊 `test_1123_fixture.py` 仍把「六項 CFD／三個 blocker／HTML未產出」當成預期，與已修正 fixture 衝突。已改為驗證六項均為 `cash_index_close`、六組數字與歷史頁來源正確、沒有 CFD rejected_reference，且只剩 VIX／MOVE／CNN Fear & Greed／FedWatch 一項截稿前刷新阻塞。現再次觸發 Monday build。


- 2026-11-21 Weekday full-build regression request: workflow push trigger now accepts `[build-tac-report:YYYY-MM-DD]` to select an exact dated fixture without changing or moving any fixture. Request `[build-tac-report:2026-11-20]` will exercise the 2026-11-20 weekday mother using its date-matched fixture; this is a regression test only, not a new production report.


- 2026-11-21 Weekday regression build follow-up: the 2026-11-20 fixture reached Builder assembly and exposed three missing FactSet fields (`mag7_eps_growth`, `other_493_eps_growth`, `source_url`). The 11/13 FactSet source does not provide a verifiable Mag 7／Other 493 split, so the fixture now marks both split values `待核實` and links the exact 11/13 FactSet PDF; it does not backfill the later 11/20 values. Added a regression test for this pending-state behavior. Re-run weekday build.


- 2026-11-21 Weekday visual QA 修正：2026-11-20 舊 fixture 原本 `key_levels.items=[]`，因此今日觀察第三活頁沒有五檔現金指數 OHLC、支撐／壓力及來源日期，六視窗視覺驗收合理地失敗。已按該報告基準日 2026-11-19 逐筆核對 Yahoo Finance 現金指數歷史頁，補入 Dow／S&P 500／Nasdaq Composite／SOX／Russell 2000 五檔 OHLC，並按同一公式重算 S2/S1/P/R1/R2；新增測試驗證日期一致、來源 URL 與公式結果。沒有沿用 11/20 週一 fixture 的 11/20 OHLC。重新執行 weekday full build。

## 2026-11-21｜完整 build／QA 實證更新（SIM-1.4 仍為 DRAFT）
- 週一 2026-11-23 fixture 已由 run 44904316843 完成真實 HTML build；母版結構比較、獨立 artifact／provenance、44項／行事曆／新聞契約、Playwright 互動與六視窗視覺 QA 全部通過。QA_PASSED，但 review_ready=false，唯一 blocker 為 VIX／MOVE／CNN Fear & Greed／FedWatch須在報告截稿前刷新。審核 HTML blob SHA e6ea8ca01e38e68cc34fe4d74874f1b915e994d6，QA sidecar SHA f7ccad8ea44c578f3a620bf17b79e2c8be347c92。
- 平日 2026-11-20 fixture 已由 run 44902986319 完成真實 HTML build；母版結構比較、artifact／provenance、44項／行事曆／新聞契約、Playwright 互動與六視窗視覺 QA 全部通過；QA_PASSED 且 review_ready=true。審核 HTML blob SHA 0597447d59563d459fc4c913639a07d7ecfcdbbf，QA sidecar SHA 0d18025b4a2a197b1c6c6877ff93b9d6bd8d4bf6。
- 因兩個完整 build 均通過，前文「尚未完成 build／DOM diff／Playwright／六 viewport」僅是當時歷史狀態，不再代表最新狀態。Builder 已具備兩種母版的實際組裝與 QA 證據；但尚未完成報告截稿前情緒／FedWatch刷新，因此不可把週一審核版標為 REVIEW_READY。
- 2026-11-21 20:33 Asia/Taipei 重新讀取 VIX／MOVE／FGScore CNN Provider Index／Investing.com Fed Rate Monitor，數值與來源時間未見更新：VIX 35.89、MOVE 106.31（均為11/20收盤）；FGScore CNN Provider Index 10（as of 11/20 UTC）；FedWatch 12/09/2026 hold 13.6%、升息25bp 86.4%，Updated Nov 21 00:35 EST（台灣13:35）。最後截稿刷新仍待11/23 05:25前執行。
- main首頁、正式母版及正式行事曆JSON保持唯讀；SIM-1.4仍是DRAFT，未生效。


## 2026-11-21｜完整雙母版 Build 後的規則一致性稽核（仍為 DRAFT）

### 已由後續實證更新的歷史狀態
- 本文前段及舊紀錄中「尚未執行 HTML build／DOM／Playwright／六視窗 QA」均是當時狀態，已由 2026-11-21 20:33 的兩次完整 build 更新，不得再當成目前狀態。
- Monday 2026-11-23：Actions run 44904316843 success；HTML build、母版結構契約、artifact/provenance、44 項／行事曆／新聞契約、Playwright interaction smoke、1440／768／412／390／360／320 六視窗視覺 QA 通過。QA_PASSED；review_ready=false，僅剩 VIX／MOVE／CNN Fear & Greed／FedWatch 截稿前刷新。
- Weekday 2026-11-20：Actions run 44902986319 success；相同類別 build／QA 通過。QA_PASSED；sidecar 的資料型 review_ready=true。
- 上述 build 已證明候選 Builder 可在週一及平日 fixture 產生 HTML；不等於候選 Builder 已依本章 8.1 取得「唯一 Builder」核准，也不等於 SIM-1.4 已生效。

### 最新規則／資產 SHA
- SIM-1.3（目前有效規則）blob SHA：`679eae7ba7a40dbad64d15bb448fe53db7d67e09`。
- 本草案 SIM-1.4 blob SHA：以本次 commit 回讀值為準。
- Simulation Manifest SHA：`1496a510d144d340c41b642592675233d5bd2917`。
- QA Contract v1.6 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- Monday simulation mother SHA：`36f29bcb37816348756f9233b60f0429d675a76e`；Weekday：`19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。附錄 A1.1 與 QA Contract A2.1 已同步這兩個目前 SHA；正式母版 SHA 仍各自獨立，不得混用。

### 仍未通過的 SIM-1.4 規則／技術 Gate
1. **Builder 尚未取得唯一入口核准。** 目前候選檔為 `simulation-lab/runner/build_review_html.py`，blob SHA `b36ae1ba2b3fd3dfbde577fb6df6ea926333b3fc`。兩種母版 build 通過只是技術實證；依 8.1，仍須完整提交差異白名單、負向案例、CLI／副作用報告，並由使用者明確核准此路徑與 SHA。
2. **Build provenance 尚未滿足 8.2。** 現行 `TAC_BUILD_PROVENANCE` 有 report date、build commit、template、fixture、builder、calendar SHA，但未記錄 Manifest SHA、QA Contract SHA、SIM-1.3 active rules SHA 及 SIM-1.4 candidate rules SHA；`validate_review_artifact.py` 亦未驗證這四項。現有 build 不可宣稱已通過完整規則／資產 provenance Gate。
3. **Sidecar 的 review_ready 定義尚未與 SIM-1.4 對齊。** workflow 目前主要依 fixture 的 `review_ready_blockers` 計算布林值；它沒有納入 Builder 唯一入口核准狀態。因此 weekday sidecar 的資料型 `review_ready=true` 不可直接解讀為 SIM-1.4 Stage 5／Stage 6 的 REVIEW_READY。
4. **DOM 比對範圍必須精確命名。** `validate_mother_dom_contract.py` 目前逐項比對 style／script 節點與內容、ID inventory，以及總結段落、FOMC observation、Fed agenda wrapper、工具欄、週一收折 summary 等指定穩定節點；它不是全頁逐節點完整 DOM diff。六視窗視覺與 Playwright 通過不會自動補足未比較的 DOM 範圍。
5. **DOM 寫入白名單仍需補齊。** `scripts/tac_html_binding_map.json` 宣告 `mutate_only_text_nodes=true`、`preserve_element_tree=true`、`preserve_attributes=true`；候選 Builder 實際包含清空／重建部分內容節點、來源欄位子節點重建、事件原型 clone、排序與動態卡片產生。必須逐 selector 說明哪些是核准動態槽位、哪些操作合法，並裁決 binding map 是需同步更新的有效契約或已退役的舊附件；不可讓兩份契約互相矛盾。
6. **Fed 官員行程必須保留。** 候選 Builder 現在使用母版既有 `.fc-fomc-weekly-event-template` clone，更新既有 list，保留外層 wrapper／title／empty-state；此項有兩種母版 build 與 DOM contract 測試證據。後續修正不得移除 Fed 官員週行程，也不得清空重建 Fed 外層區塊。
7. **週一上週收折外層必須保留。** 動態事件清單可依核准槽位更新，但 `details.last-week-calendar-collapse`、`details.last-week-earnings-collapse` 及其 summary 必須保持母版結構與預設收折狀態。

### 下一個實作順序
1. 先補 Builder 的 provenance 欄位及獨立 validator：Manifest、QA Contract、active SIM-1.3、candidate SIM-1.4 的路徑／blob SHA 必須從 build commit 讀回核對。
2. 再補完整 DOM write allowlist／契約一致性測試，明確界定動態卡片及來源連結槽位；擴充 DOM validator 的檢查範圍或明確限定其名稱與驗收聲明。
3. 修正 sidecar 狀態欄位，分開 `QA_PASSED`、資料完整度、`SIM14_BUILDER_APPROVED`、`SIM14_REVIEW_READY`；Builder 未獲使用者核准前不得標示 SIM-1.4 REVIEW_READY。
4. 兩種母版重新跑完整 build／artifact validation／Playwright／六視窗 QA；完成後提交候選 Builder SHA 與證據，等待使用者核准。SIM-1.3 持續有效，SIM-1.4 持續 DRAFT。


## 2026-11-21｜S&P 500 Dashboard 與市場情緒 DOM 保留修正（待 CI）

- 再次檢查兩份實際母版後，確認舊 Builder 曾對 `#sp500-earnings-health` 執行 `health.clear()`，再以六張固定卡及 inline style 重建；這違反 QA Contract F 的母版 Dashboard 保留要求。現已改為只更新母版既有文字槽位，週一保留 4 張卡、平日保留 3 張卡，並保留原有容器、卡片、排列、欄數及 inline style。
- 舊 Builder 對市場情緒最後一張核心解讀卡執行 `interpretation.clear()`，會移除原有 body wrapper 與 inline style。現改為只更新既有 body text node，保留 label／body wrapper。
- `validate_mother_dom_contract.py` 現已將 `#sp500-earnings-health` 與 `#sentiment .sent > .sbox:last-child` 納入穩定 DOM 比對，並比較兩區 inline style；新增雙母版回歸測試 `test_earnings_health_dom_preservation.py`，已接入 workflow。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`8757c7dc3f218908a8d314156d2d6f06406e12ca`；雙母版 regression test SHA：`d66f50ef5ce3fd3ab3c8edecdecb23be9e3843aa`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`。
- 以上為程式修改已提交，尚未有這一版 Builder／validator／test 的完整 CI 結果。下一次完整 build 必須同時驗證 Monday 4 卡、Weekday 3 卡、兩區 DOM／inline style 不變、來源連結與日期更新，並通過 provenance validator、互動及六視窗視覺 QA。
- 此修正不代表 Builder 已取得唯一入口核准；SIM-1.4 仍是 DRAFT，SIM-1.3 仍有效。


## 2026-11-21｜Dashboard 資料欄位回歸修正（待重跑）

- 首次執行新 DOM 保留版本的 run 44905304475：雙母版 Dashboard／市場情緒 DOM-preservation deterministic tests 均通過；真正 Monday build 在最後 FactSet 資料 Gate 失敗，因新 renderer 未將 fixture 的 Mag 7／Other 493 成長值寫入現有分析文字槽位。
- 同一 Gate 原先要求 `.factset-source-link` class，但 Weekday 核准母版的來源連結沒有該 class；此要求會迫使 Builder 改寫母版 class，與零退化原則衝突。
- 已修正：Monday 既有「正面」文字槽位加入 Mag 7／其他 493 數值；FactSet 來源驗收改檢查母版既有 `details a` 連結及其 href，不要求新增 class。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`。以上修正尚未經新一輪完整 build 驗證；run 44905304475 保留為失敗歷史證據，不可改稱通過。


## 2026-11-21｜市場評論與 FactSet 欄位保留修正（待完整重跑）

- run 44905304475 在新 Dashboard DOM-preservation deterministic tests 通過後，於最後 FactSet Gate 失敗：Mag 7／Other 493 數值尚未寫入保留的母版文字槽位。後續已在既有 Monday／Weekday「正面／保留」文字槽位補入 Mag 7、Other 493 及 Forward 12M P/E，不增加卡片、不改變欄位排列。
- FactSet 來源連結 Gate 改為驗證母版既有 `details a` 的 href；不再要求平日母版原本不存在的 `.factset-source-link` class，避免為通過 Gate 而改寫母版屬性。
- `set_market_observation` 已由清空重建改為只更新母版既有直接子節點 `b／br／text`；移除前置的冗餘 destructive `set_text(reason,...)`。DOM validator 現比對所有 `.market-reason` 子樹及 inline style；雙母版回歸測試亦涵蓋市場評論槽位。
- QA Contract 已更新為 v1.7 DRAFT，新增市場評論、Market Sentiment 核心解讀及 S&P 500 盈餘 Dashboard 的 DOM／inline style 保護條款。QA Contract SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；Manifest SHA 仍為 `1496a510d144d340c41b642592675233d5bd2917`；雙母版 SHA 仍為 Monday `36f29bcb37816348756f9233b60f0429d675a76e`／Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`52404ce2dc6881566ea998cc84e7af030dff43ba`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；雙母版 DOM regression test SHA：`6ab733532893a17faf8814d677e11d81fa08e6fe`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`。
- 上述修改仍須在同一個最新 build commit 重新跑 Monday 與 Weekday；不得引用早一版 run 的成功作為本版通過證據。SIM-1.4 仍為 DRAFT，候選 Builder 尚未取得唯一入口核准。

## 2026-11-21｜Builder 母版零退化修正與回歸狀態（持續 DRAFT）

### 已完成的程式修正
- Fed 官員週行程功能明確保留。週一／平日母版均有固定外層、標題、清單、原型及空狀態槽位；Builder 只複製原型並填入事件，不清空重建外層。
- FedWatch 保留母版兩張機率卡、兩段分布及兩個圖例；多情境或不符合兩卡規格時 fail closed，完整情境保留在既有快照說明，不 clone 第三張卡。
- 移除 Builder 的每日版面 CSS 注入；summary 總結改為填入原有粗體標籤／換行／文字槽位，槽位數不符即停止，不再 clear 後重建。
- S&P 500 盈餘健康度 Dashboard 改為更新母版既有文字槽位，週一維持 4 張卡、平日 3 張卡；市場情緒解讀保留原有 label/body wrapper 與 inline style。
- 市場評論改為更新母版既有直接子節點（粗體標題、換行、文字），不清空重建；缺少既有槽位即停止。
- CFD quote_type 防錯保留；已修正空白正規化雙重跳脫錯誤。

### 最新程式與契約版本
- Builder：simulation-lab/runner/build_review_html.py，目前 blob SHA e03e4af65007a6cfdd3c241a1219ea28d42cbabf。
- DOM validator：simulation-lab/runner/validate_mother_dom_contract.py，目前 blob SHA 52404ce2dc6881566ea998cc84e7af030dff43ba。
- FactSet／市場情緒 DOM regression：simulation-lab/runner/test_earnings_health_dom_preservation.py，目前 blob SHA 6ab733532893a17faf8814d677e11d81fa08e6fe。
- QA Contract：版本 1.7 DRAFT，blob SHA f6848d21286f63c4eef11682eedd8825b5fd3aad；Manifest 已登記兩份 simulation 母版 SHA，未修改 main 正式母版。

### 實際驗收紀錄與未完成項
- 2026-11-23 Monday build run 44905408554 曾完成 HTML 組裝、deterministic tests、Playwright 互動、六種 viewport（1440／768／412／390／360／320）、artifact validation、44 項行情結構驗收及母版 DOM 比對；該次 QA sidecar 為 QA_PASSED。
- 該次 sidecar 的 review_ready=false：VIX、MOVE、CNN Fear & Greed、FedWatch 快照仍早於 2026-11-21 17:57:31；必須在 2026-11-23 05:25 截稿前重新讀取並更新時間，不能把結構 QA 通過當成資料完整。
- 上述 run 使用 Builder SHA 45bafe4c8e346fe1c51d1eb342c114d8009fc43c；其後又新增市場評論 DOM 保留修正，故目前最新 Builder SHA 尚須重新跑 Monday／weekday 完整 build 與 DOM validator。
- 2026-11-20 weekday 曾有完整 build／六視窗 QA 通過紀錄，但後續增加固定 DOM validator、FactSet 欄位顯示與市場評論 DOM 保護；最新 Builder／validator 組合的 weekday 完整回歸仍待重跑。
- SIM-1.4 不得標示完成或啟用；SIM-1.3 仍為唯一有效規範。正式首頁、main、正式母版及正式行事曆 JSON 均未修改。


## 2026-11-21｜市場評論槽位與 CNN 分數 DOM 保護（待最新 CI）

- 舊通用 `set_text()` 會直接 `node.clear()`，若目標有子元素便可能刪除母版 DOM。現已改為 fail-closed：遇到子元素即拒絕破壞性寫入；資料更新必須明確定位 leaf text node。
- CNN Fear & Greed 分數原先寫入父層 `.fg6-score`，會移除 `.fg6-score-main` 與固定 `.fg6-outof`（/100）子節點。現改為只更新 `.fg6-score-main`；validator 比對分數 wrapper 結構與 inline style。
- 市場評論 helper 已改為保留母版直接子節點 `b／br／text`；測試範圍限定為 Builder 真正會更新的三區市場評論、產業／債券／匯率／商品評論，以及今日市場觀點槽位。validator 仍比對全頁所有 `.market-reason` 的結構與 inline style。
- run 44905555873（commit cebd527）在 deterministic tests 階段失敗：測試曾過度涵蓋所有 `.market-reason`，包含 Builder 不會寫入的舊節點。已將測試範圍收斂至 Builder 實際寫入的母版槽位；該 run 不可算通過。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`86ad959871e9e9ecfbfd32644b06d3f34d2e05ae`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；DOM regression test SHA：`70cb06d15ed736bb7dc31b4b42455937d1566f6a`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 44905408554 曾在較早版本通過完整 Monday build，但該版本未包含後續市場評論與 fail-closed CNN 更新；本版仍須以最新 commit 重跑 Monday／Weekday，不得沿用舊 run 當成最終驗收。


## 2026-11-21｜最新測試修正與完整回歸待辦

- run 44905688058 的雙母版 Dashboard／情緒 DOM 測試已通過；失敗點是另一支 quote-type regression test 使用了不符合母版的簡化 `<div><span>` 節點，卻要求 updater 自動建立 `b`。已將該測試改為使用核准母版的 `b／br／text` 結構，並加入非母版結構必須 fail-closed 的負向案例。
- 市場評論回歸測試已限定於 Builder 真正會更新的區塊；對沒有粗體標題、但有既有文字槽位的合法評論節點，依現有 DOM 更新文字而不新增標籤。DOM validator 比對所有 `.market-reason` 的子樹與 inline style；重複的同一比對區塊已合併。
- Builder 通用 `set_text` 現在遇到子元素即拒絕清空；CNN 分數只更新 `.fg6-score-main`，保留 `/100`；市場觀察、Market Sentiment、S&P 500 Dashboard 均只更新既有節點。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；Dashboard／評論 DOM test SHA：`f4b2be83bd6efb0eeb93f9b08bf2f43f3c2d33ab`；quote-type test SHA：`e83ca9011ec6a03672b18eb2522ee633b6fc74ab`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 本版仍需重新跑 deterministic tests、Monday build、Weekday build、母版 DOM、provenance、Playwright、六視窗 QA。任何一項失敗均不可標示 QA_PASSED／SIM-1.4 REVIEW_READY；SIM-1.4 仍未生效。


## 2026-11-21｜來源揭露連結保留修正（待最新完整 CI）

- run 44905791885 已通過 deterministic tests，進入 HTML build；在更新市場行情來源揭露時，fail-closed `set_text` 正確阻止清空含有來源連結的 `.source` 容器。這證明 guard 有效，也暴露一個原先未列入白名單的來源文字槽位。
- Builder 已改用 `set_text_preserving_child_elements` 更新來源說明文字，保留母版既有 anchor／href／子元素；新增回歸測試確認來源連結仍存在且 DOM／樣式不變。
- 最新候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；Dashboard／市場評論／來源連結 regression test SHA：`b0fc64650be06d2a4f64435e2d7c9930f4852391`；quote-type test SHA：`4aa2214f175cd2a8bb1970a648fc8512f0c527a2`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；workflow SHA：`12eeeff5edbfac2486785f159bb95eb6b934420d`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 本次修改尚未完整驗收。最新 build 必須確認 fail-closed guard 不再阻止合法的來源揭露文字更新，同時不刪除既有連結；再完成 Monday／Weekday build、DOM、provenance、Playwright、六視窗 QA。


## 2026-11-21｜來源揭露文字節點保留的第二次修正（待重跑）

- run 44905957224 在來源連結 regression test 失敗：當時版本雖保留 anchor，但將來源容器內其他直接文字節點改成空字串，仍改變 DOM text-node 結構。
- 最新 helper 已改為只更新第一個核准文字槽位，保留後續所有文字節點及所有 child elements；不再移除或清空其餘文字節點。回歸測試同時比對 DOM skeleton 與來源 anchor href。
- 本次為 fail-closed／DOM-preservation 原則的修正，不可只因 anchor 仍存在就判定結構完整。必須在最新 commit 重新執行 regression tests 與完整 HTML build。


## 2026-11-21｜來源尾端文字節點測試口徑修正（待重跑）

- run 44906001227 的來源 helper 回歸測試失敗，原因是測試仍期待舊尾端文字被刪除；最新規則是保留全部既有文字節點與 anchor，故實際輸出應保留「舊尾註」尾端文字。已修正測試預期值，不再要求移除尾端節點。
- 最新 quote-type regression test SHA：`bf13d2b86dd1119132bcf214daf4bc57e0b5e415`；候選 Builder SHA：`e03e4af65007a6cfdd3c241a1219ea28d42cbabf`。本次修正仍需重新跑 deterministic tests 及完整 build。


## 2026-11-21｜空白來源槽位的非破壞式補入（待最新 CI）

- run 44906103379 的 deterministic tests 已通過，HTML assemble 階段發現部分母版 `.source` 容器只有既有 anchor，沒有直接文字節點。fail-closed helper 正確拒絕破壞式覆寫，但原先沒有處理「空白文字槽位、子元素仍存在」的情況。
- 最新 helper 若有直接文字節點，只更新第一個並保留其他文字節點／子元素；若容器只有 anchor、沒有獨立文字槽位，則回傳 False 並完全不改動，不新增節點、不覆蓋來源連結。
- 新增「只有既有來源 anchor」的回歸案例，驗證說明文字插入後連結仍保留。最新 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；DOM regression test SHA：`61a969a8504aa7e219ac3f98d2614bba7f92cf81`；quote-type test SHA：`bf13d2b86dd1119132bcf214daf4bc57e0b5e415`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`。
- 此修正尚未經新一輪 build；必須確認 source-only／source-with-link／empty-source-with-link 三種情況皆通過，然後才可繼續後續 DOM／視覺 Gate。


## 2026-11-21｜link-only source disclosure 最終口徑（待最新 CI）

- run 44906194763 顯示 link-only source regression test 不應要求 Builder 新增文字節點。母版若只有來源 anchor 而沒有獨立文字槽位，Builder 必須完全不動該容器；報告日期由既有 `.tab-panel-meta` 提供，來源 anchor 仍保留原 href／label。
- 最新 `set_text_preserving_child_elements` 採此口徑：有直接文字槽位才更新；只有 anchor 時回傳 False 並保持 DOM 完全不變。雙母版 regression test 與 quote-type test 已同步。
- 最新候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；Dashboard／市場評論／來源 regression test SHA：`07a5f8a05a0b8518223fc79fe507a4a70cfe3111`；quote-type test SHA：`a3569c0355c29278bddc0bc9ec551471036cf586`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；QA Contract v1.7 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- 上述最新 SHA 尚未取得完整 Monday／Weekday CI 通過證據。SIM-1.4 仍為 DRAFT，Builder 未獲唯一入口核准。


## 2026-11-21｜最後一處 market-reason 破壞性寫入修正（待重跑）

- run 44906262981 的 deterministic tests 通過，HTML assemble 在 global market panel 的另一處舊程式碼失敗：仍以 `set_text(reason,...)` 清空 `.market-reason`，觸發 fail-closed guard。
- 最新 Builder 已將此最後一處寫入改為 `set_market_observation(reason, "", ...)`，只更新既有市場評論標題／文字槽位，不清空節點。
- 最新 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；quote-type test SHA：`a3569c0355c29278bddc0bc9ec551471036cf586`；Dashboard／市場評論／來源 regression test SHA：`07a5f8a05a0b8518223fc79fe507a4a70cfe3111`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`。
- 本版尚未完成 Monday／Weekday build；須再執行全套 deterministic tests 與 HTML assemble，確認不再有未核准的 destructive text write。

## 2026-11-21｜最新 Builder SHA 完整 Monday 驗收（weekday 待驗）

- 最新 Builder SHA：c4c24c03625b3532f48362d7235755a8fa55850f。
- 最新 DOM validator SHA：e202923cb0d31a8381c238884203599a2937de77。
- 最新 FactSet／情緒 DOM regression SHA：07a5f8a05a0b8518223fc79fe507a4a70cfe3111。
- 最新 CFD／Fed／summary／市場評論 regression SHA：a3569c0355c29278bddc0bc9ec551471036cf586。
- 2026-11-23 Monday 完整 run 44906325728 已成功：deterministic tests、HTML assemble、Playwright 互動、approved-mother visual regression、DOM contract、artifact provenance、44 項行情／新聞結構 Gate、QA-passed HTML persist 均 PASS；六視窗為 1440／768／412／390／360／320。
- 11/23 sidecar QA_PASSED、review_ready=false；VIX、MOVE、CNN Fear & Greed、FedWatch 的來源快照仍須在報告截稿前刷新。這是資料 freshness Gate，不是 Builder／DOM Gate 失敗。
- 現在只剩最新同一組 Builder／DOM validator SHA 的 weekday 完整 build 尚未重跑；本次狀態更新將觸發 2026-11-20 weekday regression。
- SIM-1.4 仍是 DRAFT，SIM-1.3 仍有效；不得部署、不得修改 main／正式首頁／正式母版／正式行事曆 JSON。


## 2026-11-21｜繁中字型視覺 Gate（QA Contract v1.8 DRAFT）

- 先前 run 44906329420 的技術組裝、母版 DOM、互動及六視窗比較已通過，但實際 screenshot 中繁體中文字形呈方框；因此該輪視覺結果不可作最終視覺驗收，且推送審核版時遇到 simulation branch concurrent push race，未寫回 preview。
- QA Contract 更新至 v1.8 DRAFT，要求 CI 安裝 Noto CJK、確認 `fc-match "Noto Sans TC"` 解析至 Noto Sans CJK，Playwright 等待 `document.fonts.ready` 並用 `document.fonts.check` 驗證繁中字型可用；缺字即視覺 QA 失敗。
- Workflow 已加入 `fonts-noto-cjk` 安裝與 fontconfig 檢查；`visual_regression.mjs` 已加入字型檢查及 font audit 輸出。
- QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；DOM regression test SHA：`07a5f8a05a0b8518223fc79fe507a4a70cfe3111`；quote-type test SHA：`dc115b0638f3f6772eac7b28ca32a8fed867b020`；visual regression SHA：`d9712593f49dc712d248d262a0e6bff92fdd4720`；workflow SHA：`eb95ab66db37dded42d49d3e82386223b6d27265`。
- 此版尚未執行完整 Monday／Weekday build；字型 Gate 與新版本 provenance 必須以最新 build commit 驗證。SIM-1.4 仍是 DRAFT，Builder 未獲唯一入口核准。


## 2026-11-21｜Noto Sans TC fontconfig alias 修正（待重跑）

- run 44906661785 確認 `fonts-noto-cjk` 已安裝，但 Ubuntu fontconfig 的 `Noto Sans TC` family name 未自動 alias，`fc-match "Noto Sans TC"` 回退為 DejaVu Sans，因此字型 Gate 正確失敗。
- Workflow 現改為先確認 `Noto Sans CJK TC` 字型存在，再寫入 user-level fontconfig alias：`Noto Sans TC → Noto Sans CJK TC`，重建 cache 後再次驗證 `fc-match`。Playwright 仍需通過 `document.fonts.check` 才可截圖。
- 最新 workflow SHA：`eb95ab66db37dded42d49d3e82386223b6d27265`；QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`。
- 本次 alias 修正尚未經 CI 驗證；在 fontconfig、Playwright 字型檢查及六視窗截圖全部確認正常前，不得宣稱視覺 QA 通過。


## 2026-11-21｜Weekday 母版檔名映射修正（待重跑）

- run 44906846280 的 Weekday fixture 已完成 HTML assemble、Playwright interaction 與六視窗視覺／字型測試；母版 DOM 驗收未能開始，因 workflow 將 `TEMPLATE_KEY=weekdays` 直接拼成 `weekdays-mother-template.html`，但 manifest materializer 實際輸出檔名是單數 `weekday-mother-template.html`。
- 已在 build 與 qa-only 兩條路徑新增明確映射：`monday → monday-mother-template.html`；`weekdays → weekday-mother-template.html`，並以 `MOTHER_FILE` 傳給 DOM validator。這是路徑錯誤修正，不是 DOM mismatch 通過證據。
- 最新 workflow SHA：`eb95ab66db37dded42d49d3e82386223b6d27265`；候選 Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`。
- Weekday 母版必須在此映射修正後重新跑完整流程；不得沿用 44906846280 的失敗 run 當成通過。


## 2026-11-21｜雙母版實證後的規則一致性修訂（仍為 DRAFT）

1. **實際雙母版 build 已通過，但版本基準尚需統一重跑。** Monday run 44906803821 使用 candidate rules blob `9d0b2fed694ffe09724f310514f3a4f759b9b956`；Weekday run 44907253127 使用較新的 candidate rules blob `1b808c093bfd6186febdca58021589026ef23700`。兩者 Builder／Manifest／QA Contract 相同，但規則 SHA 不同，因此不可宣稱是同一個規則版本的雙母版驗收。凍結本次草案內容後，必須以同一 candidate rules SHA 重跑 Monday 與 Weekday。
2. **Provenance 四項規則／資產 SHA 已實際驗證。** `validate_review_artifact.py` 會從不可變 build commit 讀回並驗證 Manifest、QA Contract、active SIM-1.3、candidate SIM-1.4 的路徑與 blob SHA；sidecar 也分別記錄四項 SHA。舊稽核中「缺少四項 provenance」已過時。
3. **狀態欄位已分層。** Sidecar 同時記錄 `status`、`review_ready`、`data_review_ready`、`sim14_builder_approval`、`sim14_review_ready`。其中舊 `review_ready` 是資料型 readiness，不是 SIM-1.4 完整交付狀態；Builder 未經使用者核准時，`sim14_review_ready=false`。第 9.1 已補上定義。
4. **DOM validator 的聲明範圍須精確。** 現有 validator 驗證 CSS／JS、ID inventory 及列明的穩定母版結構，不是全頁每一個動態子節點的 byte-for-byte DOM diff。每日動態事件卡／財報卡／行事曆清單只可在核准槽位內更新；外層 wrapper、prototype、details／summary、來源連結及母版互動節點必須保留。
5. **舊 `tac_html_binding_map.json` 不再作活動授權。** 其 `mutate_only_text_nodes=true` 與目前經 QA Contract 定義的受控動態卡片 clone／list item refresh 並不完全相容。現階段將它標為歷史映射，不得單獨授權 Builder 寫入；若未來要恢復使用，必須先逐 selector 同步更新並納入同一 QA Contract。
6. **六視窗與字型條件一致。** 本文第 9.2 已補入 320px，並要求實際驗證繁體中文字型；QA Contract v1.8 DRAFT 同樣要求 Noto Sans CJK TC／fontconfig alias 與 Playwright 字型檢查。
7. **Fed 官員週行程不得刪除。** Builder 使用母版固定 wrapper、title、list、prototype、empty-state；只替換動態 event instances 並填入官方來源連結。FedWatch 仍固定兩卡兩段，不得擅自改回三卡。
8. **核准狀態不變。** SIM-1.3 仍為唯一現行有效規則；SIM-1.4 仍為 DRAFT。候選 Builder 尚未獲使用者明確核准為唯一入口；本修訂不授權 main、正式首頁、正式母版或正式行事曆 JSON 的修改。


## 2026-11-21｜凍結候選規則版本後的雙母版同版重跑

- 本次一致性修訂已完成；以本 commit 的 candidate SIM-1.4 blob SHA 作為雙母版同版回歸基準。
- 先跑 Monday 2026-11-23，再跑 Weekday 2026-11-20；兩次 build 必須讀取同一 candidate rules SHA、Builder SHA、Manifest SHA、QA Contract SHA。若任一規則／技術資產在兩次 run 之間變更，先停止並重新凍結版本，不得把不同 SHA 的 run 合併宣稱為同版雙母版驗收。
- 本節只規定 simulation branch 的回歸順序，不授權 SIM-1.4 生效或正式資產修改。
