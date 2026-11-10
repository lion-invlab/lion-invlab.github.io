import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";

const reportPath = process.argv[2] || "simulation-lab/fixtures/existing-preview-2026-11-06.html";
const templateKey = process.argv[3] || "weekdays";
const reportDate = process.argv[4] || "2026-11-06";
const manifest = JSON.parse(fs.readFileSync("simulation-lab/baseline/mother-template-manifest.json", "utf8"));
const master = manifest.templates[templateKey];
const masterPath = master.simulation_path;
const masterBytes = fs.readFileSync(masterPath);
const gitBlobSha = crypto.createHash("sha1").update(Buffer.concat([
  Buffer.from(`blob ${masterBytes.length}\0`), masterBytes
])).digest("hex");
if (gitBlobSha !== master.simulation_blob_sha) throw new Error(`模擬母版 SHA 不符：Manifest=${master.simulation_blob_sha} actual=${gitBlobSha}`);
if (!fs.existsSync(reportPath)) throw new Error(`審核版不存在：${reportPath}`);

const output = "simulation-lab/output/visual";
fs.mkdirSync(output, { recursive: true });
const selectors = [
  ".top", ".nav", ".wrap", ".bluf", ".sent", "#overview", "#sentiment",
  "#news-scan", "#global-markets", "#industry-bonds-fx-commodities",
  "#calendar", "#earnings", "#last-week-calendar", "#last-week-earnings", "#sp500-earnings-health", "#fed", "#view", ".footer"
];
const viewports = [
  { name: "desktop-1440", width: 1440, height: 1000 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "mobile-360", width: 360, height: 900 },
  { name: "mobile-320", width: 320, height: 844 }
];
const browser = await chromium.launch({ headless: true });
const failures = [];
const snapshots = {};
async function load(page, file) {
  await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  // Dismiss the approved fund-reminder overlay in QA captures only.
  // The source HTML remains unchanged; this prevents a modal from obscuring the visual baseline.
  await page.evaluate(() => {
    const close = document.querySelector("#tfn-close");
    if (close && getComputedStyle(close).display !== "none") close.click();
  });
  await page.waitForTimeout(80);
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
    const focusAudit = await reportPage.evaluate((reportDate) => {
      const cases = [
        { id: "focus-tab-market", panel: ".focus-market", needles: ["市場觀點", "美國10月CPI月增0.4%", "Waller支持12月升息"] },
        { id: "focus-tab-levels", panel: ".focus-levels", needles: ["道瓊工業指數", "支撐 S1：", "中樞 P：", "壓力 R1：", "S&P 500", "Nasdaq Composite", "費城半導體指數（SOX）", "Russell 2000", "關鍵價位計算方式與資料來源"] },
        { id: "focus-tab-core", panel: ".focus-core", needles: ["今日核心觀察", "12月升息", "50個基點"] }
      ];
      const results = [], invalid = [];
      for (const item of cases) {
        const input = document.getElementById(item.id);
        const label = document.querySelector(`label[for="${item.id}"]`);
        const panel = document.querySelector("#view " + item.panel);
        if (!input || !label || !panel) { invalid.push(item.id + ": input/label/panel missing"); continue; }
        label.click();
        const rect = panel.getBoundingClientRect();
        const visible = getComputedStyle(panel).display !== "none" && rect.width > 0 && rect.height > 0;
        const text = panel.innerText || "";
        if (!input.checked) invalid.push(item.id + ": radio did not become checked after label click");
        if (!visible) invalid.push(item.id + ": target panel is not visible after tab click");
        for (const needle of item.needles) if (!text.includes(needle)) invalid.push(item.id + ": missing expected content " + needle);
        if (item.id === "focus-tab-levels") {
          const source = panel.querySelector("details.source-details .source")?.textContent || "";
          const sourceDateMatch = source.match(/基準交易日：(\d{4}-\d{2}-\d{2})/);
          if (!sourceDateMatch) invalid.push(item.id + ": missing OHLC source trading date");
          else if (!(sourceDateMatch[1] < reportDate)) invalid.push(item.id + ": OHLC trading date is not before report date");
          if (!source.includes("Yahoo Finance OHLC")) invalid.push(item.id + ": missing OHLC source attribution");
        }
        results.push({ id: item.id, checked: input.checked, visible, text_length: text.length, needles: item.needles });
      }
      return { count: results.length, results, invalid };
    }, reportDate);
    snapshots[v.name].today_focus_tabs = focusAudit;
    if (focusAudit.count !== 3 || focusAudit.invalid.length) {
      failures.push(`${v.name}: 今日觀察三活頁互動 QA FAIL：` + (focusAudit.invalid.join("; ") || "three tabs not tested"));
    }
    // Expand the containing calendar panels and one published accordion for geometry measurement.
    // Do this after screenshots so the delivered initial-state captures remain unchanged.
    await reportPage.evaluate(() => {
      document.querySelectorAll("#earnings details, #last-week-calendar details, #last-week-earnings details").forEach(node => { node.open = true; });
      document.querySelectorAll("#earnings .calendar-status-group, #last-week-calendar .calendar-status-group, #last-week-earnings .calendar-status-group").forEach(node => {
        node.hidden = false;
        node.style.display = "";
      });
    });
    await reportPage.waitForTimeout(80);
    const mondayHasRetrospective = await reportPage.locator("#last-week-earnings .calendar-status-group").count();
    if (!mondayHasRetrospective) {
      // The approved fund reminder may auto-open and cover the tab labels.
      // Dismiss it and activate the published radio through the label's native click event.
      await reportPage.evaluate(() => {
        document.querySelector("#tfn-close")?.click();
        document.querySelector('label[for="week-earnings-published"]')?.click();
      });
      await reportPage.waitForFunction(() => {
        const radio = document.querySelector("#week-earnings-published");
        const group = document.querySelector("#earnings .calendar-status-group:nth-child(3)");
        return !!radio?.checked && !!group && getComputedStyle(group).display !== "none";
      });
    }
    const earningsAudit = await reportPage.evaluate(() => {
      const groups = [...document.querySelectorAll("#earnings .calendar-status-group")];
      const mondayRetrospective = document.querySelector("#last-week-earnings .calendar-status-group");
      const weekdayPublished = groups.find(group => group.querySelector(".calendar-status-heading.published"));
      const auditGroup = mondayRetrospective || weekdayPublished || groups[1];
      const publishedMode = !!mondayRetrospective || !!weekdayPublished;
      const mode = mondayRetrospective ? "monday-published-results" : weekdayPublished ? "weekday-published-results" : "weekday-upcoming-events";
      if (!auditGroup) return { mode, count: 0, invalid: ["earnings audit group missing"] };
      const cards = [...auditGroup.querySelectorAll("details.earnings-accordion")];
      const invalid = [];
      for (const [i, card] of cards.entries()) {
        if (!card.querySelector(":scope > summary.earnings-accordion-summary")) invalid.push("card " + (i+1) + ": summary missing");
        const details = card.querySelector(":scope > .earnings-accordion-details");
        if (!details) invalid.push("card " + (i+1) + ": detail panel missing");
        if (!card.querySelector(".earnings-detail-field label")) invalid.push("card " + (i+1) + ": supporting details missing");
        if (publishedMode) {
          const grid = details?.querySelector(":scope > .earnings-results-grid");
          const resultCards = grid ? grid.querySelectorAll(":scope > .earnings-actual-card").length : 0;
          if (!grid || resultCards !== 2) invalid.push("card " + (i+1) + ": paired EPS/revenue cards missing");
          const labels = [...(details?.querySelectorAll(":scope > .earnings-detail-field label") || [])].map(node => node.textContent.trim());
          if (!["財報判讀", "股價當日表現", "來源"].every(label => labels.includes(label))) {
            invalid.push("card " + (i+1) + ": published analysis/reaction/source sections missing");
          }
        }
      }
      if (cards.length === 0) invalid.push("no earnings cards in the selected report-week group");
      let columns = null, pairedGeometry = null, measured = [];
      if (publishedMode) {
        // Published earnings cards (Monday retrospective or weekday current-week) contain EPS/revenue pairs.
        const visibleGrids = [...auditGroup.querySelectorAll(".earnings-results-grid")]
          .filter(grid => {
            const rect = grid.getBoundingClientRect();
            const style = getComputedStyle(grid);
            return rect.width > 0 && rect.height > 0 &&
              style.display !== "none" && style.visibility !== "hidden";
          });
        measured = visibleGrids.map(grid => {
          const children = [...grid.querySelectorAll(":scope > .earnings-actual-card")];
          const visibleCards = children.filter(card => {
            const rect = card.getBoundingClientRect();
            const style = getComputedStyle(card);
            return rect.width > 0 && rect.height > 0 &&
              style.display !== "none" && style.visibility !== "hidden";
          });
          if (visibleCards.length < 2) return null;
          const a = visibleCards[0].getBoundingClientRect();
          const b = visibleCards[1].getBoundingClientRect();
          return {
            columns: Math.abs(a.left - b.left) > 2 && Math.abs(a.top - b.top) <= 2 ? 2 : 1,
            pairedGeometry: {
              firstLeft: Math.round(a.left), secondLeft: Math.round(b.left),
              firstTop: Math.round(a.top), secondTop: Math.round(b.top),
              firstWidth: Math.round(a.width), secondWidth: Math.round(b.width),
              sameRow: Math.abs(a.top - b.top) <= 2,
              distinctColumns: Math.abs(a.left - b.left) > 2
            }
          };
        }).filter(Boolean);
        const sample = measured.find(x => x.columns === 2) || measured[0] || null;
        columns = sample?.columns || 0;
        pairedGeometry = sample?.pairedGeometry || null;
        if (!sample) invalid.push("visible published EPS/revenue result grid with two measurable cards missing");
        else if (columns !== 2) invalid.push("visible EPS/revenue cards are not in two side-by-side columns");
      }
      return { mode, count: cards.length, invalid, columns, pairedGeometry, visible_result_grids: measured.length };
    });
    snapshots[v.name].earnings_component = earningsAudit;
    // Save a focused, unobscured screenshot of the actual published cards after
    // activating the published tab and expanding the cards for visual review.
    if (earningsAudit.mode === "weekday-published-results") {
      const publishedGroup = reportPage.locator("#earnings .calendar-status-group").filter({
        has: reportPage.locator(".calendar-status-heading.published")
      });
      await publishedGroup.screenshot({ path: path.join(output, `${v.name}-published-earnings.png`) });
    } else if (earningsAudit.mode === "monday-published-results") {
      await reportPage.locator("#last-week-earnings .calendar-status-group").screenshot({
        path: path.join(output, `${v.name}-published-earnings.png`)
      });
    }
    const economicAudit = await reportPage.evaluate(() => {
      const cards = [...document.querySelectorAll("#calendar details.econ-event, #last-week-calendar details.econ-event")];
      const invalid = [];
      for (const [i, card] of cards.entries()) {
        const details = card.querySelector(":scope > .econ-details");
        const grid = details?.querySelector(":scope > .econ-primary-grid");
        if (!grid) { invalid.push("card " + (i+1) + ": comparison grid missing"); continue; }
        for (const cls of ["econ-prev","econ-forecast","econ-actual"]) {
          if (!grid.querySelector(":scope > ." + cls)) invalid.push("card " + (i+1) + ": " + cls + " missing");
        }
        for (const cls of ["econ-impact","econ-source"]) {
          if (!details.querySelector(":scope > ." + cls)) invalid.push("card " + (i+1) + ": " + cls + " missing");
        }
        const prev = grid.querySelector(".econ-prev")?.getBoundingClientRect();
        const forecast = grid.querySelector(".econ-forecast")?.getBoundingClientRect();
        const actual = grid.querySelector(".econ-actual")?.getBoundingClientRect();
        if (prev && forecast && actual) {
          if (Math.abs(actual.top-prev.top)>2 || Math.abs(actual.bottom-forecast.bottom)>4) {
            invalid.push("card " + (i+1) + ": actual field does not span previous + forecast");
          }
          if (Math.abs(prev.left-forecast.left)>2 || actual.left < prev.right-2) {
            invalid.push("card " + (i+1) + ": previous/forecast left stack and actual right column misaligned");
          }
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
  report_date: reportDate, report_path: reportPath, master_path: masterPath,
  master_blob_sha: gitBlobSha, template: templateKey, viewports, failures, snapshots
}, null, 2));
console.log(`視覺基準比對：${failures.length ? "FAIL" : "PASS"}；視窗：1440 / 768 / 360；母版 SHA：${gitBlobSha}`);
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
