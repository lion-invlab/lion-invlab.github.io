#!/usr/bin/env python3
"""Fail early when a TAC workflow step exceeds GitHub's 21,000-character run limit."""
from pathlib import Path
import sys
import yaml

LIMIT = 21000
WORKFLOW = Path(".github/workflows/tac-simulation-lab.yml")

def main() -> int:
    if not WORKFLOW.is_file():
        raise SystemExit(f"Missing workflow: {WORKFLOW}")
    document = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        raise SystemExit("Workflow has no jobs mapping")
    checked = 0
    violations = []
    for job_id, job in jobs.items():
        for index, step in enumerate(job.get("steps") or [], start=1):
            command = step.get("run") if isinstance(step, dict) else None
            if not isinstance(command, str):
                continue
            checked += 1
            size = len(command)
            if size > LIMIT:
                violations.append((job_id, step.get("name") or f"step {index}", size))
    if violations:
        for job_id, name, size in violations:
            print(f"FAIL: {job_id} / {name}: {size} chars (limit {LIMIT})", file=sys.stderr)
        return 1
    print(f"PASS: {checked} run commands are within the {LIMIT}-character GitHub limit")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
