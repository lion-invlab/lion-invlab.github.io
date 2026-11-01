#!/usr/bin/env node
/**
 * Read-only live fallback for CME FedWatch.
 * Captures Investing.com's Fed Rate Monitor at execution time and preserves
 * both the page's own Updated timestamp and the local observation timestamp.
 */
import fs from "node:fs";
import { chromium } from "playwright";

const arg = (name) => {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : null;
};
const output = arg("--output") || "/tmp/tac-fedwatch-fallback.json";
const textOutput = arg("--text-output") || "/tmp/tac-fedwatch-fallback.txt";
const url = "https://www.investing.com/central-banks/fed-rate-monitor";
const observedAt = new Date().toISOString();
const browser = await chromium.launch({ headless: true, args: ["--disable-http2"] });
let result;
try {
  const page = await browser.newPage({
    locale: "en-US",
    timezoneId: "Asia/Taipei",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
  });
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (!response || !response.ok()) throw new Error(`Investing.com HTTP ${response?.status() ?? "no response"}`);
  await page.waitForTimeout(5000);
  const bodyText = await page.locator("body").innerText({ timeout: 20000 });
  const updatedMatches = [...bodyText.matchAll(/Updated:\s*([^\\n\\r]+)/gi)].map(m => m[1].trim());
  const meetings = [];
  const chunks = bodyText.split(/(?=\\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2},\\s+20\\d{2}\\b)/);
  for (const chunk of chunks) {
    const heading = chunk.match(/^\\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2},\\s+20\\d{2})/);
    if (!heading) continue;
    const rows = [];
    const rowPattern = /((?:\\d+\\.\\d{2,3})\\s*-\\s*(?:\\d+\\.\\d{2,3}))\\s+([0-9]+(?:\\.[0-9]+)?|—)\\s*%/g;
    for (const m of chunk.matchAll(rowPattern)) rows.push({ target_rate: m[1].replace(/\\s+/g, ""), probability: m[2] === "—" ? null : Number(m[2]) });
    const updated = chunk.match(/Updated:\\s*([^\\n\\r]+)/i)?.[1]?.trim() || null;
    if (rows.length) meetings.push({ meeting_date: heading[1], updated_at_source: updated, probabilities: rows });
  }
  const uniqueUpdated = [...new Set(updatedMatches)];
  const hasRateMonitor = /Fed Rate Monitor Tool/i.test(bodyText);
  const hasMeetingData = meetings.length > 0 && meetings.some(m => m.probabilities.length >= 2);
  const hasUpdateTime = uniqueUpdated.length > 0;
  const status = hasRateMonitor && hasMeetingData && hasUpdateTime ? "captured_for_review" : "pending_verification";
  result = {
    provider: "Investing.com Fed Rate Monitor",
    source_url: url,
    role: "fallback_only_not_CME",
    status,
    observed_at: observedAt,
    source_updated_at: uniqueUpdated,
    meetings,
    page_status: response.status(),
    validation: { has_rate_monitor: hasRateMonitor, has_meeting_data: hasMeetingData, has_source_update_time: hasUpdateTime },
    error: status === "captured_for_review" ? null : "Page did not contain a complete Fed Rate Monitor meeting/probability/update-time set"
  };
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\\n", "utf8");
  fs.writeFileSync(textOutput, bodyText, "utf8");
  console.log(JSON.stringify({ status, observed_at: observedAt, source_updated_at: uniqueUpdated, meeting_count: meetings.length, validation: result.validation, output, text_output: textOutput }, null, 2));
  if (status !== "captured_for_review") process.exitCode = 2;
} catch (error) {
  result = { provider: "Investing.com Fed Rate Monitor", source_url: url, role: "fallback_only_not_CME", status: "pending_verification", observed_at: observedAt, source_updated_at: [], meetings: [], error: error.message };
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\\n", "utf8");
  console.error(JSON.stringify(result, null, 2));
  process.exitCode = 2;
} finally {
  await browser.close();
}
