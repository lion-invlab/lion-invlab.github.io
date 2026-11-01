#!/usr/bin/env node
/** Live, read-only Investing.com fallback capture. Never labels fallback data as CME. */
import fs from "node:fs";
import { chromium } from "playwright";

const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : null; };
const output = arg("--output") || "/tmp/tac-fedwatch-fallback.json";
const textOutput = arg("--text-output") || "/tmp/tac-fedwatch-fallback.txt";
const url = "https://www.investing.com/central-banks/fed-rate-monitor";
const observedAt = new Date().toISOString();

function parseInvestingTimestamp(value) {
  // Parse the source's US timezone abbreviation explicitly; Date.parse does
  // not reliably accept strings such as "12:35AM EDT" in Node.
  const match = String(value).trim().match(
    /^([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*(EDT|EST|CDT|CST|MDT|MST|PDT|PST)$/i
  );
  if (!match) return NaN;
  const months = {jan:0,feb:1,mar:2,apr:3,may:4,jun:5,jul:6,aug:7,sep:8,oct:9,nov:10,dec:11};
  const [, mon, dayText, yearText, hourText, minuteText, meridiem, zone] = match;
  const month = months[mon.toLowerCase()];
  if (month === undefined) return NaN;
  let hour = Number(hourText) % 12;
  if (meridiem.toUpperCase() === "PM") hour += 12;
  const offsets = {EDT:-4,EST:-5,CDT:-5,CST:-6,MDT:-6,MST:-7,PDT:-7,PST:-8};
  const localAsUtc = Date.UTC(Number(yearText), month, Number(dayText), hour, Number(minuteText));
  return localAsUtc - offsets[zone.toUpperCase()] * 60 * 60 * 1000;
}

if (process.argv.includes("--self-test")) {
  const cases = [
    ["Oct 31, 2026 12:35AM EDT", "2026-10-31T04:35:00.000Z"],
    ["Oct 30, 2026 10:45 PM EDT", "2026-10-31T02:45:00.000Z"],
    ["Nov 2, 2026 9:15AM EST", "2026-11-02T14:15:00.000Z"]
  ];
  for (const [input, expected] of cases) {
    const actual = parseInvestingTimestamp(input);
    if (!Number.isFinite(actual) || new Date(actual).toISOString() !== expected) {
      throw new Error(`Timestamp parse failed: ${input} => ${Number.isFinite(actual) ? new Date(actual).toISOString() : "NaN"}; expected ${expected}`);
    }
  }
  console.log("PASS: Investing.com EDT/EST timestamps normalize to correct UTC instants");
  process.exit(0);
}

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
  const parsedUpdate = sourceUpdatedAt.length ? parseInvestingTimestamp(sourceUpdatedAt[0]) : NaN;
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
