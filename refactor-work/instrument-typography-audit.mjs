import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = path.join(here, "candidate-build.html");
const baseline = path.join(here, "source-baseline-2026-10-26.html");
const output = path.join(here, "browser-results", "instrument-typography-audit.json");
fs.mkdirSync(path.dirname(output), { recursive: true });

const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow-mobile", width: 320, height: 800 }
];

const browser = await chromium.launch({ headless: true });
const results = [];
try {
  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
    const candidatePage = await context.newPage();
    const baselinePage = await context.newPage();
    const errors = [];
    candidatePage.on("pageerror", error => errors.push(String(error)));
    await Promise.all([
      candidatePage.goto("file://" + html, { waitUntil: "domcontentloaded" }),
      baselinePage.goto("file://" + baseline, { waitUntil: "domcontentloaded" })
    ]);
    await Promise.all([candidatePage.waitForTimeout(350), baselinePage.waitForTimeout(350)]);

    const inspect = async page => page.evaluate(() => {
      const nameSelector = "#global-markets .row > b, #industry-bonds-fx-commodities .tac-tab-panel .row > b";
      const names = [...document.querySelectorAll(nameSelector)];
      const valueSelector = "#global-markets .row .r, #industry-bonds-fx-commodities .tac-tab-panel .row .r";
      const values = [...document.querySelectorAll(valueSelector)];
      const expectedRuleSelector = "#global-markets .row > b, html body #industry-bonds-fx-commodities .tac-tab-panel .row > b";
      const rules = [];
      const walk = list => {
        for (const rule of list) {
          if (rule.selectorText === expectedRuleSelector) {
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
          fontVariantNumeric: s.fontVariantNumeric,
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
        key, [...document.querySelectorAll(selector)].map(signature)
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

    const report = await inspect(candidatePage);
    const baselineReport = await inspect(baselinePage);
    const measureTabRows = async (page, group, tabIndex) => {
      const rootSelector = group === "global"
        ? "#global-markets"
        : "#industry-bonds-fx-commodities";
      try {
        // Use native DOM activation so the Q4 fund notice overlay cannot intercept this geometry-only diagnostic.
        await page.evaluate(({ group, tabIndex }) => {
          const id = group === "global" ? `tac-region-${tabIndex}` : `tac-assets-${tabIndex}`;
          const input = document.getElementById(id);
          if (!input) throw new Error(`Missing tab input: ${id}`);
          input.click();
        }, { group, tabIndex });
        await page.waitForTimeout(50);
        if (group === "assets" && tabIndex === 0) {
          const disclosure = page.locator("#industry-bonds-fx-commodities #tac-assets-panel-0 details.sector-collapse");
          const isOpen = await disclosure.evaluate(el => el.open);
          if (!isOpen) await disclosure.locator(":scope > summary").evaluate(el => el.click());
          await page.waitForTimeout(50);
        }
        return await page.evaluate(({ group, tabIndex }) => {
          const panelId = group === "global" ? `tac-region-panel-${tabIndex}` : `tac-assets-panel-${tabIndex}`;
          const panel = document.getElementById(panelId);
          if (!panel || getComputedStyle(panel).display === "none") {
            return { group, tabIndex, panelId, error: "Active tab panel is missing or hidden", rows: [] };
          }
          const selector = group === "global"
            ? ".row"
            : tabIndex === 0 ? ".sector-row"
            : tabIndex === 1 ? "#bonds .row"
            : tabIndex === 2 ? "#fx .row"
            : tabIndex === 3 ? ".energy-card .row"
            : ".row";
          const rows = [...panel.querySelectorAll(selector)].filter(row => row.getBoundingClientRect().height > 0);
          const round = n => Math.round(n * 100) / 100;
          const panelRect = panel.getBoundingClientRect();
          return {
            group, tabIndex, panelId, rowCount: rows.length,
            rows: rows.map(row => {
              const rr = row.getBoundingClientRect();
              const name = group === "assets" && tabIndex === 0
                ? row.querySelector(".sector-label")
                : row.querySelector(":scope > b");
              const nr = name?.getBoundingClientRect();
              const rank = row.querySelector(".rank");
              const kr = rank?.getBoundingClientRect();
              const values = [...row.querySelectorAll(".r")].map(value => {
                const vr = value.getBoundingClientRect();
                return {
                  text: (value.textContent || "").trim().replace(/\\s+/g, " "),
                  left: round(vr.left - rr.left), right: round(vr.right - rr.left),
                  top: round(vr.top - rr.top), width: round(vr.width), height: round(vr.height)
                };
              });
              return {
                name: (name?.textContent || "").trim().replace(/\\s+/g, " "),
                row: {
                  left: round(rr.left - panelRect.left), top: round(rr.top - panelRect.top),
                  width: round(rr.width), height: round(rr.height)
                },
                nameBox: nr ? {
                  left: round(nr.left - rr.left), top: round(nr.top - rr.top),
                  width: round(nr.width), height: round(nr.height)
                } : null,
                rankBox: kr ? {
                  left: round(kr.left - rr.left), top: round(kr.top - rr.top),
                  width: round(kr.width), height: round(kr.height)
                } : null,
                values
              };
            })
          };
        }, { group, tabIndex });
      } catch (error) {
        return { group, tabIndex, error: String(error), rows: [] };
      }
    };

    const rowGeometryAudit = [];
    for (let i = 0; i < 3; i++) {
      const [candidateRows, baselineRows] = await Promise.all([
        measureTabRows(candidatePage, "global", i),
        measureTabRows(baselinePage, "global", i)
      ]);
      rowGeometryAudit.push({ group: "global", tabIndex: i, candidate: candidateRows, baseline: baselineRows });
    }
    for (let i = 0; i < 5; i++) {
      const [candidateRows, baselineRows] = await Promise.all([
        measureTabRows(candidatePage, "assets", i),
        measureTabRows(baselinePage, "assets", i)
      ]);
      rowGeometryAudit.push({ group: "assets", tabIndex: i, candidate: candidateRows, baseline: baselineRows });
    }
    const failures = [];
    // Verify row identity and internal alignment without rejecting intentional type-scale changes.
    // Candidate name/rank/value boxes may be more compact than baseline; they must remain inside rows.
    for (const audit of rowGeometryAudit) {
      const current = audit.candidate;
      const original = audit.baseline;
      const label = audit.group + " tab " + audit.tabIndex;
      if (current.error) failures.push(label + " candidate row geometry failed: " + current.error);
      if (original.error) failures.push(label + " baseline row geometry failed: " + original.error);
      if (current.error || original.error) continue;
      if (current.rowCount !== original.rowCount) failures.push(label + " row count differs from baseline: candidate=" + current.rowCount + ", baseline=" + original.rowCount + ".");
      if (current.rows.length !== original.rows.length) continue;
      const rightEdgesByValueIndex = new Map();
      for (let i = 0; i < current.rows.length; i++) {
        const row = current.rows[i], baseRow = original.rows[i];
        if (row.name !== baseRow.name) failures.push(label + " row #" + (i + 1) + " name/order differs from baseline.");
        if (Math.abs(row.row.left - baseRow.row.left) > 3 || Math.abs(row.row.width - baseRow.row.width) > 3) failures.push(label + " row #" + (i + 1) + " horizontal shell differs from baseline by more than 3px.");
        if (row.row.height < 30 || row.row.height > 100) failures.push(label + " row #" + (i + 1) + " has suspicious height " + row.row.height + "px.");
        for (const boxName of ["nameBox", "rankBox"]) {
          const box = row[boxName];
          if (!box) continue;
          if (box.left < -1 || box.top < -1 || box.left + box.width > row.row.width + 1 || box.top + box.height > row.row.height + 1) failures.push(label + " " + row.name + " " + boxName + " escapes its row bounds.");
        }
        for (let j = 0; j < row.values.length; j++) {
          const value = row.values[j];
          if (value.left < -1 || value.top < -1 || value.right > row.row.width + 1 || value.top + value.height > row.row.height + 1) failures.push(label + " " + row.name + " value #" + (j + 1) + " escapes its row bounds.");
          const key = String(j);
          if (!rightEdgesByValueIndex.has(key)) rightEdgesByValueIndex.set(key, []);
          rightEdgesByValueIndex.get(key).push(value.right);
        }
      }
      for (const [valueIndex, edges] of rightEdgesByValueIndex) {
        if (edges.length > 1 && Math.max(...edges) - Math.min(...edges) > 3) failures.push(label + " quote column #" + (Number(valueIndex) + 1) + " right edges are not aligned within 3px.");
      }
    }
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

    // Quote typography is compared against the source baseline per matched DOM order,
    // rather than assuming global-market and industry values share one responsive size.
    if (report.values.length !== baselineReport.values.length) {
      failures.push(`Quote value count differs from baseline: candidate=${report.values.length}, baseline=${baselineReport.values.length}.`);
    }
    const properties = ["fontSize", "lineHeight", "fontWeight", "letterSpacing", "fontVariantNumeric"];
    for (let i = 0; i < Math.min(report.values.length, baselineReport.values.length); i++) {
      const current = report.values[i];
      const original = baselineReport.values[i];
      if (current.text !== original.text) {
        failures.push(`Quote value order/text differs at #${i + 1}: candidate="${current.text}", baseline="${original.text}".`);
        continue;
      }
      for (const property of properties) {
        if (current[property] !== original[property]) {
          failures.push(`Quote value #${i + 1} (${current.text}) changed ${property}: baseline=${original[property]}, candidate=${current[property]}.`);
        }
      }
      if (current.matchedCanonicalRule) failures.push(`Quote value #${i + 1} (${current.text}) unexpectedly matches the instrument-name rule.`);
    }
    if (errors.length) failures.push(...errors.map(error => "Browser error: " + error));
    results.push({
      viewport: viewport.name, width: viewport.width, nameCount: report.nameCount,
      valueCount: report.values.length, baselineValueCount: baselineReport.values.length,
      canonicalRuleCount: report.canonicalRules.length, failures, report, baselineValues: baselineReport.values,
      rowGeometryAudit
    });
    console.log(`[${failures.length ? "FAIL" : "PASS"}] ${viewport.name}: ${report.nameCount} names, ${report.values.length} quote values compared with baseline, ${report.canonicalRules.length} canonical rule(s)`);
    await context.close();
  }
} finally {
  await browser.close();
}
fs.writeFileSync(output, JSON.stringify(results, null, 2));
if (results.some(result => result.failures.length)) {
  console.error(JSON.stringify(results.filter(result => result.failures.length).map(result => ({ viewport: result.viewport, failures: result.failures })), null, 2));
  process.exitCode = 1;
}
