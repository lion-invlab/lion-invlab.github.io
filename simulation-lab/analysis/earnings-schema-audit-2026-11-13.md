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

## 來源與單位問題

- `consensus_source`、`revenue_consensus_source` 已是物件，可存 name、url、publisher、observed_at、notes、secondary_refs；保留現有來源物件即可。
- `eps_currency`、`revenue_currency` 是單一共用欄位，不能明確分辨 actual 與 estimate 幣別。ONON 以 `CHF actual; USD estimate (not comparable)` 拼接成字串，證明欄位型別不足。
- `revenue_unit` 也是共用欄位，應拆成 actual／estimate unit。
- Actual 與 consensus source 的觀察時間已可存於來源物件，不必重複建立平行來源台帳。
- 股價反應欄位 42 筆皆未填，應列為獨立資料完整性議題，不可混入 EPS／營收 Beat／Miss 修正。

## GitHub 排程核查

main `.github/workflows/` 目前沒有 TAC calendar writer。現有 `.github/workflows/main.yml` 是 S&P 500 volatility updater，不是行事曆抓取器。WR v5.15 提到的 04:35 唯一寫入排程，其實際 workflow／程式入口目前未在 main repo 找到。此為正式整合阻塞，未經確認不得改正式 JSON 或另建第二個 writer。

## 結論

目前真正缺少的不只是欄位，而是「受控 basis code、actual／estimate 分離幣別與單位、期間一致性、判讀引擎版本、判讀原因及單一寫入者整合」。現有資料更新時有時填狀態、有時只留 notes；HTML 組裝器又保留數字 fallback，因此形成多個判讀入口。

本次隔離分支已開始建立唯一判讀引擎與只讀 renderer。正式 main 尚未修改。
