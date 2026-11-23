#!/usr/bin/env python3
"""SIM-1.4 fail-closed, pre-build receipt binding Stage 2-4 inputs to one run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_REPOSITORY = "lion-invlab/lion-invlab.github.io"
EXPECTED_BRANCH = "simulation/tac-process-lab-2026-11-06"
EXPECTED_GROUP_COUNTS = {
    "global_markets": 17, "sectors": 11, "bonds": 3, "fx": 6,
    "energy": 2, "metals": 2, "risk": 3,
}
EXPECTED_POLITICAL_DOMAINS = {
    "us_policy", "us_china", "geopolitics", "trade_sanctions",
    "major_economies", "energy_resources",
}
EXPECTED_ANALYSIS_LAYERS = {
    "political", "policy_industry", "macro", "markets", "strategy",
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_json(path: str | Path) -> tuple[dict, str]:
    p = Path(path)
    raw = p.read_bytes()
    return json.loads(raw.decode("utf-8")), sha256_bytes(raw)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_branch(repository: str, branch: str) -> None:
    require(repository.rstrip("/").lower() == EXPECTED_REPOSITORY,
            f"repository mismatch: {repository!r}")
    require(branch == EXPECTED_BRANCH,
            f"refusing non-simulation branch: {branch!r}")


def validate_market_inputs(data: dict, audit: dict, manifest: dict, report_date: str) -> dict:
    require(data.get("report_date") == report_date, "fixture report_date mismatch")
    trading_date = data.get("trading_date")
    require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(trading_date))),
            "fixture trading_date missing or malformed")
    require(audit.get("status") == "PASS", "44-row metadata/date audit is not PASS")
    require(audit.get("verification_scope") == "METADATA_AND_DATE_ONLY",
            "market audit scope must remain METADATA_AND_DATE_ONLY")
    require(audit.get("report_date") == report_date, "market audit report_date mismatch")
    require(audit.get("trading_date") == trading_date, "market audit trading_date mismatch")
    require(audit.get("indicator_count") == 44, "market audit must contain exactly 44 rows")
    require(audit.get("group_counts") == EXPECTED_GROUP_COUNTS, "market audit group counts mismatch")
    require(audit.get("source_pages_fetched") is False,
            "metadata validator must not claim source-page fetching")
    require(audit.get("displayed_values_independently_reconciled") is False,
            "metadata validator must not claim independent numeric reconciliation")

    require(manifest.get("status") == "PASS", "market source observation manifest is not PASS")
    require(manifest.get("report_date") == report_date, "source manifest report_date mismatch")
    require(manifest.get("trading_date") == trading_date, "source manifest trading_date mismatch")
    require(manifest.get("row_count") == 44 and manifest.get("verified_count") == 44
            and manifest.get("pending_count") == 0, "44 source observation rows are incomplete")
    require(manifest.get("prior_observation_reused_count") == 0,
            "current-run verification must not reuse prior fixture observations")
    require(manifest.get("source_pages_fetched") is True
            and manifest.get("displayed_values_independently_reconciled") is True,
            "44 current-run source reads and numeric reconciliations are required")
    require(manifest.get("verification_scope") ==
            "CURRENT_RUN_BROWSER_OBSERVATIONS",
            "unexpected source manifest verification scope")
    require(manifest.get("browser_observation_records_complete") is True
            and manifest.get("observation_record_hash_missing_count") == 0,
            "44 per-item observation records and hashes must be complete")
    rows = manifest.get("rows")
    require(isinstance(rows, list) and len(rows) == 44, "source manifest rows must contain 44 records")
    keys = {(row.get("group"), row.get("name")) for row in rows}
    require(len(keys) == 44 and all(a and b for a, b in keys),
            "source manifest has duplicate or unnamed rows")
    expected_keys = set()
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        expected_keys.update((group, name) for name in (data.get(group) or {}))
    expected_keys.update(("sectors", name) for name in (data.get("sectors") or {}))
    require(keys == expected_keys, "source manifest rows do not match the exact fixture indicator identities")
    observed_groups = {group: sum(1 for row in rows if row.get("group") == group)
                       for group in EXPECTED_GROUP_COUNTS}
    require(observed_groups == EXPECTED_GROUP_COUNTS,
            f"source manifest group distribution mismatch: {observed_groups}")
    require(all(row.get("verification_status") in ("VERIFIED", "BACKUP_VERIFIED")
                and row.get("display_value_matches_saved_observation") is True
                and row.get("observation_provenance") == "CURRENT_RUN_BROWSER_OBSERVATION"
                for row in rows), "one or more source rows lack an accepted prior observation")
    require(all(isinstance(row.get("browser_observation_record"), dict)
                and row["browser_observation_record"].get("source_url")
                and row["browser_observation_record"].get("data_date") == trading_date
                and row["browser_observation_record"].get("observed_value") is not None
                and row["browser_observation_record"].get("observed_change") is not None
                and row["browser_observation_record"].get("checked_at_tw")
                for row in rows), "one or more browser observation records are incomplete")
    require(all(row.get("source_page_fetched") is True and row.get("display_value_reconciled") is True for row in rows),
            "all 44 rows must be fetched and reconciled in this run")
    require(all(row.get("observation_record_sha256") and
                re.fullmatch(r"[0-9a-f]{64}", row["observation_record_sha256"])
                for row in rows), "one or more observation record hashes are invalid")
    require(all(row.get("trading_date") == trading_date for row in rows),
            "source manifest contains mixed trading dates")
    # raw_response_sha256 is optional evidence; absence is not a Stage 2 failure.
    raw_hash_count = manifest.get("raw_response_sha256_saved_count", 0)
    require(isinstance(raw_hash_count, int) and 0 <= raw_hash_count <= 44,
            "raw response hash count is malformed")
    return {
        "trading_date": trading_date,
        "indicator_count": 44,
        "group_counts": EXPECTED_GROUP_COUNTS,
        "observation_count": len(rows),
        "observation_record_hash_count": 44,
        "prior_observations_reused": 0,
        "source_pages_fetched_this_run": True,
        "numeric_values_reconciled_this_run": True,
        "raw_response_sha256_saved_count": raw_hash_count,
    }


def validate_stage4(data: dict, report_date: str) -> dict:
    require(data.get("report_date") == report_date, "Stage 4 fixture date mismatch")
    require(data.get("timezone") == "Asia/Taipei", "fixture timezone must be Asia/Taipei")
    focus = data.get("focus_news")
    headlines = data.get("headlines")
    require(isinstance(focus, list) and len(focus) == 5, "Global Focus News must contain 5 items")
    require(isinstance(headlines, list) and len(headlines) == 10, "Market Hot Headlines must contain 10 items")
    all_news = focus + headlines
    urls = []
    start_match = re.search(r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2})", str(data.get("news_window_taipei", "")))
    end_text = data.get("news_cutoff_taipei")
    require(start_match and end_text, "news window start/cutoff missing")
    start = datetime.strptime(start_match.group(1), "%Y/%m/%d %H:%M")
    end = datetime.strptime(end_text, "%Y-%m-%d %H:%M:%S")
    require(start <= end, "news window is inverted")
    for item in all_news:
        url = item.get("url", "")
        parsed = urlparse(url)
        require(parsed.scheme == "https" and parsed.netloc, "news item has invalid HTTPS URL")
        urls.append(url)
        for field in ("published_at_source", "source_timezone", "published_at_tw", "summary"):
            require(bool(item.get(field)), f"news item missing {field}: {item.get('title')}")
        require(bool(item.get("updated_at_source") or item.get("updated_at_tw")),
                f"news item missing update-time status: {item.get('title')}")
        published = datetime.strptime(item["published_at_tw"], "%Y/%m/%d %H:%M")
        require(start <= published <= end,
                f"news item outside sealed window: {item.get('title')} / {item['published_at_tw']}")
    require(len(set(urls)) == 15, "news source URLs must be unique")

    analysis = data.get("market_analysis")
    require(isinstance(analysis, dict) and set(analysis) == EXPECTED_ANALYSIS_LAYERS,
            "five-layer market analysis is incomplete or has unexpected layers")
    for layer, payload in analysis.items():
        require(isinstance(payload, dict) and isinstance(payload.get("paragraphs"), list)
                and len(payload["paragraphs"]) > 0 and all(str(x).strip() for x in payload["paragraphs"]),
                f"analysis layer {layer} has missing paragraphs")
        sources = payload.get("sources")
        require(isinstance(sources, list) and len(sources) > 0,
                f"analysis layer {layer} has no source records")
        for source in sources:
            parsed = urlparse(str(source.get("url", "")))
            require(parsed.scheme == "https" and parsed.netloc and source.get("label"),
                    f"analysis layer {layer} has an invalid source record")
    political_scan = data.get("political_scan") or {}
    domains = set(political_scan.get("domains_checked") or [])
    require(domains == EXPECTED_POLITICAL_DOMAINS,
            "six-domain political/geopolitical scan is incomplete")
    findings = political_scan.get("findings")
    require(isinstance(findings, list) and len(findings) > 0,
            "political/geopolitical scan findings are missing")
    require(data.get("report_cutoff_taipei"), "report cutoff missing")
    return {
        "focus_news_count": 5,
        "headlines_count": 10,
        "unique_news_urls": 15,
        "news_window_taipei": data.get("news_window_taipei"),
        "news_cutoff_taipei": end_text,
        "analysis_layers": sorted(analysis),
        "political_domains": sorted(domains),
        "political_findings_count": len(findings),
        "report_cutoff_taipei": data.get("report_cutoff_taipei"),
    }


def build_receipt(*, data: dict, fixture_sha256: str, audit: dict,
                  audit_sha256: str, manifest: dict, manifest_sha256: str,
                  calendar_bundle: dict, repository: str, branch: str,
                  workflow_run_id: str, workflow_run_attempt: str) -> dict:
    validate_branch(repository, branch)
    report_date = str(data.get("report_date") or "")
    market = validate_market_inputs(data, audit, manifest, report_date)
    stage4 = validate_stage4(data, report_date)

    current = calendar_bundle.get("current") or {}
    previous = calendar_bundle.get("previous") or {}
    require(bool(calendar_bundle.get("main_commit_sha")), "authoritative main commit SHA missing")
    for label, item in (("current", current), ("previous", previous)):
        require(item.get("branch") == "main", f"{label} calendar did not come from main")
        require(item.get("commit_sha") == calendar_bundle["main_commit_sha"],
                f"{label} calendar commit is not the pinned main commit")
        require(item.get("blob_sha"), f"{label} calendar blob SHA missing")
        payload = item.get("payload") or {}
        require(payload.get("week_id") == item.get("week_id"),
                f"{label} calendar week identity mismatch")
        require(len(payload.get("events", {}).get("economic", [])) == item.get("economic_count"),
                f"{label} economic event count mismatch")
        require(len(payload.get("events", {}).get("earnings", [])) == item.get("earnings_count"),
                f"{label} earnings event count mismatch")
    require(current.get("week_id") != previous.get("week_id"),
            "current and previous calendar week must be distinct")
    for item in (current, previous):
        require(item.get("path") == f"data/calendar/weeks/{item.get('week_id')}.json",
                "calendar path is not the canonical ISO-week database path")

    require(re.fullmatch(r"[0-9a-f]{64}", fixture_sha256 or "") is not None,
            "fixture SHA-256 missing or malformed")
    require(re.fullmatch(r"[0-9a-f]{64}", audit_sha256 or "") is not None,
            "market audit SHA-256 missing or malformed")
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha256 or "") is not None,
            "market source manifest SHA-256 missing or malformed")

    return {
        "schema_version": "1.0",
        "status": "PASS",
        "gate": "PRE_BUILD_STAGE_2_TO_4_INPUT_RECEIPT",
        "report_date": report_date,
        "repository": repository,
        "branch": branch,
        "workflow_run_id": str(workflow_run_id),
        "workflow_run_attempt": str(workflow_run_attempt),
        "fixture": {"path": f"simulation-lab/fixtures/report-data-{report_date}.json",
                    "sha256": fixture_sha256},
        "stage_2_market": {
            **market,
            "audit_path": "simulation-lab/output/market-snapshot-audit.json",
            "audit_sha256": audit_sha256,
            "manifest_path": "simulation-lab/output/market-source-verification-manifest.json",
            "manifest_sha256": manifest_sha256,
        },
        "stage_3_calendar": {
            "repository": EXPECTED_REPOSITORY,
            "branch": "main",
            "main_commit_sha": calendar_bundle["main_commit_sha"],
            "current": {k: current.get(k) for k in
                        ("path", "blob_sha", "week_id", "week_start", "week_end",
                         "economic_count", "earnings_count")},
            "previous": {k: previous.get(k) for k in
                         ("path", "blob_sha", "week_id", "week_start", "week_end",
                          "economic_count", "earnings_count")},
            "mode": "READ_ONLY_PINNED_MAIN_COMMIT",
        },
        "stage_4_news_and_analysis": stage4,
        "created_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "limitations": [
            "Stage 2 requires 44 complete current-run browser observations with independently mapped values; prior fixture observations are ineligible.",
            "raw_response_sha256 is optional and is not required for a completed per-item browser observation.",
            "Stage 3 calendar records are read-only projections from one pinned main commit.",
            "This receipt validates input identity/completeness before HTML assembly; it does not certify the later HTML or visual QA.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    args = parser.parse_args()

    data, fixture_sha = load_json(args.data)
    require(data.get("report_date") == args.report_date,
            "CLI report_date does not match the selected fixture")
    audit, audit_sha = load_json(args.audit)
    manifest, manifest_sha = load_json(args.manifest)

    remote = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
    normalized = remote.lower().removesuffix(".git").replace(
        "git@github.com:", "https://github.com/"
    ).rstrip("/")
    branch = os.environ.get("GITHUB_REF", "").removeprefix("refs/heads/")
    if not branch:
        branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    validate_branch(normalized.removeprefix("https://github.com/"), branch)

    from calendar_source_guard import load_authoritative_calendar
    calendar_bundle = load_authoritative_calendar(args.report_date)
    receipt = build_receipt(
        data=data, fixture_sha256=fixture_sha, audit=audit, audit_sha256=audit_sha,
        manifest=manifest, manifest_sha256=manifest_sha, calendar_bundle=calendar_bundle,
        repository=EXPECTED_REPOSITORY, branch=branch,
        workflow_run_id=args.run_id, workflow_run_attempt=args.run_attempt,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    out.write_bytes(raw)
    print(json.dumps({"status": receipt["status"], "output": str(out),
                      "sha256": sha256_bytes(raw), "report_date": receipt["report_date"],
                      "market_rows": receipt["stage_2_market"]["indicator_count"],
                      "main_commit_sha": receipt["stage_3_calendar"]["main_commit_sha"],
                      "news_count": receipt["stage_4_news_and_analysis"]["unique_news_urls"],
                      "workflow_run_id": receipt["workflow_run_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
