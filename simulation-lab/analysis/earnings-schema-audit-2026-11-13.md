# W46 財報資料欄位差異盤點｜2026-11-13

## 證據基準

- Repository：`lion-invlab/lion-invlab.github.io`
- Production branch：`main`
- Main HEAD：`d271d1226ba1c19b431118c9967d57d2bce678fa`
- WR：v5.15
- W46：`data/calendar/weeks/2026-W46.json`
- W46 blob SHA：`85edcefb1f7b86112e55d43a324c6cb5c8c2fdab`
- W46 updated_at：`2026-11-13T04:30:43+08:00`
- schema_version：1
- Events：16 economic / 48 earnings / 129 audit
- Released earnings：42

## 已公布 42 筆欄位覆蓋

| 欄位 | 有值筆數 |
|---|---:|
| EPS actual | 36 |
| EPS estimate | 34 |
| EPS actual basis（自由文字） | 18 |
| EPS estimate basis（自由文字） | 18 |
| Revenue actual | 41 |
| Revenue estimate | 34 |
| Revenue actual basis（自由文字） | 3 |
| Revenue estimate basis（自由文字） | 3 |
| EPS consensus source object | 34 |
| Revenue consensus source object | 34 |
| Financial judgment text | 42 |
| judgment_engine_version | 0 |
| Stock price reaction | 0 |
| Price reaction source | 0 |

## 目前已存比較狀態

| 狀態 | EPS | Revenue |
|---|---:|---:|
| Beat | 15 | 17 |
| Miss | 3 | 8 |
| Null / no directional judgment | 24 | 17 |

22 筆已有 Revenue Beat／Miss 狀態，但沒有 `revenue_actual_basis` 及 `revenue_estimate_basis` 欄位：TTWO、OXY、TDG、CRWV、CTVA、NBIS、HIVE、RKLB、JBS、QBTS、WIX、MRCY、SE、RGTI、FNV、HIMS、TTD、MARA、ASTS、ONTO、SANM、QLYS。

EPS 的 18 筆方向性狀態都有自由文字 basis 欄位，但尚無受控 basis code，故無法以穩定程式規則判斷同義描述是否真正可比。

## Schema 漂移

- W45（schema_version 1）沒有 EPS／Revenue actual／estimate basis 欄位。
- W46（schema_version 1）已新增這些欄位。
- 因兩週檔案同版本卻不同欄位集合，需建立正式 schema version 2 與遷移工具。

## 舊資料 v2 遷移試算（純記憶體，未寫回）

已在隔離分支使用保守 basis mapper，對 main W46 的 42 筆 released records 執行 in-memory migration preview：

| 指標 | Beat | Miss | Incomparable | Pending |
|---|---:|---:|---:|---:|
| EPS | 11 | 1 | 3 | 27 |
| Revenue | 2 | 0 | 0 | 40 |

EPS 可由現有描述與來源證據安全映射的 12 筆：B、FERG、NRG、CEG、KKR、NBIS、RGTI、MNDY、TTD、ONTO、SANM、QLYS。

- TDG、WIX、MRCY：實際值描述為 diluted，但預期值描述未明確 diluted；新規則不擅自視為同口徑，暫列 Incomparable。
- QBTS、HIMS、MARA：預期值 basis 不夠明確，原有方向性判讀不沿用，暫列 Pending。
- Revenue 只有 CEG、MNDY 兩筆具備足夠明確的 GAAP basis 描述可保留 Beat。
- FERG 雖有 actual GAAP net sales basis，但 estimate 只寫 net sales/revenue consensus，未明確 GAAP，故暫列 Pending。
- 其餘 23 筆舊 Revenue Beat／Miss 因缺少結構化 basis，全部退回 Pending；不是判定它們的實際財報表現一定不佳，而是拒絕在不可驗證口徑下宣稱 Beat／Miss。

這項試算證明舊資料庫的部分狀態確實無法通過統一口徑驗證。它只在記憶體中轉換，沒有修改 main JSON。模擬 workflow 另輸出逐公司 `earnings-migration-preview.csv` artifact，供逐筆核對。

Pending 原因再拆解：
- EPS：15 筆缺少可登錄的 basis code；12 筆缺 actual 或 consensus 數值。
- Revenue：32 筆缺少可登錄的 basis code；8 筆缺 actual 或 consensus 數值。
- EPS 的 3 筆 Incomparable 是 TDG、WIX、MRCY，均為 diluted 與 unspecified dilution 口徑差異。
- Revenue 的 2 筆通過是 CEG、MNDY；其餘 40 筆不得在 basis 或數值缺漏時沿用舊方向性狀態。

EPS basis code 待補：TTWO、OXY、CRWV、CTVA、BN、RKLB、JBS、QBTS、SE、ONON、FNV、HIMS、ASND、MARA、VYLR。
EPS actual／consensus 數值待補：PBR、HIVE、SKYD、VOD、VG、GIB、ASTS、KSPI、RBA、CNH、BAP、ALC。
Revenue basis code 待補：B、FERG、NRG、KKR、TTWO、OXY、TDG、CRWV、CTVA、BN、NBIS、HIVE、RKLB、SKYD、JBS、QBTS、WIX、MRCY、SE、RGTI、VG、ONON、FNV、HIMS、TTD、ASND、MARA、VYLR、ASTS、ONTO、SANM、QLYS。
Revenue actual／consensus 數值待補：PBR、VOD、GIB、KSPI、RBA、CNH、BAP、ALC。

## 來源與單位問題

- `consensus_source`、`revenue_consensus_source` 已是物件，可存 name、url、publisher、observed_at、notes、secondary_refs；保留現有來源物件即可。
- `eps_currency`、`revenue_currency` 是單一共用欄位，不能明確分辨 actual 與 estimate 幣別。ONON 以 `CHF actual; USD estimate (not comparable)` 拼接成字串，證明欄位型別不足。
- `revenue_unit` 也是共用欄位，應拆成 actual／estimate unit。
- Actual 與 consensus source 的觀察時間已可存於來源物件，不必重複建立平行來源台帳。
- 股價反應欄位 42 筆皆未填，應列為獨立資料完整性議題，不可混入 EPS／營收 Beat／Miss 修正。

## 04:35 唯一寫入者與排程核查

已確認 WR v5.15 所稱 04:35 唯一 writer 是 ChatGPT automation，不是 GitHub Actions：

- 任務：`TAC 行事曆資料庫｜每日 04:35 預更新`
- ID：`6ae6dff2200c81919ba2cee4db78f8a5`
- Asia/Taipei，週一至週五 04:35；目前 **disabled**。
- 最近一次 run：`3db31e2d-2b68-832f-94ea-c4dda4bbd91e`，11/13 04:30:35 啟動、04:52:16 完成，更新 W46 JSON。
- 該 automation prompt 要求「schema 未變」，且沒有引用唯一判讀引擎，因此不會主動遷移 Schema v2。
- main `.github/workflows/` 沒有 TAC calendar writer；現有 `.github/workflows/main.yml` 是 S&P 500 volatility updater。

因此正式整合前必須同步更新唯一 automation 的執行契約，並完成 42 筆既有資料遷移及回歸；不可另建第二個 JSON writer。

## 結論

目前真正缺少的不只是欄位，而是「受控 basis code、actual／estimate 分離幣別與單位、期間一致性、判讀引擎版本、判讀原因及單一寫入者整合」。現有資料更新時有時填狀態、有時只留 notes；HTML 組裝器又保留數字 fallback，因此形成多個判讀入口。

本次隔離分支已開始建立唯一判讀引擎與只讀 renderer。正式 main 尚未修改。
