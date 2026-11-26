# Stage 2 input handoff

## Optional direct ChatGPT Web observation bundle

When available, write:

- `production/input/market-history-web-observations-YYYY-MM-DD.json`
- `production/input/cnn-fear-greed-observation-YYYY-MM-DD.json` (may contain an empty observations array when the CNN official page could not be read and the 44-row bundle already carries the approved provider backup)

Validate against the adjacent JSON schemas. The 44-row bundle must contain one observation for each fixed market row, opened directly from the designated Investing.com Historical Data page. `CHATGPT_WEB_SEARCH_RESULT_HISTORICAL_PAGE` is not accepted; a search summary is not a page observation. Every row must record the exact URL, instrument identity, target and observed dates, field labels, table row text, captured/finished timestamps and direct page reference/line range.

The CNN capture is separate because Fear & Greed is a current dashboard, not an Investing.com historical price table. The official CNN current dashboard method must capture `Current Score`, `Current Band`, the page's `Last updated` timestamp and direct page reference. Never use CNN `previous_close` as the current dashboard score. If the official current dashboard is unavailable, use only the approved FGScore provider index, then Financial Context, and preserve the backup tier/date-mapping disclosure.

If the direct web bundle is absent, Stage 2 falls back to a real browser reader with a maximum of four concurrent pages. It does not bypass Cloudflare. If a page loads without a readable history table, mark TOOL_READ_FAILURE; do not label it SOURCE_NO_DATA.

## Screenshot priority

The report-date screenshot sidecar is `market-screenshot-observations-YYYY-MM-DD.json`. It is validated against the fixture's approved source URLs, report/trading dates, field labels, evidence paths and SHA-256. Screenshot values take priority over any conflicting page observation; the screenshot is not re-queried. Missing fields continue through the normal browser-read path. No prior-day fixture value is reused.
