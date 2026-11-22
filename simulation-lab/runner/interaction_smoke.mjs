import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const htmlPath = path.resolve(process.argv[2] || "");
const outputPath = path.resolve(process.argv[3] || "simulation-lab/output/interaction-smoke.json");
if (!fs.existsSync(htmlPath)) throw new Error(`HTML review file not found: ${htmlPath}`);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
page.on("pageerror", error => pageErrors.push(error.message));

try {
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "domcontentloaded" });

  // The approved mother opens a fund-date reminder on DOMContentLoaded.
  // Dismiss this intentional modal before testing navigation and accordions,
  // otherwise it correctly intercepts pointer events meant for the page.
  const fundNotice = page.locator("#tac-fund-notice");
  const fundClose = page.locator("#tfn-close");
  if (await fundClose.count()) {
    try {
      await fundNotice.waitFor({ state: "visible", timeout: 2500 });
    } catch {}
    if (await fundNotice.isVisible()) {
      await fundClose.click();
      await fundNotice.waitFor({ state: "hidden", timeout: 2000 });
    }
  }

  // The CNN score and white marker must share one 0..100 coordinate system.
  // Exercise 20/40/75 in Chromium so the mother's fixed left:23%!important
  // cannot silently override the generated marker position.
  const fearGreedMarkerTest = await page.locator(".cnn-fg-preview").evaluate(card => {
    const scoreNode = card.querySelector(".fg6-score");
    const scale = card.querySelector(".fg6-scale-wrap");
    const marker = card.querySelector(".fg6-marker");
    if (!scoreNode || !scale || !marker) throw new Error("CNN Fear & Greed score, scale, or marker missing");
    const score = Number.parseFloat(scoreNode.textContent.trim());
    if (!Number.isFinite(score) || score < 0 || score > 100) {
      throw new Error("CNN Fear & Greed score is not a valid 0..100 number");
    }
    const inlineLeft = Number.parseFloat(marker.style.getPropertyValue("left"));
    if (marker.style.getPropertyPriority("left") !== "important" || Math.abs(inlineLeft - score) > 0.001) {
      throw new Error(`marker inline position does not match displayed score: score=${score}, left=${marker.style.left}`);
    }
    const dataScore = Number.parseFloat(marker.getAttribute("data-score") || "");
    const ariaLabel = marker.getAttribute("aria-label") || "";
    if (!Number.isFinite(dataScore) || Math.abs(dataScore - score) > 0.001) {
      throw new Error(`marker data-score does not match displayed score: score=${score}, data-score=${marker.getAttribute("data-score")}`);
    }
    if (!ariaLabel.includes(String(score)) || !/Fear and Greed score/i.test(ariaLabel)) {
      throw new Error(`marker accessibility label does not describe the displayed score: ${ariaLabel}`);
    }
    const measure = () => {
      const track = scale.getBoundingClientRect();
      const dot = marker.getBoundingClientRect();
      return ((dot.left + dot.width / 2 - track.left) / track.width) * 100;
    };
    const initialPosition = measure();
    if (Math.abs(initialPosition - score) > 1.25) {
      throw new Error(`rendered white marker is misaligned: score=${score}, position=${initialPosition.toFixed(2)}%`);
    }
    const synthetic = [];
    for (const testScore of [20, 40, 75]) {
      marker.style.setProperty("left", `${testScore}%`, "important");
      const position = measure();
      if (Math.abs(position - testScore) > 1.25) {
        throw new Error(`synthetic marker test failed: expected=${testScore}, position=${position.toFixed(2)}%`);
      }
      synthetic.push({ score: testScore, rendered_position_pct: Number(position.toFixed(2)) });
    }
    return { displayed_score: score, rendered_position_pct: Number(initialPosition.toFixed(2)), synthetic_tests: synthetic };
  });
  // Restore the generated score-bound position after synthetic coordinate tests.
  await page.locator(".cnn-fg-preview .fg6-marker").evaluate((marker, score) => {
    marker.style.setProperty("left", `${score}%`, "important");
  }, await page.locator(".cnn-fg-preview .fg6-score").textContent().then(t => Number.parseFloat(t.trim())));

  // Navigation is locked to the approved mother. Monday and weekday mothers
  // have different anchor counts; compare the output against the selected mother.
  const templateKey = process.env.TEMPLATE_KEY || "weekday";
  const templateName = templateKey === "monday" ? "monday-mother-template.html" : "weekday-mother-template.html";
  const templatePath = path.resolve("simulation-lab/baseline", templateName);
  if (!fs.existsSync(templatePath)) throw new Error("approved mother template not found: " + templatePath);
  const templateHtml = fs.readFileSync(templatePath, "utf8");
  const templateNavTargets = await page.evaluate(html => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    return Array.from(doc.querySelectorAll("nav.nav a[href^='#']")).map(a => a.getAttribute("href"));
  }, templateHtml);

  const nav = page.locator("nav.nav a[href^='#']");
  const navCount = await nav.count();
  if (navCount !== templateNavTargets.length) {
    throw new Error("expected " + templateNavTargets.length + " in-page navigation links from approved " + templateKey + " mother, got " + navCount);
  }
  const navTargets = [];
  for (let i = 0; i < navCount; i++) {
    const href = await nav.nth(i).getAttribute("href");
    const targetId = href.slice(1);
    if (await page.locator('[id="' + targetId + '"]').count() !== 1) {
      throw new Error("navigation target missing or duplicated: " + href);
    }
    navTargets.push(href);
  }
  if (JSON.stringify(navTargets) !== JSON.stringify(templateNavTargets)) {
    throw new Error("rendered navigation anchors differ from the approved mother template");
  }
  const earningsNav = nav.filter({ hasText: "本週財報行事曆" });
  if (await earningsNav.count() !== 1) throw new Error("財報行事曆 navigation anchor missing");
  await earningsNav.evaluate(el => el.click());
  if (await page.evaluate(() => location.hash) !== "#earnings") {
    throw new Error("navigation click did not move to #earnings");
  }

  async function toggleDetails(selector, iconSelector = null) {
    const details = page.locator(selector).first();
    if (await details.count() !== 1) throw new Error("missing details element: " + selector);

    // The first previous-week event/card is nested inside a collapsed outer
    // disclosure. Open that parent before checking the inner control.
    const ancestor = details.locator("xpath=ancestor::details").first();
    const hasAncestor = await ancestor.count() > 0;
    const ancestorBefore = hasAncestor ? await ancestor.evaluate(el => el.open) : null;
    if (hasAncestor && !ancestorBefore) {
      const outerSummary = ancestor.locator(":scope > summary").first();
      if (!(await outerSummary.isVisible()) || !(await outerSummary.boundingBox())) {
        throw new Error("outer disclosure summary missing: " + selector);
      }
      await outerSummary.click();
      if (!(await ancestor.evaluate(el => el.open))) {
        throw new Error("outer disclosure did not open: " + selector);
      }
    }

    const summary = details.locator(":scope > summary").first();
    const before = await details.evaluate(el => el.open);
    if (iconSelector) {
      const icon = details.locator(iconSelector).first();
      if (await icon.count() !== 1 || !(await icon.boundingBox())) {
        if (hasAncestor && !ancestorBefore) await ancestor.locator(":scope > summary").click();
        throw new Error("toggle icon missing or not visible: " + iconSelector);
      }
    }
    if (!(await summary.isVisible())) throw new Error("accordion summary is not visible: " + selector);
    await summary.click();
    const after = await details.evaluate(el => el.open);
    if (after === before) throw new Error("summary did not toggle details: " + selector);
    await summary.click();
    const restored = await details.evaluate(el => el.open);
    if (restored !== before) throw new Error("details did not restore original state: " + selector);

    if (hasAncestor && !ancestorBefore) {
      await ancestor.locator(":scope > summary").click();
      if (await ancestor.evaluate(el => el.open)) {
        throw new Error("outer disclosure did not return to collapsed state: " + selector);
      }
    }
    return { selector, before, after, restored, ancestor_was_open: ancestorBefore };
  }

  const detailsTests = [
    await toggleDetails("details.earnings-accordion", ".earnings-accordion-toggle"),
    await toggleDetails("details.econ-event", ".econ-toggle, .econ-event-toggle"),
    await toggleDetails("details.sector-collapse")
  ];

  const focusLinks = await page.locator("#global-focus .newsmeta a[href]").evaluateAll(
    nodes => nodes.map(a => a.href)
  );
  if (focusLinks.length !== 5) throw new Error(`expected 5 focus news links, got ${focusLinks.length}`);
  if (!focusLinks.every(url => url.startsWith("https://hk.investing.com/") || url.includes(".cnyes.com/"))) {
    throw new Error("focus news contains a source outside Investing.com HK / Cnyes");
  }

  const headlineLinks = await page.locator("#headlines .newsmeta a[href]").evaluateAll(
    nodes => nodes.map(a => a.href)
  );
  if (headlineLinks.length !== 10) throw new Error(`expected 10 market headline links, got ${headlineLinks.length}`);
  if (!headlineLinks[9].startsWith("https://") || headlineLinks[9].includes("undefined")) {
    throw new Error("last market headline has an invalid source URL");
  }

  const investingLinks = await page.locator('a[href^="https://hk.investing.com/"], a[href^="https://www.investing.com/"]').count();
  // Count every official Cnyes subdomain (news, mobile, and Anue), not one hostname only.
  const cnyesLinks = await page.locator('a[href*=".cnyes.com/"], a[href^="https://cnyes.com/"]').count();
  if (investingLinks < 10 || cnyesLinks < 2) {
    throw new Error(`source links unexpectedly low: Investing.com=${investingLinks}, Cnyes=${cnyesLinks}`);
  }

  // Explicitly open the FOMC tab and verify the official Fed-officials agenda
  // at desktop and 320px mobile; the default screenshot only shows FedWatch.
  const fomcTab = page.locator('label[for="fed-live-tab-fomc"]');
  if (await fomcTab.count() !== 1) throw new Error("FOMC tab label missing");
  await fomcTab.click();
  if (!(await page.locator("#fed-live-tab-fomc").isChecked())) {
    throw new Error("FOMC tab radio did not become checked");
  }
  const fomcPanel = page.locator(".fed-live-panel.fed-live-fomc");
  if (!(await fomcPanel.isVisible())) throw new Error("FOMC panel did not become visible");
  const agenda = fomcPanel.locator(".fc-fomc-weekly-events");
  if (await agenda.count() !== 1 || !(await agenda.isVisible())) {
    throw new Error("本週聯準會官員行程 block missing or hidden");
  }
  const agendaEvent = agenda.locator('.fc-fomc-weekly-event:not([data-fed-event-template="true"])').first();
  if (await agendaEvent.count() !== 1) throw new Error("verified Fed official agenda event missing");
  const agendaText = (await agendaEvent.innerText()).replace(/\\s+/g, " ").trim();
  if (!agendaText.includes("預定｜11/24 二 05:00") || !agendaText.includes("John Williams")) {
    throw new Error("Fed official agenda date/name content mismatch: " + agendaText);
  }
  const agendaSource = agendaEvent.locator("a.fc-fomc-weekly-event-source[href]");
  if (await agendaSource.count() !== 1 || !(await agendaSource.getAttribute("href")).startsWith("https://")) {
    throw new Error("Fed official agenda source link missing or invalid");
  }

  const fedAgendaLayouts = [];
  const visualDir = "simulation-lab/output/visual";
  fs.mkdirSync(visualDir, { recursive: true });
  for (const width of [1440, 412, 390, 360, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const metrics = await agenda.evaluate(node => {
      const rect = node.getBoundingClientRect();
      const row = node.querySelector('.fc-fomc-weekly-event:not([data-fed-event-template="true"])');
      const rowRect = row.getBoundingClientRect();
      const date = row.querySelector(".fc-fomc-weekly-event-date");
      const content = row.querySelector(":scope > div:last-child");
      const dateRect = date.getBoundingClientRect();
      const contentRect = content.getBoundingClientRect();
      return {
        viewport_width: window.innerWidth,
        document_width: document.documentElement.scrollWidth,
        agenda_left: rect.left,
        agenda_right: rect.right,
        agenda_width: rect.width,
        row_width: rowRect.width,
        row_client_width: row.clientWidth,
        row_scroll_width: row.scrollWidth,
        date_right: dateRect.right,
        date_bottom: dateRect.bottom,
        content_left: contentRect.left,
        content_top: contentRect.top,
        content_width: contentRect.width,
        content_client_width: content.clientWidth,
        content_scroll_width: content.scrollWidth
      };
    });
    if (metrics.document_width > width + 1 || metrics.agenda_right > width + 1) {
      throw new Error(`Fed agenda overflows viewport ${width}px: ${JSON.stringify(metrics)}`);
    }
    const stackedAtNarrowWidth = width <= 412;
    const dateContentOrderValid = stackedAtNarrowWidth
      ? metrics.date_bottom <= metrics.content_top + 1 && metrics.content_width >= 150
      : metrics.date_right <= metrics.content_left + 1;
    if (metrics.row_scroll_width > metrics.row_client_width + 1 ||
        metrics.content_scroll_width > metrics.content_client_width + 1 ||
        !dateContentOrderValid || metrics.content_width < 50) {
      throw new Error(`Fed agenda columns are squeezed or overflow at ${width}px: ${JSON.stringify(metrics)}`);
    }
    await page.screenshot({ path: `${visualDir}/fed-fomc-${width}.png`, fullPage: true });
    fedAgendaLayouts.push(metrics);
  }
  if (fedAgendaLayouts.length !== 5) throw new Error("Fed official agenda was not checked at all five required viewports");

  if (pageErrors.length) throw new Error(`uncaught page errors: ${pageErrors.join(" | ")}`);

  const result = {
    status: "PASS",
    nav_count: navCount,
    nav_targets: navTargets,
    details_tests: detailsTests,
    focus_news_links: focusLinks.length,
    headline_links: headlineLinks.length,
    investing_links: investingLinks,
    cnyes_links: cnyesLinks,
    fear_greed_marker_test: fearGreedMarkerTest,
    fed_official_agenda_layout: fedAgendaLayouts,
    page_errors: pageErrors
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
  console.log("Interaction smoke test: PASS");
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
