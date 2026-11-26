#!/usr/bin/env python3
"""Prepare a QA-passed Simulation build for the whitelisted main/preview delivery."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

SOURCE_BRANCH = "simulation/tac-process-lab-2026-11-06"


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class ReportMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.report_date = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attrs = dict(attrs)
        if attrs.get("name") == "report-date":
            self.report_date = attrs.get("content")


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise SystemExit(f"refusing symlink delivery target: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".tac-preview-", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)


def prepare_delivery(
    source_html: Path,
    source_qa: Path,
    main_root: Path,
    report_date: str,
    run_id: str,
    run_attempt: str,
    trigger_commit: str,
) -> dict:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_date):
        raise SystemExit("invalid report_date")
    parsed_date = date.fromisoformat(report_date)
    if parsed_date.weekday() > 4:
        raise SystemExit("weekend report date rejected")

    expected_source_html = f"preview/{report_date}-simulation.html"
    expected_source_qa = f"preview/{report_date}-simulation.qa.json"
    if source_html.as_posix().endswith(expected_source_html) is False:
        raise SystemExit(f"source HTML must be {expected_source_html}")
    if source_qa.as_posix().endswith(expected_source_qa) is False:
        raise SystemExit(f"source QA must be {expected_source_qa}")

    html = source_html.read_bytes()
    qa = json.loads(source_qa.read_text(encoding="utf-8"))
    html_sha256 = hashlib.sha256(html).hexdigest()
    html_blob_sha = git_blob_sha(html)

    parser = ReportMetaParser()
    parser.feed(html.decode("utf-8"))
    if parser.report_date != report_date:
        raise SystemExit("HTML report-date metadata missing or mismatched")

    required = {
        "status": qa.get("status") == "QA_PASSED",
        "review_ready": qa.get("review_ready") is True,
        "data_review_ready": qa.get("data_review_ready") is True,
        "sim14_review_ready": qa.get("sim14_review_ready") is True,
        "builder_approved": qa.get("sim14_builder_approval") == "APPROVED",
        "source_branch": qa.get("branch") == SOURCE_BRANCH,
        "source_path": qa.get("report_path") == expected_source_html,
        "report_date": qa.get("report_date") == report_date,
        "html_sha256": qa.get("report_sha256") == html_sha256,
        "html_blob_sha": qa.get("report_git_blob_sha") == html_blob_sha,
        "run_id": str(qa.get("workflow_run_id")) == str(run_id),
        "run_attempt": str(qa.get("workflow_run_attempt")) == str(run_attempt),
        "prebuild_receipt": bool(qa.get("prebuild_input_receipt_sha256"))
            and qa.get("prebuild_input_receipt", {}).get("status") == "PASS",
        "builder_sha": bool(qa.get("builder_blob_sha")),
        "no_review_blockers": not qa.get("review_ready_blockers") and not qa.get("sim14_blockers"),
    }
    failed = [name for name, ok in required.items() if not ok]
    if failed:
        raise SystemExit("main preview delivery gate failed: " + ", ".join(failed))

    main_root = main_root.resolve()
    if not main_root.is_dir() or main_root.is_symlink():
        raise SystemExit("main worktree root is missing or unsafe")
    preview_dir = main_root / "preview"
    if preview_dir.exists() and preview_dir.is_symlink():
        raise SystemExit("main preview directory is a symlink")
    preview_dir.mkdir(parents=True, exist_ok=True)

    homepage = main_root / "index.html"
    homepage_before = hashlib.sha256(homepage.read_bytes()).hexdigest() if homepage.exists() else None

    html_rel = f"preview/{report_date}-review.html"
    qa_rel = f"preview/{report_date}-review.qa.json"
    receipt_rel = f"preview/{report_date}-review.delivery.json"

    delivered_qa = dict(qa)
    delivered_qa.update({
        "report_path": html_rel,
        "delivery_branch": "main",
        "delivery_path": html_rel,
        "delivery_qa_path": qa_rel,
        "delivery_receipt_path": receipt_rel,
        "delivery_workflow_run_id": str(run_id),
        "delivery_workflow_run_attempt": str(run_attempt),
        "delivery_trigger_commit": trigger_commit,
    })
    qa_bytes = (json.dumps(delivered_qa, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    receipt = {
        "schema_version": 1,
        "status": "PUBLISHED_TO_MAIN_PREVIEW",
        "report_date": report_date,
        "source_branch": SOURCE_BRANCH,
        "source_html_path": expected_source_html,
        "source_qa_path": expected_source_qa,
        "target_branch": "main",
        "html_path": html_rel,
        "qa_sidecar_path": qa_rel,
        "delivery_receipt_path": receipt_rel,
        "html_git_blob_sha": html_blob_sha,
        "html_sha256": html_sha256,
        "qa_git_blob_sha": git_blob_sha(qa_bytes),
        "qa_sha256": hashlib.sha256(qa_bytes).hexdigest(),
        "workflow_run_id": str(run_id),
        "workflow_run_attempt": str(run_attempt),
        "trigger_commit": trigger_commit,
        "builder_blob_sha": qa.get("builder_blob_sha"),
        "prebuild_input_receipt_sha256": qa.get("prebuild_input_receipt_sha256"),
        "allowed_main_paths": [html_rel, qa_rel, receipt_rel],
        "homepage_index_html_modified": False,
        "calendar_json_modified": False,
        "mother_template_modified": False,
        "manifest_modified": False,
    }
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    _atomic_write(main_root / html_rel, html)
    _atomic_write(main_root / qa_rel, qa_bytes)
    _atomic_write(main_root / receipt_rel, receipt_bytes)

    homepage_after = hashlib.sha256(homepage.read_bytes()).hexdigest() if homepage.exists() else None
    if homepage_before != homepage_after:
        raise SystemExit("main index.html changed during preview preparation")

    return {
        "status": "READY_FOR_MAIN_COMMIT",
        "report_date": report_date,
        "html_path": html_rel,
        "qa_sidecar_path": qa_rel,
        "delivery_receipt_path": receipt_rel,
        "html_git_blob_sha": html_blob_sha,
        "html_sha256": html_sha256,
        "qa_git_blob_sha": git_blob_sha(qa_bytes),
        "qa_sha256": hashlib.sha256(qa_bytes).hexdigest(),
        "homepage_index_html_unchanged": True,
        "allowed_paths": [html_rel, qa_rel, receipt_rel],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-html", required=True, type=Path)
    parser.add_argument("--source-qa", required=True, type=Path)
    parser.add_argument("--main-root", required=True, type=Path)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--trigger-commit", required=True)
    args = parser.parse_args()
    result = prepare_delivery(
        args.source_html, args.source_qa, args.main_root,
        args.report_date, args.run_id, args.run_attempt, args.trigger_commit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
