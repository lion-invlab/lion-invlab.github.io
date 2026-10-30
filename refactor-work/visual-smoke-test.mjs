import { chromium } from "playwright";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const candidate = path.join(here, "candidate-build.html");
const baseline = path.join(here, "source-baseline-2026-10-26.html");
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
  { input: "#week-econ-today", label: 'label[for="week-econ-today"]', panel: "#calendar .week-econ-panels > .calendar-status-group:nth-child(1)" },
  { input: "#week-econ-upcoming", label: 'label[for="week-econ-upcoming"]', panel: "#calendar .week-econ-panels > .calendar-status-group:nth-child(2)" },
  { input: "#week-econ-published", label: 'label[for="week-econ-published"]', panel: "#calendar .week-econ-panels > .calendar-status-group:nth-child(3)" },
  { input: "#week-earnings-today", label: 'label[for="week-earnings-today"]', panel: "#earnings .week-earnings-panels > .calendar-status-group:nth-child(1)" },
  { input: "#week-earnings-upcoming", label: 'label[for="week-earnings-upcoming"]', panel: "#earnings .week-earnings-panels > .calendar-status-group:nth-child(2)" },
  { input: "#week-earnings-published", label: 'label[for="week-earnings-published"]', panel: "#earnings .week-earnings-panels > .calendar-status-group:nth-child(3)" },
  { input: "#fed-live-tab-fomc", label: 'label[for="fed-live-tab-fomc"]', panel: ".fed-live-fomc" },
  { input: "#focus-tab-core", label: 'label[for="focus-tab-core"]', panel: ".focus-core" }
];

async function dismissNotice(page) {
  const closeButton = page.locator("#tfn-close");
  if (await closeButton.count()) await closeButton.click({ force: true }).catch(() => {});
  await page.waitForTimeout(150);
}
async function loadPage(browser, file, viewport) {
  const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
  const pageErrors = [];
  page.on("pageerror", e => pageErrors.push(String(e)));
  page.on("console", msg => { if (msg.type() === "error") pageErrors.push("console: " + msg.text()); });
  await page.goto("file://" + file, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(650);
  await dismissNotice(page);
  // Validate the transient comic-bubble onboarding before cleaning screenshots.
  await page.evaluate(() => {
    const bubble = document.querySelector("#tac-toolbar-coach-bubble");
    const target = document.querySelector(".tac-toolbar-coach-target");
    const mobile = window.innerWidth < 1100;
    const style = bubble ? getComputedStyle(bubble) : null;
    document.documentElement.dataset.tacCoachPresentBeforeCleanup = String(!!bubble);
    document.documentElement.dataset.tacCoachMobileExpected = String(mobile);
    document.documentElement.dataset.tacCoachTextContract = String(!!bubble && /工具欄/.test(bubble.textContent));
    document.documentElement.dataset.tacCoachPointerEventsNone = String(!!style && style.pointerEvents === "none");
    document.documentElement.dataset.tacCoachTargetPulse = String(!!target && getComputedStyle(target).animationName.includes("tac-toolbar-coach-pulse"));
    document.documentElement.dataset.tacCoachInitialVisibility = style ? style.display : "missing";
    const bubbleRect = bubble ? bubble.getBoundingClientRect() : null;
    const text = bubble ? bubble.querySelector(".tac-toolbar-coach-bubble__text") : null;
    const textRect = text ? text.getBoundingClientRect() : null;
    document.documentElement.dataset.tacCoachBubbleInViewport = String(!!bubbleRect && bubbleRect.left >= -1 && bubbleRect.right <= window.innerWidth + 1);
    document.documentElement.dataset.tacCoachBubbleWraps = String(!!bubble && !!style && style.whiteSpace !== "nowrap" && bubble.scrollWidth <= bubble.clientWidth + 1 && bubble.clientHeight < 90);
    document.documentElement.dataset.tacCoachTextInsideBubble = String(!!bubbleRect && !!textRect && textRect.left >= bubbleRect.left - 1 && textRect.right <= bubbleRect.right + 1 && text.scrollWidth <= text.clientWidth + 1);
    document.documentElement.dataset.tacCoachBubbleWidth = String(bubbleRect ? Math.round(bubbleRect.width) : 0);
    document.documentElement.dataset.tacLegacyHintRemoved = String(!document.querySelector("#tac-tools-hint") && !document.querySelector(".tac-tools-hint") && !document.querySelector(".tac-tools-arrow-live"));
    document.querySelectorAll("#tac-toolbar-coach-bubble").forEach(el => el.remove());
    document.querySelectorAll(".tac-toolbar-coach-target").forEach(el => el.classList.remove("tac-toolbar-coach-target"));
    document.body.style.overflow = "";
  });
  await page.waitForTimeout(120);
  return { page, pageErrors };
}
async function inspect(page) {
  return page.evaluate(({ panelIds }) => {
    const ids = [...document.querySelectorAll("[id]")].map(el => el.id);
    const duplicateIds = ids.filter((id, i) => ids.indexOf(id) !== i);
    const navLinks = [...document.querySelectorAll("nav a[href^='#']")];
    const unmatchedNav = navLinks.filter(a => !document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1))))
      .map(a => ({ label: a.textContent.trim(), href: a.getAttribute("href") }));
    return {
      title: document.title,
      width: window.innerWidth,
      docWidth: document.documentElement.scrollWidth,
      pageHeight: document.documentElement.scrollHeight,
      panelGeometry: panelIds.map(id => {
        const el = document.getElementById(id);
        if (!el) return { id, missing: true };
        const r = el.getBoundingClientRect();
        return { id, top: Math.round(r.top + window.scrollY), height: Math.round(r.height), bottom: Math.round(r.bottom + window.scrollY), width: Math.round(r.width), padding: getComputedStyle(el).padding, margin: getComputedStyle(el).margin, gap: getComputedStyle(el).gap };
      }),
      tabbedPanelHeadingGeometry: [
        ["news-scan", "重點新聞掃瞄"],
        ["global-markets", "全球主要股市"],
        ["industry-bonds-fx-commodities", "產業債匯商品"]
      ].map(([id]) => {
        const panel = document.getElementById(id);
        const container = panel?.querySelector(":scope > .tac-section-heading");
        const el = container?.querySelector("h2");
        if (!el) return { id, missing: true };
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        const cr = container.getBoundingClientRect(), cs = getComputedStyle(container);
        const before = getComputedStyle(el, "::before");
        return {
          id, text: (el.textContent || "").trim(),
          height: Math.round(r.height), width: Math.round(r.width),
          containerHeight: Math.round(cr.height), containerWidth: Math.round(cr.width),
          fontSize: s.fontSize, fontWeight: s.fontWeight, lineHeight: s.lineHeight,
          color: s.color, backgroundColor: s.backgroundColor, padding: s.padding,
          margin: s.margin, display: s.display, alignItems: s.alignItems, gap: s.gap,
          borderLeftWidth: s.borderLeftWidth, borderLeftColor: s.borderLeftColor,
          letterSpacing: s.letterSpacing, textAlign: s.textAlign,
          beforeContent: before.content, beforeColor: before.color, beforeBackgroundColor: before.backgroundColor,
          beforeDisplay: before.display, beforeWidth: before.width, beforeHeight: before.height
        };
      }),
      specialHeadingGeometry: [
        ["bluf", "main.wrap > section.grid.two > article.bluf > .title"],
        ["sentiment", "#sentiment > .title"],
        ["last-week-calendar", "#last-week-calendar > article.calendar-card > .title"],
        ["last-week-earnings", "#last-week-earnings > article.calendar-card > .title"],
        ["calendar", "#calendar > article.calendar-card > .title"],
        ["earnings", "#earnings > article.calendar-card > .title"],
        ["sp500-earnings-health", "#sp500-earnings-health > .title"],
        ["fed", "#fed > .title"],
        ["view", "#view > .title"]
      ].map(([id, selector]) => {
        const el = document.querySelector(selector);
        if (!el) return { id, missing: true };
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        const before = getComputedStyle(el, "::before");
        return {
          id, text: (el.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 50),
          height: Math.round(r.height), width: Math.round(r.width),
          fontSize: s.fontSize, fontWeight: s.fontWeight, lineHeight: s.lineHeight,
          color: s.color, backgroundColor: s.backgroundColor, padding: s.padding,
          margin: s.margin, display: s.display, alignItems: s.alignItems, gap: s.gap,
          borderLeftWidth: s.borderLeftWidth, borderLeftColor: s.borderLeftColor,
          letterSpacing: s.letterSpacing, textAlign: s.textAlign,
          beforeContent: before.content, beforeColor: before.color, beforeBackgroundColor: before.backgroundColor, beforeDisplay: before.display,
          beforeWidth: before.width, beforeHeight: before.height
        };
      }),
      sp500DeepGeometry: (() => {
        const root = document.getElementById("sp500-earnings-health");
        if (!root) return { missing: true };
        return [...root.querySelectorAll("*")].filter(el => {
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        }).map((el, i) => {
          const r = el.getBoundingClientRect(), s = getComputedStyle(el);
          const text = (el.innerText || el.textContent || "").trim().replace(/\\s+/g, " ");
          return {
            i, tag: el.tagName, id: el.id, cls: String(el.className || "").slice(0, 100),
            top: Math.round(r.top + window.scrollY), height: Math.round(r.height), width: Math.round(r.width),
            padding: s.padding, margin: s.margin, gap: s.gap, fontSize: s.fontSize, lineHeight: s.lineHeight,
            clientHeight: el.clientHeight, scrollHeight: el.scrollHeight, textLength: text.length,
            textPreview: text.slice(0, 110)
          };
        }).slice(0, 160);
      })(),
      detailedGeometry: ["overview","sentiment","news-scan","global-markets","industry-bonds-fx-commodities","sp500-earnings-health","last-week-calendar","last-week-earnings","calendar","earnings","fed","view"].map(id => {
        const root = document.getElementById(id);
        if (!root) return { id, missing: true };
        return { id, nodes: [...root.querySelectorAll(":scope > *, .tac-ds-card--news, .newsitem, .news-card, .region-card, .asset-card, .econ-event, .earnings-accordion, details, .calendar-card, .tac-ds-event, .tac-ds-earnings-card, .tac-section-heading, .title, article.card.bluf, #overview h1, #overview p, #overview .chips, #overview .chip, #overview .bluf-subtitle, #overview .summary-subtitle, .news-list, .news-grid, .grid, .tac-ds-tabs, .row, .sector-row, .instrument-name, .sp500-health-row, .earnings-health-row, .week-econ-tabs, .week-econ-tab-labels, .week-econ-panels, .week-earnings-tabs, .week-earnings-tab-labels, .week-earnings-panels, .calendar-status-group, .calendar-status-heading, .calendar-status-empty, .econ-event-list, .earnings-accordion-list, .focus-tabs, .focus-tab-labels, .fed-live-tabs, .fed-live-tab-labels, #sentiment .sbox, #sentiment .fg6-score-row, #sentiment .fg6-scale-wrap, #sentiment details.source-details > summary")].slice(0,110).map((el,i) => {
          const r = el.getBoundingClientRect(), s = getComputedStyle(el);
          return {i, tag:el.tagName, cls:String(el.className||"").slice(0,100), id:el.id, top:Math.round(r.top+window.scrollY), height:Math.round(r.height), width:Math.round(r.width), padding:s.padding, margin:s.margin, gap:s.gap, fontSize:s.fontSize, lineHeight:s.lineHeight, display:s.display};
        })};
      }),
      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      duplicateIds: [...new Set(duplicateIds)],
      missingPanels: panelIds.filter(id => !document.getElementById(id)),
      navCount: navLinks.length,
      unmatchedNav,
      coachPresentBeforeCleanup: document.documentElement.dataset.tacCoachPresentBeforeCleanup === "true",
      coachMobileExpected: document.documentElement.dataset.tacCoachMobileExpected === "true",
      coachTextContract: document.documentElement.dataset.tacCoachTextContract === "true",
      coachPointerEventsNone: document.documentElement.dataset.tacCoachPointerEventsNone === "true",
      coachTargetPulse: document.documentElement.dataset.tacCoachTargetPulse === "true",
      coachInitialVisibility: document.documentElement.dataset.tacCoachInitialVisibility || "missing",
      coachBubbleInViewport: document.documentElement.dataset.tacCoachBubbleInViewport === "true",
      coachBubbleWraps: document.documentElement.dataset.tacCoachBubbleWraps === "true",
      coachTextInsideBubble: document.documentElement.dataset.tacCoachTextInsideBubble === "true",
      coachBubbleWidth: Number(document.documentElement.dataset.tacCoachBubbleWidth || 0),
      coachLegacyHintRemoved: document.documentElement.dataset.tacLegacyHintRemoved === "true",
      toolbarButtonInNav: !!document.querySelector(".nav .tac-side-open"),
      toolbarButtonPlacement: document.querySelector(".tac-side-open")?.getAttribute("data-tac-toolbar-placement") || "",
      toolbarButtonPosition: document.querySelector(".tac-side-open") ? getComputedStyle(document.querySelector(".tac-side-open")).position : "missing",
      temporaryPreviewFooterText: /修正測試版|提醒膠囊與彈窗保留原母版結構/.test(document.querySelector("footer.footer")?.textContent || ""),
      fearGreedScore: Number(document.querySelector("#sentiment .fg6-score-main")?.textContent || NaN),
      fearGreedMarkerPosition: Number(document.querySelector("#sentiment .fg6-marker")?.getAttribute("data-score-position") || NaN),
      earningsAccordionStyle: ["#earnings", "#last-week-earnings"].map(id => {
        const cards = [...document.querySelectorAll(id + " details.earnings-accordion")];
        const card = cards.find(el => el.getBoundingClientRect().height > 0) || cards[0];
        if (!card) return { id, missing: true };
        const summary = card.querySelector(":scope > summary");
        const toggle = summary?.querySelector(".earnings-accordion-toggle");
        const cs = getComputedStyle(card), ss = summary ? getComputedStyle(summary) : null;
        const ts = toggle ? getComputedStyle(toggle) : null;
        const ps = toggle ? getComputedStyle(toggle, "::before") : null;
        return {
          id,
          card: { height: Math.round(card.getBoundingClientRect().height), minWidth: cs.minWidth, margin: cs.margin, borderRadius: cs.borderRadius, borderColor: cs.borderColor, backgroundColor: cs.backgroundColor, boxShadow: cs.boxShadow, overflow: cs.overflow, transition: cs.transition },
          summary: ss ? { height: Math.round(summary.getBoundingClientRect().height), display: ss.display, flexDirection: ss.flexDirection, alignItems: ss.alignItems, justifyContent: ss.justifyContent, gap: ss.gap, padding: ss.padding, minHeight: ss.minHeight, borderRadius: ss.borderRadius, backgroundColor: ss.backgroundColor, listStyleType: ss.listStyleType, cursor: ss.cursor } : null,
          toggle: ts ? { width: ts.width, height: ts.height, minWidth: ts.minWidth, minHeight: ts.minHeight, padding: ts.padding, border: ts.border, borderRadius: ts.borderRadius, backgroundColor: ts.backgroundColor, color: ts.color, fontSize: ts.fontSize, lineHeight: ts.lineHeight, position: ts.position, opacity: ts.opacity, visibility: ts.visibility, beforeContent: ps?.content, beforeColor: ps?.color, beforeFontSize: ps?.fontSize, beforeBackground: ps?.backgroundColor } : { missing: true }
        };
      }),
      fiveStarRedCount: [...document.querySelectorAll(".earnings-accordion.star-verified-five .earnings-stars, .econ-event.star-verified-five .econ-stars")].filter(el => getComputedStyle(el).color === "rgb(198, 40, 40)").length,
      sourceTrianglesPresent: [...document.querySelectorAll("main.wrap details.source-details > summary")].filter(el => getComputedStyle(el, "::before").content.includes("▸")).length,
      doubleBarHeadings: [...document.querySelectorAll(".tac-tabset .tac-section-heading h2")].filter(el => getComputedStyle(el).borderLeftWidth !== "0px" && getComputedStyle(el, "::before").display !== "none").length,
      globalMarketNameFontSizes: [...new Set([...document.querySelectorAll("#global-markets .row b, #global-markets .instrument-name")].slice(0,20).map(el => getComputedStyle(el).fontSize))],
      industryRowTypography: ["#bonds","#fx",".energy-card","#tac-assets-panel-4"].map(selector => {
        const root = document.querySelector("#industry-bonds-fx-commodities " + selector);
        if (!root) return { selector, missing: true };
        const row = root.querySelector(".row");
        if (!row) return { selector, rowMissing: true };
        const name = row.querySelector("b, .name, .label");
        const values = [...row.querySelectorAll(".r")];
        const signature = el => {
          if (!el) return null;
          const s = getComputedStyle(el);
          return { tag:el.tagName, className:String(el.className||""), fontSize:s.fontSize, lineHeight:s.lineHeight, fontWeight:s.fontWeight, letterSpacing:s.letterSpacing, whiteSpace:s.whiteSpace, fontVariantNumeric:s.fontVariantNumeric };
        };
        return { selector, row:signature(row), name:signature(name), values:values.slice(0,2).map(signature) };
      }),

      letterSpacingRuleAudit: (() => {
        const legacySelector = "html body #industry-bonds-fx-commodities .tac-tab-panel .row b";
        const sharedSelector = "#global-markets .row > b, html body #industry-bonds-fx-commodities .tac-tab-panel .row > b";
        const rules = [];
        const visit = list => {
          for (const rule of list) {
            if (rule.selectorText && (rule.selectorText.includes("#global-markets .row > b") || rule.selectorText.includes("#industry-bonds-fx-commodities .tac-tab-panel .row > b"))) {
              rules.push({ selector:rule.selectorText, fontSize:rule.style.getPropertyValue("font-size"), lineHeight:rule.style.getPropertyValue("line-height"), fontWeight:rule.style.getPropertyValue("font-weight"), letterSpacing:rule.style.getPropertyValue("letter-spacing"), important:{fontSize:rule.style.getPropertyPriority("font-size")==="important",lineHeight:rule.style.getPropertyPriority("line-height")==="important",fontWeight:rule.style.getPropertyPriority("font-weight")==="important",letterSpacing:rule.style.getPropertyPriority("letter-spacing")==="important"} });
            }
            if (rule.cssRules) visit(rule.cssRules);
          }
        };
        for (const sheet of document.styleSheets) {
          try { visit(sheet.cssRules); } catch (_) {}
        }
        const styleSignature = el => {
          const s = getComputedStyle(el);
          const matchedLetterSpacingRules = [];
          const inspect = list => {
            for (const rule of list) {
              if (rule.selectorText && rule.style && rule.style.getPropertyValue("letter-spacing")) {
                try {
                  if (el.matches(rule.selectorText)) matchedLetterSpacingRules.push({selector:rule.selectorText,value:rule.style.getPropertyValue("letter-spacing"),important:rule.style.getPropertyPriority("letter-spacing")==="important"});
                } catch (_) {}
              }
              if (rule.cssRules) inspect(rule.cssRules);
            }
          };
          for (const sheet of document.styleSheets) { try { inspect(sheet.cssRules); } catch (_) {} }
          return {text:(el.textContent||"").trim().slice(0,40),fontSize:s.fontSize,lineHeight:s.lineHeight,fontWeight:s.fontWeight,letterSpacing:s.letterSpacing,matchedLetterSpacingRules};
        };
        return {
          matchingGlobalNames: document.querySelectorAll("#global-markets .row > b").length,
          matchingIndustryNames: document.querySelectorAll("#industry-bonds-fx-commodities .tac-tab-panel .row > b").length,
          computedGlobal: [...document.querySelectorAll("#global-markets .row > b")].slice(0,3).map(styleSignature),
          computedIndustry: [...document.querySelectorAll("#industry-bonds-fx-commodities .tac-tab-panel .row > b")].slice(0,5).map(styleSignature),
          rules
        };
      })(),
      industryInstrumentFontSizes: [...new Set([...document.querySelectorAll("#industry-bonds-fx-commodities #bonds .row b, #industry-bonds-fx-commodities .row .instrument-name")].map(el => getComputedStyle(el).fontSize))],
      tabNavGeometry: ["#news-scan", "#global-markets", "#industry-bonds-fx-commodities"].map(id => {
        const root = document.querySelector(id);
        const nav = root?.querySelector(".tac-tab-nav");
        if (!nav) return { id, missing: true };
        const nr = nav.getBoundingClientRect(), ns = getComputedStyle(nav);
        return {
          id,
          nav: { top: Math.round(nr.top + window.scrollY), height: Math.round(nr.height), width: Math.round(nr.width), display: ns.display, gridTemplateColumns: ns.gridTemplateColumns, gridAutoFlow: ns.gridAutoFlow, gap: ns.gap, padding: ns.padding, overflowX: ns.overflowX },
          labels: [...nav.querySelectorAll("label")].map(label => {
            const r = label.getBoundingClientRect(), s = getComputedStyle(label);
            return { text: label.textContent.trim(), top: Math.round(r.top + window.scrollY), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height), display: s.display, flex: s.flex, gridColumn: s.gridColumn, minHeight: s.minHeight, padding: s.padding, fontSize: s.fontSize, lineHeight: s.lineHeight, boxSizing: s.boxSizing, borderTopWidth: s.borderTopWidth, borderBottomWidth: s.borderBottomWidth, transform: s.transform, clientHeight: label.clientHeight, scrollHeight: label.scrollHeight, offsetHeight: label.offsetHeight, whiteSpace: s.whiteSpace };
          })
        };
      }),
      mainHeadingCascade: ["overview","sentiment","news-scan","global-markets","industry-bonds-fx-commodities","last-week-calendar","last-week-earnings","calendar","earnings","sp500-earnings-health","fed","view"].map(id => {
        const root = document.getElementById(id);
        const heading = root?.querySelector(".title, .tac-section-heading h2, [data-main-section-title]");
        if (!root || !heading) return { id, missing: true };
        const s = getComputedStyle(heading);
        const matchedRules = [];
        const walkRules = (rules, conditions = []) => {
          for (const rule of rules) {
            if (rule.cssRules && !rule.selectorText) {
              const condition = rule.conditionText || rule.name || "";
              let applies = true;
              if (rule.media && rule.media.mediaText) applies = window.matchMedia(rule.media.mediaText).matches;
              if (applies) walkRules(rule.cssRules, condition ? [...conditions, condition] : conditions);
              continue;
            }
            if (!rule.selectorText || !rule.style) continue;
            const selectors = rule.selectorText.split(",").map(x => x.trim());
            const matching = selectors.filter(selector => {
              if (!/(\.title|tac-section-heading h2|section-title|panel-title|card-title|data-main-section-title)/.test(selector)) return false;
              try { return heading.matches(selector); } catch { return false; }
            });
            if (!matching.length) continue;
            const declarations = {};
            for (const prop of ["color","font-size","line-height","font-weight"]) {
              const value = rule.style.getPropertyValue(prop);
              if (value) declarations[prop] = { value: value.trim(), important: rule.style.getPropertyPriority(prop) === "important" };
            }
            if (Object.keys(declarations).length) matchedRules.push({ selectors: matching, conditions, declarations });
          }
        };
        for (const sheet of [...document.styleSheets]) {
          try { walkRules(sheet.cssRules); } catch (error) { matchedRules.push({ inaccessible: String(error) }); }
        }
        return { id, tag: heading.tagName, className: String(heading.className || ""), color: s.color, fontSize: s.fontSize, lineHeight: s.lineHeight, fontWeight: s.fontWeight, matchedRules };
      }),
      mainTabStyleSignatures: ["#news-scan", "#global-markets", "#industry-bonds-fx-commodities"].map(id => {
        const el = document.querySelector(id + " .tac-tab-nav label");
        if (!el) return {id, missing:true};
        const s = getComputedStyle(el);
        return {id, fontSize:s.fontSize, minHeight:s.minHeight, padding:s.padding, borderRadius:s.borderRadius, whiteSpace:s.whiteSpace};
      }),
      styleTagCount: document.querySelectorAll("style").length,
      scriptCount: document.querySelectorAll("script").length,
      sharedTabLabelCount: document.querySelectorAll(".tac-ds-tabs__tab").length,
      auditDisclosureCount: document.querySelectorAll("main.wrap details.audit-details").length,
      sharedDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure").length,
      methodDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure--method").length,
      methodDisclosureInlineStyles: document.querySelectorAll("details.tac-ds-disclosure--method[style*=\"margin-top:8px\"]").length,
      regionSectorSourceTypography: [...document.querySelectorAll("details.region-source > summary, details.sector-source > summary")].map(el => { const s = getComputedStyle(el); return {fontSize:s.fontSize,fontWeight:s.fontWeight,color:s.color,padding:s.padding}; }),
      sourceDisclosureGeometry: [...document.querySelectorAll("main.wrap details.source-details")].map(el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        const summary = el.querySelector(":scope > summary");
        const sr = summary?.getBoundingClientRect();
        const ss = summary ? getComputedStyle(summary) : null;
        const before = summary ? getComputedStyle(summary, "::before") : null;
        const panel = el.closest("section[id]");
        return {
          panel: panel?.id || "outside-panel",
          className: el.className || "",
          text: (summary?.textContent || "").trim().slice(0, 40),
          visible: r.width > 0 && r.height > 0,
          height: Math.round(r.height),
          summaryHeight: sr ? Math.round(sr.height) : null,
          marginTop: s.marginTop,
          padding: s.padding,
          borderTopWidth: s.borderTopWidth,
          borderBottomWidth: s.borderBottomWidth,
          summaryFontSize: ss?.fontSize || null,
          summaryFontWeight: ss?.fontWeight || null,
          summaryColor: ss?.color || null,
          summaryLineHeight: ss?.lineHeight || null,
          summaryPadding: ss?.padding || null,
          summaryBeforeContent: before?.content || null,
          summaryBeforeDisplay: before?.display || null,
          summaryBeforeColor: before?.color || null
        };
      }),
      otherDisclosureGeometry: [...document.querySelectorAll("main.wrap details.calendar-source-collapse, main.wrap details.audit-details, main.wrap #last-week-calendar details.last-week-calendar-collapse, main.wrap #last-week-earnings details.last-week-earnings-collapse")].map(el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        const summary = el.querySelector(":scope > summary");
        const sr = summary?.getBoundingClientRect();
        const ss = summary ? getComputedStyle(summary) : null;
        const before = summary ? getComputedStyle(summary, "::before") : null;
        const panel = el.closest("section[id]");
        return {
          panel: panel?.id || "outside-panel",
          kind: el.className || "",
          text: (summary?.textContent || "").trim().slice(0, 45),
          visible: r.width > 0 && r.height > 0,
          height: Math.round(r.height),
          summaryHeight: sr ? Math.round(sr.height) : null,
          marginTop: s.marginTop,
          padding: s.padding,
          borderTopWidth: s.borderTopWidth,
          borderBottomWidth: s.borderBottomWidth,
          summaryFontSize: ss?.fontSize || null,
          summaryLineHeight: ss?.lineHeight || null,
          summaryPadding: ss?.padding || null,
          beforeContent: before?.content || null
        };
      }),
      darkDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure--dark").length,
      darkDisclosureStyleSignatures: [...document.querySelectorAll("#sentiment details.tac-ds-disclosure--dark")].map(el => { const s=getComputedStyle(el.querySelector(":scope > summary")); const a=getComputedStyle(el.querySelector(":scope > summary"),"::before"); const body=el.querySelector(":scope > .source"); return {summaryColor:s.color,markerColor:a.color,sourceColor:body?getComputedStyle(body).color:null}; }),
      sharedEmptyStateCount: document.querySelectorAll(".tac-ds-empty").length,
      sharedNewsCardCount: document.querySelectorAll(".tac-ds-card--news").length,
      sharedNewsCardBackgrounds: [...new Set([...document.querySelectorAll(".tac-ds-card--news")].map(el => getComputedStyle(el).backgroundColor))],
      sharedNewsCardRadii: [...new Set([...document.querySelectorAll(".tac-ds-card--news")].map(el => getComputedStyle(el).borderRadius))],
      sharedEventCardCount: document.querySelectorAll("details.tac-ds-event").length,
      sharedEventCardRadii: [...new Set([...document.querySelectorAll("details.tac-ds-event")].map(el => getComputedStyle(el).borderRadius))],
      sharedEarningsCardCount: document.querySelectorAll("details.tac-ds-earnings-card").length,
      sharedEarningsCardRadii: [...new Set([...document.querySelectorAll("details.tac-ds-earnings-card")].map(el => getComputedStyle(el).borderRadius))],
      sharedSectorRowCount: document.querySelectorAll(".tac-ds-data-row--sector").length,
      sharedSectorRowRadii: [...new Set([...document.querySelectorAll(".tac-ds-data-row--sector")].map(el => getComputedStyle(el).borderRadius))],
      sharedSectorRowBackgrounds: [...new Set([...document.querySelectorAll(".tac-ds-data-row--sector")].map(el => getComputedStyle(el).backgroundColor))],
      sharedActualEarningsCardCount: document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card").length,
      sharedActualEarningsCardRadii: [...new Set([...document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card")].map(el => getComputedStyle(el).borderRadius))],
      sharedActualEarningsCardBackgrounds: [...new Set([...document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card")].map(el => getComputedStyle(el).backgroundColor))],
      actualEarningsBeatCount: document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card.beat").length,
      actualEarningsMissCount: document.querySelectorAll("#last-week-earnings .tac-ds-earnings-actual-card.miss").length,
      sentimentThemeClassPresent: document.getElementById("sentiment")?.classList.contains("tac-ds-panel--sentiment") || false,
      sentimentBackgroundImage: getComputedStyle(document.getElementById("sentiment")).backgroundImage,
      sentimentBeforeContent: getComputedStyle(document.getElementById("sentiment"), "::before").content,
      sentimentBeforeBoxShadow: getComputedStyle(document.getElementById("sentiment"), "::before").boxShadow,
      sentimentAfterContent: getComputedStyle(document.getElementById("sentiment"), "::after").content,
      sentimentAfterBoxShadow: getComputedStyle(document.getElementById("sentiment"), "::after").boxShadow,
      sentimentBackgroundColor: getComputedStyle(document.getElementById("sentiment")).backgroundColor
    };
  }, { panelIds });
}

const browser = await chromium.launch({ headless: true });
const results = { candidate, baseline, viewports: [], errors: [], visualDiffs: [] };
try {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1000 },
    { name: "mobile", width: 390, height: 844 },
    { name: "narrow-mobile", width: 320, height: 800 }
  ]) {
    const base = await loadPage(browser, baseline, viewport);
    const cand = await loadPage(browser, candidate, viewport);
    const baseReport = await inspect(base.page);
    const report = await inspect(cand.page);

    const fullPageShot = viewport.name === "desktop";
    const baseShot = await base.page.screenshot({ path: path.join(outDir, "baseline-" + viewport.name + ".png"), fullPage: fullPageShot, animations: "disabled" });
    const candShot = await cand.page.screenshot({ path: path.join(outDir, "candidate-" + viewport.name + ".png"), fullPage: fullPageShot, animations: "disabled" });
    const basePng = PNG.sync.read(baseShot);
    const candPng = PNG.sync.read(candShot);
    let diffPixels = null;
    let diffRatio = null;
    let dimensionsMatch = basePng.width === candPng.width && basePng.height === candPng.height;
    if (dimensionsMatch) {
      const diff = new PNG({ width: basePng.width, height: basePng.height });
      diffPixels = pixelmatch(basePng.data, candPng.data, diff.data, basePng.width, basePng.height, { threshold: 0.1, includeAA: false });
      diffRatio = diffPixels / (basePng.width * basePng.height);
      fs.writeFileSync(path.join(outDir, "diff-" + viewport.name + ".png"), PNG.sync.write(diff));
    }
    // Keep the existing viewport-sized screenshots for comparable pixel-diff metrics.
    // Also capture full-page mobile views so reviewers can inspect below-the-fold panels
    // that are not visible in the first 844px/800px viewport.
    if (viewport.name !== "desktop") {
      await base.page.screenshot({ path: path.join(outDir, "baseline-" + viewport.name + "-full.png"), fullPage: true, animations: "disabled" });
      await cand.page.screenshot({ path: path.join(outDir, "candidate-" + viewport.name + "-full.png"), fullPage: true, animations: "disabled" });
    }
    results.visualDiffs.push({ viewport: viewport.name, dimensionsMatch, baselineSize: [basePng.width, basePng.height], candidateSize: [candPng.width, candPng.height], diffPixels, diffRatio });

    // Real navigation-anchor geometry: click every main nav link and measure the target heading against the sticky header/nav bottom.
    const navAnchorResults = [];
    const navLinksForAnchors = cand.page.locator("nav.nav a[href^='#']");
    for (let i = 0; i < await navLinksForAnchors.count(); i++) {
      const link = navLinksForAnchors.nth(i);
      const label = (await link.innerText()).trim();
      const href = await link.getAttribute("href");
      try {
        await link.click({ timeout: 5000 });
        await cand.page.waitForTimeout(420);
        const measurement = await cand.page.evaluate((targetHref) => {
          const id = decodeURIComponent((targetHref || "").slice(1));
          const target = document.getElementById(id);
          const heading = target?.matches(".title,h1,h2,h3") ? target : target?.querySelector(".title,h1,h2,h3");
          const sticky = document.querySelector("header.top, .top");
          const nav = document.querySelector("nav.nav");
          const stickyRect = sticky?.getBoundingClientRect();
          const navRect = nav?.getBoundingClientRect();
          const headingRect = heading?.getBoundingClientRect();
          const visibleBottom = Math.max(stickyRect?.bottom || 0, navRect?.bottom || 0);
          return {
            targetFound: !!target, headingFound: !!heading,
            headingTop: headingRect ? Math.round(headingRect.top) : null,
            headingBottom: headingRect ? Math.round(headingRect.bottom) : null,
            stickyBottom: Math.round(stickyRect?.bottom || 0),
            navBottom: Math.round(navRect?.bottom || 0),
            visibleHeaderBottom: Math.round(visibleBottom),
            clearance: headingRect ? Math.round(headingRect.top - visibleBottom) : null,
            headingVisible: !!headingRect && headingRect.bottom > visibleBottom && headingRect.top < innerHeight
          };
        }, href);
        navAnchorResults.push({ label, href, ...measurement });
      } catch (error) {
        navAnchorResults.push({ label, href, interactionError: String(error.message || error).slice(0, 220) });
      }
    }
    const navAnchorsPass = navAnchorResults.length > 0 && navAnchorResults.every(x =>
      x.targetFound && x.headingFound && x.headingVisible && x.clearance !== null && x.clearance >= 6 && !x.interactionError
    );
    // Verify the mobile toolbar stays attached to the navigation after scrolling.
    await cand.page.evaluate(() => window.scrollTo(0, Math.min(600, document.documentElement.scrollHeight - window.innerHeight)));
    await cand.page.waitForTimeout(120);
    const toolbarScrollCheck = await cand.page.evaluate(() => {
      const btn = document.querySelector(".tac-side-open");
      const nav = document.querySelector(".nav");
      if (!btn || !nav) return { exists: false, buttonWithinNav: false, buttonInsideNavViewport: false };
      const b = btn.getBoundingClientRect();
      const n = nav.getBoundingClientRect();
      return {
        exists: true,
        buttonWithinNav: btn.parentElement === nav,
        buttonInsideNavViewport: b.top >= n.top - 1 && b.bottom <= n.bottom + 1,
        buttonTop: Math.round(b.top), buttonBottom: Math.round(b.bottom),
        navTop: Math.round(n.top), navBottom: Math.round(n.bottom),
        scrollY: Math.round(window.scrollY)
      };
    });
    await cand.page.evaluate(() => window.scrollTo(0, 0));
    await cand.page.waitForTimeout(100);
    const tabResults = [];
    for (const tab of tabCases) {
      const label = cand.page.locator(tab.label).first();
      const input = cand.page.locator(tab.input).first();
      if (await label.count() && await input.count()) {
        try {
          await label.click({ timeout: 3000 });
          // Let the shared color transition finish before comparing computed styles.
          await cand.page.waitForTimeout(260);
          const checked = await input.isChecked();
          // Clear :hover so the assertion reads the selected state, not the hover state.
          const safePoint = await cand.page.evaluate(() => ({ x: Math.max(1, innerWidth - 6), y: Math.max(1, innerHeight - 6) }));
          await cand.page.mouse.move(safePoint.x, safePoint.y);
          await cand.page.waitForTimeout(80);
          const backgroundColor = await label.evaluate(el => getComputedStyle(el).backgroundColor);
          const textColor = await label.evaluate(el => getComputedStyle(el).color);
          const selectorMatch = await cand.page.evaluate((inputSelector) => {
            const id = inputSelector.slice(1);
            const input = document.getElementById(id);
            const labelEl = document.querySelector('label[for="' + id + '"]');
            const wrapperClass = id.startsWith("tac-news-") ? ".tac-ds-tabs" :
              id.startsWith("tac-region-") ? ".tac-ds-tabs" :
              id.startsWith("tac-assets-") ? ".tac-ds-tabs" :
              id.startsWith("week-econ-") ? ".week-econ-tab-labels" :
              id.startsWith("week-earnings-") ? ".week-earnings-tab-labels" :
              id.startsWith("fed-live-tab-") ? ".fed-live-tab-labels" : ".focus-tab-labels";
            return {
              checked: !!input?.checked,
              matchingSelector: !!document.querySelector("#" + id + ":checked ~ " + wrapperClass + ' label[for="' + id + '"]'),
              sameParent: !!input && !!labelEl && input.parentElement === labelEl.parentElement.parentElement
            };
          }, tab.input);
          let panelVisible = null;
          if (await cand.page.locator(tab.panel).count()) panelVisible = await cand.page.locator(tab.panel).first().isVisible();
          let visibleStatusGroupCount = null;
          if (tab.input.startsWith("#week-econ-")) visibleStatusGroupCount = await cand.page.locator("#calendar .week-econ-panels > .calendar-status-group:visible").count();
          if (tab.input.startsWith("#week-earnings-")) visibleStatusGroupCount = await cand.page.locator("#earnings .week-earnings-panels > .calendar-status-group:visible").count();
          tabResults.push({ input: tab.input, checked, panelVisible, visibleStatusGroupCount, backgroundColor, textColor, selectorMatch });
        } catch (error) {
          tabResults.push({ input: tab.input, interactionError: String(error).split("\\n")[0] });
        }
      } else {
        tabResults.push({ input: tab.input, missingLabelOrInput: true });
      }
    }
    const sourceDisclosure = cand.page.locator("#sentiment details.source-details").first();
    let sourceDisclosureWorks = null;
    let sourceDisclosureCloses = null;
    let sourceDisclosureMarker = null;
    if (await sourceDisclosure.count()) {
      const sourceSummary = sourceDisclosure.locator("summary");
      await sourceSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      sourceDisclosureWorks = await sourceDisclosure.evaluate(el => el.open);
      sourceDisclosureMarker = await sourceSummary.evaluate(el => getComputedStyle(el, "::before").content);
      await sourceSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      sourceDisclosureCloses = !(await sourceDisclosure.evaluate(el => el.open));
    }
    // The only .audit-details instance is the 11-sector accordion.
    // Its open/close and +/- marker behavior is covered by the dedicated
    // sector-collapse interaction assertions below; avoid duplicating that test.
    const auditDisclosureCount = await cand.page.locator("main.wrap details.audit-details").count();
    const auditDisclosureWorks = null;
    const auditDisclosureCloses = null;
    const auditClosedMarker = null;
    const auditOpenMarker = null;
    const collapse = cand.page.locator("#last-week-calendar .last-week-calendar-collapse").first();
    const earningsCollapse = cand.page.locator("#last-week-earnings .last-week-earnings-collapse").first();
    let earningsCollapseWorks = null;
    if (await earningsCollapse.count()) {
      const before = await earningsCollapse.evaluate(el => el.open);
      await earningsCollapse.locator("summary").first().click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(100);
      const after = await earningsCollapse.evaluate(el => el.open);
      earningsCollapseWorks = before === false && after === true;
    }
    let collapseWorks = null;
    let collapseBefore = null;
    let collapseClickError = null;
    let collapseAfter = null;
    if (await collapse.count()) {
      collapseBefore = await collapse.evaluate(el => el.open);
      try {
        await collapse.locator("summary").first().click({ timeout: 3000, force: true });
        await cand.page.waitForTimeout(100);
      } catch (error) {
        collapseClickError = String(error).split("\\n")[0];
      }
      collapseAfter = await collapse.evaluate(el => el.open);
      collapseWorks = collapseBefore === false && collapseAfter === true;
    }
    const eventCard = cand.page.locator("#last-week-calendar details.tac-ds-event").first();
    let eventCardWorks = null;
    let eventCardCloses = null;
    if (await eventCard.count() && collapseAfter === true) {
      const eventSummary = eventCard.locator("summary");
      await eventSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      eventCardWorks = await eventCard.evaluate(el => el.open);
      await eventSummary.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(80);
      eventCardCloses = !(await eventCard.evaluate(el => el.open));
    }
    const earningsUpcomingLabel = cand.page.locator('#earnings label[for="week-earnings-upcoming"]').first();
    let earningsUpcomingTabWorks = false;
    let earningsAccordionWorks = null;
    let earningsAccordionCloses = null;
    if (await earningsUpcomingLabel.count()) {
      await earningsUpcomingLabel.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(260);
      earningsUpcomingTabWorks = await cand.page.locator("#week-earnings-upcoming").isChecked().catch(() => false);
      const earningsAccordion = cand.page.locator("#earnings details.tac-ds-earnings-card").first();
      if (await earningsAccordion.count()) {
        const earningsSummary = earningsAccordion.locator("summary");
        await earningsSummary.click({ timeout: 3000, force: true }).catch(() => {});
        await cand.page.waitForTimeout(80);
        earningsAccordionWorks = await earningsAccordion.evaluate(el => el.open);
        await earningsSummary.click({ timeout: 3000, force: true }).catch(() => {});
        await cand.page.waitForTimeout(80);
        earningsAccordionCloses = !(await earningsAccordion.evaluate(el => el.open));
      }
    }
    const sectorTabLabel = cand.page.locator('#industry-bonds-fx-commodities label[for="tac-assets-0"]').first();
    let sectorTabWorks = false;
    let sectorTabColor = null;
    let sectorTabTextColor = null;
    let sectorCollapseWorks = null;
    let sectorCollapseCloses = null;
    let sectorOpenMarkerPass = false;
    let sectorClosedMarkerPass = false;
    let sectorOpenSummaryColor = null;
    let sectorOpenMarkerColor = null;
    let sectorOpenMarkerBackground = null;
    let sectorClosedMarkerColor = null;
    let sectorClosedMarkerBackground = null;
    let sectorOpenMarkerDiagnostics = null;
    let sectorClosedMarkerDiagnostics = null;
    if (await sectorTabLabel.count()) {
      await sectorTabLabel.click({ timeout: 3000, force: true }).catch(() => {});
      await cand.page.waitForTimeout(260);
      sectorTabWorks = await cand.page.locator("#tac-assets-0").isChecked().catch(() => false);
      sectorTabColor = await sectorTabLabel.evaluate(el => getComputedStyle(el).backgroundColor);
      sectorTabTextColor = await sectorTabLabel.evaluate(el => getComputedStyle(el).color);
      const sectorDisclosure = cand.page.locator("#industry-bonds-fx-commodities details.sector-collapse").first();
      if (await sectorDisclosure.count()) {
        const sectorSummary = sectorDisclosure.locator(":scope > summary");
        await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
        await cand.page.waitForTimeout(350);
        const sectorBefore = await sectorDisclosure.evaluate(el => el.open);
        let sectorClickError = "";
        await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError = String(e.message || e).slice(0, 240); });
        await cand.page.waitForTimeout(350);
        const sectorAfterToggle = await sectorDisclosure.evaluate(el => el.open);
        sectorCollapseWorks = sectorAfterToggle !== sectorBefore;
        if (sectorAfterToggle) {
          const openStyle = await sectorDisclosure.evaluate(el => {
            const summary = el.querySelector(":scope > summary");
            const marker = getComputedStyle(summary, "::before");
            return { summaryColor: getComputedStyle(summary).color, markerContent: marker.content, markerColor: marker.color, markerBackground: marker.backgroundColor, markerDisplay: marker.display, markerFontSize: marker.fontSize, markerTextFill: marker.webkitTextFillColor };
          });
          sectorOpenMarkerDiagnostics = openStyle;
          sectorOpenSummaryColor = openStyle.summaryColor;
          sectorOpenMarkerColor = openStyle.markerColor;
          sectorOpenMarkerBackground = openStyle.markerBackground;
          sectorOpenMarkerPass = openStyle.markerContent.includes("−") &&
            openStyle.summaryColor === "rgb(169, 31, 39)" &&
            openStyle.markerColor === "rgb(255, 255, 255)" &&
            openStyle.markerTextFill === "rgb(255, 255, 255)" &&
            openStyle.markerBackground === "rgb(32, 35, 40)" &&
            openStyle.markerDisplay === "flex" &&
            openStyle.markerFontSize === (viewport.width <= 700 ? "22px" : "21px");
        }
        if (!sectorCollapseWorks) {
          // Retry once after tab/panel transition has fully settled; preserve a real pointer interaction.
          await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | retry: " + String(e.message || e).slice(0, 180); });
          await cand.page.waitForTimeout(350);
        }
        await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
        await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | close: " + String(e.message || e).slice(0, 180); });
        await cand.page.waitForTimeout(350);
        sectorCollapseCloses = (await sectorDisclosure.evaluate(el => el.open)) === sectorBefore;
        if (sectorCollapseCloses && !sectorBefore) {
          const closedStyle = await sectorDisclosure.evaluate(el => {
            const summary = el.querySelector(":scope > summary");
            const marker = getComputedStyle(summary, "::before");
            return { markerContent: marker.content, markerColor: marker.color, markerBackground: marker.backgroundColor, markerDisplay: marker.display, markerFontSize: marker.fontSize, markerTextFill: marker.webkitTextFillColor };
          });
          sectorClosedMarkerDiagnostics = closedStyle;
          sectorClosedMarkerColor = closedStyle.markerColor;
          sectorClosedMarkerBackground = closedStyle.markerBackground;
          sectorClosedMarkerPass = closedStyle.markerContent.includes("＋") &&
            closedStyle.markerColor === "rgb(255, 255, 255)" &&
            closedStyle.markerTextFill === "rgb(255, 255, 255)" &&
            closedStyle.markerBackground === "rgb(198, 40, 40)" &&
            closedStyle.markerDisplay === "flex" &&
            closedStyle.markerFontSize === (viewport.width <= 700 ? "22px" : "21px");
        }
        if (!sectorCollapseCloses) {
          await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
          await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | close retry: " + String(e.message || e).slice(0, 180); });
          await cand.page.waitForTimeout(350);
          sectorCollapseCloses = (await sectorDisclosure.evaluate(el => el.open)) === sectorBefore;
        }
        results.sectorCollapseClickError = sectorClickError;
      }
    }
    const selectedTabColors = tabResults.filter(t => t.backgroundColor).map(t => t.backgroundColor);
    const selectedTabTextColors = tabResults.filter(t => t.textColor).map(t => t.textColor);
    const consistentSelectedTabColor = selectedTabColors.length > 0 && selectedTabColors.every(color => color === "rgb(180, 35, 50)");
    const consistentSelectedTabTextColor = selectedTabTextColors.length > 0 && selectedTabTextColors.every(color => color === "rgb(255, 255, 255)");
    const baselineDetailedGeometry = await base.page.evaluate(() => {
      const ids = ["overview","sentiment","news-scan","global-markets","industry-bonds-fx-commodities","sp500-earnings-health","last-week-calendar","last-week-earnings","calendar","earnings","fed","view"];
      return ids.map(id => {
        const root = document.getElementById(id);
        if (!root) return { id, missing: true };
        return { id, nodes: [...root.querySelectorAll(":scope > *, .tac-ds-card--news, .newsitem, .news-card, .region-card, .asset-card, .econ-event, .earnings-accordion, details, .calendar-card, .tac-ds-event, .tac-ds-earnings-card, .tac-section-heading, .title, article.card.bluf, #overview h1, #overview p, #overview .chips, #overview .chip, #overview .bluf-subtitle, #overview .summary-subtitle, .news-list, .news-grid, .grid, .tac-ds-tabs, .row, .sector-row, .instrument-name, .sp500-health-row, .earnings-health-row, .week-econ-tabs, .week-econ-tab-labels, .week-econ-panels, .week-earnings-tabs, .week-earnings-tab-labels, .week-earnings-panels, .calendar-status-group, .calendar-status-heading, .calendar-status-empty, .econ-event-list, .earnings-accordion-list, .focus-tabs, .focus-tab-labels, .fed-live-tabs, .fed-live-tab-labels, #sentiment .sbox, #sentiment .fg6-score-row, #sentiment .fg6-scale-wrap, #sentiment details.source-details > summary")].slice(0,110).map((el,i) => {
          const r=el.getBoundingClientRect(), s=getComputedStyle(el);
          return {i,tag:el.tagName,cls:String(el.className||"").slice(0,100),id:el.id,top:Math.round(r.top+window.scrollY),height:Math.round(r.height),width:Math.round(r.width),padding:s.padding,margin:s.margin,gap:s.gap,fontSize:s.fontSize,lineHeight:s.lineHeight,display:s.display};
        })};
      });
    });
    const newErrors = cand.pageErrors.filter(error => !base.pageErrors.includes(error));
    // Focused FedWatch mobile cascade assertion: these overrides must win over later base rules.
    const fedWatchStyleCheck = await cand.page.evaluate(() => {
      const card = document.querySelector("#fed .fc-probs-refined .fc-prob");
      const value = document.querySelector("#fed .fc-probs-refined .fc-prob strong");
      if (!card || !value) return { found: false, padding: null, numberFontSize: null };
      return { found: true, padding: getComputedStyle(card).padding, numberFontSize: getComputedStyle(value).fontSize };
    });
    const expectedFedWatchStyle = viewport.width <= 560
      ? { padding: "11px 10px", numberFontSize: "27px" }
      : { padding: "14px 15px", numberFontSize: "32px" };
    const fedWatchStylePass = fedWatchStyleCheck.found &&
      fedWatchStyleCheck.padding === expectedFedWatchStyle.padding &&
      fedWatchStyleCheck.numberFontSize === expectedFedWatchStyle.numberFontSize;
    if (!fedWatchStylePass) results.errors.push({ viewport: viewport.name, error: "FedWatch computed mobile/base style mismatch", actual: fedWatchStyleCheck, expected: expectedFedWatchStyle });

    // Focused sentiment disclosure geometry parity: prevent the dark source variant
    // from inheriting a border or changing summary/CNN card heights versus the frozen baseline.
    const readSentimentDisclosureGeometry = page => page.evaluate(() => {
      const root = document.querySelector("#sentiment");
      if (!root) return { found: false, disclosures: [], cnnCardHeight: null };
      const disclosures = [...root.querySelectorAll("details.source-details")].map(el => {
        const summary = el.querySelector(":scope > summary");
        const s = getComputedStyle(el);
        return {
          height: Math.round(el.getBoundingClientRect().height),
          summaryHeight: summary ? Math.round(summary.getBoundingClientRect().height) : null,
          borderTopWidth: s.borderTopWidth,
          borderBottomWidth: s.borderBottomWidth,
          padding: s.padding,
          marginTop: s.marginTop
        };
      });
      const cnn = root.querySelector(".cnn-fg-preview");
      return { found: true, disclosures, cnnCardHeight: cnn ? Math.round(cnn.getBoundingClientRect().height) : null };
    });
    const [baselineSentimentDisclosureGeometry, candidateSentimentDisclosureGeometry] = await Promise.all([
      readSentimentDisclosureGeometry(base.page),
      readSentimentDisclosureGeometry(cand.page)
    ]);
    const sentimentDisclosureGeometryPass =
      baselineSentimentDisclosureGeometry.found &&
      candidateSentimentDisclosureGeometry.found &&
      baselineSentimentDisclosureGeometry.disclosures.length === 3 &&
      candidateSentimentDisclosureGeometry.disclosures.length === 3 &&
      baselineSentimentDisclosureGeometry.disclosures.every((b, i) => {
        const c = candidateSentimentDisclosureGeometry.disclosures[i];
        return c && c.height === b.height && c.summaryHeight === b.summaryHeight &&
          c.borderTopWidth === b.borderTopWidth && c.borderBottomWidth === b.borderBottomWidth &&
          c.padding === b.padding && c.marginTop === b.marginTop;
      }) &&
      candidateSentimentDisclosureGeometry.cnnCardHeight === baselineSentimentDisclosureGeometry.cnnCardHeight;
    if (!sentimentDisclosureGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "Sentiment source disclosure/CNN card geometry differs from frozen baseline",
      baseline: baselineSentimentDisclosureGeometry,
      candidate: candidateSentimentDisclosureGeometry
    });

    // News-card geometry gate: allow the documented 1px responsive rounding,
    // but catch wrapping/spacing regressions that materially change card height.
    const readVisibleNewsCardGeometry = page => page.evaluate(() => {
      const root = document.querySelector("#news-scan");
      if (!root) return { found: false, cards: [] };
      // Tab interaction checks above deliberately visit the second news tab.
      // Normalize both pages to the same first tab before comparing visible cards.
      const baselineComparableTab = document.querySelector("#tac-news-0");
      if (baselineComparableTab) baselineComparableTab.checked = true;
      const cards = [...root.querySelectorAll(".newsitem")].map(el => {
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return {
          height: Math.round(r.height),
          width: Math.round(r.width),
          padding: s.padding,
          marginBottom: s.marginBottom
        };
      }).filter(card => card.height > 0 && card.width > 0);
      return { found: true, cards };
    });
    const [baselineNewsCardGeometry, candidateNewsCardGeometry] = await Promise.all([
      readVisibleNewsCardGeometry(base.page),
      readVisibleNewsCardGeometry(cand.page)
    ]);
    const newsCardHeightDeltas = baselineNewsCardGeometry.cards.map((b, i) =>
      candidateNewsCardGeometry.cards[i] ? candidateNewsCardGeometry.cards[i].height - b.height : null
    );
    const newsCardGeometryPass =
      baselineNewsCardGeometry.found &&
      candidateNewsCardGeometry.found &&
      baselineNewsCardGeometry.cards.length > 0 &&
      candidateNewsCardGeometry.cards.length === baselineNewsCardGeometry.cards.length &&
      baselineNewsCardGeometry.cards.every((b, i) =>
        candidateNewsCardGeometry.cards[i] &&
        candidateNewsCardGeometry.cards[i].width === b.width &&
        Math.abs(candidateNewsCardGeometry.cards[i].height - b.height) <= 1
      );
    if (!newsCardGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "Visible news-card geometry exceeds 1px baseline tolerance",
      baseline: baselineNewsCardGeometry,
      candidate: candidateNewsCardGeometry,
      heightDeltas: newsCardHeightDeltas
    });

    // The S&P 500 earnings-health title and its method/source summary are compact
    // legacy geometry exceptions; keep their heights aligned at narrow widths too.
    const readSp500TitleSourceGeometry = page => page.evaluate(() => {
      const root = document.querySelector("#sp500-earnings-health");
      const title = root?.querySelector(":scope > .title");
      const summary = root?.querySelector("details > summary");
      const measure = el => {
        if (!el) return null;
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        const before = getComputedStyle(el, "::before");
        return {
          height: Math.round(r.height),
          fontSize: s.fontSize,
          lineHeight: s.lineHeight,
          minHeight: s.minHeight,
          padding: s.padding,
          beforeContent: before.content,
          beforeDisplay: before.display
        };
      };
      return { found: !!root && !!title && !!summary, title: measure(title), summary: measure(summary) };
    });
    const [baselineSp500TitleSourceGeometry, candidateSp500TitleSourceGeometry] = await Promise.all([
      readSp500TitleSourceGeometry(base.page),
      readSp500TitleSourceGeometry(cand.page)
    ]);
    const sp500TitleSourceGeometryPass =
      baselineSp500TitleSourceGeometry.found &&
      candidateSp500TitleSourceGeometry.found &&
      baselineSp500TitleSourceGeometry.title.height === candidateSp500TitleSourceGeometry.title.height &&
      baselineSp500TitleSourceGeometry.summary.height === candidateSp500TitleSourceGeometry.summary.height &&
      baselineSp500TitleSourceGeometry.summary.beforeContent === candidateSp500TitleSourceGeometry.summary.beforeContent &&
      String(candidateSp500TitleSourceGeometry.summary.beforeContent || "").includes("▸");
    if (!sp500TitleSourceGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "S&P 500 title/source summary height differs from frozen baseline",
      baseline: baselineSp500TitleSourceGeometry,
      candidate: candidateSp500TitleSourceGeometry
    });

    const baselineAssetSourceRows = (baseReport.sourceDisclosureGeometry || []).filter(x => x.panel === "industry-bonds-fx-commodities");
    const candidateAssetSourceRows = (report.sourceDisclosureGeometry || []).filter(x => x.panel === "industry-bonds-fx-commodities");
    const assetSourceDisclosureGeometryPass =
      baselineAssetSourceRows.length === 5 &&
      candidateAssetSourceRows.length === baselineAssetSourceRows.length &&
      baselineAssetSourceRows.every((b, i) => {
        const c = candidateAssetSourceRows[i];
        return c && c.visible === b.visible && c.height === b.height &&
          c.summaryHeight === b.summaryHeight && c.marginTop === b.marginTop &&
          c.padding === b.padding && c.borderTopWidth === b.borderTopWidth &&
          c.borderBottomWidth === b.borderBottomWidth && c.summaryPadding === b.summaryPadding;
      });
    if (!assetSourceDisclosureGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "Asset-panel source disclosure geometry differs from frozen baseline",
      baseline: baselineAssetSourceRows,
      candidate: candidateAssetSourceRows
    });

    const baselineTabbedPanelHeadingGeometry = baseReport.tabbedPanelHeadingGeometry || [];
    const candidateTabbedPanelHeadingGeometry = report.tabbedPanelHeadingGeometry || [];
    const headingFields = [
      "height", "width", "containerHeight", "containerWidth", "fontSize", "fontWeight",
      "lineHeight", "color", "backgroundColor", "padding", "margin", "display",
      "alignItems", "gap", "borderLeftWidth", "borderLeftColor", "letterSpacing",
      "textAlign", "beforeContent", "beforeColor", "beforeDisplay", "beforeWidth", "beforeHeight"
    ];
    const tabbedPanelHeadingConsistencyPass =
      candidateTabbedPanelHeadingGeometry.length === 3 &&
      candidateTabbedPanelHeadingGeometry.every(x => !x.missing) &&
      headingFields.every(field => candidateTabbedPanelHeadingGeometry.every(
        x => x[field] === candidateTabbedPanelHeadingGeometry[0][field]
      ));
    if (!tabbedPanelHeadingConsistencyPass) results.errors.push({
      viewport: viewport.name,
      error: "Shared tabbed-panel headings do not share one computed typography/geometry signature",
      baseline: baselineTabbedPanelHeadingGeometry,
      candidate: candidateTabbedPanelHeadingGeometry
    });

    const baselineSpecialHeadingGeometry = baseReport.specialHeadingGeometry || [];
    const candidateSpecialHeadingGeometry = report.specialHeadingGeometry || [];
    const specialHeadingTypographyPass =
      baselineSpecialHeadingGeometry.length === 9 &&
      candidateSpecialHeadingGeometry.length === baselineSpecialHeadingGeometry.length &&
      baselineSpecialHeadingGeometry.every((b, i) => {
        const h = candidateSpecialHeadingGeometry[i];
        return h && !h.missing && h.id === b.id &&
          h.fontSize === b.fontSize && h.fontWeight === b.fontWeight &&
          h.lineHeight === b.lineHeight && h.color === b.color;
      });
    if (!specialHeadingTypographyPass) results.errors.push({
      viewport: viewport.name,
      error: "Special heading typography/color differs from the frozen baseline",
      baseline: baselineSpecialHeadingGeometry,
      candidate: candidateSpecialHeadingGeometry
    });
    const specialHeadingMarkerContractPass =
      candidateSpecialHeadingGeometry.length === 9 &&
      candidateSpecialHeadingGeometry.every(h => {
        if (h.missing) return false;
        if (h.id === "sentiment") {
          return h.borderLeftWidth === "0px" &&
            h.padding === "0px 0px 0px 15px" &&
            h.beforeDisplay === "block" &&
            h.beforeBackgroundColor === "rgb(224, 176, 75)";
        }
        if (h.id === "fed" || h.id === "view") {
          const expectedPadding = viewport.width <= 700 ? "0px 0px 0px 12px" : "0px 0px 0px 10px";
          return h.borderLeftWidth === "5px" && h.beforeDisplay === "none" && h.padding === expectedPadding;
        }
        return h.borderLeftWidth === "5px" && h.beforeDisplay === "none";
      });
    if (!specialHeadingMarkerContractPass) results.errors.push({
      viewport: viewport.name,
      error: "Special headings must use one marker; Fed/Today Focus must preserve canonical marker-to-text spacing",
      baseline: baselineSpecialHeadingGeometry,
      candidate: candidateSpecialHeadingGeometry
    });

    const baselinePanelGeometry = baseReport.panelGeometry || [];
    const candidatePanelGeometry = report.panelGeometry || [];
    const panelGeometryPass =
      baselinePanelGeometry.length === 12 &&
      candidatePanelGeometry.length === baselinePanelGeometry.length &&
      baselinePanelGeometry.every((b, i) => {
        const c = candidatePanelGeometry[i];
        return c && c.id === b.id && c.width === b.width &&
          Math.abs(c.top - b.top) <= 1 &&
          Math.abs(c.height - b.height) <= 2;
      });
    if (!panelGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "One or more main panels exceed the approved geometry tolerance (top ±1px, height ±2px, exact width)",
      baseline: baselinePanelGeometry,
      candidate: candidatePanelGeometry
    });

    const candidateSourceDisclosureColors = report.sourceDisclosureGeometry || [];
    const sourceDisclosureColorPass =
      candidateSourceDisclosureColors.length === 11 &&
      candidateSourceDisclosureColors.every(row => {
        const darkVariant = String(row.className || "").includes("tac-ds-disclosure--dark");
        return row.summaryColor === (darkVariant ? "rgb(174, 187, 200)" : "rgb(115, 121, 129)");
      });
    if (!sourceDisclosureColorPass) results.errors.push({
      viewport: viewport.name,
      error: "Source disclosure summary text color differs from light-muted/dark-contrast variant contract",
      candidate: candidateSourceDisclosureColors.map(row => ({
        panel: row.panel, className: row.className, color: row.summaryColor
      }))
    });

    const baselineSourceDisclosureGeometry = baseReport.sourceDisclosureGeometry || [];
    const candidateSourceDisclosureGeometry = report.sourceDisclosureGeometry || [];
    const sourceDisclosureGeometryPass =
      baselineSourceDisclosureGeometry.length === 11 &&
      candidateSourceDisclosureGeometry.length === baselineSourceDisclosureGeometry.length &&
      baselineSourceDisclosureGeometry.every((b, i) => {
        const c = candidateSourceDisclosureGeometry[i];
        return c && c.panel === b.panel && c.text === b.text &&
          c.visible === b.visible && c.height === b.height &&
          c.summaryHeight === b.summaryHeight && c.marginTop === b.marginTop &&
          c.padding === b.padding && c.borderTopWidth === b.borderTopWidth &&
          c.borderBottomWidth === b.borderBottomWidth &&
          c.summaryPadding === b.summaryPadding &&
          c.summaryBeforeContent === b.summaryBeforeContent &&
          c.summaryBeforeDisplay === b.summaryBeforeDisplay;
      });
    if (!sourceDisclosureGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "One or more source disclosure rows differ from frozen baseline geometry/marker contract",
      baseline: baselineSourceDisclosureGeometry,
      candidate: candidateSourceDisclosureGeometry
    });

    const baselineSectorCollapse = (baseReport.otherDisclosureGeometry || []).filter(x =>
      x.panel === "industry-bonds-fx-commodities" && String(x.kind).includes("sector-collapse")
    );
    const candidateSectorCollapse = (report.otherDisclosureGeometry || []).filter(x =>
      x.panel === "industry-bonds-fx-commodities" && String(x.kind).includes("sector-collapse")
    );
    const sectorCollapseMarkerPass =
      baselineSectorCollapse.length === 1 &&
      candidateSectorCollapse.length === 1 &&
      baselineSectorCollapse[0].beforeContent === candidateSectorCollapse[0].beforeContent &&
      String(candidateSectorCollapse[0].beforeContent || "").includes("＋");
    if (!sectorCollapseMarkerPass) results.errors.push({
      viewport: viewport.name,
      error: "Sector-list expansion marker differs from frozen baseline",
      baseline: baselineSectorCollapse,
      candidate: candidateSectorCollapse
    });
    const baselinePriorWeekDisclosureGeometry = (baseReport.otherDisclosureGeometry || []).filter(x =>
      x.panel === "last-week-calendar" || x.panel === "last-week-earnings"
    );
    const candidatePriorWeekDisclosureGeometry = (report.otherDisclosureGeometry || []).filter(x =>
      x.panel === "last-week-calendar" || x.panel === "last-week-earnings"
    );
    const priorWeekDisclosureGeometryPass =
      baselinePriorWeekDisclosureGeometry.length === 2 &&
      candidatePriorWeekDisclosureGeometry.length === 2 &&
      baselinePriorWeekDisclosureGeometry.every((b, i) => {
        const c = candidatePriorWeekDisclosureGeometry[i];
        return c && c.panel === b.panel && c.kind === b.kind &&
          c.visible === b.visible && c.height === b.height &&
          c.summaryHeight === b.summaryHeight && c.marginTop === b.marginTop &&
          c.padding === b.padding && c.borderTopWidth === b.borderTopWidth &&
          c.borderBottomWidth === b.borderBottomWidth &&
          c.summaryFontSize === b.summaryFontSize &&
          c.summaryLineHeight === b.summaryLineHeight &&
          c.summaryPadding === b.summaryPadding && c.beforeContent === b.beforeContent;
      });
    if (!priorWeekDisclosureGeometryPass) results.errors.push({
      viewport: viewport.name,
      error: "Prior-week calendar/earnings disclosure geometry differs from frozen baseline",
      baseline: baselinePriorWeekDisclosureGeometry,
      candidate: candidatePriorWeekDisclosureGeometry
    });
    results.viewports.push({
      ...viewport, baselineDetailedGeometry, baseline: baseReport, ...report, navAnchorResults, navAnchorsPass, toolbarScrollCheck, tabResults, auditDisclosureCount, auditDisclosureWorks, auditDisclosureCloses, auditClosedMarker, auditOpenMarker, consistentSelectedTabColor, consistentSelectedTabTextColor, sourceDisclosureWorks, sourceDisclosureCloses, sourceDisclosureMarker, collapseWorks, earningsCollapseWorks, collapseBefore, collapseAfter, collapseClickError, eventCardWorks, eventCardCloses, earningsUpcomingTabWorks, earningsAccordionWorks, earningsAccordionCloses, sectorTabWorks, sectorTabColor, sectorTabTextColor, sectorCollapseWorks, sectorCollapseCloses, sectorOpenMarkerPass, sectorClosedMarkerPass, sectorOpenSummaryColor, sectorOpenMarkerColor, sectorOpenMarkerBackground, sectorClosedMarkerColor, sectorClosedMarkerBackground, sectorOpenMarkerDiagnostics, sectorClosedMarkerDiagnostics,
      fedWatchStyleCheck, expectedFedWatchStyle, fedWatchStylePass,
      baselineSentimentDisclosureGeometry, candidateSentimentDisclosureGeometry, sentimentDisclosureGeometryPass,
      baselineNewsCardGeometry, candidateNewsCardGeometry, newsCardHeightDeltas, newsCardGeometryPass,
      baselineSp500TitleSourceGeometry, candidateSp500TitleSourceGeometry, sp500TitleSourceGeometryPass,
      baselineAssetSourceRows, candidateAssetSourceRows, assetSourceDisclosureGeometryPass,
      baselineTabbedPanelHeadingGeometry, candidateTabbedPanelHeadingGeometry, tabbedPanelHeadingConsistencyPass,
      baselineSpecialHeadingGeometry, candidateSpecialHeadingGeometry, specialHeadingTypographyPass, specialHeadingMarkerContractPass,
      baselinePanelGeometry, candidatePanelGeometry, panelGeometryPass,
      candidateSourceDisclosureColors, sourceDisclosureColorPass,
      baselineSourceDisclosureGeometry, candidateSourceDisclosureGeometry, sourceDisclosureGeometryPass,
      baselineSectorCollapse, candidateSectorCollapse, sectorCollapseMarkerPass,
      baselinePriorWeekDisclosureGeometry, candidatePriorWeekDisclosureGeometry, priorWeekDisclosureGeometryPass,
      baselinePageErrors: base.pageErrors, pageErrors: cand.pageErrors, newErrors,
      screenshots: ["baseline-" + viewport.name + ".png", "candidate-" + viewport.name + ".png", "diff-" + viewport.name + ".png"]
    });
    if (report.fiveStarRedCount !== 16) {
      results.errors.push({ viewport: viewport.name, error: `Expected 16 exact five-star glyphs red, got ${report.fiveStarRedCount}` });
    }
    results.errors.push(...newErrors.map(error => ({ viewport: viewport.name, error })));
    await base.page.close();
    await cand.page.close();
  }
  results.static = {
    requiredPanelIds: panelIds,
    requiredTabCaseCount: tabCases.length,
    expectedScripts: 10,
    note: "Pixel diffs compare the frozen baseline with the CSS-extracted candidate. A zero diff verifies parity, not design improvement."
  };
  fs.writeFileSync(path.join(outDir, "results.json"), JSON.stringify(results, null, 2));
  const summary = [
    "# TAC Refactor Browser Smoke Test",
    "",
    ...results.viewports.map(v => `## ${v.name} — ${v.width}×${v.height}
- Document width: baseline=${v.baseline.docWidth}, candidate=${v.docWidth}
- Horizontal overflow: baseline=${v.baseline.horizontalOverflow}, candidate=${v.horizontalOverflow}
- Missing panel IDs: ${v.missingPanels.join(", ") || "none"}
- Duplicate IDs: ${v.duplicateIds.join(", ") || "none"}
- Unmatched nav links: ${v.unmatchedNav.length}
- Navigation anchor geometry: pass=${v.navAnchorsPass}; measurements=${v.navAnchorResults.map(a => `${a.href} top=${a.headingTop} visibleBottom=${a.visibleHeaderBottom} clearance=${a.clearance} visible=${a.headingVisible} target=${a.targetFound} heading=${a.headingFound}`).join(" | ")}
- Shared tabbed-panel heading consistency: pass=${v.tabbedPanelHeadingConsistencyPass}; candidate signatures=${JSON.stringify(v.candidateTabbedPanelHeadingGeometry)}\n- Special heading typography parity: pass=${v.specialHeadingTypographyPass}; marker contract: pass=${v.specialHeadingMarkerContractPass}; variants (baseline → candidate): ${JSON.stringify(v.specialHeadingGeometry.map(h => { const b=(v.baseline.specialHeadingGeometry||[]).find(x=>x.id===h.id); return {id:h.id,missing:h.missing||b?.missing,fontSize:[b?.fontSize,h.fontSize],fontWeight:[b?.fontWeight,h.fontWeight],lineHeight:[b?.lineHeight,h.lineHeight],color:[b?.color,h.color],padding:[b?.padding,h.padding],margin:[b?.margin,h.margin],borderLeftWidth:[b?.borderLeftWidth,h.borderLeftWidth],height:[b?.height,h.height],width:[b?.width,h.width],beforeColor:[b?.beforeColor,h.beforeColor],beforeBackgroundColor:[b?.beforeBackgroundColor,h.beforeBackgroundColor],beforeDisplay:[b?.beforeDisplay,h.beforeDisplay],beforeHeight:[b?.beforeHeight,h.beforeHeight]}; }))}\n- Main-panel geometry tolerance: pass=${v.panelGeometryPass}; baseline → candidate heights: ${v.panelGeometry.map(p => { const b=v.baseline.panelGeometry.find(x=>x.id===p.id); return `${p.id}: ${b?.height ?? "missing"}px → ${p.height}px (Δ${b ? p.height-b.height : "n/a"}px; top Δ${b ? p.top-b.top : "n/a"}px; width Δ${b ? p.width-b.width : "n/a"}px)`; }).join(" | ")}
- Prior-week disclosure geometry parity: pass=${v.priorWeekDisclosureGeometryPass}; baseline=${JSON.stringify(v.baselinePriorWeekDisclosureGeometry)}; candidate=${JSON.stringify(v.candidatePriorWeekDisclosureGeometry)}
- Toolbar onboarding bubble: present before screenshot cleanup=${v.coachPresentBeforeCleanup}, mobile expected=${v.coachMobileExpected}, toolbar text=${v.coachTextContract}, pointer-events disabled=${v.coachPointerEventsNone}, target pulse=${v.coachTargetPulse}, initial display=${v.coachInitialVisibility}, bubble in viewport=${v.coachBubbleInViewport}, wraps=${v.coachBubbleWraps}, text inside bubble=${v.coachTextInsideBubble}, width=${v.coachBubbleWidth}, legacy hint removed=${v.coachLegacyHintRemoved}\n- Style/script tags: ${v.styleTagCount}/${v.scriptCount}
- Audit disclosure: count=${v.auditDisclosureCount}, opens=${v.auditDisclosureWorks}, closes=${v.auditDisclosureCloses}, closed marker=${v.auditClosedMarker}, open marker=${v.auditOpenMarker}
- Source disclosure: opens=${v.sourceDisclosureWorks}, closes=${v.sourceDisclosureCloses}, marker=${v.sourceDisclosureMarker}
- Sentiment special background: class=${v.sentimentThemeClassPresent}, layered background=${v.sentimentBackgroundImage?.includes("gradient")}, orbit before=${v.sentimentBeforeContent}/${v.sentimentBeforeBoxShadow}, orbit after=${v.sentimentAfterContent}/${v.sentimentAfterBoxShadow}, canvas=${v.sentimentBackgroundColor}\n- Shared components: tabs=${v.sharedTabLabelCount}, disclosures=${v.sharedDisclosureCount}, dark disclosures=${v.darkDisclosureCount}, empty states=${v.sharedEmptyStateCount}, news cards=${v.sharedNewsCardCount}, news backgrounds=${v.sharedNewsCardBackgrounds?.join(",")}, news radii=${v.sharedNewsCardRadii?.join(",")}, event cards=${v.sharedEventCardCount}, event radii=${v.sharedEventCardRadii?.join(",")}, event open/close=${v.eventCardWorks}/${v.eventCardCloses}, earnings cards=${v.sharedEarningsCardCount}, earnings radii=${v.sharedEarningsCardRadii?.join(",")}, earnings open/close=${v.earningsAccordionWorks}/${v.earningsAccordionCloses}, sector rows=${v.sharedSectorRowCount}, sector radii=${v.sharedSectorRowRadii?.join(",")}, sector backgrounds=${v.sharedSectorRowBackgrounds?.join(",")}, sector tab/collapse=${v.sectorTabWorks}/${v.sectorCollapseWorks}/${v.sectorCollapseCloses}, actual earnings result cards=${v.sharedActualEarningsCardCount}, radii=${v.sharedActualEarningsCardRadii?.join(",")}, backgrounds=${v.sharedActualEarningsCardBackgrounds?.join(",")}, beat/miss=${v.actualEarningsBeatCount}/${v.actualEarningsMissCount}
- Prior-week disclosures open: economics=${v.collapseWorks}, earnings=${v.earningsCollapseWorks} (before=${v.collapseBefore}, after=${v.collapseAfter}, error=${v.collapseClickError || "none"})
- Sentiment disclosure geometry parity: pass=${v.sentimentDisclosureGeometryPass}; baseline=${JSON.stringify(v.baselineSentimentDisclosureGeometry)}; candidate=${JSON.stringify(v.candidateSentimentDisclosureGeometry)}\n- All source-disclosure geometry parity: pass=${v.sourceDisclosureGeometryPass}; color contract: pass=${v.sourceDisclosureColorPass}; baseline=${JSON.stringify(v.baselineSourceDisclosureGeometry)}; candidate=${JSON.stringify(v.candidateSourceDisclosureGeometry)}\n- Calendar/audit disclosure geometry audit: baseline=${JSON.stringify(v.baseline.otherDisclosureGeometry)}; candidate=${JSON.stringify(v.otherDisclosureGeometry)}\n- Visible news-card geometry parity: pass=${v.newsCardGeometryPass}; height deltas=${JSON.stringify(v.newsCardHeightDeltas)}; baseline=${JSON.stringify(v.baselineNewsCardGeometry)}; candidate=${JSON.stringify(v.candidateNewsCardGeometry)}\n- S&P 500 title/source row geometry parity: pass=${v.sp500TitleSourceGeometryPass}; baseline=${JSON.stringify(v.baselineSp500TitleSourceGeometry)}; candidate=${JSON.stringify(v.candidateSp500TitleSourceGeometry)}\n- Asset source-disclosure geometry parity: pass=${v.assetSourceDisclosureGeometryPass}; baseline=${JSON.stringify(v.baselineAssetSourceRows)}; candidate=${JSON.stringify(v.candidateAssetSourceRows)}\n- Sector-list expansion marker parity: pass=${v.sectorCollapseMarkerPass}; baseline=${JSON.stringify(v.baselineSectorCollapse)}; candidate=${JSON.stringify(v.candidateSectorCollapse)}\n - New browser errors: ${v.newErrors.length}
- Pixel diff: ${results.visualDiffs.find(d => d.viewport === v.name)?.diffPixels} pixels (${results.visualDiffs.find(d => d.viewport === v.name)?.diffRatio})
- Instrument font sizes: global market=${JSON.stringify(v.globalMarketNameFontSizes)}, industry=${JSON.stringify(v.industryInstrumentFontSizes)}, comparable=${v.globalMarketNameFontSizes.length > 0 && v.industryInstrumentFontSizes.length > 0 && v.industryInstrumentFontSizes.every(size => v.globalMarketNameFontSizes.includes(size))}
- Hidden acceptance metrics: audit details=${v.auditDisclosureCount}/${v.auditDisclosureWorks}/${v.auditDisclosureCloses}/${v.auditClosedMarker}/${v.auditOpenMarker}; method disclosures=${v.methodDisclosureCount}/${v.methodDisclosureInlineStyles}; region source typography=${JSON.stringify(v.regionSectorSourceTypography)}; dark disclosure signatures=${JSON.stringify(v.darkDisclosureStyleSignatures)}; temporary preview footer=${v.temporaryPreviewFooterText}; fear/greed=${v.fearGreedScore}/${v.fearGreedMarkerPosition}; five-star red=${v.fiveStarRedCount}; source triangles=${v.sourceTrianglesPresent}; double-bar headings=${v.doubleBarHeadings}; sector tab color/text=${v.sectorTabColor}/${v.sectorTabTextColor}; earnings upcoming tab=${v.earningsUpcomingTabWorks}; event open/close=${v.eventCardWorks}/${v.eventCardCloses}; earnings accordion=${v.earningsAccordionWorks}/${v.earningsAccordionCloses}; sector tab/collapse=${v.sectorTabWorks}/${v.sectorCollapseWorks}/${v.sectorCollapseCloses}; source disclosure=${v.sourceDisclosureWorks}/${v.sourceDisclosureCloses}; prior-week collapses=${v.collapseWorks}/${v.earningsCollapseWorks}; selected colors=${v.consistentSelectedTabColor}/${v.consistentSelectedTabTextColor}; coach contract=${v.coachPresentBeforeCleanup}/${v.coachTextContract}/${v.coachPointerEventsNone}/${v.coachTargetPulse}/${v.coachBubbleInViewport}/${v.coachBubbleWraps}/${v.coachTextInsideBubble}/${v.coachLegacyHintRemoved}; tab errors=${v.tabResults.filter(t => t.missingLabelOrInput || t.checked === false || t.panelVisible === false || t.interactionError).length}; browser errors=${v.newErrors.length}
- Main tab style signatures: ${JSON.stringify(v.mainTabStyleSignatures)}
- Toolbar placement/scroll: nav=${v.toolbarButtonInNav}, placement=${v.toolbarButtonPlacement}, position=${v.toolbarButtonPosition}, scroll=${JSON.stringify(v.toolbarScrollCheck)}
- Selected tab color unified: ${v.consistentSelectedTabColor}; selected text white: ${v.consistentSelectedTabTextColor}
- Tab checks: ${v.tabResults.map(t => `${t.input}: checked=${t.checked}, visible=${t.panelVisible}, visibleStatusGroups=${t.visibleStatusGroupCount ?? "n/a"}, bg=${t.backgroundColor || ""}, selector=${JSON.stringify(t.selectorMatch || {})}, error=${t.interactionError || ""}, missing=${t.missingLabelOrInput || false}`).join("; ")}`),
    "",
    "Screenshots include baseline, candidate, and pixel-diff images for each viewport.",
    "Pixel differences are expected during the design migration; inspect baseline/candidate/diff artifacts for quality and regressions."
  ].join("\n");
  fs.writeFileSync(path.join(outDir, "summary.md"), summary);
  console.log(summary);
  const failed = results.viewports.some(v =>
    v.duplicateIds.length || v.missingPanels.length || v.unmatchedNav.length || !v.navAnchorsPass ||
    (v.coachMobileExpected && (!v.coachPresentBeforeCleanup || !v.coachTextContract || !v.coachPointerEventsNone || !v.coachTargetPulse)) ||
    (v.coachMobileExpected && (!v.coachBubbleInViewport || !v.coachBubbleWraps || !v.coachTextInsideBubble || !v.coachLegacyHintRemoved || v.coachBubbleWidth > Math.min(240, v.width - 28) + 1)) ||
    (!v.coachMobileExpected && v.coachInitialVisibility !== "missing") ||
    v.sentimentThemeClassPresent !== true || !String(v.sentimentBackgroundImage || "").includes("gradient") || v.sentimentBeforeContent === "none" || v.sentimentBeforeContent === "normal" || !String(v.sentimentBeforeBoxShadow || "").includes("rgba") || v.sentimentAfterContent === "none" || v.sentimentAfterContent === "normal" || !String(v.sentimentAfterBoxShadow || "").includes("rgba") ||
    v.auditDisclosureCount !== 1 || v.sharedTabLabelCount !== 21 || v.sharedDisclosureCount < 13 || v.methodDisclosureCount !== 4 || v.methodDisclosureInlineStyles !== 0 || v.regionSectorSourceTypography.length !== 4 || v.regionSectorSourceTypography.some(s => s.fontSize !== "11px" || s.fontWeight !== "400" || s.color !== "rgb(115, 121, 129)" || s.padding !== "2px 0px") || v.darkDisclosureCount < 2 || v.darkDisclosureStyleSignatures.length !== 3 || v.darkDisclosureStyleSignatures.some(s => s.summaryColor !== "rgb(174, 187, 200)" || s.markerColor !== "rgb(226, 184, 77)" || (s.sourceColor !== null && s.sourceColor !== "rgb(194, 204, 214)")) || v.sharedEmptyStateCount !== 4 || v.sharedNewsCardCount !== 15 ||
    JSON.stringify(v.sharedNewsCardBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || JSON.stringify(v.sharedNewsCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.sharedEventCardCount !== 12 || JSON.stringify(v.sharedEventCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.eventCardWorks !== true || v.eventCardCloses !== true || v.sharedEarningsCardCount !== 22 || JSON.stringify(v.sharedEarningsCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.earningsUpcomingTabWorks !== true || v.earningsAccordionWorks !== true || v.earningsAccordionCloses !== true || v.sharedSectorRowCount !== 11 || JSON.stringify(v.sharedSectorRowRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || JSON.stringify(v.sharedSectorRowBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || v.sharedActualEarningsCardCount !== 14 || JSON.stringify(v.sharedActualEarningsCardRadii) !== JSON.stringify([v.width <= 640 ? "12px" : "14px"]) || JSON.stringify(v.sharedActualEarningsCardBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || v.actualEarningsBeatCount < 1 || v.actualEarningsMissCount < 1 || v.sectorTabWorks !== true || v.sectorTabColor !== "rgb(180, 35, 50)" || v.sectorTabTextColor !== "rgb(255, 255, 255)" || v.sectorCollapseWorks !== true || v.sectorCollapseCloses !== true ||
    !v.sentimentDisclosureGeometryPass ||
    !v.newsCardGeometryPass ||
    !v.sp500TitleSourceGeometryPass ||
    !v.assetSourceDisclosureGeometryPass ||
    !v.sectorCollapseMarkerPass || !v.sectorOpenMarkerPass || !v.sectorClosedMarkerPass ||
    v.sourceDisclosureWorks !== true || v.sourceDisclosureCloses !== true || !String(v.sourceDisclosureMarker || "").includes("▸") ||
    (v.horizontalOverflow && !v.baseline.horizontalOverflow) ||
    !v.toolbarButtonInNav || v.toolbarButtonPlacement !== "navigation" || (v.width < 1100 && v.toolbarButtonPosition !== "relative") || (v.width < 1100 && (!v.toolbarScrollCheck?.buttonWithinNav || !v.toolbarScrollCheck?.buttonInsideNavViewport)) ||
    v.temporaryPreviewFooterText || !Number.isFinite(v.fearGreedScore) || !Number.isFinite(v.fearGreedMarkerPosition) ||
    Math.abs(v.fearGreedScore - v.fearGreedMarkerPosition) > 0.1 || v.fiveStarRedCount !== 16 ||
    v.sourceTrianglesPresent < 1 || v.doubleBarHeadings > 0 ||
    (v.globalMarketNameFontSizes.length > 0 && v.industryInstrumentFontSizes.some(size => !v.globalMarketNameFontSizes.includes(size))) ||
    (v.width > 380 && new Set(v.mainTabStyleSignatures.filter(x => !x.missing).map(x => JSON.stringify({fontSize:x.fontSize,minHeight:x.minHeight,padding:x.padding,borderRadius:x.borderRadius,whiteSpace:x.whiteSpace}))).size > 1) || (v.width <= 380 && v.mainTabStyleSignatures.some(x => !x.missing && (x.whiteSpace !== "nowrap" || x.fontSize !== "12px"))) ||
    v.tabResults.some(t => t.missingLabelOrInput || t.checked === false || t.panelVisible === false || t.interactionError || (t.input.startsWith("#week-") && t.visibleStatusGroupCount !== 1)) ||
    !v.consistentSelectedTabColor || !v.consistentSelectedTabTextColor || v.collapseWorks === false || v.earningsCollapseWorks === false || v.newErrors.length
  ) || results.visualDiffs.some(d => d.baselineSize[0] !== d.candidateSize[0]);
  if (failed || results.errors.length > 0) process.exitCode = 1;
} finally {
  await browser.close();
}
