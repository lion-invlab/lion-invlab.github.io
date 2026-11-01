#!/usr/bin/env node
/**
 * Read-only diagnostic of Investing.com's official Economic Calendar Widget builder.
 * Does not accept terms, submit settings, call undocumented endpoints, or publish an embed.
 */
import fs from "node:fs";
import { chromium } from "playwright";
const output = process.argv[process.argv.indexOf("--output") + 1];
if (!output) throw new Error("Usage: node probe_tac_investing_calendar_widget.mjs --output FILE");
const browser = await chromium.launch({ headless: true });
const report = { source_url: "https://www.investing.com/webmaster-tools/economiccalendar", observed_at: new Date().toISOString(), status: "pending_verification" };
try {
  const page = await browser.newPage({ locale: "en-US", timezoneId: "Asia/Taipei" });
  const response = await page.goto(report.source_url, { waitUntil: "domcontentloaded", timeout: 90000 });
  report.http_status = response?.status() ?? null;
  report.final_url = page.url();
  report.title = await page.title();
  if (!response?.ok()) throw new Error("Widget builder page returned HTTP " + report.http_status);
  await page.waitForTimeout(3000);
  report.builder = await page.evaluate(() => {
    const selects = [...document.querySelectorAll("select")].map((el) => ({
      name: el.name || null, id: el.id || null,
      options: [...el.options].map((o) => ({ text: o.textContent.trim(), value: o.value }))
    }));
    const inputs = [...document.querySelectorAll("input")].map((el) => ({
      type: el.type, name: el.name || null, id: el.id || null,
      value: el.value || null, checked: el.checked,
      label: el.labels?.[0]?.textContent?.trim() || null
    }));
    const frames = [...document.querySelectorAll("iframe")].map((el) => ({
      src: el.getAttribute("src"), title: el.title || null, id: el.id || null
    }));
    return { selects, inputs, frames, bodyText: document.body.innerText.slice(-5000) };
  });
  report.frames = [];
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    const item = { url: frame.url() };
    try {
      item.title = await frame.title();
      item.text = (await frame.locator("body").innerText({ timeout: 10000 })).slice(0, 12000);
      item.row_count = await frame.locator('tr, [class*="event"]').count();
      item.importance_markers = await frame.locator('[class*="bull"], [class*="star"], [title*="High"]').count();
    } catch (error) { item.read_error = String(error); }
    report.frames.push(item);
  }
  report.status = "builder_accessible";
  report.note = "Read-only builder inspection only. No terms accepted, no embed generated, no private endpoints queried.";
} catch (error) {
  report.error = String(error);
}
fs.writeFileSync(output, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
if (report.status !== "builder_accessible") process.exitCode = 1;
finally { await browser.close(); }
