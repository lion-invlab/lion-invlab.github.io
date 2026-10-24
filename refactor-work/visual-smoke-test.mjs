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
      scriptCount: document.querySelectorAll("script").length,
      sharedTabLabelCount: document.querySelectorAll(".tac-ds-tabs__tab").length,
      sharedDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure").length,
      darkDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure--dark").length,
      sharedEmptyStateCount: document.querySelectorAll(".tac-ds-empty").length,
      sharedNewsCardCount: document.querySelectorAll(".tac-ds-card--news").length,
      sharedNewsCardBackgrounds: [...new Set([...document.querySelectorAll(".tac-ds-card--news")].map(el => getComputedStyle(el).backgroundColor))],
      sharedNewsCardRadii: [...new Set([...document.querySelectorAll(".tac-ds-card--news")].map(el => getComputedStyle(el).borderRadius))],
      sharedEventCardCount: document.querySelectorAll("details.tac-ds-event").length,
      sharedEventCardRadii: [...new Set([...document.querySelectorAll("details.tac-ds-event")].map(el => getComputedStyle(el).borderRadius))],
      sharedEarningsCardCount: document.querySelectorAll("details.tac-ds-earnings-card").length,
      sharedEarningsCardRadii: [...new Set([...document.querySelectorAll("details.tac-ds-earnings-card")].map(el => getComputedStyle(el).borderRadius))],
      sharedSectorRowCount: document.querySelectorAll(".tac-ds-data-row--sector").length,
      sharedSectorRowRadii: [...new Set([...document.querySelectorAll(".tac-ds-data-row--sector")].map(el => getComputedStyle(el).borderRadius))],
      sharedSectorRowBackgrounds: [...new Set([...document.querySelectorAll(".tac-ds-data-row--sector")].map(el => getComputedStyle(el).backgroundColor))],
      sharedActualEarningsCardCount: document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card").length,
      sharedActualEarningsCardRadii: [...new Set([...document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card")].map(el => getComputedStyle(el).borderRadius))],
      sharedActualEarningsCardBackgrounds: [...new Set([...document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card")].map(el => getComputedStyle(el).backgroundColor))],
      actualEarningsBeatCount: document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card.beat").length,
      actualEarningsMissCount: document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card.miss").length
      ,
      sentimentThemeClassPresent: document.getElementById("sentiment")?.classList.contains("tac-ds-panel--sentiment") || false,
      sentimentBackgroundImage: getComputedStyle(document.getElementById("sentiment")).backgroundImage,
      sentimentBeforeContent: getComputedStyle(document.getElementById("sentiment"), "::before").content,
      sentimentBeforeBoxShadow: getComputedStyle(document.getElementById("sentiment"), "::before").boxShadow,
      sentimentAfterContent: getComputedStyle(document.getElementById("sentiment"), "::after").content,
      sentimentAfterBoxShadow: getComputedStyle(document.getElementById("sentiment"), "::after").boxShadow,
      sentimentBackgroundColor: getComputedStyle(document.getElementById("sentiment")).backgroundColor
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
          // Let the shared color transition finish before comparing computed styles.
          await cand.page.waitForTimeout(260);
          const checked = await input.isChecked();
          // Clear :hover so the assertion reads the selected state, not the hover state.
          const safePoint = await cand.page.evaluate(() => ({ x: Math.max(1, innerWidth - 6), y: Math.max(1, innerHeight - 6) }));
          await cand.page.mouse.move(safePoint.x, safePoint.y);
          await cand.page.waitForTimeout(80);
          const backgroundColor = await label.evaluate(el => getComputedStyle(el).backgroundColor);
          const textColor = await label.evaluate(el => getComputedStyle(el).color);
          const selectorMatch = await cand.page.evaluate((inputSelector) => {
            const id = inputSelector.slice(1);
            const input = document.getElementById(id);
            const labelEl = document.querySelector('label[for="' + id + '"]');
            const wrapperClass = id.startsWith("tac-news-") ? ".tac-ds-tabs" :
              id.startsWith("tac-region-") ? ".tac-ds-tabs" :
              id.startsWith("tac-assets-") ? ".tac-ds-tabs" :
              id.startsWith("week-econ-") ? ".week-econ-tab-labels" :
              id.startsWith("week-earnings-") ? ".week-earnings-tab-labels" :
              id.startsWith("fed-live-tab-") ? ".fed-live-tab-labels" : ".focus-tab-labels";
            return {
              checked: !!input?.checked,
              matchingSelector: !!document.querySelector("#" + id + ":checked ~ " + wrapperClass + ' label[for="' + id + '"]'),
              sameParent: !!input && !!labelEl && input.parentElement === labelEl.parentElement.parentElement
            };
          }, tab.input);
          let panelVisible = null;
          if (await cand.page.locator(tab.panel).count()) panelVisible = await cand.page.locator(tab.panel).first().isVisible();
          tabResults.push({ input: tab.input, checked, panelVisible, backgroundColor, textColor, selectorMatch });
        } catch (error) {
          tabResults.push({ input: tab.input, interactionError: String(error).split("\\n")[0] });
        }
      } else {
        tabResults.push({ input: tab.input, missingLabelOrInput: true });
      }
    }
    const sourceDisclosure = cand.page.locator("#sentiment details.source-details").first();
    let sourceDisclosureWorks = null;
    let sourceDisclosureCloses = null;
    let sourceDisclosureMarker = null;
    if (await sourceDisclosure.count()) {
      const sourceSummary = sourceDisclosure.locator("summary");
      await sourceSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      sourceDisclosureWorks = await sourceDisclosure.evaluate(el => el.open);
      sourceDisclosureMarker = await sourceSummary.evaluate(el => getComputedStyle(el, "::before").content);
      await sourceSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      sourceDisclosureCloses = !(await sourceDisclosure.evaluate(el => el.open));
    }
    const collapse = cand.page.locator("#last-week-calendar .last-week-calendar-collapse").first();
    const earningsCollapse = cand.page.locator("#last-week-earnings .last-week-earnings-collapse").first();
    let earningsCollapseWorks = null;
    if (await earningsCollapse.count()) {
      const before = await earningsCollapse.evaluate(el => el.open);
      await earningsCollapse.locator("summary").first().click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(100);
      const after = await earningsCollapse.evaluate(el => el.open);
      earningsCollapseWorks = before === false && after === true;
    }
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
    const eventCard = cand.page.locator("#last-week-calendar details.tac-ds-event").first();
    let eventCardWorks = null;
    let eventCardCloses = null;
    if (await eventCard.count() && collapseAfter === true) {
      const eventSummary = eventCard.locator("summary");
      await eventSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      eventCardWorks = await eventCard.evaluate(el => el.open);
      await eventSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      eventCardCloses = !(await eventCard.evaluate(el => el.open));
    }
    const earningsUpcomingLabel = cand.page.locator('#earnings label[for="week-earnings-upcoming"]').first();
    let earningsUpcomingTabWorks = false;
    let earningsAccordionWorks = null;
    let earningsAccordionCloses = null;
    if (await earningsUpcomingLabel.count()) {
      await earningsUpcomingLabel.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(260);
      earningsUpcomingTabWorks = await cand.page.locator("#week-earnings-upcoming").isChecked().catch(() => false);
      const earningsAccordion = cand.page.locator("#earnings details.tac-ds-earnings-card").first();
      if (await earningsAccordion.count()) {
        const earningsSummary = earningsAccordion.locator("summary");
        await earningsSummary.click({ timeout: 3000, force: true }).catch(() => {});
        await cand.page.waitForTimeout(80);
        earningsAccordionWorks = await earningsAccordion.evaluate(el => el.open);
        await earningsSummary.click({ timeout: 3000, force: true }).catch(() => {});
        await cand.page.waitForTimeout(80);
        earningsAccordionCloses = !(await earningsAccordion.evaluate(el => el.open));
      }
    }
    const sectorTabLabel = cand.page.locator('#industry-bonds-fx-commodities label[for="tac-assets-0"]').first();
    let sectorTabWorks = false;
    let sectorTabColor = null;
    let sectorTabTextColor = null;
    let sectorCollapseWorks = null;
    let sectorCollapseCloses = null;
    if (await sectorTabLabel.count()) {
      await sectorTabLabel.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(260);
      sectorTabWorks = await cand.page.locator("#tac-assets-0").isChecked().catch(() => false);
      sectorTabColor = await sectorTabLabel.evaluate(el => getComputedStyle(el).backgroundColor);
      sectorTabTextColor = await sectorTabLabel.evaluate(el => getComputedStyle(el).color);
      const sectorDisclosure = cand.page.locator("#industry-bonds-fx-commodities details.sector-collapse").first();
      if (await sectorDisclosure.count()) {
        const sectorSummary = sectorDisclosure.locator(":scope > summary");
        await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
        await cand.page.waitForTimeout(350);
        const sectorBefore = await sectorDisclosure.evaluate(el => el.open);
        let sectorClickError = "";
        await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError = String(e.message || e).slice(0, 240); });
        await cand.page.waitForTimeout(350);
        const sectorAfterToggle = await sectorDisclosure.evaluate(el => el.open);
        sectorCollapseWorks = sectorAfterToggle !== sectorBefore;
        if (!sectorCollapseWorks) {
          // Retry once after tab/panel transition has fully settled; preserve a real pointer interaction.
          await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | retry: " + String(e.message || e).slice(0, 180); });
          await cand.page.waitForTimeout(350);
        }
        await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
        await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | close: " + String(e.message || e).slice(0, 180); });
        await cand.page.waitForTimeout(350);
        sectorCollapseCloses = (await sectorDisclosure.evaluate(el => el.open)) === sectorBefore;
        if (!sectorCollapseCloses) {
          await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
          await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | close retry: " + String(e.message || e).slice(0, 180); });
          await cand.page.waitForTimeout(350);
          sectorCollapseCloses = (await sectorDisclosure.evaluate(el => el.open)) === sectorBefore;
        }
        results.sectorCollapseClickError = sectorClickError;
      }
    }
    const selectedTabColors = tabResults.filter(t => t.backgroundColor).map(t => t.backgroundColor);
    const selectedTabTextColors = tabResults.filter(t => t.textColor).map(t => t.textColor);
    const consistentSelectedTabColor = selectedTabColors.length > 0 && selectedTabColors.every(color => color === "rgb(180, 35, 50)");
    const consistentSelectedTabTextColor = selectedTabTextColors.length > 0 && selectedTabTextColors.every(color => color === "rgb(255, 255, 255)");
    const newErrors = cand.pageErrors.filter(error => !base.pageErrors.includes(error));
    results.viewports.push({
      ...viewport, baseline: baseReport, ...report, tabResults, consistentSelectedTabColor, consistentSelectedTabTextColor, sourceDisclosureWorks, sourceDisclosureCloses, sourceDisclosureMarker, collapseWorks, earningsCollapseWorks, collapseBefore, collapseAfter, collapseClickError, eventCardWorks, eventCardCloses, earningsUpcomingTabWorks, earningsAccordionWorks, earningsAccordionCloses, sectorTabWorks, sectorTabColor, sectorTabTextColor, sectorCollapseWorks, sectorCollapseCloses,
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
- Source disclosure: opens=${v.sourceDisclosureWorks}, closes=${v.sourceDisclosureCloses}, marker=${v.sourceDisclosureMarker}
- Sentiment special background: class=${v.sentimentThemeClassPresent}, layered background=${v.sentimentBackgroundImage?.includes("gradient")}, orbit before=${v.sentimentBeforeContent}/${v.sentimentBeforeBoxShadow}, orbit after=${v.sentimentAfterContent}/${v.sentimentAfterBoxShadow}, canvas=${v.sentimentBackgroundColor}\n- Shared components: tabs=${v.sharedTabLabelCount}, disclosures=${v.sharedDisclosureCount}, dark disclosures=${v.darkDisclosureCount}, empty states=${v.sharedEmptyStateCount}, news cards=${v.sharedNewsCardCount}, news backgrounds=${v.sharedNewsCardBackgrounds?.join(",")}, news radii=${v.sharedNewsCardRadii?.join(",")}, event cards=${v.sharedEventCardCount}, event radii=${v.sharedEventCardRadii?.join(",")}, event open/close=${v.eventCardWorks}/${v.eventCardCloses}, earnings cards=${v.sharedEarningsCardCount}, earnings radii=${v.sharedEarningsCardRadii?.join(",")}, earnings open/close=${v.earningsAccordionWorks}/${v.earningsAccordionCloses}, sector rows=${v.sharedSectorRowCount}, sector radii=${v.sharedSectorRowRadii?.join(",")}, sector backgrounds=${v.sharedSectorRowBackgrounds?.join(",")}, sector tab/collapse=${v.sectorTabWorks}/${v.sectorCollapseWorks}/${v.sectorCollapseCloses}, actual earnings result cards=${v.sharedActualEarningsCardCount}, radii=${v.sharedActualEarningsCardRadii?.join(",")}, backgrounds=${v.sharedActualEarningsCardBackgrounds?.join(",")}, beat/miss=${v.actualEarningsBeatCount}/${v.actualEarningsMissCount}
- Prior-week disclosures open: economics=${v.collapseWorks}, earnings=${v.earningsCollapseWorks} (before=${v.collapseBefore}, after=${v.collapseAfter}, error=${v.collapseClickError || "none"})
- New browser errors: ${v.newErrors.length}
- Pixel diff: ${results.visualDiffs.find(d => d.viewport === v.name)?.diffPixels} pixels (${results.visualDiffs.find(d => d.viewport === v.name)?.diffRatio})
- Selected tab color unified: ${v.consistentSelectedTabColor}; selected text white: ${v.consistentSelectedTabTextColor}
- Tab checks: ${v.tabResults.map(t => `${t.input}: checked=${t.checked}, visible=${t.panelVisible}, bg=${t.backgroundColor || ""}, selector=${JSON.stringify(t.selectorMatch || {})}, error=${t.interactionError || ""}, missing=${t.missingLabelOrInput || false}`).join("; ")}`),
    "",
    "Screenshots include baseline, candidate, and pixel-diff images for each viewport.",
    "Pixel differences are expected during the design migration; inspect baseline/candidate/diff artifacts for quality and regressions."
  ].join("\n");
  fs.writeFileSync(path.join(outDir, "summary.md"), summary);
  console.log(summary);
  const failed = results.viewports.some(v =>
    v.duplicateIds.length || v.missingPanels.length || v.unmatchedNav.length ||
    v.sentimentThemeClassPresent !== true || !String(v.sentimentBackgroundImage || "").includes("gradient") || v.sentimentBeforeContent === "none" || v.sentimentBeforeContent === "normal" || !String(v.sentimentBeforeBoxShadow || "").includes("rgba") || v.sentimentAfterContent === "none" || v.sentimentAfterContent === "normal" || !String(v.sentimentAfterBoxShadow || "").includes("rgba") ||
    v.sharedTabLabelCount !== 21 || v.sharedDisclosureCount < 13 || v.darkDisclosureCount < 2 || v.sharedEmptyStateCount !== 4 || v.sharedNewsCardCount !== 15 ||
    JSON.stringify(v.sharedNewsCardBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || JSON.stringify(v.sharedNewsCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.sharedEventCardCount !== 12 || JSON.stringify(v.sharedEventCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.eventCardWorks !== true || v.eventCardCloses !== true || v.sharedEarningsCardCount !== 22 || JSON.stringify(v.sharedEarningsCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.earningsUpcomingTabWorks !== true || v.earningsAccordionWorks !== true || v.earningsAccordionCloses !== true || v.sharedSectorRowCount !== 11 || JSON.stringify(v.sharedSectorRowRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || JSON.stringify(v.sharedSectorRowBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || v.sharedActualEarningsCardCount !== 14 || JSON.stringify(v.sharedActualEarningsCardRadii) !== JSON.stringify([v.width <= 640 ? "12px" : "14px"]) || JSON.stringify(v.sharedActualEarningsCardBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || v.actualEarningsBeatCount < 1 || v.actualEarningsMissCount < 1 || v.sectorTabWorks !== true || v.sectorTabColor !== "rgb(180, 35, 50)" || v.sectorTabTextColor !== "rgb(255, 255, 255)" || v.sectorCollapseWorks !== true || v.sectorCollapseCloses !== true ||
    v.sourceDisclosureWorks !== true || v.sourceDisclosureCloses !== true || !String(v.sourceDisclosureMarker || "").includes("▸") ||
    (v.horizontalOverflow && !v.baseline.horizontalOverflow) ||
    v.tabResults.some(t => t.missingLabelOrInput || t.checked === false || t.panelVisible === false || t.interactionError) ||
    !v.consistentSelectedTabColor || !v.consistentSelectedTabTextColor || v.collapseWorks === false || v.earningsCollapseWorks === false || v.newErrors.length
  ) || results.visualDiffs.some(d => d.baselineSize[0] !== d.candidateSize[0]);
  if (failed) process.exitCode = 1;
} finally {
  await browser.close();
}
