# Equibles Analyst Estimates API — PIT Source Qualification
**Audit date:** 2026-11-15  
**Scope:** simulation branch only; read-only provider evaluation  
**Decision:** NOT QUALIFIED for TAC pre-release Beat/Miss judgment under SIM-1.2

## Evidence collected
- API authentication succeeded using the GitHub Actions secret `EQUIBLES_API_KEY`; the key was never printed.
- Provider returned `provider=Aggregated` for NVDA, WMT, and BIDU.
- Historical snapshot index totals: NVDA 21, WMT 31, BIDU 24 (76 total).
- The first 30 snapshots were checked in the initial 10-per-ticker pass; the remaining 46 were fetched by the historical remainder probe and archived as raw JSON with SHA-256.
- Remainder probe workflow: run `43680707448`, artifact `14148436817`, commit `34bb3097dc14239e6f8e9f42798166f8be7426bd`.
- Remainder report: `simulation-lab/output/equibles-historical-pit-remainder.json`.
- Raw response files: `simulation-lab/output/equibles-raw/` in the workflow artifact.

## Field-level findings
| Required evidence | API payload observation | Qualification |
|---|---|---|
| Provider snapshot ID | Present | Available |
| capturedAt / verifiedAt | Present | Capture/verification time only; not source estimate effective time |
| metric / period / statistic / value / unit | Present | Available for many rows; still requires matching and validation |
| analyst count | Present as `Analyst count` statistic | Available |
| provider `data_as_of` | Absent | FAIL |
| source estimate `published_at` | Absent; `publicationLabel` null | FAIL |
| EPS / Revenue accounting basis | `basis: null` in all inspected historical payloads | FAIL |
| source URL per estimate / independently retrievable evidence | Not exposed in inspected API payload | FAIL / provider-side evidence not independently auditable from payload |

## Non-negotiable mapping rules
- Never map `capturedAt`, `verifiedAt`, or `lastCheckedAt` into `data_as_of`.
- Never map `publicationLabel` into a timestamp or invent `published_at`.
- Never infer GAAP/Adjusted, Basic/Diluted, or any `basis_code` when the provider field is null.
- Never infer an original analyst estimate publication time from the date on which Equibles captured a snapshot.
- Never label any of these records Beat/Miss eligible solely because the snapshot capture predates the earnings event.

## Decision
Equibles is useful as a current/historical reference feed and provides analyst counts plus immutable snapshot identifiers. However, the inspected API response does not satisfy TAC SIM-1.2 PIT requirements. Do not connect it to the production judgment path or relax the PIT gate. Keep it in the research-only tier unless Equibles supplies independently verifiable source-level effective timestamps, accounting basis, and evidence URLs.

## Next valid route
1. Ask Equibles support whether the API can expose, per metric/period, the underlying estimate's effective/as-of timestamp, accounting basis, and source evidence URL or downloadable verification record.
2. If the provider cannot supply those fields, exclude Equibles from PIT judgment and use it only for non-directional reference display with explicit provider/capture labels.
3. Continue collecting immutable daily snapshots prospectively only as a separately labeled TAC-observed history; do not backfill historical PIT.
