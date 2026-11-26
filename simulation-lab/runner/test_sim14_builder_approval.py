#!/usr/bin/env python3
"""Deterministic regression tests for SIM-1.4 Builder approval sidecar state."""
from __future__ import annotations

from sim14_builder_approval import git_blob_sha, resolve_builder_approval


def expect_error(fn, text):
    try:
        fn()
    except ValueError as exc:
        assert text in str(exc), str(exc)
    else:
        raise AssertionError("expected ValueError")


def main():
    builder_path = "simulation-lab/runner/build_review_html.py"
    builder_bytes = b"approved builder fixture\n"
    builder_sha = git_blob_sha(builder_bytes)
    rules_text = (
        "8. **本版唯一正式 Builder 已核准：** "
        f"`{builder_path}`，blob SHA `{builder_sha}`。\n"
    )
    rules_bytes = rules_text.encode("utf-8")
    approved = resolve_builder_approval(
        rules_text, rules_bytes, builder_path, builder_bytes
    )
    assert approved["decision"] == "APPROVED"
    assert approved["approved_builder_blob_sha"] == builder_sha
    assert approved["active_rules_blob_sha"] == git_blob_sha(rules_bytes)

    # Updating an unrelated active SIM rule changes the rules blob SHA, but does
    # not revoke the separately approved Builder path/blob SHA.
    amended_rules_text = rules_text + "\n0.5.4 Stage 2 blank-first amendment.\n"
    amended_rules_bytes = amended_rules_text.encode("utf-8")
    amended = resolve_builder_approval(
        amended_rules_text, amended_rules_bytes, builder_path, builder_bytes
    )
    assert amended["decision"] == "APPROVED"
    assert amended["approved_builder_blob_sha"] == builder_sha
    assert amended["active_rules_blob_sha"] != approved["active_rules_blob_sha"]

    pending = resolve_builder_approval(
        "No approval clause.", b"No approval clause.",
        builder_path, builder_bytes
    )
    assert pending["decision"] == "NOT_APPROVED"

    historical_text = (
        "此前已核准的 Builder（歷史核准基準）： "
        f"`{builder_path}`，blob SHA `{builder_sha}`。"
    )
    historical = resolve_builder_approval(
        historical_text, historical_text.encode("utf-8"), builder_path, builder_bytes
    )
    assert historical["decision"] == "NOT_APPROVED"

    expect_error(
        lambda: resolve_builder_approval(
            rules_text, rules_bytes, "simulation-lab/runner/other_builder.py", builder_bytes
        ),
        "Builder path differs",
    )
    expect_error(
        lambda: resolve_builder_approval(
            rules_text, rules_bytes, builder_path, b"changed builder bytes\n"
        ),
        "Builder bytes differ",
    )
    print("PASS: SIM-1.4 Builder approval is derived from active rules and exact path/blob SHA")


if __name__ == "__main__":
    main()
