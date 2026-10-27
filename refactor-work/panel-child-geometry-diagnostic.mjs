import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const candidate = path.join(here, "candidate-build.html");
const baseline = path.join(here, "source-baseline-2026-10-26.html");
const out = path.join(here, "browser-results", "panel-child-geometry-diagnostic.json");
fs.mkdirSync(path.dirname(out), { recursive: true });

const targets = ["overview", "sentiment", "news-scan", "global-markets", "industry-bonds-fx-commodities", "last-week-calendar", "last-week-earnings", "calendar", "earnings", "sp500-earnings-health", "fed", "view"];
const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow-mobile", width: 320, height: 800 }
];
const browser = await chromium.launch({ headless: true });
const results = [];

try {
  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1
    });
    const pages = [await context.newPage(), await context.newPage()];
    await Promise.all([
      pages[0].goto("file://" + baseline, { waitUntil: "domcontentloaded" }),
      pages[1].goto("file://" + candidate, { waitUntil: "domcontentloaded" })
    ]);
    await Promise.all(pages.map(page => page.waitForTimeout(400)));

    const inspect = page => page.evaluate(ids => ids.map(id => {
      const panel = document.getElementById(id);
      if (!panel) return { id, missing: true };
      const panelRect = panel.getBoundingClientRect();
      const rect = element => {
        const r = element.getBoundingClientRect();
        return {
          top: Math.round(r.top),
          relativeTop: Math.round(r.top - panelRect.top),
          left: Math.round(r.left),
          width: Math.round(r.width),
          height: Math.round(r.height),
          bottom: Math.round(r.bottom)
        };
      };
      const style = element => {
        const s = getComputedStyle(element);
        return {
          display: s.display,
          position: s.position,
          boxSizing: s.boxSizing,
          padding: s.padding,
          margin: s.margin,
          gap: s.gap,
          fontSize: s.fontSize,
          lineHeight: s.lineHeight
        };
      };
      let previousBottom = panelRect.top;
      const children = [...panel.children]
        .filter(element => getComputedStyle(element).display !== "none")
        .map((element, index) => {
          const elementRect = rect(element);
          const gapBefore = Math.round(element.getBoundingClientRect().top - previousBottom);
          previousBottom = element.getBoundingClientRect().bottom;
          return {
            index,
            tag: element.tagName,
            id: element.id || "",
            className: typeof element.className === "string" ? element.className : "",
            text: (element.innerText || "").trim().replace(/\s+/g, " ").slice(0, 70),
            rect: { ...elementRect, gapBefore },
            style: style(element)
          };
        });
      const deepGeometry = ["global-markets", "industry-bonds-fx-commodities", "news-scan"].includes(id)
        ? [...panel.querySelectorAll(".tac-tab-nav, .tac-tab-panel, .tac-tab-panel .row, .tac-tab-panel .row > b, .tac-tab-panel .row > span, .tac-tab-panel .row > .r, .tac-section-heading, .tac-section-heading h2")]
          .filter(element => {
            const r = element.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && !element.closest(".tac-tab-panel .tac-tab-panel");
          }).slice(0, 180).map(element => ({
            tag: element.tagName,
            id: element.id || "",
            className: typeof element.className === "string" ? element.className : "",
            text: (element.innerText || element.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 90),
            rect: rect(element),
            style: style(element)
          })) : [];
      const newsCards = id === "news-scan" ? [...panel.querySelectorAll(".newsitem, .tac-ds-card--news, .news-card, article")]
        .filter(element => getComputedStyle(element).display !== "none")
        .map((element, index) => {
          const r = rect(element);
          const descendants = [...element.querySelectorAll("*")].filter(child => {
            const cr = child.getBoundingClientRect();
            return cr.width > 0 && cr.height > 0 && (child.children.length === 0 || /title|headline|summary|source|meta|time|news/i.test(String(child.className || "") + " " + child.tagName));
          }).slice(0, 30).map(child => ({
            tag: child.tagName,
            className: typeof child.className === "string" ? child.className : "",
            text: (child.innerText || child.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 100),
            rect: rect(child),
            style: style(child)
          }));
          return { index, tag: element.tagName, id: element.id || "", className: typeof element.className === "string" ? element.className : "", text: (element.innerText || "").trim().replace(/\\s+/g, " ").slice(0, 160), rect: r, style: style(element), descendants };
        }) : [];
      const overviewNested = id === "overview" ? [...panel.querySelectorAll(":scope > .grid.two > *, :scope > .grid.two > * *")]
        .filter(element => {
          const r = element.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && !element.closest("#sentiment, #news-scan, #global-markets, #industry-bonds-fx-commodities, #last-week-calendar, #last-week-earnings, #calendar, #earnings, #sp500-earnings-health, #fed, #view");
        }).slice(0, 100).map(element => ({
          tag: element.tagName,
          id: element.id || "",
          className: typeof element.className === "string" ? element.className : "",
          text: (element.innerText || element.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 110),
          rect: rect(element),
          style: style(element)
        })) : [];
      const summaryCard = id === "overview" ? (() => {
        const card = panel.querySelector("article.card.bluf");
        if (!card) return { missing: true };
        const title = card.querySelector(":scope > .title");
        const headline = card.querySelector(":scope > h1");
        const body = card.querySelector(":scope > p");
        const details = element => element ? {
          tag: element.tagName,
          className: typeof element.className === "string" ? element.className : "",
          text: (element.innerText || element.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 180),
          rect: rect(element),
          style: { ...style(element), fontWeight: getComputedStyle(element).fontWeight, letterSpacing: getComputedStyle(element).letterSpacing, border: getComputedStyle(element).border, boxShadow: getComputedStyle(element).boxShadow }
        } : null;
        return { card: details(card), title: details(title), headline: details(headline), body: details(body) };
      })() : null;
      return { id, panelRect: rect(panel), panelStyle: style(panel), children, deepGeometry, newsCards, overviewNested, summaryCard };
    }), targets);

    const [b, c] = await Promise.all(pages.map(inspect));
    results.push({
      viewport: viewport.name,
      width: viewport.width,
      panels: targets.map(id => ({
        id,
        baseline: b.find(item => item.id === id),
        candidate: c.find(item => item.id === id)
      }))
    });
    await context.close();
  }
} finally {
  await browser.close();
}

fs.writeFileSync(out, JSON.stringify({ generatedAt: new Date().toISOString(), results }, null, 2));
let changed = 0;
for (const viewport of results) {
  for (const panel of viewport.panels) {
    const baselinePanel = panel.baseline;
    const candidatePanel = panel.candidate;
    const baseHeight = baselinePanel?.panelRect?.height;
    const candidateHeight = candidatePanel?.panelRect?.height;
    console.log(`[${viewport.width}px] #${panel.id}: panel ${baseHeight}px -> ${candidateHeight}px (Δ ${candidateHeight - baseHeight}px)`);
    if (["news-scan", "global-markets", "industry-bonds-fx-commodities"].includes(panel.id)) {
      for (const selector of [".tac-section-heading", ".tac-section-heading h2", ".tac-tab-nav", ".tac-tab-panel"]) {
        const pick = item => (item?.deepGeometry || []).filter(el => selector === ".tac-tab-panel" ? el.className.includes("tac-tab-panel") : selector === ".tac-tab-nav" ? el.className.includes("tac-tab-nav") : selector === ".tac-section-heading h2" ? el.tag === "H2" && el.className.includes("tac-section-title") : el.className.includes("tac-section-heading")).map(el => ({text: el.text.slice(0,35), top:el.rect.relativeTop, height:el.rect.height, padding:el.style.padding, margin:el.style.margin, lineHeight:el.style.lineHeight}));
        const before = pick(baselinePanel), after = pick(candidatePanel);
        if (before.length || after.length) console.log(`  DETAIL ${selector}: baseline=${JSON.stringify(before)} candidate=${JSON.stringify(after)}`);
      }
    }
    const baseDeep = baselinePanel?.deepGeometry || [];
    const candidateDeep = candidatePanel?.deepGeometry || [];
    const deepKey = item => [item.tag, item.id, item.className, item.text].join("|");
    const baseByKey = new Map(baseDeep.map(item => [deepKey(item), item]));
    const candidateByKey = new Map(candidateDeep.map(item => [deepKey(item), item]));
    let deepChanged = 0;
    for (const [key, before] of baseByKey) {
      const after = candidateByKey.get(key);
      if (!after) continue;
      const dh = after.rect.height - before.rect.height;
      const dt = after.rect.relativeTop - before.rect.relativeTop;
      if (Math.abs(dh) >= 1 || Math.abs(dt) >= 2 || before.style.padding !== after.style.padding || before.style.margin !== after.style.margin || before.style.gap !== after.style.gap || before.style.lineHeight !== after.style.lineHeight) {
        if (deepChanged < 60) console.log(`  nested ${before.tag}.${before.className} "${before.text.slice(0,42)}": top ${before.rect.relativeTop}->${after.rect.relativeTop} (Δ${dt}), h ${before.rect.height}->${after.rect.height} (Δ${dh}); padding ${before.style.padding}->${after.style.padding}; margin ${before.style.margin}->${after.style.margin}; line-height ${before.style.lineHeight}->${after.style.lineHeight}`);
        deepChanged++;
      }
    }
    if (deepChanged) console.log(`  nested geometry changed elements: ${deepChanged}`);
    if (panel.id === "news-scan") {
      const beforeCards = baselinePanel?.newsCards || [];
      const afterCards = candidatePanel?.newsCards || [];
      for (let i = 0; i < Math.min(beforeCards.length, afterCards.length); i++) {
        const before = beforeCards[i], after = afterCards[i];
        const dh = after.rect.height - before.rect.height;
        const dt = after.rect.relativeTop - before.rect.relativeTop;
        if (Math.abs(dh) >= 1 || Math.abs(dt) >= 1 || before.style.padding !== after.style.padding || before.style.margin !== after.style.margin) {
          console.log(`  NEWS CARD[${i}] ${before.className || before.tag}: top ${before.rect.relativeTop}->${after.rect.relativeTop} (Δ${dt}), h ${before.rect.height}->${after.rect.height} (Δ${dh}), padding ${before.style.padding}->${after.style.padding}, margin ${before.style.margin}->${after.style.margin}`);
          for (let j = 0; j < Math.min(before.descendants.length, after.descendants.length); j++) {
            const x = before.descendants[j], y = after.descendants[j];
            const childDh = y.rect.height - x.rect.height, childDt = y.rect.relativeTop - x.rect.relativeTop;
            if (Math.abs(childDh) >= 1 || Math.abs(childDt) >= 1 || x.style.lineHeight !== y.style.lineHeight || x.style.margin !== y.style.margin) {
              console.log(`    NEWS CHILD ${x.tag}.${x.className}: top ${x.rect.relativeTop}->${y.rect.relativeTop} (Δ${childDt}), h ${x.rect.height}->${y.rect.height} (Δ${childDh}), line-height ${x.style.lineHeight}->${y.style.lineHeight}, margin ${x.style.margin}->${y.style.margin}`);
            }
          }
        }
      }
    }
    const baseChildren = baselinePanel?.children || [];
    const candidateChildren = candidatePanel?.children || [];
    if (baseChildren.length !== candidateChildren.length) {
      console.log(`  CHILD COUNT baseline=${baseChildren.length}, candidate=${candidateChildren.length}`);
    }
    for (let i = 0; i < Math.max(baseChildren.length, candidateChildren.length); i++) {
      const before = baseChildren[i];
      const after = candidateChildren[i];
      if (!before || !after) {
        console.log(`  child[${i}] missing in ${before ? "candidate" : "baseline"}`);
        changed++;
        continue;
      }
      const deltas = {
        relativeTop: after.rect.relativeTop - before.rect.relativeTop,
        gapBefore: after.rect.gapBefore - before.rect.gapBefore,
        height: after.rect.height - before.rect.height,
        width: after.rect.width - before.rect.width
      };
      if (before.id !== after.id || before.className !== after.className ||
          Math.abs(deltas.gapBefore) > 1 || Math.abs(deltas.height) > 1 || Math.abs(deltas.width) > 1) {
        console.log(`  child[${i}] ${before.tag}#${before.id}.${before.className}`);
        console.log(`    relativeTop ${before.rect.relativeTop} -> ${after.rect.relativeTop} (Δ ${deltas.relativeTop}); gapBefore ${before.rect.gapBefore} -> ${after.rect.gapBefore} (Δ ${deltas.gapBefore}); height ${before.rect.height} -> ${after.rect.height} (Δ ${deltas.height}); width ${before.rect.width} -> ${after.rect.width} (Δ ${deltas.width})`);
        if (before.text !== after.text) console.log(`    text changed: "${before.text}" -> "${after.text}"`);
        changed++;
      }
    }
  }
}
console.log(`Saved panel-relative geometry report: ${out}; changed child comparisons: ${changed}`);
