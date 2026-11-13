import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const manifest = JSON.parse(fs.readFileSync("母版專區/mother-template-manifest.json", "utf8"));
const masters = [
  { key: "monday", path: manifest.templates.monday.path },
  { key: "weekdays", path: manifest.templates.weekdays.path }
];
const viewports = [
  { name: "desktop-1440", width: 1440, height: 1000 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "mobile-412", width: 412, height: 900 },
  { name: "mobile-390", width: 390, height: 900 },
  { name: "mobile-360", width: 360, height: 900 }
];
const output = "artifacts/summary-heading-typography";
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];
const failures = [];

try {
  for (const master of masters) {
    for (const viewport of viewports) {
      const page = await browser.newPage({
        viewport: { width: viewport.width, height: viewport.height },
        deviceScaleFactor: 1
      });
      await page.goto(pathToFileURL(path.resolve(master.path)).href, { waitUntil: "load" });
      await page.evaluate(() => document.fonts.ready);
      const audit = await page.evaluate(() => {
        const summaryLabel = document.querySelector("#overview > section.grid.two > article.card.bluf > .title");
        const sentimentLabel = document.querySelector("#sentiment > .title");
        const takeaway = document.querySelector("#overview > section.grid.two > article.card.bluf > h1");
        if (!summaryLabel || !sentimentLabel || !takeaway) {
          return { valid: false, reason: "required summary or sentiment heading node missing" };
        }
        const summaryStyle = getComputedStyle(summaryLabel);
        const sentimentStyle = getComputedStyle(sentimentLabel);
        const rawTakeaway = takeaway.textContent || "";
        const takeawayText = rawTakeaway.trim().replace(/\s+/g, " ");
        const generic = new Set(["總結", "摘要", "市場情緒", "Summary", "Market Summary"]);
        const semanticValid = takeawayText.length >= 8 && takeawayText.length <= 36 &&
          !generic.has(takeawayText) && !/[｜\r\n]/.test(rawTakeaway);
        return {
          valid: summaryStyle.fontSize === sentimentStyle.fontSize && semanticValid,
          summaryFontSize: summaryStyle.fontSize,
          sentimentFontSize: sentimentStyle.fontSize,
          summaryFontWeight: summaryStyle.fontWeight,
          summaryLineHeight: summaryStyle.lineHeight,
          takeawayText,
          semanticValid
        };
      });
      results.push({ master: master.key, viewport: viewport.name, ...audit });
      if (!audit.valid) failures.push(master.key + "/" + viewport.name + ": " + JSON.stringify(audit));
      await page.locator("#overview > section.grid.two > article.card.bluf").screenshot({
        path: path.join(output, master.key + "-" + viewport.name + "-summary.png")
      });
      await page.close();
    }
  }
} finally {
  await browser.close();
}
fs.writeFileSync(path.join(output, "summary-heading-audit.json"), JSON.stringify({
  generatedAt: new Date().toISOString(),
  viewports,
  results,
  failures
}, null, 2));
if (failures.length) {
  console.error("SUMMARY HEADING TYPOGRAPHY FAIL");
  for (const failure of failures) console.error(" - " + failure);
  process.exit(1);
}
console.log("PASS: " + results.length + " summary heading audits; both masters match sentiment title at all five WR viewports.");
