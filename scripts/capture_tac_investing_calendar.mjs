#!/usr/bin/env node
/**
 * Capture Investing.com economic calendar through ordinary public webpage navigation.
 * Try the preferred Hong Kong site first, then official regional/global hosts.
 * No private/protected JSON endpoints are called.
 */
import fs from "node:fs";
import { chromium } from "playwright";

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : null;
}
const start = arg("--start-date");
const end = arg("--end-date");
const output = arg("--output");
if (!start || !end || !output) {
  console.error("Usage: node capture_tac_investing_calendar.mjs --start-date YYYY-MM-DD --end-date YYYY-MM-DD --output FILE");
  process.exit(2);
}
if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || !/^\d{4}-\d{2}-\d{2}$/.test(end) || start > end) {
  throw new Error("Invalid date range");
}

const hosts = [
  { name: "Hong Kong", base: "https://hk.investing.com/economic-calendar/index" },
  // Mobile regional calendar is a public HTML fallback candidate; it is
  // accepted only if the same date-range and event-row checks pass.
  { name: "Australia mobile", base: "https://m.au.investing.com/economic-calendar" },
  { name: "Australia", base: "https://au.investing.com/economic-calendar" },
  { name: "Global", base: "https://www.investing.com/economic-calendar/index" },
  { name: "United Kingdom", base: "https://uk.investing.com/economic-calendar/index" },
  { name: "Italy", base: "https://it.investing.com/economic-calendar/index" }
];
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    locale: "zh-HK",
    timezoneId: "Asia/Taipei",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
  });
  let captured = null;
  const attempts = [];
  for (const host of hosts) {
    const url = new URL(host.base);
    url.searchParams.set("timeFilter", "custom");
    url.searchParams.set("currentTab", "custom");
    url.searchParams.set("dateFrom", start);
    url.searchParams.set("dateTo", end);
    try {
      const response = await page.goto(url.toString(), { waitUntil: "domcontentloaded", timeout: 90000 });
      if (!response || !response.ok()) throw new Error(`HTTP status: ${response?.status() ?? "no response"}`);
      await page.waitForSelector('tr[id^="eventRowId_"], #economicCalendarData', { timeout: 45000 });
      await page.waitForTimeout(2500);
      const result = await page.evaluate(() => {
        const rows = [...document.querySelectorAll('tr[id^="eventRowId_"]')];
        const days = [...document.querySelectorAll('[id^="theDay"]')].map(el => ({
          id: el.id,
          text: el.textContent?.trim() || ""
        }));
        const dayDates = days.map(d => {
          const stamp = Number((d.id.match(/\d+/) || [])[0]);
          return Number.isFinite(stamp) ? new Date(stamp * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Taipei" }) : null;
        }).filter(Boolean);
        return { html: document.documentElement.outerHTML, rowCount: rows.length, days, dayDates, title: document.title, url: location.href };
      });
      if (!result.rowCount) throw new Error("page loaded but contains no event rows");
      const inRange = result.dayDates.filter(d => d >= start && d <= end);
      if (!inRange.length || result.dayDates.some(d => d < start || d > end)) {
        throw new Error(`date filter not applied; requested ${start}..${end}, page days: ${result.dayDates.join(",")}`);
      }
      captured = { ...result, host: host.name };
      break;
    } catch (error) {
      attempts.push(`${host.name}: ${error.message}`);
    }
  }
  if (!captured) throw new Error("All public Investing.com calendar hosts failed: " + attempts.join(" | "));
  const actualUrl = new URL(captured.url);
  const sourceUrl = `${actualUrl.origin}/economic-calendar/`;
  fs.writeFileSync(output, `<!-- tac-source-url: ${sourceUrl} -->\n${captured.html}`, "utf8");
  console.log(JSON.stringify({
    source_url: sourceUrl,
    source_host: captured.host,
    page_title: captured.title,
    requested_start: start,
    requested_end: end,
    event_rows: captured.rowCount,
    day_headers: captured.days.length,
    visible_taipei_dates: captured.dayDates,
    failed_host_attempts: attempts,
    output,
    note: "Saved normal public webpage HTML; parser independently verifies date coverage and native 3-star markers."
  }, null, 2));
} finally {
  await browser.close();
}
