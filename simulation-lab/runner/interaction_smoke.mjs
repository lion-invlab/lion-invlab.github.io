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

  async function toggleDetails(selector, iconSelector) {
  const details = page.locator(selector).first();
  if (await details.count() < 1) throw new Error("accordion not found: " + selector);

  // Previous-week sections are nested inside a collapsed outer disclosure.
  // Open ancestor details first so the inner control is actually visible.
  const ancestor = details.locator("xpath=ancestor::details").first();
  const hasAncestor = await ancestor.count() > 0;
  let ancestorWasOpen = false;
  if (hasAncestor) {
    ancestorWasOpen = await ancestor.evaluate(el => el.open);
    const ancestorSummary = ancestor.locator("summary").first();
    if (!(await ancestorSummary.isVisible()) || !(await ancestorSummary.boundingBox())) {
      throw new Error("outer disclosure control is not visible: " + selector);
    }
    if (!ancestorWasOpen) {
      await ancestorSummary.click();
      if (!(await ancestor.evaluate(el => el.open))) {
        throw new Error("outer disclosure did not open: " + selector);
      }
    }
  }

  const icon = details.locator(iconSelector).first();
  if (await icon.count() !== 1 || !(await icon.boundingBox())) {
    if (hasAncestor && !ancestorWasOpen) await ancestor.locator("summary").click();
    throw new Error("toggle icon missing or not visible: " + iconSelector);
  }
  const summary = details.locator("summary").first();
  if (!(await summary.isVisible())) throw new Error("accordion summary is not visible: " + selector);
  await summary.click();
  if (!(await details.evaluate(el => el.open))) throw new Error("accordion did not open: " + selector);
  await summary.click();
  if (await details.evaluate(el => el.open)) throw new Error("accordion did not close: " + selector);

  if (hasAncestor && !ancestorWasOpen) {
    await ancestor.locator("summary").click();
    if (await ancestor.evaluate(el => el.open)) {
      throw new Error("outer disclosure did not return to collapsed state: " + selector);
    }
  }
}
