import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const args = process.argv.slice(2);
const getArg = (name) => args[args.indexOf(name) + 1];
const reportPath = getArg("--report");
const outputDir = getArg("--output") || "artifacts/tac-layout";
if (!reportPath || args.includes("--help")) {
  console.error("Usage: node scripts/tac_browser_layout_regression.mjs --report preview/YYYY-MM-DD.html [--output DIR]");
  process.exit(2);
}
const dateMatch = reportPath.match(/(2026-\d{2}-\d{2})/);
if (!dateMatch) throw new Error("Report path must contain a YYYY-MM-DD date");
const reportDate = new Date(dateMatch[1] + "T12:00:00Z");
const day = reportDate.getUTCDay();
if (day === 0 || day === 6) throw new Error("Weekend report date is not allowed");
const manifest = JSON.parse(fs.readFileSync("母版專區/mother-template-manifest.json", "utf8"));
const scenario = day === 1 ? "monday" : "weekdays";
const masterPath = manifest.templates[scenario].path;
if (!fs.existsSync(reportPath) || !fs.existsSync(masterPath)) throw new Error("Master or report file missing");

fs.mkdirSync(outputDir, { recursive: true });
const viewports = [
  { name: "desktop-1440", width: 1440, height: 1000 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "mobile-320", width: 320, height: 900 },
];
const selectors = [
  ".top", ".nav", ".wrap", ".bluf", ".sent",
  "#overview", "#sentiment", "#news-scan", "#global-markets",
  "#industry-bonds-fx-commodities", "#calendar", "#earnings",
  "#sp500-earnings-health", "#fed", "#view", ".footer"
];
const visualCompareSelectors = [".top", ".nav", ".footer", ".tac-section-heading"];
const compareMaskedPng = (leftPath, rightPath, label) => {
  const left = PNG.sync.read(fs.readFileSync(leftPath));
  const right = PNG.sync.read(fs.readFileSync(rightPath));
  if (left.width !== right.width || left.height !== right.height) {
    failures.push(label + ": masked screenshot dimensions differ");
    return;
  }
  const diff = new PNG({ width: left.width, height: left.height });
  const changed = pixelmatch(left.data, right.data, diff.data, left.width, left.height, {
    threshold: 0.12,
    includeAA: false
  });
  const ratio = changed / (left.width * left.height);
  if (ratio > 0.01) failures.push(label + ": masked screenshot pixel difference " + (ratio * 100).toFixed(2) + "% exceeds 1.00%");
};
const browser = await chromium.launch({ headless: true });
let failures = [];
const openLocal = async (page, file) => {
  await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
};
const snapshot = async (page) => page.evaluate((targets) => {
  const round = (v) => Math.round(v * 100) / 100;
  const result = {};
  for (const selector of targets) {
    const el = document.querySelector(selector);
    if (!el) { result[selector] = null; continue; }
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    result[selector] = {
      x: round(r.x), width: round(r.width),
      display: cs.display, position: cs.position,
      gridTemplateColumns: cs.gridTemplateColumns,
      gap: cs.gap, columnGap: cs.columnGap, rowGap: cs.rowGap,
      padding: cs.padding, margin: cs.margin,
      borderRadius: cs.borderRadius, boxSizing: cs.boxSizing,
      fontFamily: cs.fontFamily, fontSize: cs.fontSize,
      lineHeight: cs.lineHeight, whiteSpace: cs.whiteSpace
    };
  }
  return {
    viewport: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth,
    sections: result
  };
}, selectors);

try {
  for (const viewport of viewports) {
    const masterPage = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
    const reportPage = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
    masterPage.on("pageerror", error => failures.push(viewport.name + ": master JavaScript error: " + error.message));
    reportPage.on("pageerror", error => failures.push(viewport.name + ": report JavaScript error: " + error.message));
    await openLocal(masterPage, masterPath);
    await openLocal(reportPage, reportPath);
    await masterPage.screenshot({ path: path.join(outputDir, viewport.name + "-master.png"), fullPage: true });
    await reportPage.screenshot({ path: path.join(outputDir, viewport.name + "-report.png"), fullPage: true });

    // Compare stable visual chrome after masking all live text and numeric values.
    // Full-page content is not pixel-compared because event/news counts change daily.
    const maskStyle = "* { color: transparent !important; text-shadow: none !important; } .up,.down,.flat,.warn { color: transparent !important; background-color: transparent !important; border-color: transparent !important; }";
    await masterPage.addStyleTag({ content: maskStyle });
    await reportPage.addStyleTag({ content: maskStyle });
    for (const selector of visualCompareSelectors) {
      const masterElement = masterPage.locator(selector).first();
      const reportElement = reportPage.locator(selector).first();
      if (!(await masterElement.count()) || !(await reportElement.count())) {
        failures.push(viewport.name + ": visual comparison target missing: " + selector);
        continue;
      }
      const safe = selector.replace(/[^a-z0-9]+/gi, "-");
      const masterCrop = path.join(outputDir, viewport.name + "-" + safe + "-master.png");
      const reportCrop = path.join(outputDir, viewport.name + "-" + safe + "-report.png");
      await masterElement.screenshot({ path: masterCrop });
      await reportElement.screenshot({ path: reportCrop });
      compareMaskedPng(masterCrop, reportCrop, viewport.name + " " + selector);
    }

    const master = await snapshot(masterPage);
    const report = await snapshot(reportPage);
    if (master.documentWidth > viewport.width + 2) failures.push(viewport.name + ": approved master itself has horizontal overflow (" + master.documentWidth + "px)");
    if (report.documentWidth > viewport.width + 2) failures.push(viewport.name + ": report horizontal overflow (" + report.documentWidth + "px > " + viewport.width + "px)");

    for (const selector of selectors) {
      const a = master.sections[selector];
      const b = report.sections[selector];
      if (!!a !== !!b) {
        failures.push(viewport.name + ": " + selector + " presence differs (master=" + !!a + ", report=" + !!b + ")");
        continue;
      }
      if (!a) continue;
      if (a.display !== b.display || a.position !== b.position ||
          a.gridTemplateColumns !== b.gridTemplateColumns ||
          a.gap !== b.gap || a.padding !== b.padding ||
          a.borderRadius !== b.borderRadius || a.boxSizing !== b.boxSizing) {
        failures.push(viewport.name + ": " + selector + " computed layout styles differ");
      }
      if (Math.abs(a.x - b.x) > 2 || Math.abs(a.width - b.width) > 2) {
        failures.push(viewport.name + ": " + selector + " geometry differs (x/width master=" + a.x + "/" + a.width + ", report=" + b.x + "/" + b.width + ")");
      }
    }

    // Dismiss the approved template's optional fund notice overlay before
    // exercising underlying page controls; do not alter the template behavior.
    const fundNotice = reportPage.locator("#tac-fund-notice");
    if (await fundNotice.count() && await fundNotice.isVisible()) {
      const closeControl = reportPage.locator("#tfn-close");
      if (await closeControl.count()) await closeControl.click({ force: true });
      if (await fundNotice.isVisible()) {
        failures.push(viewport.name + ": fund notice overlay did not close using its existing control");
      }
    }

    // Verify the approved red circular +/- controls exist and actually toggle their cards.
    const economicPlus = reportPage.locator("details.econ-event > summary .econ-event-toggle").first();
    if (await economicPlus.count()) {
      const card = reportPage.locator("details.econ-event").first();
      const before = await card.evaluate(el => el.open);
      await economicPlus.click();
      const after = await card.evaluate(el => el.open);
      if (before === after) failures.push(viewport.name + ": economic red plus control did not toggle");
    } else {
      failures.push(viewport.name + ": economic red plus control missing");
    }
    const earningsPlus = reportPage.locator("details.earnings-accordion > summary .earnings-accordion-toggle").first();
    if (await earningsPlus.count()) {
      const card = reportPage.locator("details.earnings-accordion").first();
      const before = await card.evaluate(el => el.open);
      await earningsPlus.click();
      const after = await card.evaluate(el => el.open);
      if (before === after) failures.push(viewport.name + ": earnings red plus control did not toggle");
    } else {
      failures.push(viewport.name + ": earnings red plus control missing");
    }

    // Every in-page navigation link must resolve to an existing target.
    const navErrors = await reportPage.locator(".nav a[href^='#']").evaluateAll(links =>
      links.map(link => link.getAttribute("href")).filter(href => !href || !document.getElementById(href.slice(1)))
    );
    if (navErrors.length) failures.push(viewport.name + ": broken in-page navigation targets: " + navErrors.join(", "));

    // Every Investing.com link must use HTTPS and a real instrument destination.
    const investingErrors = await reportPage.locator("a[href*='investing.com']").evaluateAll(links =>
      links.filter(link => !link.href.startsWith("https://") || !/investing\.com\//i.test(link.href)).map(link => link.href)
    );
    if (investingErrors.length) failures.push(viewport.name + ": invalid Investing.com links: " + investingErrors.join(", "));

    // Fixed market instrument links must remain byte-for-byte identical to the
    // approved mother; news and calendar source links are intentionally dynamic.
    const fixedLinkSelectors = ["#global-markets a", "#industry-bonds-fx-commodities a", "#sentiment a"];
    for (const selector of fixedLinkSelectors) {
      const masterHrefs = await masterPage.locator(selector).evaluateAll(links => links.map(link => link.getAttribute("href")));
      const reportHrefs = await reportPage.locator(selector).evaluateAll(links => links.map(link => link.getAttribute("href")));
      if (JSON.stringify(masterHrefs) !== JSON.stringify(reportHrefs)) {
        failures.push(viewport.name + ": fixed instrument links changed in " + selector);
      }
    }

    const disclosure = reportPage.locator("details summary").first();
    if (await disclosure.count()) {
      const details = reportPage.locator("details").first();
      const before = await details.evaluate(el => el.open);
      await disclosure.click();
      const after = await details.evaluate(el => el.open);
      if (before === after) failures.push(viewport.name + ": details disclosure did not toggle");
    }
    const tabs = reportPage.locator("input.tac-tab-radio");
    if (await tabs.count() >= 2) {
      const secondTabId = await tabs.nth(1).getAttribute("id");
      const tabLabel = reportPage.locator('label[for="' + secondTabId + '"]');
      if (!(await tabLabel.count())) {
        failures.push(viewport.name + ": second TAC tab has no associated label");
      } else {
        await tabLabel.click();
        if (!(await tabs.nth(1).isChecked())) failures.push(viewport.name + ": TAC tab label did not activate its radio control");
      }
    }
    await masterPage.close();
    await reportPage.close();
    console.log("PASS " + viewport.name + ": screenshots captured; section geometry, computed layout and overflow checked");
  }
} finally {
  await browser.close();
}
if (failures.length) {
  console.error("TAC BROWSER LAYOUT REGRESSION FAILED");
  for (const failure of failures) console.error(" - " + failure);
  process.exit(1);
}
console.log("TAC BROWSER LAYOUT REGRESSION PASSED");
