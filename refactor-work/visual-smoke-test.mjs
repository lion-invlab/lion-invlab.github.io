import { chromium } from "playwright";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const candidate = path.join(here, "candidate-build.html");
const baseline = path.join(here, "source-baseline-2026-10-26.html");
const outDir = path.join(here, "browser-results");
fs.mkdirSync(outDir, { recursive: true });

const panelIds = [
  "overview", "sentiment", "news-scan", "global-markets",
  "industry-bonds-fx-commodities", "last-week-calendar", "last-week-earnings",
  "calendar", "earnings", "sp500-earnings-health", "fed", "view"
];
const tabCases = [
  { input: "#tac-news-1", label: 'label[for="tac-news-1"]', panel: "#tac-news-panel-1" },
  { input: "#tac-region-1", label: 'label[for="tac-region-1"]', panel: "#tac-region-panel-1" },
  { input: "#tac-assets-4", label: 'label[for="tac-assets-4"]', panel: "#tac-assets-panel-4" },
  { input: "#week-econ-upcoming", label: 'label[for="week-econ-upcoming"]', panel: ".week-econ-panels > .calendar-status-group:nth-child(2)" },
  { input: "#week-earnings-published", label: 'label[for="week-earnings-published"]', panel: ".week-earnings-panels > .calendar-status-group:nth-child(3)" },
  { input: "#fed-live-tab-fomc", label: 'label[for="fed-live-tab-fomc"]', panel: ".fed-live-fomc" },
  { input: "#focus-tab-core", label: 'label[for="focus-tab-core"]', panel: ".focus-core" }
];

async function dismissNotice(page) {
  const closeButton = page.locator("#tfn-close");
  if (await closeButton.count()) await closeButton.click({ force: true }).catch(() => {});
  await page.waitForTimeout(150);
}
async function loadPage(browser, file, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
  const pageErrors = [];
  page.on("pageerror", e => pageErrors.push(String(e)));
  page.on("console", msg => { if (msg.type() === "error") pageErrors.push("console: " + msg.text()); });
  await page.goto("file://" + file, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(650);
  await dismissNotice(page);
  // Remove the transient onboarding hand in the test context; it is not part of the report layout.
  await page.evaluate(() => {
    document.querySelectorAll(".tac-tools-arrow-live, .tac-toolbar-hand-target").forEach(el => el.remove());
    document.body.style.overflow = "";
  });
  await page.waitForTimeout(120);
  return { page, pageErrors };
}
async function inspect(page) {
  return page.evaluate(({ panelIds }) => {
    const ids = [...document.querySelectorAll("[id]")].map(el => el.id);
    const duplicateIds = ids.filter((id, i) => ids.indexOf(id) !== i);
    const navLinks = [...document.querySelectorAll("nav a[href^='#']")];
    const unmatchedNav = navLinks.filter(a => !document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1))))
      .map(a => ({ label: a.textContent.trim(), href: a.getAttribute("href") }));
    return {
      title: document.title,
      width: window.innerWidth,
      docWidth: document.documentElement.scrollWidth,
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      duplicateIds: [...new Set(duplicateIds)],
      missingPanels: panelIds.filter(id => !document.getElementById(id)),
      navCount: navLinks.length,
      unmatchedNav,
      styleTagCount: document.querySelectorAll("style").length,
      scriptCount: document.querySelectorAll("script").length
    };
  }, { panelIds });
}

const browser = await chromium.launch({ headless: true });
const results = { candidate, baseline, viewports: [], errors: [], visualDiffs: [] };
try {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1000 },
    { name: "mobile", width: 390, height: 844 },
    { name: "narrow-mobile", width: 320, height: 800 }
  ]) {
    const base = await loadPage(browser, baseline, viewport);
    const cand = await loadPage(browser, candidate, viewport);
    const baseReport = await inspect(base.page);
    const report = await inspect(cand.page);

    const fullPageShot = viewport.name === "desktop";
    const baseShot = await base.page.screenshot({ path: path.join(outDir, "baseline-" + viewport.name + ".png"), fullPage: fullPageShot, animations: "disabled" });
    const candShot = await cand.page.screenshot({ path: path.join(outDir, "candidate-" + viewport.name + ".png"), fullPage: fullPageShot, animations: "disabled" });
    const basePng = PNG.sync.read(baseShot);
    const candPng = PNG.sync.read(candShot);
    let diffPixels = null;
    let diffRatio = null;
    let dimensionsMatch = basePng.width === candPng.width && basePng.height === candPng.height;
    if (dimensionsMatch) {
      const diff = new PNG({ width: basePng.width, height: basePng.height });
      diffPixels = pixelmatch(basePng.data, candPng.data, diff.data, basePng.width, basePng.height, { threshold: 0.1, includeAA: false });
      diffRatio = diffPixels / (basePng.width * basePng.height);
      fs.writeFileSync(path.join(outDir, "diff-" + viewport.name + ".png"), PNG.sync.write(diff));
    }
    results.visualDiffs.push({ viewport: viewport.name, dimensionsMatch, baselineSize: [basePng.width, basePng.height], candidateSize: [candPng.width, candPng.height], diffPixels, diffRatio });

    const tabResults = [];
    for (const tab of tabCases) {
      const label = cand.page.locator(tab.label).first();
      const input = cand.page.locator(tab.input).first();
      if (await label.count() && await input.count()) {
        try {
          await label.click({ timeout: 3000 });
          const checked = await input.isChecked();
          const backgroundColor = await label.evaluate(el => getComputedStyle(el).backgroundColor);
          const textColor = await label.evaluate(el => getComputedStyle(el).color);
          let panelVisible = null;
          if (await cand.page.locator(tab.panel).count()) panelVisible = await cand.page.locator(tab.panel).first().isVisible();
          tabResults.push({ input: tab.input, checked, panelVisible, backgroundColor, textColor });
        } catch (error) {
          tabResults.push({ input: tab.input, interactionError: String(error).split("\\n")[0] });
        }
      } else {
        tabResults.push({ input: tab.input, missingLabelOrInput: true });
      }
    }
    const collapse = cand.page.locator("#last-week-calendar .last-week-calendar-collapse").first();
    let collapseWorks = null;
    let collapseBefore = null;
    let collapseClickError = null;
    let collapseAfter = null;
    if (await collapse.count()) {
      collapseBefore = await collapse.evaluate(el => el.open);
      try {
        await collapse.locator("summary").first().click({ timeout: 3000, force: true });
        await cand.page.waitForTimeout(100);
      } catch (error) {
        collapseClickError = String(error).split("\\n")[0];
      }
      collapseAfter = await collapse.evaluate(el => el.open);
      collapseWorks = collapseBefore === false && collapseAfter === true;
    }
    const selectedTabColors = tabResults.filter(t => t.backgroundColor).map(t => t.backgroundColor);
    const selectedTabTextColors = tabResults.filter(t => t.textColor).map(t => t.textColor);
    const consistentSelectedTabColor = selectedTabColors.length > 0 && selectedTabColors.every(color => color === "rgb(255, 255, 255)") && selectedTabTextColors.every(color => color === "rgb(180, 35, 50)");
    const newErrors = cand.pageErrors.filter(error => !base.pageErrors.includes(error));
    results.viewports.push({
      ...viewport, baseline: baseReport, ...report, tabResults, consistentSelectedTabColor, collapseWorks, collapseBefore, collapseAfter, collapseClickError,
      baselinePageErrors: base.pageErrors, pageErrors: cand.pageErrors, newErrors,
      screenshots: ["baseline-" + viewport.name + ".png", "candidate-" + viewport.name + ".png", "diff-" + viewport.name + ".png"]
    });
    results.errors.push(...newErrors.map(error => ({ viewport: viewport.name, error })));
    await base.page.close();
    await cand.page.close();
  }
  results.static = {
    requiredPanelIds: panelIds,
    requiredTabCaseCount: tabCases.length,
    expectedScripts: 10,
    note: "Pixel diffs compare the frozen baseline with the CSS-extracted candidate. A zero diff verifies parity, not design improvement."
  };
  fs.writeFileSync(path.join(outDir, "results.json"), JSON.stringify(results, null, 2));
  const summary = [
    "# TAC Refactor Browser Smoke Test",
    "",
    ...results.viewports.map(v => `## ${v.name} — ${v.width}×${v.height}
- Document width: baseline=${v.baseline.docWidth}, candidate=${v.docWidth}
- Horizontal overflow: baseline=${v.baseline.horizontalOverflow}, candidate=${v.horizontalOverflow}
- Missing panel IDs: ${v.missingPanels.join(", ") || "none"}
- Duplicate IDs: ${v.duplicateIds.join(", ") || "none"}
- Unmatched nav links: ${v.unmatchedNav.length}
- Style/script tags: ${v.styleTagCount}/${v.scriptCount}
- Disclosure opens: ${v.collapseWorks} (before=${v.collapseBefore}, after=${v.collapseAfter}, error=${v.collapseClickError || "none"})
- New browser errors: ${v.newErrors.length}
- Pixel diff: ${results.visualDiffs.find(d => d.viewport === v.name)?.diffPixels} pixels (${results.visualDiffs.find(d => d.viewport === v.name)?.diffRatio})
- Selected tab color unified: ${v.consistentSelectedTabColor}
- Tab checks: ${v.tabResults.map(t => `${t.input}: checked=${t.checked}, visible=${t.panelVisible}, bg=${t.backgroundColor || ""}, error=${t.interactionError || ""}, missing=${t.missingLabelOrInput || false}`).join("; ")}`),
    "",
    "Screenshots include baseline, candidate, and pixel-diff images for each viewport.",
    "Pixel differences are expected during the design migration; inspect baseline/candidate/diff artifacts for quality and regressions."
  ].join("\n");
  fs.writeFileSync(path.join(outDir, "summary.md"), summary);
  console.log(summary);
  const failed = results.viewports.some(v =>
    v.duplicateIds.length || v.missingPanels.length || v.unmatchedNav.length ||
    (v.horizontalOverflow && !v.baseline.horizontalOverflow) ||
    v.tabResults.some(t => t.missingLabelOrInput || t.checked === false || t.panelVisible === false || t.interactionError) ||
    !v.consistentSelectedTabColor || v.collapseWorks === false || v.newErrors.length
  ) || results.visualDiffs.some(d => d.baselineSize[0] !== d.candidateSize[0]);
  if (failed) process.exitCode = 1;
} finally {
  await browser.close();
}
