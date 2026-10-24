import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const candidate = path.join(here, "candidate-build.html");
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

const browser = await chromium.launch({ headless: true });
const results = { candidate, viewports: [], static: {}, errors: [] };
try {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1000 },
    { name: "mobile", width: 390, height: 844 },
    { name: "narrow-mobile", width: 320, height: 800 }
  ]) {
    const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
    const pageErrors = [];
    page.on("pageerror", e => pageErrors.push(String(e)));
    page.on("console", msg => { if (msg.type() === "error") pageErrors.push("console: " + msg.text()); });
    await page.goto("file://" + candidate, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(700);
    // The baseline intentionally opens a Q4 fund notice on first load; dismiss it before interaction tests.
    const fundNotice = page.locator("#tac-fund-notice");
    if (await fundNotice.count() && await fundNotice.isVisible().catch(() => false)) {
      const closeButton = page.locator("#tfn-close");
      if (await closeButton.count()) await closeButton.click({ force: true }).catch(() => {});
      await page.waitForTimeout(150);
    }
    const report = await page.evaluate(({ panelIds }) => {
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
    const tabResults = [];
    for (const tab of tabCases) {
      const label = page.locator(tab.label).first();
      const input = page.locator(tab.input).first();
      if (await label.count() && await input.count()) {
        try {
          await label.click({ timeout: 3000 });
          const checked = await input.isChecked();
          let panelVisible = null;
          if (await page.locator(tab.panel).count()) panelVisible = await page.locator(tab.panel).first().isVisible();
          tabResults.push({ input: tab.input, checked, panelVisible });
        } catch (error) {
          tabResults.push({ input: tab.input, interactionError: String(error).split("\\n")[0] });
        }
      } else {
        tabResults.push({ input: tab.input, missingLabelOrInput: true });
      }
    }
    const collapse = page.locator("#last-week-calendar details").first();
    let collapseWorks = null;
    if (await collapse.count()) {
      await collapse.locator("summary").click();
      collapseWorks = await collapse.evaluate(el => el.open);
    }
    const screenshotPath = path.join(outDir, viewport.name + ".png");
    await page.screenshot({ path: screenshotPath, fullPage: true, animations: "disabled" });
    results.viewports.push({
      ...viewport, ...report, tabResults, collapseWorks, pageErrors,
      screenshot: path.basename(screenshotPath)
    });
    results.errors.push(...pageErrors.map(error => ({ viewport: viewport.name, error })));
    await page.close();
  }
  results.static = {
    requiredPanelIds: panelIds,
    requiredTabCaseCount: tabCases.length,
    scriptBlocksExpected: 10,
    note: "Browser smoke test; visual screenshots require human comparison with the frozen baseline."
  };
  fs.writeFileSync(path.join(outDir, "results.json"), JSON.stringify(results, null, 2));
  const summary = [
    "# TAC Refactor Browser Smoke Test",
    "",
    ...results.viewports.map(v => `## ${v.name} — ${v.width}×${v.height}
- Document width: ${v.docWidth}; horizontal overflow: ${v.horizontalOverflow}
- Missing panel IDs: ${v.missingPanels.join(", ") || "none"}
- Duplicate IDs: ${v.duplicateIds.join(", ") || "none"}
- Unmatched nav links: ${v.unmatchedNav.length}
- Style/script tags: ${v.styleTagCount}/${v.scriptCount}
- Disclosure opens: ${v.collapseWorks}
- Page errors: ${v.pageErrors.length}
- Tab checks: ${v.tabResults.map(t => `${t.input}: checked=${t.checked}, visible=${t.panelVisible}, missing=${t.missingLabelOrInput || false}`).join("; ")}`),
    "",
    "Screenshots: desktop.png, mobile.png, narrow-mobile.png",
    "",
    "Note: passing smoke tests do not by themselves prove that visual quality exceeds the baseline."
  ].join("\n");
  fs.writeFileSync(path.join(outDir, "summary.md"), summary);
  console.log(summary);
  const failed = results.viewports.some(v =>
    v.duplicateIds.length || v.missingPanels.length || v.unmatchedNav.length ||
    v.horizontalOverflow || v.tabResults.some(t => t.missingLabelOrInput || t.checked === false || t.panelVisible === false) ||
    v.collapseWorks === false || v.pageErrors.length
  );
  if (failed) process.exitCode = 1;
} finally {
  await browser.close();
}
