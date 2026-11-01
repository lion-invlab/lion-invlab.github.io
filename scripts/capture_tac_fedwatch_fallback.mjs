#!/usr/bin/env node
/** Live, read-only primary capture from the WR-designated Investing.com Fed Rate Monitor. */
import fs from "node:fs";

const arg = name => { const i = process.argv.indexOf(name); return i >= 0 ? process.argv[i + 1] : null; };
const output = arg("--output") || "/tmp/tac-fedwatch-primary.json";
const textOutput = arg("--text-output") || "/tmp/tac-fedwatch-primary.txt";
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

function parseMeetingsFromText(bodyText) {
  const dateRe = /\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\b/g;
  const dates = [...bodyText.matchAll(dateRe)].map(m => ({ date: m[0], index: m.index }));
  const byDate = new Map();
  const conflicts = [];
  for (let i = 0; i < dates.length; i++) {
    const chunk = bodyText.slice(dates[i].index, dates[i + 1]?.index ?? bodyText.length);
    const rowRe = /(\d+\.\d{2,3}\s*-\s*\d+\.\d{2,3})\s+([0-9]+(?:\.[0-9]+)?|—)\s*%/g;
    if (!byDate.has(dates[i].date)) byDate.set(dates[i].date, new Map());
    const rows = byDate.get(dates[i].date);
    for (const m of chunk.matchAll(rowRe)) {
      const rate = m[1].replace(/\s+/g, "");
      const probability = m[2] === "—" ? null : Number(m[2]);
      if (rows.has(rate) && rows.get(rate) !== probability) {
        conflicts.push({meeting_date:dates[i].date,target_rate:rate,values:[rows.get(rate),probability]});
      } else if (!rows.has(rate)) {
        rows.set(rate, probability);
      }
    }
  }
  const meetings = [...byDate.entries()]
    .map(([meeting_date, rows]) => ({
      meeting_date,
      probabilities:[...rows.entries()].map(([target_rate,probability])=>({target_rate,probability}))
    }))
    .filter(m => m.probabilities.length > 0);
  return {meetings, conflicts};
}
function parseCurrentTargetRange(bodyText) {
  const patterns = [
    /Current\s+(?:Federal\s+Funds|Fed\s+Funds)\s+(?:Target\s+)?(?:Rate\s+)?(?:Range)?\s*[:：]?\s*(\d+\.\d{2,3})\s*[-–]\s*(\d+\.\d{2,3})\s*%?/i,
    /Current\s+Target\s+Range\s*[:：]?\s*(\d+\.\d{2,3})\s*[-–]\s*(\d+\.\d{2,3})\s*%?/i,
    /Current\s+Rate\s+Range\s*[:：]?\s*(\d+\.\d{2,3})\s*[-–]\s*(\d+\.\d{2,3})\s*%?/i
  ];
  for (const pattern of patterns) {
    const match = bodyText.match(pattern);
    if (!match) continue;
    const lower = Number(match[1]);
    const upper = Number(match[2]);
    if (!Number.isFinite(lower) || !Number.isFinite(upper) || upper <= lower) return null;
    return lower.toFixed(2) + "-" + upper.toFixed(2);
  }
  return null;
}

function validateMeetingDistribution(meetings, conflicts) {
  if (conflicts.length || !meetings.length) return false;
  return meetings.every(meeting => {
    if (meeting.probabilities.length !== 2) return false;
    if (meeting.probabilities.some(p => !Number.isFinite(p.probability) || p.probability < 0 || p.probability > 100)) return false;
    const total = meeting.probabilities.reduce((sum,p)=>sum+p.probability,0);
    return Math.abs(total-100) <= 0.2;
  });
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
  const duplicateText = [
    "Dec 09, 2026",
    "3.75-4.00 30.2 %",
    "4.00-4.25 69.8 %",
    "Dec 09, 2026",
    "3.75-4.00 30.2 %",
    "4.00-4.25 69.8 %"
  ].join("\n");
  const normalized = parseMeetingsFromText(duplicateText);
  const currentRange = parseCurrentTargetRange("Current Fed Funds Rate Range: 3.75-4.00%");
  if (currentRange !== "3.75-4.00") throw new Error("Current target rate range parsing failed");
  if (normalized.meetings.length !== 1 || normalized.meetings[0].probabilities.length !== 2 ||
      !validateMeetingDistribution(normalized.meetings, normalized.conflicts)) {
    throw new Error("Duplicate FedWatch sections were not safely normalized");
  }
  const conflictText = [
    "Dec 09, 2026",
    "3.75-4.00 30.2 %",
    "4.00-4.25 69.8 %",
    "Dec 09, 2026",
    "3.75-4.00 31.0 %",
    "4.00-4.25 69.0 %"
  ].join("\n");
  const conflict = parseMeetingsFromText(conflictText);
  if (!conflict.conflicts.length || validateMeetingDistribution(conflict.meetings, conflict.conflicts)) {
    throw new Error("Conflicting duplicate FedWatch probabilities were not rejected");
  }
  console.log("PASS: Investing.com EDT/EST timestamps; duplicate FedWatch rows deduplicated; conflicting distributions rejected");
  process.exit(0);
}

let browser;
try {
  const { chromium } = await import("playwright");
  browser = await chromium.launch({ headless: true, args: ["--disable-http2"] });
  const page = await browser.newPage({ locale: "en-US", timezoneId: "Asia/Taipei",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" });
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (!response?.ok()) throw new Error(`Investing.com HTTP ${response?.status() ?? "no response"}`);
  await page.waitForTimeout(5000);
  const bodyText = await page.locator("body").innerText({ timeout: 20000 });
  const updatedMatches = [...bodyText.matchAll(/Updated:\s*([^\n\r]+)/gi)].map(m => m[1].trim());
  const {meetings, conflicts} = parseMeetingsFromText(bodyText);
  const currentTargetRange = parseCurrentTargetRange(bodyText);
  const sourceUpdatedAt = [...new Set(updatedMatches)];
  const parsedUpdate = sourceUpdatedAt.length ? parseInvestingTimestamp(sourceUpdatedAt[0]) : NaN;
  const ageHours = Number.isFinite(parsedUpdate) ? (Date.now() - parsedUpdate) / 3600000 : null;
  const freshnessLimitHours = 72; // permits the latest Friday close to remain valid over a weekend
  const fresh = ageHours !== null && ageHours >= -1 && ageHours <= freshnessLimitHours;
  const hasData = validateMeetingDistribution(meetings, conflicts);
  const isMonitor = /Fed Rate Monitor/i.test(bodyText);
  const status = isMonitor && hasData && fresh && currentTargetRange ? "captured_for_review" : "pending_verification";
  const result = { provider: "Investing.com Fed Rate Monitor", source_url: url, role: "primary",
    status, observed_at: observedAt, source_updated_at: sourceUpdatedAt,
    source_updated_at_iso: Number.isFinite(parsedUpdate) ? new Date(parsedUpdate).toISOString() : null,
    source_age_hours: ageHours, freshness_limit_hours: freshnessLimitHours,
    current_target_range: currentTargetRange, meetings, page_status: response.status(),
    validation: { is_monitor: isMonitor, has_meeting_probabilities: hasData, has_unique_meetings: meetings.length > 0, has_unique_rate_ranges: meetings.every(m=>m.probabilities.length===2), probabilities_sum_to_100: meetings.every(m=>Math.abs(m.probabilities.reduce((sum,p)=>sum+p.probability,0)-100)<=0.2), has_current_target_range: Boolean(currentTargetRange), has_conflicts: conflicts.length>0, has_source_update_time: sourceUpdatedAt.length > 0, is_fresh: fresh },
    deduplication_conflicts: conflicts,
    error: status === "captured_for_review" ? null : "Missing meeting probabilities, current target range or source Updated time, or source data is stale" };
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\n", "utf8");
  fs.writeFileSync(textOutput, bodyText, "utf8");
  console.log(JSON.stringify({ status, observed_at: observedAt, source_updated_at: sourceUpdatedAt, source_age_hours: ageHours, meeting_count: meetings.length, validation: result.validation }, null, 2));
  if (status !== "captured_for_review") process.exitCode = 2;
} catch (error) {
  const result = { provider: "Investing.com Fed Rate Monitor", source_url: url, role: "primary",
    status: "pending_verification", observed_at: observedAt, source_updated_at: [],
    current_target_range: null, meetings: [], error: error.message };
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + "\n", "utf8");
  console.error(JSON.stringify(result, null, 2));
  process.exitCode = 2;
} finally { if (browser) await browser.close(); }
