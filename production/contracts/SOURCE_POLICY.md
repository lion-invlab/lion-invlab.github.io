# SOURCE POLICY v1.2

## Market data
- For every field not supplied by a valid user screenshot, Stage 2 opens the exact approved Investing.com instrument page in a browser, navigates to Historical Data, and reads the actual historical table row for the target trading date.
- Do not substitute search snippets, Yahoo Finance, third-party APIs or unapproved sources for the required Investing.com historical-page read. Do not bypass Cloudflare, login, robots or other access restrictions.
- Maximum concurrency is four distinct Investing.com Historical Data pages. Each page is independently identified and observed. Do not shorten page timeouts or increase concurrency to evade access controls.
- A valid user screenshot identifying instrument, date and value has priority across all 44 items, not only MOVE. Adopt its supplied fields without re-reading or overwriting them. Read the official Investing.com history page only for required fields missing from the screenshot. For screenshot-supplied fields, report source display remains the relevant Investing.com product page; never expose “依使用者截圖” in the report. For the approved MOVE TradingView fallback, the source disclosure must identify TradingView as the actual evidence provider and must not mislabel it as Investing.com.
- Record screenshot evidence truthfully as USER_PROVIDED_SCREENSHOT; do not claim browser page read. Field-level evidence is mandatory for mixed screenshot/browser inputs.
- Browser page/table inaccessible => TOOL_READ_FAILURE. Page/table readable but no target-date row => SOURCE_NO_DATA. Never conflate.
- First pass covers all 44. Lock values as soon as identity/date/field/quote type/evidence match. Later passes only resolve unresolved rows; never re-fetch locked values without correction evidence.
- Do not use disabled repository collectors as production quote sources.

## Market universe
44 fixed items: 17 global indices including SOX; 11 sector ETFs XLE, XLF, XLK, XLI, XLY, XLP, XLU, XLV, XLB, XLRE, XLC; 2Y/10Y/30Y Treasury yields; DXY, USD/TWD, EUR/USD, GBP/USD, AUD/USD, USD/JPY; WTI, Brent, Gold, Silver; VIX, MOVE, CNN Fear & Greed. Exact item identities and selectors are taken from selected mother template and its Manifest. FedWatch is separate.

## Special instruments
- SOX: Investing.com HK historical page; Yahoo ^SOX only as approved backup/cross-check.
- VIX: Investing.com HK historical page; Cboe official history cross-check; Yahoo ^VIX backup.
- Nikkei 225: use only the pinned Investing.com Nikkei 225 Historical Data page (`https://www.investing.com/indices/japan-ni225-historical-data`) and read its actual dated table row for Price, Open, High, Low and Change %. Do not switch to Nikkei Indexes official pages, Daily Summary, Yahoo Finance or third-party APIs. Record the product identity and quote wording exactly as Investing.com displays them; do not relabel a provider-derived/CFD quote as an exchange-official cash-index value. If the page's instrument identity does not match the fixture's required Nikkei 225 identity, record the mismatch explicitly rather than substituting another source.
- MOVE only: (1) a valid current-run user screenshot takes priority; (2) otherwise read the pinned Investing.com MOVE Historical Data page; (3) if the page is inaccessible or the target-date row is unavailable, use TradingView's exact ICE:MOVE instrument page (`https://www.tradingview.com/symbols/ICE-MOVE/`) as the first backup and accept it only when the dated daily close and required change field are directly readable and independently evidenced; (4) if TradingView also lacks a verifiable target-date observation, retain the appropriate failure/no-data state. Do not substitute a different MOVE-like instrument. The TradingView backup must be recorded as `TRADINGVIEW_HISTORICAL_PAGE` with `source_role=BACKUP_1`; never relabel it as Investing.com. This exception applies only to `risk.move`, not to any of the other 43 market rows.
- CNN Fear & Greed: CNN Business dashboard current score and Last updated first; Previous close is not current score. Then CNN graphdata endpoint, FGScore CNN Provider Index, Financial Context CNN Tracker as specified. No third-party self-estimated score.
- FedWatch: read Investing.com Fed Rate Monitor at report production time. CME FedWatch is methodology/cross-check only; do not label Investing.com data as CME official.

## Quote identity
Distinguish cash index, CFD, futures, continuous contract, settlement and Last. Do not use a CFD as official cash-index close. Futures require exchange, product code, expiry month, date and quote type. Public commodity labels stay short (WTI 原油期貨, Brent 原油期貨, 黃金期貨, 白銀期貨); full contract detail belongs in the existing source disclosure.

## Calendar and earnings
Stage 3 reads only main weekly JSON. Yahoo Finance Average Estimate is first-choice earnings consensus source; fallback order per metric is Investing.com, LSEG I/B/E/S, FactSet Estimates. EPS and Revenue are selected independently; stop at first available valid average estimate for each metric.

## News
Global Focus News target 5, Market Hot Headlines target 10. Use original publication time, timezone and canonical HTTPS URL. Shared report cutoff window applies; do not use page updated time as original publication time.
