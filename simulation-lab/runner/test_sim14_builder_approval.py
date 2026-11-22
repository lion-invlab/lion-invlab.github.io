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

    pending = resolve_builder_approval(
        "No approval clause.", b"No approval clause.",
        builder_path, builder_bytes
    )
    assert pending["decision"] == "NOT_APPROVED"

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
