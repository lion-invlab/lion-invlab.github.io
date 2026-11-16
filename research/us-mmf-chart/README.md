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

### 1. Federal Reserve Z.1 via FRED — primary AUM series
- Series: `MMMFFAQ027S`
- Title: Money Market Funds; Total Financial Assets, Level
- Frequency: quarterly, end of period
- Units: millions of U.S. dollars
- Seasonal adjustment: not seasonally adjusted
- First non-zero observation: 1974 Q1 (263 million USD)
- Latest observation in source snapshot: 2026 Q2 (8,441,374 million USD = USD 8.441374tn)
- Last updated: 2026-09-11
- Next scheduled release shown by FRED: 2026-12-10
- Source: https://fred.stlouisfed.org/data/MMMFFAQ027S
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
- [x] Download and archive full FRED AUM quarterly series snapshot (210 observations, 1974 Q1–2026 Q2) at `data/us-mmf/fed_mmmffaq027s_1974q1_2026q2.csv`; validated row count, unique dates, uninterrupted quarterly cadence, and latest value against FRED.
- [ ] Download OFR CSV exports for monthly total and category series.
- [ ] Build monthly/quarterly reconciliation and revision-aware data snapshots.
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
