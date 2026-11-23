// [build-tac-report] Full simulation browser QA; includes summary heading typography parity and explicit WTI/Brent energy tab geometry.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";

const [reportPath, templateKey, reportDate] = process.argv.slice(2);
if (!reportPath || !templateKey || !reportDate) {
  throw new Error("用法：node simulation-lab/runner/visual_regression.mjs <審核版HTML路徑> <monday|weekdays> <YYYY-MM-DD>；禁止回退至舊版 fixture。");
}
if (!["monday", "weekdays"].includes(templateKey)) throw new Error(`未知母版類型：${templateKey}`);
if (!/^\d{4}-\d{2}-\d{2}$/.test(reportDate) || Number.isNaN(Date.parse(reportDate))) {
  throw new Error(`報告日期格式錯誤：${reportDate}`);
}
const manifest = JSON.parse(fs.readFileSync("simulation-lab/baseline/mother-template-manifest.json", "utf8"));
const master = manifest.templates[templateKey];
const masterPath = master.simulation_path;
const masterBytes = fs.readFileSync(masterPath);
const gitBlobSha = crypto.createHash("sha1").update(Buffer.concat([
  Buffer.from(`blob ${masterBytes.length}\0`), masterBytes
])).digest("hex");
if (gitBlobSha !== master.simulation_blob_sha) throw new Error(`模擬母版 SHA 不符：Manifest=${master.simulation_blob_sha} actual=${gitBlobSha}`);
if (!fs.existsSync(reportPath)) throw new Error(`審核版不存在：${reportPath}`);
const reportHtml = fs.readFileSync(reportPath, "utf8");
const reportDateTag = reportHtml.match(/<meta\b[^>]*\bname=["']report-date["'][^>]*>/i)?.[0] || "";
const embeddedDate = reportDateTag.match(/\bcontent=["']([^"']+)["']/i)?.[1];
if (!embeddedDate) throw new Error("審核版缺少 meta[name=report-date]；拒絕執行日期未核實的視覺 QA。");
if (embeddedDate !== reportDate) throw new Error(`審核版日期不符：HTML=${embeddedDate}，參數=${reportDate}`);

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
  { name: "mobile-412", width: 412, height: 900 },
  { name: "mobile-390", width: 390, height: 900 },
  { name: "mobile-360", width: 360, height: 900 },
  { name: "mobile-320", width: 320, height: 900 }
];
const browser = await chromium.launch({ headless: true });
const failures = [];
const snapshots = {};
const fontAudits = [];
async function load(page, file) {
  await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: "load" });
  const fontAudit = await page.evaluate(async () => {
    await document.fonts.ready;
    return {
      font_family: getComputedStyle(document.body).fontFamily,
      noto_sans_tc_available: document.fonts.check('16px "Noto Sans TC"', "繁體中文")
    };
  });
  fontAudits.push({ file, ...fontAudit });
  if (!fontAudit.noto_sans_tc_available || !fontAudit.font_family.includes("Noto Sans TC")) {
    throw new Error(`繁體中文字型未就緒：${file}；family=${fontAudit.font_family}；Noto Sans TC=${fontAudit.noto_sans_tc_available}`);
  }
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

    // Explicitly exercise the Energy tab at every viewport; the default screenshot
    // only captures the initially selected S&P 11 tab.
    const energyTab = reportPage.locator('label[for="tac-assets-3"]');
    if (await energyTab.count() !== 1) throw new Error(`${v.name}: Energy tab label missing or duplicated`);
    await energyTab.click();
    await reportPage.waitForFunction(() => {
      const radio = document.querySelector("#tac-assets-3");
      const panel = document.querySelector("#tac-assets-panel-3");
      return !!radio?.checked && !!panel && getComputedStyle(panel).display !== "none";
    });
    const energyAudit = await reportPage.evaluate(() => {
      const panel = document.querySelector("#tac-assets-panel-3");
      const card = panel?.querySelector(".energy-card");
      const rows = [...(card?.querySelectorAll(":scope .row") || [])];
      const invalid = [];
      const measured = rows.map((row, index) => {
        const children = [...row.children];
        if (children.length !== 3 || !children[0].matches("b") ||
            !children[1].classList.contains("r") || !children[2].classList.contains("r")) {
          invalid.push(`row ${index + 1}: expected label, price and change as three direct children`);
          return { index, child_count: children.length };
        }
        const box = node => {
          const r = node.getBoundingClientRect();
          return { left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width, height:r.height };
        };
        const rowBox = box(row), label = box(children[0]), price = box(children[1]), change = box(children[2]);
        if (!(rowBox.width > 0 && label.width > 0 && price.width > 0 && change.width > 0)) invalid.push(`row ${index + 1}: zero-sized child`);
        if (label.right > price.left + 1 || price.right > change.left + 1) invalid.push(`row ${index + 1}: label/price/change overlap`);
        if (label.left < rowBox.left - 1 || change.right > rowBox.right + 1) invalid.push(`row ${index + 1}: child exceeds row bounds`);
        // Energy quote alignment is measured by visual cell centers, not text top edges.
        const centerY = box => (box.top + box.bottom) / 2;
        if (Math.abs(centerY(label) - centerY(price)) > 3 || Math.abs(centerY(price) - centerY(change)) > 3) invalid.push(`row ${index + 1}: quote columns are vertically misaligned`);
        return { index, text:row.innerText, row:rowBox, label, price, change };
      });
      const gridDisplay = rows.map(row => getComputedStyle(row).display);
      if (!card) invalid.push("energy card missing");
      if (rows.length !== 2) invalid.push(`expected exactly WTI and Brent rows, found ${rows.length}`);
      if (gridDisplay.some(value => value !== "grid")) invalid.push(`energy quote rows are not CSS grid: ${gridDisplay.join(",")}`);
      const text = card?.innerText || "";
      if (!text.includes("WTI 原油期貨") || !text.includes("Brent 原油期貨")) invalid.push("WTI/Brent labels missing");
      return { visible:!!card && card.getBoundingClientRect().width > 0, rows:measured, grid_display:gridDisplay, invalid, text };
    });
    snapshots[v.name] = snapshots[v.name] || {};
    snapshots[v.name].energy_tab = energyAudit;
    if (!energyAudit.visible || energyAudit.rows.length !== 2 || energyAudit.invalid.length) {
      failures.push(`${v.name}: WTI/Brent energy tab QA FAIL: ${energyAudit.invalid.join("; ") || "energy panel not visible"}`);
    }
    await reportPage.locator("#tac-assets-panel-3").screenshot({ path:path.join(output, `${v.name}-energy-report.png`) });
    const a = await inspect(masterPage), b = await inspect(reportPage);
    snapshots[v.name] = { ...(snapshots[v.name] || {}), master: a, report: b };
    const summaryHeadingAudit = await reportPage.evaluate(() => {
      const summary = document.querySelector("#overview .card.bluf > .title");
      const reference = document.querySelector("#sentiment > .title");
      if (!summary || !reference) return { valid: false, reason: "summary/sentiment section heading missing" };
      const summarySize = getComputedStyle(summary).fontSize;
      const referenceSize = getComputedStyle(reference).fontSize;
      return { valid: summarySize === referenceSize, summarySize, referenceSize };
    });
    snapshots[v.name].summary_heading = summaryHeadingAudit;
    if (!summaryHeadingAudit.valid) {
      failures.push(`${v.name}: summary red section heading font size does not match the primary section heading: ${JSON.stringify(summaryHeadingAudit)}`);
    }
    const specialAudit = await reportPage.evaluate(() => {
      const node = document.querySelector("#tac-special-focus-cpi");
      if (!node) return { exists: false };
      const rect = node.getBoundingClientRect();
      const summary = document.querySelector("#overview > section.grid.two > article.card.bluf");
      const summaryRect = summary?.getBoundingClientRect();
      const bg = getComputedStyle(node).backgroundImage;
      return { exists: true, width: Math.round(rect.width), right: Math.round(rect.right),
        beforeSummary: !!summaryRect && rect.bottom <= summaryRect.top + 1,
        darkOverlay: bg.includes("linear-gradient"), text: node.innerText };
    });
    snapshots[v.name].special_focus = specialAudit;
    // Special-focus sections are optional on ordinary report days; when present, validate them.
    if (specialAudit.exists && (!specialAudit.beforeSummary || specialAudit.width > v.width || specialAudit.right > v.width)) failures.push(`${v.name}: CPI special focus placement/overflow invalid`);
    if (specialAudit.exists && !["0.4%", "0.3%", "未公布", "Waller"].every(x => specialAudit.text.includes(x))) failures.push(`${v.name}: CPI special focus missing key data/analysis`);
    const focusAudit = await reportPage.evaluate((reportDate) => {
      const cases = [
        // Validate the approved tab semantics: 盤面觀察重點, the full
        // OHLC level set with source/date disclosure, and three weekly observation points.
        { id: "focus-tab-market", panel: ".focus-market", expectedLabel: "盤面觀察重點", needles: ["盤面觀察重點"], minLength: 80 },
        { id: "focus-tab-levels", panel: ".focus-levels", expectedLabel: "今日關鍵價位", needles: ["道瓊工業指數", "第二支撐", "第一支撐", "中樞", "第一壓力", "第二壓力", "S&P 500", "Nasdaq Composite", "費城半導體指數（SOX）", "Russell 2000", "價位計算方式與資料來源"], minLength: 200 },
        { id: "focus-tab-core", panel: ".focus-core", expectedLabel: "今日核心觀察", needles: ["本週三大觀察焦點"], minLength: 100 }
      ];
      const results = [], invalid = [];
      for (const item of cases) {
        const input = document.getElementById(item.id);
        const label = document.querySelector(`label[for="${item.id}"]`);
        const panel = document.querySelector("#view " + item.panel);
        if (!input || !label || !panel) { invalid.push(item.id + ": input/label/panel missing"); continue; }
        if (item.expectedLabel && label.textContent.trim() !== item.expectedLabel) invalid.push(item.id + ": tab label mismatch (expected " + item.expectedLabel + ", got " + label.textContent.trim() + ")");
        label.click();
        const rect = panel.getBoundingClientRect();
        const visible = getComputedStyle(panel).display !== "none" && rect.width > 0 && rect.height > 0;
        const text = panel.innerText || "";
        if (!input.checked) invalid.push(item.id + ": radio did not become checked after label click");
        if (!visible) invalid.push(item.id + ": target panel is not visible after tab click");
        for (const needle of item.needles) if (!text.includes(needle)) invalid.push(item.id + ": missing expected content " + needle);
        if (text.trim().length < (item.minLength || 0)) invalid.push(item.id + ": tab content is too short (" + text.trim().length + " chars)");
        if (item.id === "focus-tab-core" && !["①", "②", "③"].every(marker => text.includes(marker))) invalid.push(item.id + ": three weekly observation markers are incomplete");
        if (item.id === "focus-tab-levels") {
          const source = panel.querySelector("details.compact-disclosure, details.source-details")?.textContent || "";
      const sourceDateMatch = source.match(/基準交易日：(\d{4}-\d{2}-\d{2})/);
          if (!sourceDateMatch) invalid.push(item.id + ": missing OHLC source trading date");
          else if (!(sourceDateMatch[1] < reportDate)) invalid.push(item.id + ": OHLC trading date is not before report date");
          if (!source.includes("Yahoo Finance") && !source.includes("Investing.com")) invalid.push(item.id + ": missing OHLC source attribution");
        }
        results.push({ id: item.id, checked: input.checked, visible, text_length: text.length, needles: item.needles });
      }
      return { count: results.length, results, invalid };
    }, reportDate);
    const fedPanel = reportPage.locator(".fed-live-watch");
    const fedWatchText = await fedPanel.innerText().catch(() => "");
    const fedCards = await fedPanel.locator(".fc-prob").count().catch(() => 0);
    const fedStructure = await fedPanel.evaluate(node => ({
      cardCount: node.querySelectorAll(".fc-prob").length,
      segmentCount: node.querySelectorAll(".fc-split-bar > span").length,
      legendCount: node.querySelectorAll(".fc-split-legend > span").length,
      barHidden: node.querySelector(".fc-split-bar")?.hasAttribute("hidden") ?? true,
      labels: [...node.querySelectorAll(".fc-prob-label span:not(.fc-dot)")].map(x => x.textContent.trim()),
      values: [...node.querySelectorAll(".fc-prob strong")].map(x => x.textContent.trim())
    })).catch(() => null);
    if (!fedStructure || fedCards !== 2 || fedStructure.cardCount !== 2 || fedStructure.segmentCount !== 2 || fedStructure.legendCount !== 2) {
      failures.push(`${v.name}: FedWatch must preserve the mother template's 2-card / 2-segment / 2-legend structure`);
    } else if (fedStructure.labels.some(x => !x) || fedStructure.values.some(x => !x)) {
      failures.push(`${v.name}: FedWatch card labels or probability values are empty`);
    } else if (fedStructure.values.some(x => x.includes("待核實"))) {
      const fullPanelText = await reportPage.locator("#fed").innerText().catch(() => "");
      if (!fedStructure.barHidden || !fullPanelText.includes("完整分布")) failures.push(`${v.name}: unsupported FedWatch scenarios must fail closed and preserve full distribution in the snapshot disclosure`);
    } else {
      const pct = fedStructure.values.map(x => Number.parseFloat(x.replace("%", "")));
      if (fedStructure.barHidden || pct.some(x => !Number.isFinite(x)) || Math.abs(pct.reduce((a,b)=>a+b,0)-100) > 0.2) {
        failures.push(`${v.name}: FedWatch two-slot probabilities/bar are inconsistent`);
      }
    }
    // Regional observation cards live inside switchable global-market tabs.
    // Assert their actual DOM textContent (not rendered innerText/getByText visibility),
    // because inactive tabs are intentionally hidden until selected by the reader.
    for (const [panelId, requiredObservation] of [
      ["tac-global-panel-1", "📌 亞股觀察"],
      ["tac-global-panel-2", "📌 歐股觀察"]
    ]) {
      const observationText = await reportPage.locator(`#${panelId} .market-reason`).evaluate(
        node => node.textContent || ""
      ).catch(() => "");
      if (!observationText.includes(requiredObservation)) {
        failures.push(`${v.name}: ${panelId} missing observation heading in DOM: ${requiredObservation}`);
      }
      if (observationText.trim().length < requiredObservation.length + 10) {
        failures.push(`${v.name}: ${panelId} observation content is empty or incomplete`);
      }
    }
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
          if (grid) {
            const resultCards = [...grid.querySelectorAll(":scope > .earnings-actual-card")];
            const expectedLabels = {
              beat: "優於預期",
              miss: "低於預期",
              inline: "符合預期",
              pending: "尚未公布"
            };
            for (const [metricIndex, resultCard] of resultCards.entries()) {
              const status = resultCard.querySelector(".earnings-actual-status");
              // The approved Builder stores the canonical comparison state on
              // data-comparison-status and the visible badge element. Do not
              // require a duplicate state class on the outer card wrapper.
              const state = resultCard.dataset.comparisonStatus
                || Object.keys(expectedLabels).find(value => resultCard.classList.contains(value))
                || Object.keys(expectedLabels).find(value => status?.classList.contains(value));
              const declaredState = resultCard.dataset.comparisonStatus;
              if (declaredState && status && !status.classList.contains(declaredState)) {
                invalid.push("card " + (i+1) + ": comparison state attribute and visible badge class disagree at metric " + (metricIndex+1));
              }
              const expectedTitle = metricIndex === 0 ? "EPS" : "營收";
              const title = resultCard.querySelector(":scope > .earnings-actual-card-title")?.textContent.trim() || "";
              if (title !== expectedTitle) invalid.push("card " + (i+1) + ": expected one " + expectedTitle + " card, found " + title);
              const rows = [...resultCard.querySelectorAll(":scope > .earnings-actual-line")];
              const actualValue = rows.find(row => row.querySelector(":scope > span")?.textContent.trim() === "實際")?.querySelector(":scope > strong")?.textContent.trim() || "";
              const estimateValue = rows.find(row => row.querySelector(":scope > span")?.textContent.trim() === "預期")?.querySelector(":scope > strong")?.textContent.trim() || "";
              const detailText = details?.textContent || "";
              const comparisonBlocked = /not comparable|不判 beat\/miss|未證明.{0,20}同口徑|幣別不同|貨幣不同|單位不同/i.test(detailText);
              const expectedStatusLabels = state === "pending"
                ? (detailText.includes("公告已發布")
                    ? ["公告已發布；實際值待核實"]
                    : comparisonBlocked
                      ? ["比較資料尚未齊備"]
                      : (actualValue && actualValue !== "未取得" && estimateValue === "未取得"
                          ? ["比較資料尚未齊備"]
                          : ["尚未公布"]))
                : [expectedLabels[state]];
              if (!state || !status || !status.classList.contains(state) || !expectedStatusLabels.includes(status.textContent.trim())) {
                invalid.push("card " + (i+1) + ": EPS/revenue comparison badge state and label mismatch at metric " + (metricIndex+1));
              }
              const rowLabels = rows.map(row => row.querySelector(":scope > span")?.textContent.trim() || "");
              if (JSON.stringify(rowLabels) !== JSON.stringify(["實際", "預期"])) {
                invalid.push("card " + (i+1) + ": " + expectedTitle + " must show exactly one 實際 and one 預期 row");
              }
              for (const row of rows) {
                const value = row.querySelector(":scope > strong");
                if (!value || !value.textContent.trim()) invalid.push("card " + (i+1) + ": " + expectedTitle + " value missing");
                else {
                  const vr = value.getBoundingClientRect(), cr = resultCard.getBoundingClientRect();
                  if (value.scrollWidth > value.clientWidth + 1 || vr.left < cr.left - 1 || vr.right > cr.right + 1) {
                    invalid.push("card " + (i+1) + ": " + expectedTitle + " " + row.querySelector(":scope > span")?.textContent.trim() + " value clipped/overflowing");
                  }
                }
              }
            }
          }
          const labels = [...(details?.querySelectorAll(":scope > .earnings-detail-field label") || [])].map(node => node.textContent.trim());
          const expectedDetailLabels = mondayRetrospective
            ? ["財報判讀", "股價當日表現", "來源"]
            : ["公布時段", "EPS 預估／實際", "營收預估／實際", "財報判讀與股價反應", "資料來源"];
          if (JSON.stringify(labels) !== JSON.stringify(expectedDetailLabels)) {
            invalid.push("card " + (i+1) + ": published detail labels differ from the selected approved mother template");
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
            media_max_640_matches: matchMedia("(max-width: 640px)").matches,
            computed_grid_template_columns: getComputedStyle(grid).gridTemplateColumns,
            mobile_override_present: !!document.querySelector("#tac-published-earnings-mobile-v1"),
            grid_client_width: grid.clientWidth,
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
        else {
          const expectedColumns = 2; // TAC published EPS/revenue comparison remains side-by-side on mobile and desktop.
          if (columns !== expectedColumns) invalid.push("visible EPS/revenue cards layout mismatch: expected " + expectedColumns + " column(s), found " + columns);
        }
      }
      return {
        mode, count: cards.length, invalid, columns, pairedGeometry,
        viewport_inner_width: innerWidth,
        diagnostic_sample: measured[0] ? {
          media_max_640_matches: measured[0].media_max_640_matches,
          computed_grid_template_columns: measured[0].computed_grid_template_columns,
          mobile_override_present: measured[0].mobile_override_present,
          grid_client_width: measured[0].grid_client_width
        } : null,
        visible_result_grids: measured.length
      };
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
    // Compare the actual economic-card component against the selected approved mother,
    // not only the outer calendar section. Reveal hidden tabs/disclosures in QA after the
    // initial screenshots; this changes browser state only, never the source HTML.
    const revealEconomicCards = async page => {
      await page.evaluate(() => {
        document.querySelectorAll("#last-week-calendar details.last-week-calendar-collapse").forEach(node => { node.open = true; });
        document.querySelectorAll("#calendar .calendar-status-group, #last-week-calendar .calendar-status-group").forEach(node => {
          node.hidden = false;
          node.style.display = "block";
        });
        document.querySelectorAll("#calendar details.econ-event, #last-week-calendar details.econ-event").forEach(node => { node.open = true; });
      });
      await page.waitForTimeout(60);
    };
    await revealEconomicCards(masterPage);
    await revealEconomicCards(reportPage);
    const readEconomicCardStyle = async page => page.evaluate(() => {
      const card = document.querySelector("#calendar details.econ-event, #last-week-calendar details.econ-event");
      if (!card) return { exists: false };
      // Compare only the shared outer shell against the immutable formal mother.
      // The five-zone economic detail layout is a separately approved simulation
      // contract and is validated below for DOM order, labels, source and geometry.
      // Text-dependent meta widths and the detail grid must not be compared to
      // the older four-zone formal mother baseline.
      const selectors = {
        card: ":scope",
        summary: ":scope > summary",
        toggle: ":scope > summary .econ-toggle, :scope > summary .econ-event-toggle"
      };
      // Border color is intentionally status-coded (published/upcoming); row
      // tracks and heights are content-dependent. Compare invariant shell/layout
      // properties while the five-zone DOM and geometry are validated separately.
      const properties = ["display","fontFamily","fontSize","fontWeight","lineHeight","color","backgroundColor","borderTopWidth","borderTopStyle","borderRadius","paddingTop","paddingRight","paddingBottom","paddingLeft","marginTop","gap","gridTemplateColumns","gridArea","width","minHeight"];
      const result = {};
      for (const [key, selector] of Object.entries(selectors)) {
        const node = key === "card" ? card : card.querySelector(selector);
        if (!node) { result[key] = null; continue; }
        const css = getComputedStyle(node), rect = node.getBoundingClientRect();
        result[key] = Object.fromEntries(properties.map(prop => [prop, css[prop]]));
        result[key].rect = { x:Math.round(rect.x), y:Math.round(rect.y), width:Math.round(rect.width), height:Math.round(rect.height) };
      }
      return { exists: true, parts: result };
    });
    const masterEconomicStyle = await readEconomicCardStyle(masterPage);
    const reportEconomicStyle = await readEconomicCardStyle(reportPage);
    const economicStyleDifferences = [];
    if (!masterEconomicStyle.exists || !reportEconomicStyle.exists) {
      economicStyleDifferences.push("approved mother or review has no measurable economic card");
    } else {
      for (const [part, masterPart] of Object.entries(masterEconomicStyle.parts)) {
        const reportPart = reportEconomicStyle.parts[part];
        if (!masterPart || !reportPart) {
          if (!!masterPart !== !!reportPart) economicStyleDifferences.push(part + ": element presence differs from approved mother");
          continue;
        }
        for (const [property, expected] of Object.entries(masterPart)) {
          if (property === "rect") {
            for (const dimension of ["width"]) {
              if (Math.abs(expected[dimension] - reportPart.rect[dimension]) > 3) {
                economicStyleDifferences.push(part + " " + dimension + " differs: mother=" + expected[dimension] + ", review=" + reportPart.rect[dimension]);
              }
            }
          } else if (expected !== reportPart[property]) {
            economicStyleDifferences.push(part + " " + property + " differs: mother=" + expected + ", review=" + reportPart[property]);
          }
        }
      }
    }
    snapshots[v.name].economic_card_mother_parity = {
      master: masterEconomicStyle, report: reportEconomicStyle, differences: economicStyleDifferences
    };
    const economicCardSelector = "#calendar details.econ-event, #last-week-calendar details.econ-event";
    if (await masterPage.locator(economicCardSelector).count()) {
      await masterPage.locator(economicCardSelector).first().screenshot({
        path: path.join(output, `${v.name}-economic-card-master.png`)
      });
    }
    if (await reportPage.locator(economicCardSelector).count()) {
      await reportPage.locator(economicCardSelector).first().screenshot({
        path: path.join(output, `${v.name}-economic-card-report.png`)
      });
    }
    if (economicStyleDifferences.length) {
      failures.push(v.name + ": 經濟卡片與核准母版樣式不一致：" + economicStyleDifferences.join("; "));
    }

    // Economic cards must be measured while their details and calendar status groups
    // are actually rendered. The three radio tabs otherwise leave two-thirds of the
    // cards display:none, and closed <details> produce zero-sized child geometry.
    // This QA-only reveal happens after the initial-state screenshots and never edits source HTML.
    await reportPage.evaluate(() => {
      // Monday retrospective cards sit inside a separate outer disclosure.
      // Open it only after the initial-state screenshot so its descendants can be measured.
      document.querySelectorAll("#last-week-calendar details.last-week-calendar-collapse").forEach(node => {
        node.open = true;
      });
      document.querySelectorAll("#calendar .calendar-status-group, #last-week-calendar .calendar-status-group").forEach(node => {
        node.hidden = false;
        node.style.display = "block";
      });
      document.querySelectorAll("#calendar details.econ-event, #last-week-calendar details.econ-event").forEach(node => {
        node.open = true;
      });
    });
    await reportPage.waitForTimeout(80);
    const economicAudit = await reportPage.evaluate(() => {
      const cards = [...document.querySelectorAll("#calendar details.econ-event, #last-week-calendar details.econ-event")];
      const invalid = [];
      const geometrySamples = [];
      const expectedComparisons = [
        ["econ-prev", "前值"],
        ["econ-forecast", "市場預估"],
        ["econ-actual", "實際"]
      ];
      for (const [i, card] of cards.entries()) {
        const details = card.querySelector(":scope > .econ-details");
        if (!details) { invalid.push("card " + (i+1) + ": .econ-details missing"); continue; }
        const primary = details.querySelector(":scope > .econ-primary-grid");
        if (!primary) { invalid.push("card " + (i+1) + ": direct .econ-primary-grid missing"); continue; }
        const comparisonFields = [...primary.children].filter(node => node.classList.contains("econ-field"));
        if (comparisonFields.length !== 3) {
          invalid.push("card " + (i+1) + ": primary grid must contain exactly 3 comparison fields");
          continue;
        }
        for (const [j, [requiredClass, requiredLabel]] of expectedComparisons.entries()) {
          const field = comparisonFields[j];
          const label = field.querySelector(":scope > label")?.textContent.trim() || "";
          if (!field.classList.contains(requiredClass) || label !== requiredLabel) {
            invalid.push("card " + (i+1) + ": comparison field " + (j+1) + " class/label mismatch");
          }
          if (!field.querySelector(":scope > .econ-value")) invalid.push("card " + (i+1) + ": " + requiredLabel + " value missing");
        }
        const wideFields = [...details.children].filter(node =>
          node.classList.contains("econ-field") && node.classList.contains("wide")
        );
        if (wideFields.length !== 2) {
          invalid.push("card " + (i+1) + ": expected two full-width sibling fields after primary grid");
          continue;
        }
        const impactField = wideFields[0], sourceField = wideFields[1];
        const impactLabel = impactField.querySelector(":scope > label")?.textContent.trim() || "";
        const sourceLabel = sourceField.querySelector(":scope > label")?.textContent.trim() || "";
        if (!impactField.classList.contains("econ-impact") || impactLabel !== "市場影響") {
          invalid.push("card " + (i+1) + ": market impact field class/label/order mismatch");
        }
        if (!sourceField.classList.contains("econ-source") || sourceLabel !== "資料來源") {
          invalid.push("card " + (i+1) + ": source field class/label/order mismatch");
        }
        const impactText = impactField.querySelector(":scope > .econ-value")?.textContent.trim() || "";
        if (!impactText || ["待核實", "不適用／待核實"].includes(impactText) ||
            /依當次事件公布結果|待填|待補判讀/.test(impactText)) {
          invalid.push("card " + (i+1) + ": market impact judgment missing or still a template placeholder");
        }
        const source = sourceField.querySelector(":scope > .econ-value");
        if (!source?.querySelector("a[href^='https://']")) invalid.push("card " + (i+1) + ": HTTPS source link missing");

        // Verify actual rendered geometry at every viewport: left-side prev/forecast
        // stack, right-side actual spanning both rows, then two full-width siblings.
        const rect = node => {
          const r = node.getBoundingClientRect();
          return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height };
        };
        const p = rect(comparisonFields[0]), f = rect(comparisonFields[1]), a = rect(comparisonFields[2]);
        const impact = rect(impactField), sourceBox = rect(sourceField);
        const eps = 2;
        if (!(p.width > 0 && f.width > 0 && a.width > 0)) invalid.push("card " + (i+1) + ": comparison grid has zero-sized field");
        if (!(Math.abs(p.left - f.left) <= eps && f.top > p.top + eps)) {
          invalid.push("card " + (i+1) + ": prev/forecast are not vertically stacked in left column");
        }
        if (!(a.left > p.left + eps && a.top <= p.top + eps && a.bottom >= f.bottom - eps)) {
          invalid.push("card " + (i+1) + ": actual field does not occupy right column across both rows");
        }
        const primaryRect = rect(primary);
        if (!(Math.abs(impact.left - primaryRect.left) <= 3 &&
              Math.abs(sourceBox.left - primaryRect.left) <= 3 &&
              Math.abs(impact.width - primaryRect.width) <= 6 &&
              Math.abs(sourceBox.width - primaryRect.width) <= 6 &&
              impact.top >= Math.max(p.bottom, f.bottom, a.bottom) - eps &&
              sourceBox.top >= impact.bottom - eps)) {
          invalid.push("card " + (i+1) + ": impact/source fields are not consecutive full-width rows");
        }
        if (i === 0) geometrySamples.push({ prev:p, forecast:f, actual:a, impact, source:sourceBox });
      }
      return { count: cards.length, invalid, geometry_samples: geometrySamples };
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
  master_blob_sha: gitBlobSha, template: templateKey, viewports, failures, snapshots, font_audits: fontAudits
}, null, 2));
console.log(`視覺基準比對：${failures.length ? "FAIL" : "PASS"}；視窗：${viewports.map(v => v.width).join(" / ")}；母版 SHA：${gitBlobSha}`);
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
