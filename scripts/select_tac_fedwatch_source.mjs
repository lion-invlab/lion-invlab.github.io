#!/usr/bin/env node
/** Select exactly one live FedWatch source. Never merge probabilities across providers. */
import fs from "node:fs";
const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : null; };
const read = path => { try { return JSON.parse(fs.readFileSync(path, "utf8")); } catch { return null; } };
const output = arg("--output") || "/tmp/tac-fedwatch-selected.json";
const cme = read(arg("--cme") || "/tmp/tac-cme-fedwatch-capture.json");
const fallback = read(arg("--fallback") || "/tmp/tac-fedwatch-fallback.json");
const observedAt = new Date().toISOString();
const cmeValid = cme?.status === "captured_for_review" && typeof cme.body_text === "string" && /FedWatch|Target Rate|Probability/i.test(cme.body_text) && /%/.test(cme.body_text) && !!cme.captured_at;
const fallbackValid = fallback?.status === "captured_for_review" && fallback?.role === "fallback_only_not_CME" && Array.isArray(fallback.meetings) && fallback.meetings.length > 0 && Array.isArray(fallback.source_updated_at) && fallback.source_updated_at.length > 0 && fallback.validation?.is_fresh === true;
let selected;
if (cmeValid) selected = { status: "selected_for_review", selected_source: "CME FedWatch", source_url: cme.page_url, source_observed_at: cme.captured_at, selected_at: observedAt, source_updated_at: null, raw_body_text: cme.body_text, meetings: [], selection_reason: "CME primary capture passed validation; fallback not selected." };
else if (fallbackValid) selected = { status: "selected_for_review", selected_source: "Investing.com Fed Rate Monitor", source_url: fallback.source_url, source_observed_at: fallback.observed_at, source_updated_at: fallback.source_updated_at, selected_at: observedAt, meetings: fallback.meetings, selection_reason: "CME capture unavailable or invalid; live fallback passed freshness and probability validation." };
else selected = { status: "pending_verification", selected_source: null, selected_at: observedAt, meetings: [], selection_reason: "Neither CME nor the live fallback passed validation; no stale values carried forward.", cme_status: cme?.status ?? "missing_or_unreadable", fallback_status: fallback?.status ?? "missing_or_unreadable" };
fs.writeFileSync(output, JSON.stringify(selected, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ status: selected.status, selected_source: selected.selected_source, selection_reason: selected.selection_reason, meeting_count: selected.meetings.length, output }, null, 2));
if (selected.status !== "selected_for_review") process.exitCode = 2;
