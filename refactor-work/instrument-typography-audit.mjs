import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = path.join(here, "candidate-build.html");
const output = path.join(here, "browser-results", "instrument-typography-audit.json");
fs.mkdirSync(path.dirname(output), { recursive: true });

const viewports = [
  { name: "desktop", width: 1440, height: 1000, valueSize: "16px", valueLineHeight: "24px" },
  { name: "mobile", width: 390, height: 844, valueSize: "15px", valueLineHeight: "22.5px" },
  { name: "narrow-mobile", width: 320, height: 800, valueSize: "15px", valueLineHeight: "22.5px" }
];

const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", error => errors.push(String(error)));
    await page.goto("file://" + html, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);
    const report = await page.evaluate(() => {
      const nameSelector = "#global-markets .row > b, #industry-bonds-fx-commodities .tac-tab-panel .row > b";
      const names = [...document.querySelectorAll(nameSelector)];
      const valueSelector = "#global-markets .row .r, #industry-bonds-fx-commodities .tac-tab-panel .row .r";
      const values = [...document.querySelectorAll(valueSelector)];
      const expectedRuleSelector = "#global-markets .row > b, html body #industry-bonds-fx-commodities .tac-tab-panel .row > b";
      const rules = [];
      const walk = list => {
        for (const rule of list) {
          if (rule.selectorText && rule.selectorText === expectedRuleSelector) {
            rules.push({
              selector: rule.selectorText,
              fontSize: rule.style.getPropertyValue("font-size").trim(),
              lineHeight: rule.style.getPropertyValue("line-height").trim(),
              fontWeight: rule.style.getPropertyValue("font-weight").trim(),
              letterSpacing: rule.style.getPropertyValue("letter-spacing").trim(),
              important: ["font-size", "line-height", "font-weight", "letter-spacing"].every(p => rule.style.getPropertyPriority(p) === "important")
            });
          }
          if (rule.cssRules) walk(rule.cssRules);
        }
      };
      for (const sheet of document.styleSheets) {
        try { walk(sheet.cssRules); } catch (_) {}
      }
      const signature = el => {
        const s = getComputedStyle(el);
        return {
          text: (el.textContent || "").trim().slice(0, 50),
          fontSize: s.fontSize,
          lineHeight: s.lineHeight,
          fontWeight: s.fontWeight,
          letterSpacing: s.letterSpacing,
          matchedCanonicalRule: el.matches(expectedRuleSelector)
        };
      };
      const categorySelectors = {
        globalMarkets: "#global-markets .row > b",
        bonds: "#industry-bonds-fx-commodities #bonds .row > b",
        fx: "#industry-bonds-fx-commodities #fx .row > b",
        energy: "#industry-bonds-fx-commodities .energy-card .row > b",
        metalsAndOtherAssets: "#industry-bonds-fx-commodities #tac-assets-panel-4 .row > b"
      };
      const categories = Object.fromEntries(Object.entries(categorySelectors).map(([key, selector]) => [
        key,
        [...document.querySelectorAll(selector)].map(signature)
      ]));
      return {
        width: innerWidth,
        nameCount: names.length,
        globalNameCount: document.querySelectorAll("#global-markets .row > b").length,
        industryNameCount: document.querySelectorAll("#industry-bonds-fx-commodities .tac-tab-panel .row > b").length,
        names: names.map(signature),
        values: values.map(signature),
        categories,
        canonicalRules: rules
      };
    });
    const failures = [];
    if (report.nameCount === 0) failures.push("No instrument names were found.");
    if (report.globalNameCount === 0 || report.industryNameCount === 0) failures.push("Global market or industry instrument names are missing.");
    if (report.canonicalRules.length !== 1) failures.push(`Expected exactly one canonical CSS rule, found ${report.canonicalRules.length}.`);
    const rule = report.canonicalRules[0];
    if (!rule || rule.fontSize !== "16px" || rule.lineHeight !== "1.35" || rule.fontWeight !== "700" || rule.letterSpacing !== "0px" || !rule.important) {
      failures.push("Canonical CSSOM declaration does not match 16px / 1.35 / 700 / 0px with !important.");
    }
    for (const [index, name] of report.names.entries()) {
      if (name.fontSize !== "16px" || name.lineHeight !== "21.6px" || name.fontWeight !== "700" || !name.matchedCanonicalRule) {
        failures.push(`Instrument name #${index + 1} (${name.text}) mismatch: ${JSON.stringify(name)}`);
      }
    }
    for (const [category, items] of Object.entries(report.categories)) {
      if (items.length === 0) failures.push(`Category sample ${category} returned no names.`);
      for (const item of items) {
        if (item.fontSize !== "16px" || item.lineHeight !== "21.6px" || item.fontWeight !== "700") {
          failures.push(`Category ${category} mismatch: ${JSON.stringify(item)}`);
        }
      }
    }
    for (const [index, value] of report.values.entries()) {
      if (value.fontSize !== viewport.valueSize || value.lineHeight !== viewport.valueLineHeight) {
        failures.push(`Quote value #${index + 1} (${value.text}) changed sizing: expected ${viewport.valueSize}/${viewport.valueLineHeight}, got ${value.fontSize}/${value.lineHeight}`);
      }
    }
    if (errors.length) failures.push(...errors.map(error => "Browser error: " + error));
    results.push({ viewport: viewport.name, width: viewport.width, nameCount: report.nameCount, valueCount: report.values.length, canonicalRuleCount: report.canonicalRules.length, failures, report });
    console.log(`[${failures.length ? "FAIL" : "PASS"}] ${viewport.name}: ${report.nameCount} names, ${report.values.length} quote values, ${report.canonicalRules.length} canonical rule(s)`);
    await page.close();
  }
} finally {
  await browser.close();
}
fs.writeFileSync(output, JSON.stringify(results, null, 2));
if (results.some(result => result.failures.length)) {
  console.error(JSON.stringify(results.filter(result => result.failures.length).map(result => ({ viewport: result.viewport, failures: result.failures })), null, 2));
  process.exitCode = 1;
}
