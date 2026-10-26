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
  { input: "#week-econ-upcoming", label: 'label[for="week-econ-upcoming"]', panel: ".week-econ-panels > .calendar-status-group:nth-child(2)" },
  { input: "#week-earnings-published", label: 'label[for="week-earnings-published"]', panel: ".week-earnings-panels > .calendar-status-group:nth-child(3)" },
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
      detailedGeometry: ["overview","news-scan","global-markets","industry-bonds-fx-commodities","sp500-earnings-health","last-week-calendar","last-week-earnings","calendar","earnings","fed","view"].map(id => {
        const root = document.getElementById(id);
        if (!root) return { id, missing: true };
        return { id, nodes: [...root.querySelectorAll(":scope > *, .tac-ds-card--news, .newsitem, .news-card, .region-card, .asset-card, .econ-event, .earnings-accordion, details, .calendar-card, .tac-ds-event, .tac-ds-earnings-card, .tac-section-heading, .title, .news-list, .news-grid, .grid, .tac-ds-tabs, .row, .sector-row, .instrument-name, .sp500-health-row, .earnings-health-row")].slice(0,80).map((el,i) => {
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
      fiveStarRedCount: [...document.querySelectorAll(".earnings-accordion.star-verified-five .earnings-stars, .econ-event.star-verified-five .econ-stars")].filter(el => getComputedStyle(el).color === "rgb(198, 40, 40)").length,
      sourceTrianglesPresent: [...document.querySelectorAll("main.wrap details.source-details > summary")].filter(el => getComputedStyle(el, "::before").content.includes("▸")).length,
      doubleBarHeadings: [...document.querySelectorAll(".tac-tabset .tac-section-heading h2")].filter(el => getComputedStyle(el).borderLeftWidth !== "0px" && getComputedStyle(el, "::before").display !== "none").length,
      globalMarketNameFontSizes: [...new Set([...document.querySelectorAll("#global-markets .row b, #global-markets .instrument-name")].slice(0,20).map(el => getComputedStyle(el).fontSize))],
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
            return { text: label.textContent.trim(), top: Math.round(r.top + window.scrollY), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height), display: s.display, flex: s.flex, gridColumn: s.gridColumn, minHeight: s.minHeight, padding: s.padding, fontSize: s.fontSize, whiteSpace: s.whiteSpace };
          })
        };
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
      sharedDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure").length,
      methodDisclosureCount: document.querySelectorAll("details.tac-ds-disclosure--method").length,
      methodDisclosureInlineStyles: document.querySelectorAll("details.tac-ds-disclosure--method[style*=\"margin-top:8px\"]").length,
      regionSectorSourceTypography: [...document.querySelectorAll("details.region-source > summary, details.sector-source > summary")].map(el => { const s = getComputedStyle(el); return {fontSize:s.fontSize,fontWeight:s.fontWeight,color:s.color,padding:s.padding}; }),
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
          tabResults.push({ input: tab.input, checked, panelVisible, backgroundColor, textColor, selectorMatch });
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
        if (!sectorCollapseWorks) {
          // Retry once after tab/panel transition has fully settled; preserve a real pointer interaction.
          await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | retry: " + String(e.message || e).slice(0, 180); });
          await cand.page.waitForTimeout(350);
        }
        await sectorSummary.scrollIntoViewIfNeeded().catch(() => {});
        await sectorSummary.click({ timeout: 5000 }).catch(e => { sectorClickError += " | close: " + String(e.message || e).slice(0, 180); });
        await cand.page.waitForTimeout(350);
        sectorCollapseCloses = (await sectorDisclosure.evaluate(el => el.open)) === sectorBefore;
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
      const ids = ["overview","news-scan","global-markets","industry-bonds-fx-commodities","sp500-earnings-health"];
      return ids.map(id => {
        const root = document.getElementById(id);
        if (!root) return { id, missing: true };
        return { id, nodes: [...root.querySelectorAll(":scope > *, .tac-ds-card--news, .newsitem, .news-card, .region-card, .asset-card, .econ-event, .earnings-accordion, details, .calendar-card, .tac-ds-event, .tac-ds-earnings-card, .tac-section-heading, .title, .news-list, .news-grid, .grid, .tac-ds-tabs, .row, .sector-row, .instrument-name, .sp500-health-row, .earnings-health-row")].slice(0,80).map((el,i) => {
          const r=el.getBoundingClientRect(), s=getComputedStyle(el);
          return {i,tag:el.tagName,cls:String(el.className||"").slice(0,100),id:el.id,top:Math.round(r.top+window.scrollY),height:Math.round(r.height),width:Math.round(r.width),padding:s.padding,margin:s.margin,gap:s.gap,fontSize:s.fontSize,lineHeight:s.lineHeight,display:s.display};
        })};
      });
    });
    const newErrors = cand.pageErrors.filter(error => !base.pageErrors.includes(error));
    results.viewports.push({
      ...viewport, baselineDetailedGeometry, baseline: baseReport, ...report, navAnchorResults, navAnchorsPass, toolbarScrollCheck, tabResults, consistentSelectedTabColor, consistentSelectedTabTextColor, sourceDisclosureWorks, sourceDisclosureCloses, sourceDisclosureMarker, collapseWorks, earningsCollapseWorks, collapseBefore, collapseAfter, collapseClickError, eventCardWorks, eventCardCloses, earningsUpcomingTabWorks, earningsAccordionWorks, earningsAccordionCloses, sectorTabWorks, sectorTabColor, sectorTabTextColor, sectorCollapseWorks, sectorCollapseCloses,
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
- Panel geometry (baseline → candidate): ${v.panelGeometry.map(p => { const b=v.baseline.panelGeometry.find(x=>x.id===p.id); return `${p.id}: ${b?.height ?? "missing"}px → ${p.height}px (Δ${b ? p.height-b.height : "n/a"}px)`; }).join(" | ")}
- Prior-week disclosure summary geometry: ${JSON.stringify(v.detailedGeometry.filter(g=>["last-week-calendar","last-week-earnings"].includes(g.id)).map(g=>({id:g.id,nodes:g.nodes.filter(n=>/last-week-(calendar|earnings)-collapse/.test(n.cls)).map(n=>({cls:n.cls,height:n.height,padding:n.padding,display:n.display}))})))}
- Toolbar onboarding bubble: present before screenshot cleanup=${v.coachPresentBeforeCleanup}, mobile expected=${v.coachMobileExpected}, toolbar text=${v.coachTextContract}, pointer-events disabled=${v.coachPointerEventsNone}, target pulse=${v.coachTargetPulse}, initial display=${v.coachInitialVisibility}, bubble in viewport=${v.coachBubbleInViewport}, wraps=${v.coachBubbleWraps}, text inside bubble=${v.coachTextInsideBubble}, width=${v.coachBubbleWidth}, legacy hint removed=${v.coachLegacyHintRemoved}\n- Style/script tags: ${v.styleTagCount}/${v.scriptCount}
- Source disclosure: opens=${v.sourceDisclosureWorks}, closes=${v.sourceDisclosureCloses}, marker=${v.sourceDisclosureMarker}
- Sentiment special background: class=${v.sentimentThemeClassPresent}, layered background=${v.sentimentBackgroundImage?.includes("gradient")}, orbit before=${v.sentimentBeforeContent}/${v.sentimentBeforeBoxShadow}, orbit after=${v.sentimentAfterContent}/${v.sentimentAfterBoxShadow}, canvas=${v.sentimentBackgroundColor}\n- Shared components: tabs=${v.sharedTabLabelCount}, disclosures=${v.sharedDisclosureCount}, dark disclosures=${v.darkDisclosureCount}, empty states=${v.sharedEmptyStateCount}, news cards=${v.sharedNewsCardCount}, news backgrounds=${v.sharedNewsCardBackgrounds?.join(",")}, news radii=${v.sharedNewsCardRadii?.join(",")}, event cards=${v.sharedEventCardCount}, event radii=${v.sharedEventCardRadii?.join(",")}, event open/close=${v.eventCardWorks}/${v.eventCardCloses}, earnings cards=${v.sharedEarningsCardCount}, earnings radii=${v.sharedEarningsCardRadii?.join(",")}, earnings open/close=${v.earningsAccordionWorks}/${v.earningsAccordionCloses}, sector rows=${v.sharedSectorRowCount}, sector radii=${v.sharedSectorRowRadii?.join(",")}, sector backgrounds=${v.sharedSectorRowBackgrounds?.join(",")}, sector tab/collapse=${v.sectorTabWorks}/${v.sectorCollapseWorks}/${v.sectorCollapseCloses}, actual earnings result cards=${v.sharedActualEarningsCardCount}, radii=${v.sharedActualEarningsCardRadii?.join(",")}, backgrounds=${v.sharedActualEarningsCardBackgrounds?.join(",")}, beat/miss=${v.actualEarningsBeatCount}/${v.actualEarningsMissCount}
- Prior-week disclosures open: economics=${v.collapseWorks}, earnings=${v.earningsCollapseWorks} (before=${v.collapseBefore}, after=${v.collapseAfter}, error=${v.collapseClickError || "none"})
- New browser errors: ${v.newErrors.length}
- Pixel diff: ${results.visualDiffs.find(d => d.viewport === v.name)?.diffPixels} pixels (${results.visualDiffs.find(d => d.viewport === v.name)?.diffRatio})
- Instrument font sizes: global market=${JSON.stringify(v.globalMarketNameFontSizes)}, industry=${JSON.stringify(v.industryInstrumentFontSizes)}, comparable=${v.globalMarketNameFontSizes.length > 0 && v.industryInstrumentFontSizes.length > 0 && v.industryInstrumentFontSizes.every(size => v.globalMarketNameFontSizes.includes(size))}
- Main tab style signatures: ${JSON.stringify(v.mainTabStyleSignatures)}
- Toolbar placement/scroll: nav=${v.toolbarButtonInNav}, placement=${v.toolbarButtonPlacement}, position=${v.toolbarButtonPosition}, scroll=${JSON.stringify(v.toolbarScrollCheck)}
- Selected tab color unified: ${v.consistentSelectedTabColor}; selected text white: ${v.consistentSelectedTabTextColor}
- Tab checks: ${v.tabResults.map(t => `${t.input}: checked=${t.checked}, visible=${t.panelVisible}, bg=${t.backgroundColor || ""}, selector=${JSON.stringify(t.selectorMatch || {})}, error=${t.interactionError || ""}, missing=${t.missingLabelOrInput || false}`).join("; ")}`),
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
    v.sharedTabLabelCount !== 21 || v.sharedDisclosureCount < 13 || v.methodDisclosureCount !== 4 || v.methodDisclosureInlineStyles !== 0 || v.regionSectorSourceTypography.length !== 4 || v.regionSectorSourceTypography.some(s => s.fontSize !== "11px" || s.fontWeight !== "400" || s.color !== "rgb(156, 163, 175)" || s.padding !== "2px 0px") || v.darkDisclosureCount < 2 || v.darkDisclosureStyleSignatures.length !== 3 || v.darkDisclosureStyleSignatures.some(s => s.summaryColor !== "rgb(174, 187, 200)" || s.markerColor !== "rgb(226, 184, 77)" || (s.sourceColor !== null && s.sourceColor !== "rgb(194, 204, 214)")) || v.sharedEmptyStateCount !== 4 || v.sharedNewsCardCount !== 15 ||
    JSON.stringify(v.sharedNewsCardBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || JSON.stringify(v.sharedNewsCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.sharedEventCardCount !== 12 || JSON.stringify(v.sharedEventCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.eventCardWorks !== true || v.eventCardCloses !== true || v.sharedEarningsCardCount !== 22 || JSON.stringify(v.sharedEarningsCardRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || v.earningsUpcomingTabWorks !== true || v.earningsAccordionWorks !== true || v.earningsAccordionCloses !== true || v.sharedSectorRowCount !== 11 || JSON.stringify(v.sharedSectorRowRadii) !== JSON.stringify([v.width <= 700 ? "10px" : "12px"]) || JSON.stringify(v.sharedSectorRowBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || v.sharedActualEarningsCardCount !== 14 || JSON.stringify(v.sharedActualEarningsCardRadii) !== JSON.stringify([v.width <= 640 ? "12px" : "14px"]) || JSON.stringify(v.sharedActualEarningsCardBackgrounds) !== JSON.stringify(["rgb(255, 255, 255)"]) || v.actualEarningsBeatCount < 1 || v.actualEarningsMissCount < 1 || v.sectorTabWorks !== true || v.sectorTabColor !== "rgb(180, 35, 50)" || v.sectorTabTextColor !== "rgb(255, 255, 255)" || v.sectorCollapseWorks !== true || v.sectorCollapseCloses !== true ||
    v.sourceDisclosureWorks !== true || v.sourceDisclosureCloses !== true || !String(v.sourceDisclosureMarker || "").includes("▸") ||
    (v.horizontalOverflow && !v.baseline.horizontalOverflow) ||
    !v.toolbarButtonInNav || v.toolbarButtonPlacement !== "navigation" || (v.width < 1100 && v.toolbarButtonPosition !== "relative") || (v.width < 1100 && (!v.toolbarScrollCheck?.buttonWithinNav || !v.toolbarScrollCheck?.buttonInsideNavViewport)) ||
    v.temporaryPreviewFooterText || !Number.isFinite(v.fearGreedScore) || !Number.isFinite(v.fearGreedMarkerPosition) ||
    Math.abs(v.fearGreedScore - v.fearGreedMarkerPosition) > 0.1 || v.fiveStarRedCount !== 16 ||
    v.sourceTrianglesPresent < 1 || v.doubleBarHeadings > 0 ||
    (v.globalMarketNameFontSizes.length > 0 && v.industryInstrumentFontSizes.some(size => !v.globalMarketNameFontSizes.includes(size))) ||
    (v.width > 380 && new Set(v.mainTabStyleSignatures.filter(x => !x.missing).map(x => JSON.stringify({fontSize:x.fontSize,minHeight:x.minHeight,padding:x.padding,borderRadius:x.borderRadius,whiteSpace:x.whiteSpace}))).size > 1) || (v.width <= 380 && v.mainTabStyleSignatures.some(x => !x.missing && x.whiteSpace !== "nowrap")) ||
    v.tabResults.some(t => t.missingLabelOrInput || t.checked === false || t.panelVisible === false || t.interactionError) ||
    !v.consistentSelectedTabColor || !v.consistentSelectedTabTextColor || v.collapseWorks === false || v.earningsCollapseWorks === false || v.newErrors.length
  ) || results.visualDiffs.some(d => d.baselineSize[0] !== d.candidateSize[0]);
  if (failed || results.errors.length > 0) process.exitCode = 1;
} finally {
  await browser.close();
}
