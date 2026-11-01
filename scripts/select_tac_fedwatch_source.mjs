#!/usr/bin/env node
/** Select exactly one live FedWatch source. Never merge probabilities across providers. */
import fs from "node:fs";
const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : null; };
const read = path => { try { return JSON.parse(fs.readFileSync(path, "utf8")); } catch { return null; } };
const output = arg("--output") || "/tmp/tac-fedwatch-selected.json";
const cme = read(arg("--cme") || "/tmp/tac-cme-fedwatch-capture.json");
const fallback = read(arg("--fallback") || "/tmp/tac-fedwatch-fallback.json");
const observedAt = new Date().toISOString();

// A successful page/iframe load is NOT a valid CME probability capture.
// The current CME probe only stores body_text; it does not parse structured
// meeting distributions into the snapshot adapter's supported contract.
// Keep CME unavailable until that parser and adapter are explicitly implemented.
const cmeMeetings = Array.isArray(cme?.meetings) ? cme.meetings : [];
const cmeHasStructuredDistribution = cmeMeetings.length > 0 && cmeMeetings.every(meeting =>
  typeof meeting.meeting_date === "string" &&
  Array.isArray(meeting.probabilities) && meeting.probabilities.length > 0 &&
  meeting.probabilities.every(item =>
    typeof item.target_rate === "string" &&
    typeof item.probability === "number" &&
    Number.isFinite(item.probability) && item.probability >= 0 && item.probability <= 100
  )
);
const cmeValid = cme?.status === "captured_for_review" &&
  cme?.snapshot_adapter_compatible === true &&
  cmeHasStructuredDistribution &&
  !!cme.captured_at &&
  typeof cme.page_url === "string" &&
  /cmegroup\.com/i.test(cme.page_url);
const fallbackValid = fallback?.status === "captured_for_review" &&
  fallback?.role === "fallback_only_not_CME" &&
  fallback?.source_url === "https://www.investing.com/central-banks/fed-rate-monitor" &&
  Array.isArray(fallback.meetings) && fallback.meetings.length > 0 &&
  Array.isArray(fallback.source_updated_at) && fallback.source_updated_at.length > 0 &&
  fallback.validation?.is_fresh === true;
let selected;
if (cmeValid) selected = { status: "selected_for_review", selected_source: "CME FedWatch", source_url: cme.page_url, source_observed_at: cme.captured_at, selected_at: observedAt, source_updated_at: cme.source_updated_at ?? null, meetings: cmeMeetings, selection_reason: "CME structured probability distribution passed the adapter-compatible contract." };
else if (fallbackValid) selected = { status: "selected_for_review", selected_source: "Investing.com Fed Rate Monitor", source_url: fallback.source_url, source_observed_at: fallback.observed_at, source_updated_at: fallback.source_updated_at, selected_at: observedAt, meetings: fallback.meetings, selection_reason: "CME lacks an adapter-compatible structured distribution; live fallback passed freshness and probability validation." };
else selected = { status: "pending_verification", selected_source: null, selected_at: observedAt, meetings: [], selection_reason: "Neither CME nor the live fallback passed validation; no stale values carried forward.", cme_status: cme?.status ?? "missing_or_unreadable", fallback_status: fallback?.status ?? "missing_or_unreadable" };
fs.writeFileSync(output, JSON.stringify(selected, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ status: selected.status, selected_source: selected.selected_source, selection_reason: selected.selection_reason, meeting_count: selected.meetings.length, output }, null, 2));
if (selected.status !== "selected_for_review") process.exitCode = 2;
