import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

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
  { name: "mobile-412", width: 412, height: 900 },
  { name: "mobile-390", width: 390, height: 900 },
  { name: "mobile-360", width: 360, height: 900 },
];
const selectors = [
  ".top", ".nav", ".wrap", ".bluf", ".sent",
  "#overview", "#sentiment", "#news-scan", "#global-markets",
  "#industry-bonds-fx-commodities", "#calendar", "#earnings",
  "#sp500-earnings-health", "#fed", "#view", ".footer"
];
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
    await openLocal(masterPage, masterPath);
    await openLocal(reportPage, reportPath);
    await masterPage.screenshot({ path: path.join(outputDir, viewport.name + "-master.png"), fullPage: true });
    await reportPage.screenshot({ path: path.join(outputDir, viewport.name + "-report.png"), fullPage: true });

    const summaryTypography = await reportPage.evaluate(() => {
      const sectionLabel = document.querySelector("#overview > section.grid.two > article.card.bluf > .title");
      const referenceLabel = document.querySelector("#sentiment > .title");
      const takeaway = document.querySelector("#overview > section.grid.two > article.card.bluf > h1");
      if (!sectionLabel || !referenceLabel || !takeaway) {
        return { valid: false, reason: "summary red label, sentiment reference label, or black takeaway h1 missing" };
      }
      const summarySize = getComputedStyle(sectionLabel).fontSize;
      const referenceSize = getComputedStyle(referenceLabel).fontSize;
      const rawTakeaway = takeaway.textContent || "";
      const takeawayText = rawTakeaway.trim().replace(/\s+/g, " ");
      const genericLabels = new Set(["總結", "摘要", "市場情緒", "Summary", "Market Summary"]);
      const semanticValid = takeawayText.length >= 8 && takeawayText.length <= 36 &&
        !genericLabels.has(takeawayText) && !/[｜\r\n]/.test(rawTakeaway);
      return {
        valid: summarySize === referenceSize && semanticValid,
        summarySize, referenceSize, takeawayText, semanticValid
      };
    });
    if (!summaryTypography.valid) {
      failures.push(viewport.name + ": summary typography/content contract failed: " + JSON.stringify(summaryTypography));
    } else {
      console.log("PASS " + viewport.name + ": summary section title " + summaryTypography.summarySize +
        " matches sentiment title; black takeaway is a concise market sentence");
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

    // Exercise every native disclosure, including nested cards hidden inside
    // collapsed parent sections. Restore the original state after each click.
    const disclosures = reportPage.locator("details > summary");
    const disclosureCount = await disclosures.count();
    if (!disclosureCount) failures.push(viewport.name + ": no details disclosures found");
    for (let i = 0; i < disclosureCount; i++) {
      const result = await disclosures.nth(i).evaluate(el => {
        const own = el.parentElement;
        const before = own.open;
        const ancestors = [];
        for (let parent = own.parentElement; parent; parent = parent.parentElement) {
          if (parent.tagName === "DETAILS") {
            ancestors.push([parent, parent.open]);
            parent.open = true;
          }
        }
        own.open = before;
        el.click();
        const after = own.open;
        el.click();
        const restored = own.open;
        for (let j = ancestors.length - 1; j >= 0; j--) {
          ancestors[j][0].open = ancestors[j][1];
        }
        return { before, after, restored };
      });
      if (result.before === result.after) failures.push(viewport.name + ": disclosure " + (i + 1) + "/" + disclosureCount + " did not toggle");
      if (result.restored !== result.before) failures.push(viewport.name + ": disclosure " + (i + 1) + "/" + disclosureCount + " did not restore its initial state");
    }

    // Activate every radio-backed tab, not just one representative TAC tab.
    const radios = reportPage.locator('input[type="radio"]');
    const radioCount = await radios.count();
    for (let i = 0; i < radioCount; i++) {
      const radio = radios.nth(i);
      const id = await radio.getAttribute("id");
      if (!id) {
        failures.push(viewport.name + ": radio " + (i + 1) + " has no id");
        continue;
      }
      const label = reportPage.locator('label[for="' + id + '"]');
      if (!(await label.count())) {
        failures.push(viewport.name + ": radio " + id + " has no associated label");
        continue;
      }
      await label.first().click({ force: true });
      if (!(await radio.isChecked())) failures.push(viewport.name + ": tab label did not activate radio " + id);
    }

    // Verify every in-page navigation target and exercise its click behavior.
    const internalLinks = reportPage.locator('a[href^="#"]');
    const internalLinkCount = await internalLinks.count();
    for (let i = 0; i < internalLinkCount; i++) {
      const link = internalLinks.nth(i);
      const href = await link.getAttribute("href");
      const targetId = decodeURIComponent((href || "").slice(1));
      const targetExists = await reportPage.evaluate(id => !!document.getElementById(id), targetId);
      if (!targetExists) {
        failures.push(viewport.name + ": internal link target missing for " + href);
        continue;
      }
      await link.evaluate(el => el.click());
      if (href === "#tac-history-shortcut") {
        const opened = await reportPage.evaluate(() => document.body.classList.contains("tac-side-open"));
        if (!opened) failures.push(viewport.name + ": history shortcut did not open the side panel");
        await reportPage.keyboard.press("Escape");
      } else {
        const currentHash = await reportPage.evaluate(() => window.location.hash);
        if (currentHash !== href) failures.push(viewport.name + ": internal navigation did not reach " + href);
      }
    }

    // The approved red circular plus controls are fixed at 32 x 32 px.
    const circleSpecs = [
      // The previous-week economic calendar exists only in the Monday master.
      // The Manifest-selected weekday master has no #last-week-calendar by design.
      ...(scenario === "monday" ? [
        { selector: "#last-week-calendar .econ-event-toggle", pseudo: null }
      ] : []),
      { selector: ".earnings-accordion-toggle", pseudo: null }
    ];
    for (const spec of circleSpecs) {
      const controls = reportPage.locator(spec.selector);
      const count = await controls.count();
      if (!count) {
        failures.push(viewport.name + ": missing plus-control selector " + spec.selector);
        continue;
      }
      const dimensions = await controls.evaluateAll((els, pseudo) => els.map(el => {
        const style = getComputedStyle(el, pseudo);
        return {
          width: parseFloat(style.width),
          height: parseFloat(style.height),
          radius: style.borderRadius,
          background: style.backgroundColor
        };
      }), spec.pseudo);
      dimensions.forEach((d, i) => {
        if (Math.abs(d.width - 32) > 1 || Math.abs(d.height - 32) > 1) {
          failures.push(viewport.name + ": " + spec.selector + " control " + (i + 1) + " is not 32 x 32 px (" + d.width + " x " + d.height + ")");
        }
        if (!d.radius.includes("50%")) failures.push(viewport.name + ": " + spec.selector + " control " + (i + 1) + " is not circular");
        if (d.background !== "rgb(198, 40, 40)") failures.push(viewport.name + ": " + spec.selector + " control " + (i + 1) + " is not TAC red (" + d.background + ")");
      });
    }
    // Current-week economic plus markers and the sector disclosure are
    // compared against the approved master. Known master-level styling gaps
    // are warnings, not preview regressions; do not silently restyle a locked master.
    const readCurrentWeekEconMarker = el => {
      const style = getComputedStyle(el);
      return { display: style.display, width: style.width, height: style.height, radius: style.borderRadius, background: style.backgroundColor };
    };
    const masterCurrentWeekLocator = masterPage.locator("#calendar .econ-event-toggle");
    const masterCurrentWeekCount = await masterCurrentWeekLocator.count();
    const reportCurrentWeekMarkers = await reportPage.locator("#calendar .econ-event-toggle").evaluateAll(els => els.map(el => {
      const style = getComputedStyle(el);
      return { display: style.display, width: style.width, height: style.height, radius: style.borderRadius, background: style.backgroundColor };
    }));
    if (masterCurrentWeekCount === 0 && reportCurrentWeekMarkers.length > 0) {
      console.warn("WARN " + viewport.name + ": approved master has no current-week economic plus-control markup; preview contains " + reportCurrentWeekMarkers.length + " markers that lack the master red-circle styling. Requires formal master/renderer correction.");
    } else if (masterCurrentWeekCount > 0) {
      const masterCurrentWeekMarker = await masterCurrentWeekLocator.first().evaluate(readCurrentWeekEconMarker);
      if (!reportCurrentWeekMarkers.length || reportCurrentWeekMarkers.some(x => JSON.stringify(x) !== JSON.stringify(masterCurrentWeekMarker))) {
        failures.push(viewport.name + ": current-week economic disclosure marker styling differs from the approved master");
      } else if (masterCurrentWeekMarker.background !== "rgb(198, 40, 40)" || !masterCurrentWeekMarker.radius.includes("50%") || parseFloat(masterCurrentWeekMarker.width) < 31 || parseFloat(masterCurrentWeekMarker.height) < 31) {
        console.warn("WARN " + viewport.name + ": current-week economic event markers inherit the approved master styling gap; preview matches master. Formal master change required to add 32px red circles.");
      }
    }

    const sectorSelector = "#industry-bonds-fx-commodities .sector-collapse > summary";
    const readSectorMarker = page => page.locator(sectorSelector).evaluate(el => {
      const style = getComputedStyle(el, "::before");
      return { width: style.width, height: style.height, radius: style.borderRadius, background: style.backgroundColor };
    });
    const masterSectorMarker = await readSectorMarker(masterPage);
    const reportSectorMarker = await readSectorMarker(reportPage);
    if (JSON.stringify(masterSectorMarker) !== JSON.stringify(reportSectorMarker)) {
      failures.push(viewport.name + ": sector disclosure marker styling differs from the approved master");
    } else if (parseFloat(reportSectorMarker.width) < 31 || parseFloat(reportSectorMarker.height) < 31) {
      console.warn("WARN " + viewport.name + ": sector disclosure plus is " + reportSectorMarker.width + " x " + reportSectorMarker.height + " in the approved master; preview matches master.");
    }

    console.log("PASS " + viewport.name + ": " + disclosureCount + " disclosures, " + radioCount + " radio tabs, " + internalLinkCount + " internal links and approved 32px calendar plus controls exercised");
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
