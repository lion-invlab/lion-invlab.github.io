#!/usr/bin/env python3
"""Main-native pre-build receipt binding Stage 2-4 inputs to one run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_REPOSITORY = "lion-invlab/lion-invlab.github.io"
EXPECTED_BRANCH = "main"
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

def parse_taipei_datetime(value: str) -> datetime:
    raw = str(value).strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError(f"invalid Taiwan-local datetime: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(ZoneInfo("Asia/Taipei")).replace(tzinfo=None)
    return parsed


def validate_branch(repository: str, branch: str) -> None:
    require(repository.rstrip("/").lower() == EXPECTED_REPOSITORY,
            f"repository mismatch: {repository!r}")
    require(branch == EXPECTED_BRANCH,
            f"refusing non-main branch: {branch!r}")


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

    require(manifest.get("status") in ("PASS", "PARTIAL", "PENDING"),
            "market source observation manifest is neither PASS nor PARTIAL")
    require(manifest.get("report_date") == report_date, "source manifest report_date mismatch")
    require(manifest.get("trading_date") == trading_date, "source manifest trading_date mismatch")
    verified_count = manifest.get("verified_count")
    pending_count = manifest.get("pending_count")
    closed_count = manifest.get("closed_count", 0)
    require(manifest.get("row_count") == 44
            and all(isinstance(x, int) and x >= 0 for x in (verified_count, pending_count, closed_count))
            and verified_count + pending_count + closed_count == 44,
            "44-row source register is incomplete or verified + pending + closed counts do not reconcile")
    require(manifest.get("prior_observation_reused_count") == 0,
            "current-run verification must not reuse prior fixture observations")
    require(manifest.get("source_pages_fetched") in (True, False)
            and manifest.get("displayed_values_reconciled") is (verified_count + closed_count == 44 and pending_count == 0),
            "source value reconciliation summary does not match verified-row count")
    screenshot_field_count = manifest.get("screenshot_field_count", 0)
    require(isinstance(screenshot_field_count, int) and screenshot_field_count >= 0,
            "screenshot field count is malformed")
    require(manifest.get("displayed_values_independently_reconciled") is (
                verified_count + closed_count == 44 and pending_count == 0 and screenshot_field_count == 0
            ),
            "independent history-page reconciliation flag does not match screenshot evidence count")
    require(manifest.get("verification_scope") in (
                "CURRENT_REPORT_SESSION_SOURCE_OBSERVATIONS",
                "CURRENT_REPORT_SESSION_FIELD_LEVEL_SOURCE_OBSERVATIONS",
            ),
            "unexpected source manifest verification scope")
    require(manifest.get("observation_record_hash_missing_count") == 0,
            "a verified observation is missing its record hash")
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
    allowed_provenance = {
        "CURRENT_RUN_BROWSER_OBSERVATION",
        "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
        "CURRENT_CHATGPT_WEB_SEARCH_RESULT_OBSERVATION",
        "CURRENT_CNN_OFFICIAL_API_OBSERVATION",
        "CURRENT_RUN_MIXED_FIELD_OBSERVATION",
        "USER_SUPPLIED_SCREENSHOT",
        "CURRENT_USER_PROVIDED_SCREENSHOT",
        "SYNTHETIC_TEST_ONLY",
    }
    for row in rows:
        require(row.get("trading_date") == trading_date,
                f"source manifest contains mixed trading dates: {row.get('name')}")
        if row.get("verification_status") in ("VERIFIED", "BACKUP_VERIFIED"):
            require(row.get("display_value_matches_saved_observation") is True
                    and row.get("observation_provenance") in allowed_provenance,
                    f"verified row lacks current-session evidence: {row.get('name')}")
            record = row.get("browser_observation_record")
            require(isinstance(record, dict) and record.get("source_url")
                    and record.get("data_date") == trading_date
                    and record.get("observed_value") is not None
                    and record.get("observed_change") is not None
                    and record.get("checked_at_tw"),
                    f"verified row observation record incomplete: {row.get('name')}")
            provenance = row.get("observation_provenance")
            if provenance == "CURRENT_USER_PROVIDED_SCREENSHOT":
                require(row.get("source_page_fetched") is False,
                        f"screenshot-only row must not claim a history-page read: {row.get('name')}")
            else:
                require(row.get("source_page_fetched") is True,
                        f"page-completed row lacks a current source-page read: {row.get('name')}")
            require(row.get("display_value_reconciled") is True,
                    f"verified row was not reconciled: {row.get('name')}")
            if provenance in ("CURRENT_USER_PROVIDED_SCREENSHOT", "CURRENT_RUN_MIXED_FIELD_OBSERVATION"):
                evidence_fields = (record.get("field_evidence") or {})
                required_fields = ("score", "band") if row.get("group") == "risk" and row.get("name") == "fear_greed" else ("close", "change")
                require(record.get("screenshot_instrument_identity_status") == "VERIFIED",
                        f"screenshot-backed row lacks screenshot instrument identity verification: {row.get('name')}")
                for field in required_fields:
                    evidence = evidence_fields.get(field) or {}
                    require(bool(evidence), f"screenshot-backed row missing required field evidence: {row.get('name')}/{field}")
                    if provenance == "CURRENT_USER_PROVIDED_SCREENSHOT":
                        require(evidence.get("source_type") == "USER_PROVIDED_SCREENSHOT",
                                f"screenshot-only required field has non-screenshot provenance: {row.get('name')}/{field}")
                    else:
                        require(evidence.get("source_type") in ("USER_PROVIDED_SCREENSHOT", "INVESTING_HISTORICAL_PAGE", "CNN_OFFICIAL_API"),
                                f"mixed field has unknown source provenance: {row.get('name')}/{field}")
                for evidence in evidence_fields.values():
                    if evidence.get("source_type") == "USER_PROVIDED_SCREENSHOT":
                        evidence_path = Path(str(evidence.get("evidence_path") or ""))
                        if not evidence_path.is_absolute():
                            evidence_path = Path.cwd() / evidence_path
                        require(evidence_path.is_file(), f"screenshot evidence file missing: {row.get('name')}")
                        require(sha256_bytes(evidence_path.read_bytes()) == evidence.get("evidence_sha256"),
                                f"screenshot evidence SHA mismatch: {row.get('name')}")
            require(row.get("observation_record_sha256")
                    and re.fullmatch(r"[0-9a-f]{64}", row["observation_record_sha256"]),
                    f"verified row observation hash invalid: {row.get('name')}")
        else:
            state = row.get("verification_status")
            require(state in ("PENDING_CURRENT_RUN_BROWSER_OBSERVATION", "CLOSED"),
                    f"unknown source status: {row.get('name')}")
            require(row.get("display_value_matches_saved_observation") is False,
                    f"unverified/closed row cannot claim a value match: {row.get('name')}")
            if state == "CLOSED":
                require(row.get("evidence_status") == "MARKET_CLOSED"
                        and row.get("source_page_fetched") is True,
                        f"closed row lacks direct page/holiday evidence: {row.get('name')}")
    # raw_response_sha256 is optional evidence; absence is not a Stage 2 failure.
    raw_hash_count = manifest.get("raw_response_sha256_saved_count", 0)
    require(isinstance(raw_hash_count, int) and 0 <= raw_hash_count <= 44,
            "raw response hash count is malformed")
    return {
        "trading_date": trading_date,
        "indicator_count": 44,
        "group_counts": EXPECTED_GROUP_COUNTS,
        "observation_count": len(rows),
        "observation_record_hash_count": verified_count,
        "closed_count": closed_count,
        "prior_observations_reused": 0,
        "source_pages_fetched_this_run": manifest.get("source_pages_fetched"),
        "numeric_values_reconciled_this_run": manifest.get("displayed_values_reconciled") is True,
        "numeric_values_independently_reconciled_this_run": manifest.get("displayed_values_independently_reconciled") is True,
        "numeric_values_reconciled_count": verified_count,
        "source_verification_status": manifest.get("status"),
        "pending_observation_count": pending_count,
        "raw_response_sha256_saved_count": raw_hash_count,
    }



def validate_observation_bundle(bundle: dict, report_date: str, trading_date: str) -> dict:
    require(bundle.get("report_date") == report_date, "observation bundle report_date mismatch")
    require(bundle.get("trading_date") == trading_date, "observation bundle trading_date mismatch")
    observations = bundle.get("observations")
    require(isinstance(observations, list) and len(observations) == 44,
            "observation bundle must contain exactly 44 rows")
    require(bundle.get("row_count", 44) == 44, "observation bundle row_count metadata mismatch")
    keys = set()
    screenshot_only = mixed = page_only = 0
    for row in observations:
        key = (row.get("group"), row.get("name"))
        require(all(key) and key not in keys, f"observation bundle has duplicate or unnamed row: {key}")
        keys.add(key)
        require(row.get("target_date") == trading_date,
                f"observation bundle target date mismatch: {key}")
        require(bool(row.get("source_url")), f"observation bundle source URL missing: {key}")
        digest = str(row.get("observation_record_sha256") or "")
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                f"observation bundle row hash missing or malformed: {key}")
        if row.get("status") not in ("CLOSED", "MARKET_CLOSED"):
            canonical_row = dict(row)
            canonical_row.pop("observation_record_sha256", None)
            canonical = json.dumps(canonical_row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            require(hashlib.sha256(canonical).hexdigest() == digest,
                    f"observation bundle row SHA-256 mismatch: {key}")
        if row.get("status") == "VERIFIED":
            value_key = row.get("observed_value_key") or ("score" if key == ("risk", "fear_greed") else "close")
            change_key = row.get("observed_change_key") or ("band" if key == ("risk", "fear_greed") else "change")
            evidence = row.get("field_evidence") or {}
            require(row.get("observed_value") is not None and row.get("observed_change") is not None,
                    f"verified observation missing required values: {key}")
            require(value_key in evidence and change_key in evidence,
                    f"verified observation missing field-level provenance: {key}")
            types = {item.get("source_type") for item in evidence.values() if isinstance(item, dict)}
            if row.get("read_method") == "USER_PROVIDED_SCREENSHOT":
                require(row.get("source_page_fetched") is False,
                        f"screenshot-only observation falsely claims a page read: {key}")
                screenshot_only += 1
                require(types == {"USER_PROVIDED_SCREENSHOT"},
                        f"screenshot-only observation contains non-screenshot fields: {key}")
            elif str(row.get("read_method") or "").startswith("MIXED_SCREENSHOT_"):
                require(row.get("source_page_fetched") is True,
                        f"mixed observation lacks a page/official-source read: {key}")
                mixed += 1
                require("USER_PROVIDED_SCREENSHOT" in types,
                        f"mixed observation missing screenshot field provenance: {key}")
                require(bool(types & {"INVESTING_HISTORICAL_PAGE", "CNN_OFFICIAL_API"}),
                        f"mixed observation missing page/official-source field provenance: {key}")
            else:
                require(row.get("source_page_fetched") is True,
                        f"page-only observation lacks a current source-page read: {key}")
                page_only += 1
                require(bool(types), f"page observation missing field provenance: {key}")
    return {
        "row_count": len(observations),
        "screenshot_only_row_count": screenshot_only,
        "mixed_field_row_count": mixed,
        "page_only_row_count": page_only,
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
    start_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2} \d{2}:\d{2})", str(data.get("news_window_taipei", "")))
    end_text = data.get("news_cutoff_taipei")
    require(start_match and end_text, "news window start/cutoff missing")
    start = parse_taipei_datetime(start_match.group(1))
    end = parse_taipei_datetime(str(end_text))
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
        published = parse_taipei_datetime(item["published_at_tw"])
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
    require(isinstance(findings, list),
            "political/geopolitical scan findings must be an explicit list")
    if not findings:
        require(bool(str(political_scan.get("no_material_change_note") or "").strip()),
                "empty political scan requires a documented no-material-change conclusion")
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
                  workflow_run_id: str, workflow_run_attempt: str,
                  observation_bundle: dict | None = None,
                  observation_bundle_sha256: str | None = None,
                  observation_bundle_path: str = "production/runs/current/market-history-browser-observations.json") -> dict:
    validate_branch(repository, branch)
    report_date = str(data.get("report_date") or "")
    market = validate_market_inputs(data, audit, manifest, report_date)
    stage4 = validate_stage4(data, report_date)
    observation_summary = None
    if observation_bundle is not None:
        observation_summary = validate_observation_bundle(
            observation_bundle, report_date, str(data.get("trading_date") or "")
        )
        observation_map = {
            (row.get("group"), row.get("name")): row
            for row in observation_bundle.get("observations", [])
        }
        manifest_map = {
            (row.get("group"), row.get("name")): row
            for row in manifest.get("rows", [])
        }
        require(set(observation_map) == set(manifest_map),
                "observation bundle identities do not match the 44-row Manifest")
        for key, manifest_row in manifest_map.items():
            observation = observation_map[key]
            require(observation.get("source_url") == manifest_row.get("source_url")
                    and observation.get("target_date") == manifest_row.get("trading_date"),
                    f"observation bundle source/date mismatch with Manifest: {key}")
            if manifest_row.get("verification_status") in ("VERIFIED", "BACKUP_VERIFIED"):
                record = manifest_row.get("browser_observation_record") or {}
                require(observation.get("status") == "VERIFIED"
                        and observation.get("observed_value") == record.get("observed_value")
                        and observation.get("observed_change") == record.get("observed_change"),
                        f"observation bundle values do not match verified Manifest record: {key}")
        require(re.fullmatch(r"[0-9a-f]{64}", observation_bundle_sha256 or "") is not None,
                "observation bundle SHA-256 missing or malformed")

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
        "schema_version": "1.1",
        "status": "PASS",
        "gate": "PRE_BUILD_STAGE_2_TO_4_INPUT_RECEIPT",
        "report_date": report_date,
        "repository": repository,
        "branch": branch,
        "workflow_run_id": str(workflow_run_id),
        "workflow_run_attempt": str(workflow_run_attempt),
        "fixture": {"path": (data.get("run_metadata") or {}).get("fixture_path", "production/runs/current/report-data.json"),
                    "sha256": fixture_sha256},
        "stage_2_market": {
            **market,
            "audit_path": (data.get("run_metadata") or {}).get("market_audit_path", "production/runs/current/market-snapshot-audit.json"),
            "audit_sha256": audit_sha256,
            "manifest_path": (data.get("run_metadata") or {}).get("market_manifest_path", "production/runs/current/market-source-verification-manifest.json"),
            "manifest_sha256": manifest_sha256,
            **({
                "observation_bundle_path": observation_bundle_path,
                "observation_bundle_sha256": observation_bundle_sha256,
                **observation_summary,
            } if observation_summary is not None else {}),
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
            "Stage 2 requires a complete 44-row current-session source register; rows may be verified from SHA-bound user screenshot fields, mixed screenshot/page fields, or current approved source-page fields. Screenshot-backed rows are not misreported as independently page-reconciled; pending rows must render as 待核實; prior fixture observations are ineligible.",
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
    parser.add_argument("--observations", default="production/runs/current/market-history-browser-observations.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    args = parser.parse_args()

    data, fixture_sha = load_json(args.data)
    require(data.get("report_date") == args.report_date,
            "CLI report_date does not match the selected fixture")
    audit, audit_sha = load_json(args.audit)
    manifest, manifest_sha = load_json(args.manifest)
    require(Path(args.observations).is_file(), "final 44-row observation bundle is missing")
    observation_bundle, observation_bundle_sha = load_json(args.observations)

    remote = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
    normalized = remote.lower().removesuffix(".git").replace(
        "git@github.com:", "https://github.com/"
    ).rstrip("/")
    branch = os.environ.get("GITHUB_REF", "").removeprefix("refs/heads/")
    if not branch:
        branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    validate_branch(normalized.removeprefix("https://github.com/"), branch)

    from calendar_source_guard import load_authoritative_calendar
    calendar_bundle = load_authoritative_calendar(args.report_date, expected_commit=(data.get("run_metadata") or {}).get("main_commit_sha"))
    receipt = build_receipt(
        data=data, fixture_sha256=fixture_sha, audit=audit, audit_sha256=audit_sha,
        manifest=manifest, manifest_sha256=manifest_sha, calendar_bundle=calendar_bundle,
        repository=EXPECTED_REPOSITORY, branch=branch,
        workflow_run_id=args.run_id, workflow_run_attempt=args.run_attempt,
        observation_bundle=observation_bundle,
        observation_bundle_sha256=observation_bundle_sha,
        observation_bundle_path=args.observations,
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
