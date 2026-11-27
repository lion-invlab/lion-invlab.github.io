# Stage 2 input handoff — Main R2

## Run-scoped input only

All mutable Stage 2 inputs belong inside the exact Stage 1 directory:

`production/runs/<run_id>/`

Required:
- `run-context.json`
- `report-data.json`
- `stage1-receipt.json`
- `market-history-web-observations.json` (exactly 44 rows)
- `stage2-chatgpt-handoff.json` (package manifest)

Optional, only when applicable:
- `cnn-fear-greed-observation.json`
- `market-screenshot-observations.json`
- original screenshot bytes stored inside this same Run directory

The package manifest must bind `run_id`, `report_date`, `trading_date`, `stage1_receipt_sha256`, `run_context_sha256`, `stage1_fixture_sha256`, capture timestamp, each fixed filename and its SHA-256. It must include the SHA-256 inventory of original screenshot bytes. Use the exact filenames and fields defined in `production/contracts/HANDOFF_CONTRACT.md`.

## Direct source observations

The 44-row bundle must contain one observation for each fixed market row, opened directly from the designated Investing.com Historical Data page unless the applicable fields were already supplied in a valid same-day screenshot. `CHATGPT_WEB_SEARCH_RESULT_HISTORICAL_PAGE` is not accepted; a search summary is not a page observation. Every row records exact URL, instrument identity, target and observed dates, field labels, table row text, capture/finish timestamps and direct page reference/line range.

CNN Fear & Greed is separate because it is a current dashboard, not an Investing.com historical price table. Record Current Score, Current Band, page Last updated timestamp and direct page reference. Never use CNN previous_close as the current dashboard score. If CNN's official dashboard is unavailable, preserve the approved provider fallback tier and date-mapping disclosure; do not invent a CNN observation.

## Screenshot priority

A screenshot is eligible only when its report_date, trading_date, instrument identity, approved source URL, field labels, original bytes and SHA-256 are all present and verifiable. Screenshot-provided fields take priority and are not re-queried. Missing fields continue through the approved direct Investing.com Historical Data read. Do not reuse a prior-day screenshot or a screenshot from another Run.

## Prohibited fallback

The Stage 2 Runner does not open market pages. If a ChatGPT observation bundle is absent, malformed, stale, belongs to another Run, or fails any SHA check, the receiver rejects it and stops. It must not start Playwright, browser_verify_market_history.py, TradingView MOVE backup, or another substitute reader. Cloudflare is never bypassed. If a page loads but its history table is unreadable, record TOOL_READ_FAILURE; do not relabel it SOURCE_NO_DATA.

## Completion marker

ChatGPT commits the complete Run-local bundle only after reading back and verifying the written bytes. The commit message contains `[stage2-complete:<run_id>]`. The receiver processes only the exact Run ID in the marker; it never searches for a Run by report_date or chooses the newest Run.
