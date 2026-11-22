#!/usr/bin/env node
/** Responsive browser smoke test for the five-layer analysis slots in both simulation mothers. */
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const root = process.cwd();
const outDir = path.join(root, "simulation-lab/output/market-analysis-browser");
const widths = [1440, 768, 412, 390, 360, 320];
const candidatePaths = process.argv.slice(2);
if (candidatePaths.length !== 0 && candidatePaths.length !== 2) {
  throw new Error("Pass either no paths for synthetic mother fixtures or exactly two paths for full Builder candidate reports");
}
const pages = candidatePaths.length === 2
  ? [["monday", path.resolve(candidatePaths[0])], ["weekdays", path.resolve(candidatePaths[1])]]
  : [
      ["monday", path.join(outDir, "monday.html")],
      ["weekdays", path.join(outDir, "weekdays.html")],
    ];
const evidenceFile = candidatePaths.length === 2 ? "browser-qa-candidate.json" : "browser-qa.json";
const expected = [
  "一、政治與地緣政治局勢",
  "二、政策傳導與企業／產業鏈影響",
  "三、宏觀經濟傳導",
  "四、金融市場定價、情緒與風險",
  "五、機構資金動向與投資策略",
];
if (pages.some(([, file]) => !fs.existsSync(file))) {
  throw new Error("Isolated five-layer HTML fixtures are missing; run render_market_analysis_test_pages.py first");
}
const browser = await chromium.launch({ headless: true });
const evidence = [];
try {
  for (const [variant, file] of pages) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
    await page.route("**/*", route => {
      const url = route.request().url();
      if (url.startsWith("http://") || url.startsWith("https://")) return route.abort();
      return route.continue();
    });
    await page.goto(pathToFileURL(file).href, { waitUntil: "domcontentloaded" });
    await page.evaluate(async () => { await document.fonts.ready; return true; });
    for (const width of widths) {
      await page.setViewportSize({ width, height: 1000 });
      const metrics = await page.evaluate(() => {
        const box = document.querySelector("#market-analysis");
        if (!box) throw new Error("market-analysis container missing");
        const boxRect = box.getBoundingClientRect();
        const layers = [...box.querySelectorAll(":scope > .market-analysis-layer")];
        return {
          viewport: window.innerWidth,
          boxLeft: boxRect.left,
          boxRight: boxRect.right,
          boxWidth: box.clientWidth,
          boxScrollWidth: box.scrollWidth,
          headings: layers.map(layer => {
            const heading = layer.querySelector(":scope > h3");
            const content = layer.querySelector(":scope > .market-analysis-content");
            const hr = heading.getBoundingClientRect();
            return {
              text: heading?.textContent?.trim() || "",
              headingWidth: heading?.clientWidth || 0,
              headingScrollWidth: heading?.scrollWidth || 0,
              contentWidth: content?.clientWidth || 0,
              contentScrollWidth: content?.scrollWidth || 0,
              height: layer.getBoundingClientRect().height,
              headingRight: hr.right,
              paragraphs: content?.querySelectorAll(":scope > p").length || 0,
              sourceLinks: content?.querySelectorAll("p.market-analysis-sources a[href^='https://']").length || 0,
            };
          }),
        };
      });
      if (metrics.headings.length !== 5) throw new Error(variant + "/" + width + ": expected five layers");
      if (metrics.boxLeft < -1 || metrics.boxRight > width + 1) {
        throw new Error(variant + "/" + width + ": analysis container exceeds viewport: " + JSON.stringify(metrics));
      }
      if (metrics.boxScrollWidth > metrics.boxWidth + 1) {
        throw new Error(variant + "/" + width + ": analysis container has horizontal overflow");
      }
      metrics.headings.forEach((h, index) => {
        if (h.text !== expected[index]) throw new Error(variant + "/" + width + ": heading order mismatch at " + index);
        if (h.headingScrollWidth > h.headingWidth + 1 || h.contentScrollWidth > h.contentWidth + 1) {
          throw new Error(variant + "/" + width + ": layer " + (index + 1) + " has horizontal text overflow");
        }
        if (!h.height || h.paragraphs < 2 || h.sourceLinks < 1) {
          throw new Error(variant + "/" + width + ": layer " + (index + 1) + " missing visible text/source content");
        }
      });
      if (width === 1440 || width === 320) {
        await page.screenshot({
          path: path.join(outDir, variant + "-" + width + ".png"),
          fullPage: false,
        });
      }
      evidence.push({ variant, ...metrics });
    }
    await page.close();
  }
} finally {
  await browser.close();
}
const result = {
  status: "PASS",
  variants: pages.map(([name]) => name),
  viewports: widths,
  layers: expected,
  evidence,
};
fs.writeFileSync(path.join(outDir, evidenceFile), JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify(result, null, 2));
