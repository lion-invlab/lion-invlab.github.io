#!/usr/bin/env node
/**
 * Capture Investing.com Hong Kong calendar through the ordinary public web page.
 * This uses browser navigation only; it does not call private/protected JSON APIs.
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
const url = new URL("https://hk.investing.com/economic-calendar/index");
url.searchParams.set("timeFilter", "custom");
url.searchParams.set("currentTab", "custom");
url.searchParams.set("dateFrom", start);
url.searchParams.set("dateTo", end);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    locale: "zh-HK",
    timezoneId: "Asia/Taipei",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
  });
  const response = await page.goto(url.toString(), { waitUntil: "domcontentloaded", timeout: 90000 });
  if (!response || !response.ok()) throw new Error(`Calendar page HTTP status: ${response?.status() ?? "no response"}`);
  await page.waitForSelector('tr[id^="eventRowId_"], #economicCalendarData', { timeout: 45000 });
  await page.waitForTimeout(2500);
  const result = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('tr[id^="eventRowId_"]')];
    const days = [...document.querySelectorAll('[id^="theDay"]')].map(el => ({
      id: el.id,
      text: el.textContent?.trim() || ""
    }));
    const dayDates = days.map(d => {
      const stamp = Number((d.id.match(/\\d+/) || [])[0]);
      return Number.isFinite(stamp) ? new Date(stamp * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Taipei" }) : null;
    }).filter(Boolean);
    return { html: document.documentElement.outerHTML, rowCount: rows.length, days, dayDates, title: document.title, url: location.href };
  });
  if (!result.rowCount) throw new Error("Calendar page loaded but contains no event rows");
  const inRange = result.dayDates.filter(d => d >= start && d <= end);
  if (!inRange.length || result.dayDates.some(d => d < start || d > end)) {
    throw new Error(`Date filter was not applied; requested ${start}.. ${end}, page days: ${result.dayDates.join(",")}`);
  }
  fs.writeFileSync(output, result.html, "utf8");
  console.log(JSON.stringify({
    source_url: result.url,
    page_title: result.title,
    requested_start: start,
    requested_end: end,
    event_rows: result.rowCount,
    day_headers: result.days.length,\n    visible_taipei_dates: result.dayDates,
    output,
    note: "Saved normal public webpage HTML; parser will independently verify date coverage and native 3-star markers."
  }, null, 2));
} finally {
  await browser.close();
}
