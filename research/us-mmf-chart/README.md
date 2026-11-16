# U.S. Money Market Funds — Research Workstream

Status: source validation and data architecture. No production chart, no homepage/index changes, and no main-branch writes.

## Scope
- Subject: U.S. money market funds (MMFs) only.
- Cost constraint: free, public sources only. No paid subscriptions or paid data products.
- Main series: Federal Reserve Z.1 / FRED quarterly total financial assets (AUM).
- Secondary composition: OFR U.S. Money Market Fund Monitor / SEC Form N-MFP monthly filings.
- Do not mix the Fed quarterly level series with OFR monthly category aggregates as one continuous series.
- Do not interpret AUM changes as net subscriptions/redemptions.
- Keep transactions separate from AUM and label the Fed transaction series as seasonally adjusted annual rate (SAAR).

## Validated sources

### 1. Federal Reserve Z.1 — primary AUM series (FRED mirror for cross-check)
- Series: `MMMFFAQ027S`
- Title: Money Market Funds; Total Financial Assets, Level
- Frequency: quarterly, end of period
- Units: millions of U.S. dollars
- Seasonal adjustment: not seasonally adjusted
- First non-zero observation: 1974 Q1 (263 million USD)
- Latest observation in source snapshot: 2026 Q2 (8,441,374 million USD = USD 8.441374tn)
- Last updated: 2026-09-11
- Next scheduled release shown by FRED: 2026-12-10
- Primary raw source: https://www.federalreserve.gov/releases/z1/current/z1_csv_files.zip (table `csv/S123_s.csv`).
- FRED cross-check mirror: https://fred.stlouisfed.org/data/MMMFFAQ027S
- ALFRED vintage history: https://alfred.stlouisfed.org/series?seid=MMMFFAQ027S
- Important: FRED's quarter date is encoded as the first day of the quarter (e.g. 2026-04-01 represents Q2 2026). Preserve the source date and separately derive the quarter label; do not mislabel it as an actual daily observation date.
- Earlier observations before 1974 Q1 are zero or missing and must not be plotted as genuine market AUM.

### 2. Federal Reserve Z.1 via FRED — transactions, separate series
- Series: `MMMFTAQ027S`
- Title: Money Market Funds; Total Financial Assets, Transactions
- Frequency: quarterly
- Units: millions of U.S. dollars, seasonally adjusted annual rate (SAAR)
- Latest source snapshot: 2026 Q2, 723,692 million USD SAAR
- Source: https://fred.stlouisfed.org/series/MMMFTAQ027S
- This is a financial-account transactions measure, not a direct weekly/monthly subscription-redemption statistic. Never label it simply as “net fund flows” without explaining the accounting definition and SAAR unit. Keep it as a separate optional panel pending further validation.

### 2A. Federal Reserve Z.1 — MMF net acquisition transactions (separate panel)
- Official table: https://www.federalreserve.gov/releases/z1/current/html/S123_t.htm
- Table: S123.t, line 1, series code: FA634090005; FRED mirror: MMMFTAQ027S.
- Meaning: net acquisition of financial assets by the MMF sector in the financial accounts. This is a transaction measure and is distinct from the S123.s balance-sheet AUM level.
- Frequency: quarterly; units: millions of U.S. dollars, seasonally adjusted annual rate (SAAR).
- Latest official value at 2026 Q2: USD 723,692 million SAAR (USD 723.692 billion SAAR).
- The series can be negative; preserve negative values. Do not convert it to a quarterly cash amount by treating the SAAR figure as the quarter's actual total.
- Critical interpretation: this is not a direct measure of investor net subscriptions/redemptions. Label it “MMF 金融資產淨取得額（季調年率）”, not “資金淨流入”.
- Ingestion: the public Z.1 ZIP parser now reads both S123.s and S123.t, archives the S123.t raw table with SHA-256, and normalizes the total transaction series to `data/us-mmf/fed_mmf_transactions_latest.csv`.
- QA: `scripts/us_mmf/test_mmf_transactions.py` checks sorted unique quarterly dates, uninterrupted quarterly cadence, units, quarter labels, and the official 2026 Q2 value.
- Fund-type transaction breakdown is not being charted yet; the total transaction series is the only candidate pending full ingestion QA and interpretation review.

### 3. OFR U.S. Money Market Fund Monitor — monthly category and portfolio detail
- Source page: https://www.financialresearch.gov/money-market-funds/
- Underlying source: SEC Form N-MFP plus OFR aggregation/analysis
- Monitor history shown: 2011-01-31 through 2026-09-30
- Data can be downloaded as CSV from the monitor's Data control.
- Categories reported by OFR: Government, Prime, Tax Exempt.
- OFR combines Treasury, Government/Agency and Exempt Government into Government; Single State and Other Tax Exempt into Tax Exempt.
- OFR's monitor is useful for category/portfolio composition and risk breakdowns; do not silently merge it into the Fed quarterly AUM line.

### 4. SEC Form N-MFP — underlying public monthly filings
- Source: https://www.sec.gov/data-research/sec-markets-data/dera-form-n-mfp-data-sets
- SEC data sets listed from September 2010 through October 2026 in the current source page.
- Files are provided as monthly ZIP flat-file data sets extracted from EDGAR XML submissions.
- Data are provided as-filed and SEC warns that registrant data and extraction may contain errors; use for audit/reconstruction, not as an unqualified error-free aggregate.
- SEC page notes updates to include N-MFP3 submissions in July 2025 and prior updates to NT filings and series/class names in May 2023.



### 7. Federal Reserve Z.1 — quarterly AUM by fund type (preferred category split)
- Official table: https://www.federalreserve.gov/releases/z1/current/html/S123_s.htm
- Total AUM series: `MMMFFAQ027S` (FRED) / Z.1 line 1, FL634090005.
- Government: `BOGZ1FL634090033Q` / Z.1 memo line 15, FL634090033.
- Prime: `BOGZ1FL634090043Q` / Z.1 memo line 16, FL634090043.
- Tax-exempt: `BOGZ1FL634090053Q` / Z.1 memo line 17, FL634090053.
- The three fund-type categories reconcile to total financial assets within USD 1 million (rounding) in every quarter from 2010 Q4 through 2026 Q2.
- Archived file: `data/us-mmf/fed_mmf_aum_by_fund_type_2010q4_2026q2.csv` (63 quarterly rows). It stores total, Government, Prime, Tax-exempt, category sum, and reconciliation difference.
- 2026 Q2: total USD 8,441,374m; Government USD 6,893,476m; Prime USD 1,393,709m; Tax-exempt USD 154,189m. Categories sum exactly to total.
- Use this Z.1 series for the category stacked chart, not OFR or EFA, because all three categories and total are from the same table and reconcile. Use EFA monthly files only for the separate portfolio-instrument detail panel.
- Floating NAV category data begin 2016 Q4; stable/floating NAV is a separate split and must not be confused with Government/Prime/Tax-exempt fund type.

### 6. Federal Reserve Enhanced Financial Accounts — monthly holdings by fund type
- Official page: https://www.federalreserve.gov/releases/efa/efa-project-money-market-funds-investment-holdings-detail.htm
- Monthly security-level holdings dataset from SEC Form N-MFP, available beginning December 2010; page last updated 2026-09-18.
- Separate CSV files are published for Total, Prime, Government, and Tax-exempt MMF investment holdings.
- Each file breaks the fund type into instrument holdings. Sum the instrument columns within each file to derive that category's total portfolio investment holdings; check Prime + Government + Tax-exempt against Total within rounding.
- The Fed explicitly states that these monthly holdings totals differ slightly from Z.1 Table S123.s total financial assets because they exclude fund-of-funds and include some non-portfolio assets.
- Therefore use Z.1 `MMMFFAQ027S` as the long-run total AUM backbone (1974 Q1 onward), and use EFA as a separate monthly fund-type composition panel (2010-12 onward). Do not splice or force equality between the two.
- The downloader archives the four raw EFA CSV files and their SHA-256 hashes. Instrument-level parsing and reconciliation are still pending.

### 5. ICI weekly MMF assets — optional current-market context only
- Source: https://www.ici.org/research/stats/mmf
- Public page provides weekly aggregate assets and category split, but only the most recent 20 weeks.
- Not suitable as the long-term historical database. May be used as a clearly separate “latest weekly snapshot” card if needed.

## Structural breaks and comparability
- OFR's historical guide states that prior to April 2016 the reported fund categories were grouped as Prime, Government and Tax-exempt. Starting April 2016, reporting reflected SEC rule changes and category subgroups (including retail/institutional distinctions for Prime and Tax-exempt, and fee/gate distinctions for Government).
- Therefore, category history should be normalized only at a defensible broad level (Government / Prime / Tax Exempt), with the April 2016 reporting change explicitly annotated. Do not backfill or invent subcategory splits before the reporting change.
- OFR guide: https://www.financialresearch.gov/briefs/files/OFRbr_2016-07_Money-Market-Fund-Monitor.pdf
- OFR monitor reports its own aggregation methodology; preserve OFR values as OFR-derived rather than treating them as raw SEC totals.

## Data handling rules
1. Preserve original source values and units.
2. Convert FRED millions USD to USD trillions by dividing by 1,000,000; retain raw value.
3. Store FRED observation date exactly as supplied and derive a separate quarter label.
4. Preserve retrieval timestamp, source update date, source URL, series ID, seasonal adjustment, frequency, units and vintage/revision metadata.
5. Missing values remain null; never interpolate or manufacture observations.
6. Keep Fed AUM level, Fed transactions SAAR, OFR category assets and ICI weekly assets in separate datasets.
7. Record SHA-256 for downloaded snapshots and never overwrite prior snapshots.
8. Before chart implementation, reconcile OFR aggregate totals against Fed quarterly totals for overlapping periods and document the expected differences in scope/methodology. Do not force equality.

## Current completion state
- [x] Scope changed from global MMF to U.S. MMF.
- [x] Paid IIFA subscription explicitly excluded.
- [x] Fed AUM series metadata and first non-zero observation verified.
- [x] OFR monitor coverage and category definitions verified.
- [x] SEC raw monthly dataset availability verified.
- [x] April 2016 category reporting break identified.
- [x] Create an initial FRED AUM quarterly data snapshot (210 observations, 1974 Q1–2026 Q2) at `data/us-mmf/fed_mmmffaq027s_1974q1_2026q2.csv`; validated row count, unique dates, uninterrupted quarterly cadence, and latest value against FRED. This first snapshot was transcribed from the official FRED table; replace it with the raw-download output before production use.
- [x] Identify OFR's public no-token API and its `mmf` dataset endpoint; raw response can be archived with provenance.
- [ ] Retrieve and inspect the OFR API payload and OFR Monitor category chart CSV exports; map the exact series for total AUM and Government / Prime / Tax Exempt before building category history.
- [x] Parse the official Z.1 CSV ZIP (`S123.s`) into directly refreshed normalized quarterly AUM and fund-type history; raw ZIP and table CSV are archived with SHA-256.
- [ ] Finalize UI and implement interactive chart.
- [ ] Browser QA on desktop and mobile.
- [ ] User review before any main-branch or public index update.


## Archived Fed AUM snapshot validation
- File: `data/us-mmf/fed_mmmffaq027s_1974q1_2026q2.csv`
- Snapshot source: FRED table data page, retrieved 2026-11-16.
- Source metadata: last updated 2026-09-11; date range shown by FRED 1945-10-01 to 2026-04-01.
- Stored valid observations: 210 quarterly rows, 1974 Q1 through 2026 Q2.
- QA: zero duplicate dates; zero quarterly gaps; all included observations positive; final value 8,441,374 million USD (8.441374 trillion USD).
- Pre-1974 zero/missing records intentionally excluded from the plotted AUM dataset.
- FRED date labels are quarter-start encodings; the CSV retains the original observation date and a separate human-readable quarter label.
- Source table: https://fred.stlouisfed.org/data/MMMFFAQ027S

## OFR public data retrieval
- OFR API documentation: https://www.financialresearch.gov/short-term-funding-monitor/api/
- Public API base: `https://data.financialresearch.gov/v1`; documentation states no token or registration is required.
- Dataset endpoint: `/series/dataset?dataset=mmf`; supports start_date, end_date, vintage and periodicity parameters.
- The dataset endpoint returns metadata plus a `timeseries` object. Its exact series inventory still needs inspection; do not assume it directly contains the OFR Monitor's category-level AUM chart.
- OFR Monitor provides a visible Data button that downloads the current chart view as CSV. Category chart: https://www.financialresearch.gov/money-market-funds/us-mmfs-investments-by-fund-category/
- The monitor currently reports data through 2026-09-30 and notes that its aggregates are OFR-derived on an ultimate-parent basis. This differs from raw SEC fund-level totals.
- SEC Form N-MFP raw data sets are public from September 2010 through October 2026, updated monthly; SEC warns that filings/extraction can contain errors and that the data are provided as-filed.
- Downloader: `scripts/us_mmf/update_public_data.py`. It downloads the Federal Reserve Z.1 CSV package, parses `S123.s` into the normalized 1974Q1+ total AUM and 2010Q4+ fund-type split, downloads four EFA monthly holdings CSVs, and archives the OFR `mmf` API response. The FRED graph CSV endpoint is not used for ingestion because it timed out from GitHub Actions; FRED remains a cross-check mirror. The OFR response is gzip-compressed and the script decompresses it before validating its 42-series payload.

- Structural break confirmation: OFR category chart notes six categories from April 2016 and a June 2024 reporting change removing the Government fee/no-fee distinction. Source: https://www.financialresearch.gov/money-market-funds/us-mmfs-investments-by-fund-category/
- QA script: `scripts/us_mmf/test_fed_aum_data.py` checks required columns, positive values, quarterly date continuity, unique/sorted dates, USD conversion, quarter labels, and the latest 2026 Q2 value.

## EFA monthly portfolio holdings (2026-11-16)
- Official source: https://www.federalreserve.gov/releases/efa/efa-project-money-market-funds-investment-holdings-detail.htm
- The Fed documents these monthly security-level holdings as based on SEC Form N-MFP; EFA tables include total, Prime, Government and Tax-exempt portfolio allocation. Coverage begins December 2010. The Fed notes totals differ slightly from Z.1 S123.s because EFA excludes fund-of-funds and includes some non-portfolio assets.
- Normalized output: `data/us-mmf/fed_mmf_holdings_by_type_latest.csv` (long form: month, fund type, instrument, USD millions, USD trillions, share).
- Coverage: 188 monthly observations per group, 2010-12 to 2026-07; 20 instrument series in total.
- Reconciliation: Government + Prime + Tax-exempt EFA holdings match EFA Total to within USD 3 million maximum across all months; the small difference is source rounding. QA permits up to USD 5 million and checks every monthly portfolio share sums to 100%.
- Latest EFA total at 2026-07-31: USD 8.411936 trillion. Government USD 6.886513T; Prime USD 1.371120T; Tax-exempt USD 0.154302T.
- Latest Government mix: U.S. Treasuries 47.59%; U.S. Treasury repo 23.26%; U.S. Agencies 17.50%; U.S. Agency repo 11.26%; Other assets 0.39%.
- Latest Prime mix: U.S. Government security repo 27.54%; Other instruments 23.44%; Certificates of deposit 15.00%; Unsecured commercial paper 14.38%; Other repo 12.27%; Asset-backed commercial paper 7.38%.
- Latest Tax-exempt mix: Variable rate demand obligations 74.53%; Other municipal 14.05%; Other assets 11.41%.
- Interactive chart: fourth panel in `chart-preview.html`, with selectors for Total, Government, Prime and Tax-exempt. Each portfolio is normalized to 100% within its own category; dollar values remain available in tooltips.
- Data QA: `scripts/us_mmf/test_efa_holdings.py` validates coverage, monthly date consistency, instrument counts, units, portfolio shares and fund-type reconciliation.

## OFR monthly MMF dataset research
- Official dataset: https://www.financialresearch.gov/short-term-funding-monitor/datasets/mmf/
- Based on SEC Form N-MFP filings and OFR mappings; 42 series currently returned by the public dataset API.
- Useful series groups include total investments, U.S. Treasury securities, repo investments, repo collateral types and repo counterparty categories. Median repo yields are also available from 2016-04 onward.
- Selected series for future liquidity research: `MMF-MMF_TOT-M` (total investments), `MMF-MMF_T_TOT-M` (U.S. Treasury securities), `MMF-MMF_RP_TOT-M` (repo total), `MMF-MMF_RP_wDFI-M` (repo with U.S. financial institutions), `MMF-MMF_RP_wFFI-M` (repo with foreign financial institutions), and `MMF-MMF_RP_wFR-M` (repo with Federal Reserve).
- Do not sum overlapping repo collateral, tenor and counterparty series; they are alternative cuts of the same underlying repo positions. The OFR series are holdings snapshots, not flows.
- Normalized broad portfolio file: `data/us-mmf/fed_mmf_ofr_portfolio_latest.csv`; six series (total plus five non-overlapping asset classes), 191 monthly observations from 2010-11 to 2026-09.
- The five broad classes reconcile to total in every month; maximum absolute difference is less than USD 0.001. Latest 2026-09 total is USD 8.396822T: U.S. Treasury securities USD 3.483974T (41.49%), repo USD 2.871495T (34.20%), agency/GSE USD 1.194287T (14.22%), bank-related assets USD 0.495239T (5.90%), and other assets USD 0.351828T (4.19%).
- QA: `scripts/us_mmf/test_ofr_portfolio.py` validates 191 monthly observations, unique categories, units, and monthly reconciliation.
- OFR dataset is retained as compressed raw JSON with SHA-256 in the source snapshot artifact. Detailed repo tenor/collateral/counterparty series remain separate research inputs; do not add overlapping cuts together.

## Z.1 transactions ingestion and third chart panel (2026-11-16)
- [x] Parse the official Z.1 CSV package table S123.t alongside S123.s.
- [x] Archive the raw S123.t table and SHA-256 in the public-data workflow artifact.
- [x] Normalize series FA634090005 / FRED MMMFTAQ027S to `data/us-mmf/fed_mmf_transactions_latest.csv`.
- [x] Preserve original quarterly date labels, negative values, and missing quarters without interpolation.
- [x] Validate 304 observations from 1946 Q4 through 2026 Q2; latest value USD 723,692 million SAAR (USD 0.723692tn SAAR). QA checks units, quarter labels, date order/uniqueness, and official latest value.
- [x] Add an interactive third chart panel with zero baseline, signed positive/negative values, pan/zoom and tooltip.
- [ ] Complete desktop/mobile browser visual QA for the third panel.
- Interpretation warning: S123.t is net acquisition of financial assets by the MMF sector, seasonally adjusted annual rate. It is not direct investor net subscriptions/redemptions and must not be labeled “資金淨流入”.
- The transaction history has genuine gaps in earlier decades; the data and chart preserve these gaps instead of filling them.

## Automated research-branch data refresh
- Workflow: `.github/workflows/us-mmf-public-data-qa.yml` (push / manual dispatch on the research branch only).
- Downloads official Z.1 CSV package, EFA monthly CSVs and OFR API data; creates SHA-256 manifest; validates both normalized quarterly datasets; commits only the normalized CSVs and manifest to `research/us-mmf-chart-20261116`; uploads raw snapshots as a 90-day workflow artifact.
- Workflow permissions are limited to repository contents on this research branch. It does not target `main`, the homepage, or the interactive-chart index.

## Interactive preview
- Preview source: `research/us-mmf-chart/chart-preview.html`.
- Main chart: 1974 Q1–latest quarterly total AUM.
- Secondary chart: Government / Prime / Tax-exempt stacked AUM, 2010 Q4–latest.
- Interactions: drag/pan, mouse-wheel zoom, touch pinch zoom, quick range buttons; y-axis auto-adjusts to visible data.
- Data files loaded by the preview: `data/us-mmf/fed_mmmffaq027s_latest.csv`, `data/us-mmf/fed_mmf_aum_by_fund_type_latest.csv`, and `data/us-mmf/latest_manifest.json`.
- Browser QA: `.github/workflows/us-mmf-chart-visual-qa.yml`; tests desktop and 390px mobile layout, data load, KPI values, chart series rendering, zoom controls and horizontal overflow. Screenshots and report are retained as workflow artifacts.
- This preview is research-only. It is not linked from the main interactive-chart index and has not been published to main.

- Latest browser QA: PASS on desktop and 390px mobile. Verified chart data loading, latest KPIs, line/stacked-area rendering, zoom presets, zoom reset, no horizontal overflow, no console/page errors, and an actual two-finger pinch gesture (zoom scale increased to 2.07x). Workflow run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/43793626168
