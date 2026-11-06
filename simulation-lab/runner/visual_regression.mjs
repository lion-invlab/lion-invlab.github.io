import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";

const reportPath = process.argv[2] || "simulation-lab/fixtures/existing-preview-2026-11-06.html";
const reportDate = "2026-11-06";
const manifest = JSON.parse(fs.readFileSync("母版專區/mother-template-manifest.json", "utf8"));
const master = manifest.templates.weekdays;
const masterBytes = fs.readFileSync(master.path);
const gitBlobSha = crypto.createHash("sha1").update(Buffer.concat([
  Buffer.from(`blob ${masterBytes.length}\0`), masterBytes
])).digest("hex");
if (gitBlobSha !== master.blob_sha) throw new Error(`母版 SHA 不符：Manifest=${master.blob_sha} actual=${gitBlobSha}`);
if (!fs.existsSync(reportPath)) throw new Error(`審核版不存在：${reportPath}`);

const output = "simulation-lab/output/visual";
fs.mkdirSync(output, { recursive: true });
const selectors = [
  ".top", ".nav", ".wrap", ".bluf", ".sent", "#overview", "#sentiment",
  "#news-scan", "#global-markets", "#industry-bonds-fx-commodities",
  "#calendar", "#earnings", "#sp500-earnings-health", "#fed", "#view", ".footer"
];
const viewports = [
  { name: "desktop-1440", width: 1440, height: 1000 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "mobile-360", width: 360, height: 900 }
];
const browser = await chromium.launch({ headless: true });
const failures = [];
const snapshots = {};
async function load(page, file) {
  await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
}
async function inspect(page) {
  return page.evaluate((targets) => {
    const round = n => Math.round(n * 100) / 100;
    const sections = {};
    for (const selector of targets) {
      const el = document.querySelector(selector);
      if (!el) { sections[selector] = null; continue; }
      const cs = getComputedStyle(el), r = el.getBoundingClientRect();
      sections[selector] = {
        x: round(r.x), width: round(r.width), display: cs.display,
        position: cs.position, gridTemplateColumns: cs.gridTemplateColumns,
        gap: cs.gap, padding: cs.padding, borderRadius: cs.borderRadius,
        boxSizing: cs.boxSizing, fontFamily: cs.fontFamily, fontSize: cs.fontSize
      };
    }
    return { viewport: innerWidth, documentWidth: document.documentElement.scrollWidth, sections };
  }, selectors);
}
try {
  for (const v of viewports) {
    const masterPage = await browser.newPage({ viewport: { width: v.width, height: v.height } });
    const reportPage = await browser.newPage({ viewport: { width: v.width, height: v.height } });
    await load(masterPage, master.path);
    await load(reportPage, reportPath);
    await masterPage.screenshot({ path: path.join(output, `${v.name}-master.png`), fullPage: true });
    await reportPage.screenshot({ path: path.join(output, `${v.name}-report.png`), fullPage: true });
    const a = await inspect(masterPage), b = await inspect(reportPage);
    snapshots[v.name] = { master: a, report: b };
    // Component-level acceptance: published earnings retain paired EPS/revenue cards.
    const earningsAudit = await reportPage.evaluate(() => {
      const groups = [...document.querySelectorAll("#earnings .calendar-status-group")];
      const published = groups[2];
      if (!published) return { count: 0, invalid: ["published group missing"] };
      const cards = [...published.querySelectorAll("details.earnings-accordion")];
      const invalid = [];
      for (const [i, card] of cards.entries()) {
        const grid = card.querySelector(":scope > .earnings-accordion-details > .earnings-results-grid");
        const resultCards = grid ? grid.querySelectorAll(":scope > .earnings-actual-card").length : 0;
        if (!grid || resultCards !== 2) invalid.push("card " + (i+1) + ": paired EPS/revenue cards missing");
        if (!card.querySelector(".earnings-detail-field label")) invalid.push("card " + (i+1) + ": supporting details missing");
      }
      const sampleGrid = published.querySelector(".earnings-results-grid");
      const columns = sampleGrid ? getComputedStyle(sampleGrid).gridTemplateColumns.split(" ").length : 0;
      if (cards.length && columns !== 2) invalid.push("published result grid columns=" + columns + ", expected 2");
      return { count: cards.length, invalid, columns };
    });
    snapshots[v.name].earnings_component = earningsAudit;
    const economicAudit = await reportPage.evaluate(() => {
      const cards = [...document.querySelectorAll("#calendar details.econ-event")];
      const invalid = [];
      for (const [i, card] of cards.entries()) {
        const grid = card.querySelector(":scope > .econ-details > .econ-primary-grid");
        if (!grid) { invalid.push("card " + (i+1) + ": comparison grid missing"); continue; }
        for (const cls of ["econ-prev","econ-forecast","econ-actual"]) {
          if (!grid.querySelector(":scope > ." + cls)) invalid.push("card " + (i+1) + ": " + cls + " missing");
        }
        for (const cls of ["econ-impact","econ-source"]) {
          if (!card.querySelector(":scope > .econ-details > ." + cls)) invalid.push("card " + (i+1) + ": " + cls + " missing or not full-width");
        }
        const prev = grid.querySelector(".econ-prev")?.getBoundingClientRect();
        const forecast = grid.querySelector(".econ-forecast")?.getBoundingClientRect();
        const actual = grid.querySelector(".econ-actual")?.getBoundingClientRect();
        if (prev && forecast && actual && Math.abs(actual.height - (prev.height + forecast.height + parseFloat(getComputedStyle(grid).rowGap || "0"))) > 4) {
          invalid.push("card " + (i+1) + ": actual field height does not span previous + forecast");
        }
      }
      return { count: cards.length, invalid };
    });
    snapshots[v.name].economic_component = economicAudit;
    if (economicAudit.count === 0 || economicAudit.invalid.length) {
      failures.push(v.name + ": 經濟行事曆元件 QA FAIL：" + (economicAudit.invalid.join("; ") || "no economic cards"));
    }

    if (earningsAudit.count === 0 || earningsAudit.invalid.length) {
      failures.push(v.name + ": 已公布財報元件 QA FAIL：" + (earningsAudit.invalid.join("; ") || "no published cards"));
    }

    if (a.documentWidth > v.width + 2) failures.push(`${v.name}: 母版本身橫向溢出 ${a.documentWidth}px`);
    if (b.documentWidth > v.width + 2) failures.push(`${v.name}: 審核版橫向溢出 ${b.documentWidth}px`);
    for (const selector of selectors) {
      const x = a.sections[selector], y = b.sections[selector];
      if (!!x !== !!y) { failures.push(`${v.name}: ${selector} 存在性不同`); continue; }
      if (!x) continue;
      for (const key of ["display","position","gridTemplateColumns","gap","padding","borderRadius","boxSizing"]) {
        if (x[key] !== y[key]) failures.push(`${v.name}: ${selector} ${key} 不同`);
      }
      if (Math.abs(x.x-y.x)>2 || Math.abs(x.width-y.width)>2) {
        failures.push(`${v.name}: ${selector} 幾何差異 master=${x.x}/${x.width} report=${y.x}/${y.width}`);
      }
    }
    await masterPage.close(); await reportPage.close();
  }
} finally {
  await browser.close();
}
fs.writeFileSync(path.join(output, "visual-regression.json"), JSON.stringify({
  report_date: reportDate, report_path: reportPath, master_path: master.path,
  master_blob_sha: gitBlobSha, viewports, failures, snapshots
}, null, 2));
console.log(`視覺基準比對：${failures.length ? "FAIL" : "PASS"}；視窗：1440 / 768 / 360；母版 SHA：${gitBlobSha}`);
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
