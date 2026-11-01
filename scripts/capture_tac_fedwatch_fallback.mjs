#!/usr/bin/env node
/** Live, read-only Investing.com fallback capture. Never labels fallback data as CME. */
import fs from "node:fs";
import { chromium } from "playwright";

const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : null; };
const output = arg("--output") || "/tmp/tac-fedwatch-fallback.json";
const textOutput = arg("--text-output") || "/tmp/tac-fedwatch-fallback.txt";
const url = "https://www.investing.com/central-banks/fed-rate-monitor";
const observedAt = new Date().toISOString();
let browser;
try {
  browser = await chromium.launch({ headless: true, args: ["--disable-http2"] });
  const page = await browser.newPage({ locale: "en-US", timezoneId: "Asia/Taipei",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" });
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (!response?.ok()) throw new Error(`Investing.com HTTP ${response?.status() ?? "no response"}`);
  await page.waitForTimeout(5000);
  const bodyText = await page.locator("body").innerText({ timeout: 20000 });
  const updatedMatches = [...bodyText.matchAll(/Updated:\s*([^\n\r]+)/gi)].map(m => m[1].trim());
  const dateRe = /\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b/g;
  const dates = [...bodyText.matchAll(dateRe)].map(m => ({ date: m[0], index: m.index }));
  const meetings = [];
  for (let i = 0; i < dates.length; i++) {
    const chunk = bodyText.slice(dates[i].index, dates[i + 1]?.index ?? bodyText.length);
    const rows = [];
    const rowRe = /(\d+\.\d{2,3}\s*-\s*\d+\.\d{2,3})\s+([0-9]+(?:\.[0-9]+)?|—)\s*%/g;
    for (const m of chunk.matchAll(rowRe)) rows.push({ target_rate: m[1].replace(/\s+/g, ""), probability: m[2] === "—" ? null : Number(m[2]) });
    if (rows.length) meetings.push({ meeting_date: dates[i].date, probabilities: rows });
  }
  const sourceUpdatedAt = [...new Set(updatedMatches)];
  const parsedUpdate = sourceUpdatedAt.length ? Date.parse(sourceUpdatedAt[0]) : NaN;
  const ageHours = Number.isFinite(parsedUpdate) ? (Date.now() - parsedUpdate) / 3600000 : null;
  const freshnessLimitHours = 72; // permits the latest Friday close to remain valid over a weekend
  const fresh = ageHours !== null && ageHours >= -1 && ageHours <= freshnessLimitHours;
  const hasData = meetings.length > 0 && meetings.some(m => m.probabilities.length >= 2);
  const isMonitor = /Fed Rate Monitor/i.test(bodyText);
  const status = isMonitor && hasData && fresh ? "captured_for_review" : "pending_verification";
  const result = { provider: "Investing.com Fed Rate Monitor", source_url: url, role: "fallback_only_not_CME",
    status, observed_at: observedAt, source_updated_at: sourceUpdatedAt, source_age_hours: ageHours,
    freshness_limit_hours: freshnessLimitHours, meetings, page_status: response.status(),
    validation: { is_monitor: isMonitor, has_meeting_probabilities: hasData, has_source_update_time: sourceUpdatedAt.length > 0, is_fresh: fresh },
    error: status === "captured_for_review" ? null : "Missing meeting probabilities or source Updated time, or source data is stale" };
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\n", "utf8");
  fs.writeFileSync(textOutput, bodyText, "utf8");
  console.log(JSON.stringify({ status, observed_at: observedAt, source_updated_at: sourceUpdatedAt, source_age_hours: ageHours, meeting_count: meetings.length, validation: result.validation }, null, 2));
  if (status !== "captured_for_review") process.exitCode = 2;
} catch (error) {
  const result = { provider: "Investing.com Fed Rate Monitor", source_url: url, role: "fallback_only_not_CME",
    status: "pending_verification", observed_at: observedAt, source_updated_at: [], meetings: [], error: error.message };
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\n", "utf8");
  console.error(JSON.stringify(result, null, 2));
  process.exitCode = 2;
} finally { if (browser) await browser.close(); }
