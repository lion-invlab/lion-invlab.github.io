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

  const nav = page.locator("nav.nav a[href^='#']");
  const navCount = await nav.count();
  if (navCount !== 10) throw new Error(`expected 10 in-page navigation links, got ${navCount}`);
  const navTargets = [];
  for (let i = 0; i < navCount; i++) {
    const href = await nav.nth(i).getAttribute("href");
    const targetId = href.slice(1);
    if (await page.locator(`[id="${targetId}"]`).count() !== 1) {
      throw new Error(`navigation target missing or duplicated: ${href}`);
    }
    navTargets.push(href);
  }
  const earningsNav = nav.filter({ hasText: "本週財報行事曆" });
  if (await earningsNav.count() !== 1) throw new Error("財報行事曆 navigation anchor missing");
  await earningsNav.evaluate(el => el.click());
  if (await page.evaluate(() => location.hash) !== "#earnings") {
    throw new Error("navigation click did not move to #earnings");
  }

  async function toggleDetails(selector, iconSelector = null) {
    const details = page.locator(selector).first();
    if (await details.count() !== 1) throw new Error(`missing details element: ${selector}`);
    // Restrict to the direct summary child; nested source accordions may
    // contain their own summary elements (e.g. the sector source disclosure).
    const summary = details.locator(":scope > summary").first();
    const before = await details.evaluate(el => el.open);
    if (iconSelector) {
      const icon = details.locator(iconSelector).first();
      if (await icon.count() !== 1 || !(await icon.boundingBox())) {
        throw new Error(`toggle icon missing or not visible: ${iconSelector}`);
      }
    }
    await summary.click();
    const after = await details.evaluate(el => el.open);
    if (after === before) throw new Error(`summary did not toggle details: ${selector}`);
    await summary.click();
    const restored = await details.evaluate(el => el.open);
    if (restored !== before) throw new Error(`details did not restore original state: ${selector}`);
    return { selector, before, after, restored };
  }

  const detailsTests = [
    await toggleDetails("details.earnings-accordion", ".earnings-accordion-toggle"),
    await toggleDetails("details.econ-event", ".econ-toggle"),
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
    page_errors: pageErrors
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + "\n", "utf8");
  console.log("Interaction smoke test: PASS");
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
