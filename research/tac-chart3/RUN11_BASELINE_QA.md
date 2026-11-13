# TAC Chart 3 — Run 11 baseline QA

- Run: 43026998120 — completed successfully; all four ingestion jobs passed.
- Source commit: fd892464c00c6776f9fef5396288ba7136f2e80b
- Scope: simulation branch only. No main branch, homepage, template, or report schedule changes.
- Full downloadable package: TAC_Chart3_Run11_full_baseline_20261111.zip
- Package SHA-256: df4cb4ee18c01f4871a51eb4d7245a6322c682ef30cd89f8d11e37532693840d

## Normalized vintage event rows

| Series | Current rows | Vintage dates | Event rows |
|---|---:|---:|---:|
| VIXCLS | 9,615 | 3,970 | 9,637 |
| NFCI | 2,913 | 803 | 934,790 |
| NFCICREDIT | 2,913 | 745 | 930,171 |
| STLFSI4 | 1,714 | 209 | 319,948 |
| **Total** | **17,155** | — | **2,194,546** |

## QA

- All four raw artifact ZIP SHA-256 values match GitHub artifact metadata.
- All expected vintage-batch × observation-window chunk cells are present.
- Every vintage date from the vintage-date index is represented in output_type=3 columns.
- Zero duplicate (observation_date, vintage_date) keys; zero conflicting duplicates.
- Current output_type=1 reconciles against latest output_type=3 event values: zero mismatches.
- Comparable output_type=4 initial-release values reconcile against earliest vintage events: zero mismatches.
- Dot (.) is preserved as an explicit missing-value event; only empty/null cells are omitted as no event.
- No imputation, interpolation, or forward-fill.
- Exact per-observation release dates are not supplied; release_date remains blank.

## Coverage limitations

Vintage history starts later than current observation history:
- VIXCLS: current 1990-01-02; ALFRED vintage 2010-11-22.
- NFCI: current 1971-01-08; ALFRED vintage 2011-05-25.
- NFCICREDIT: current 1971-01-08; ALFRED vintage 2012-07-05.
- STLFSI4: current 1993-12-31; ALFRED vintage 2022-11-10.

Do not use current revised values as a substitute for unavailable historical as-of vintages. VIX methodology has a structural break in 2003. Redistribution license review remains required.

## Next gate

Baseline data QA is complete with documented coverage limitations. Incremental update implementation must be idempotent, preserve last-good data on failure, use vintage-date checkpoints plus an overlap window, and reconcile current snapshots before committing. It must not start until the baseline store is durably seeded.
