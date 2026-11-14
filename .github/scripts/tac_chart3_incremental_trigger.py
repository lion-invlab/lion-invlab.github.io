#!/usr/bin/env python3
"""Marker file used to run the first isolated incremental smoke test."""
# The workflow runs test_tac_chart3_incremental.py and tac_chart3_incremental.py.

# Smoke-test revision: include initial-release append-only validation.

# Smoke-test revision 2: scope output_type=4 to the last five ALFRED vintage dates.

# Smoke-test revision 3: run chart dataset QA and materialize chart-ready JSON.

# Smoke-test revision 4: assert deterministic no-change chart dataset generation.

# Smoke-test revision 5: deterministic chart builder syntax fix.

# Smoke-test revision 6: verify full FRED observations pagination and truncation guard.

# Smoke-test revision 7: honor sparse output_type=3 result counts.

# Smoke-test revision 8: run streaming full-history vintage integrity QA.

# Smoke-test revision 9: clean rerun after branch fast-forward conflict.

# Smoke-test revision 10: validate strict point-in-time reconstruction and current snapshot parity.

# Smoke-test revision 11: commit verified chart QA and point-in-time snapshot changes from frozen branch head.

# Smoke-test revision 12: validate dynamically resolved latest-vintage-plus-one as-of date.

# Scheduled incremental trigger: 2026-11-12T05:34:23+08:00; branch-isolated; no full-history reload.

# Scheduled incremental trigger: 2026-11-13T05:28:14+08:00; branch-isolated; five-vintage overlap; no full-history vintage reload.

# Main-branch migration smoke trigger: rebuild chart-ready JSON after baseline bootstrap.

# Main-branch incremental execution trigger: 2026-11-14T13:xx:xx+08:00; provenance manifest corrected; verify current snapshots and ALFRED vintages.
# Trigger the scheduled FRED/ALFRED incremental refresh after release-calendar support.
