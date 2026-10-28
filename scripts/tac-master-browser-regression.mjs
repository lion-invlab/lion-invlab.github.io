import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const cases = [
  { name: "monday", file: "母版專區/TAC_母版_週一_2026-10-26.html" },
  { name: "weekday", file: "母版專區/TAC_母版_週二至週五_2026-10-28.html" }
];
const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
  { name: "narrow", width: 320, height: 800 }
];
const results = [];
const failures = [];
const out = path.join(root, "artifacts", "tac-master-browser");
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ headless: true });

for (const item of cases) {
  const file = path.resolve(root, item.file);
  if (!fs.existsSync(file)) {
    failures.push(`${item.name}: missing file ${item.file}`);
    continue;
  }
  for (const vp of viewports) {
    const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", e => errors.push("pageerror: " + e.message));
    page.on("console", m => { if (m.type() === "error") errors.push("console: " + m.text()); });
    await page.goto("file://" + file, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(800);

    const initial = await page.evaluate(() => {
      const allIds = [...document.querySelectorAll("[id]")].map(el => el.id);
      const duplicates = [...new Set(allIds.filter((id, i) => allIds.indexOf(id) !== i))];
      const navLinks = [...document.querySelectorAll("nav a[href^='#'], .top a[href^='#'], a[href^='#']")];
      const unmatched = navLinks.filter(a => {
        const href = a.getAttribute("href");
        try { return !document.getElementById(decodeURIComponent(href.slice(1))); }
        catch { return true; }
      }).map(a => ({ text: a.textContent.trim(), href: a.getAttribute("href") }));
      const bubble = document.querySelector(".tac-toolbar-bubble-preview");
      const bubbleStyle = bubble ? getComputedStyle(bubble) : null;
      return {
        title: document.title,
        viewport: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        pageHeight: document.documentElement.scrollHeight,
        duplicateIds: duplicates,
        unmatchedNav: unmatched,
        mainPanels: ["overview","sentiment","news-scan","global-markets","industry-bonds-fx-commodities","last-week-calendar","last-week-earnings","calendar","earnings","sp500-earnings-health","fed","view"]
          .filter(id => document.getElementById(id)),
        missingCorePanels: ["overview","sentiment","news-scan","global-markets","industry-bonds-fx-commodities","calendar","earnings","sp500-earnings-health","fed","view"]
          .filter(id => !document.getElementById(id)),
        detailsCount: document.querySelectorAll("details").length,
        radioCount: document.querySelectorAll('input[type="radio"]').length,
        toolbarBubble: bubble ? { visible: !!bubble.getClientRects().length && bubbleStyle.display !== "none" && bubbleStyle.visibility !== "hidden" && Number(bubbleStyle.opacity) > 0, hasClientRects: !!bubble.getClientRects().length, display: bubbleStyle.display, visibility: bubbleStyle.visibility, opacity: bubbleStyle.opacity, position: bubbleStyle.position, rect: (() => { const r = bubble.getBoundingClientRect(); return { x:r.x, y:r.y, width:r.width, height:r.height }; })(), mediaMobile: matchMedia("(max-width:1099px)").matches, buttonExists: !!document.querySelector(".tac-side-open"), buttonRect: (() => { const b = document.querySelector(".tac-side-open"); if (!b) return null; const r = b.getBoundingClientRect(); return { x:r.x, y:r.y, width:r.width, height:r.height }; })(), text: bubble.textContent.trim() } : null,
        toolbarTargetCount: document.querySelectorAll(".tac-toolbar-bubble-target").length,
        visibleModalCandidates: [...document.querySelectorAll('[role="dialog"],dialog[open],.modal.show,.modal.open,.tac-modal,.tac-overlay.is-open,.tac-dialog')].map(el => { const cs=getComputedStyle(el), r=el.getBoundingClientRect(); return {tag:el.tagName,id:el.id,className:typeof el.className==="string"?el.className:"",role:el.getAttribute("role"),display:cs.display,visibility:cs.visibility,opacity:cs.opacity,width:r.width,height:r.height,text:(el.textContent||"").trim().slice(0,80)}; }).filter(el => el.display!=="none" && el.visibility!=="hidden" && Number(el.opacity||1)>0 && el.width>0 && el.height>0)
      };
    });

    if (initial.duplicateIds.length) failures.push(`${item.name}/${vp.name}: duplicate IDs ${initial.duplicateIds.join(", ")}`);
    if (initial.unmatchedNav.length) failures.push(`${item.name}/${vp.name}: unmatched nav anchors ${JSON.stringify(initial.unmatchedNav)}`);
    if (initial.missingCorePanels.length) failures.push(`${item.name}/${vp.name}: missing core panels ${initial.missingCorePanels.join(", ")}`);
    if (initial.documentWidth > vp.width + 1) failures.push(`${item.name}/${vp.name}: horizontal overflow documentWidth=${initial.documentWidth}, viewport=${vp.width}`);
    if (vp.width < 1100 && (!initial.toolbarBubble || !initial.toolbarBubble.visible)) failures.push(`${item.name}/${vp.name}: mobile toolbar reminder bubble is missing or hidden`);
    if (vp.width >= 1100 && initial.toolbarBubble) failures.push(`${item.name}/${vp.name}: mobile toolbar reminder unexpectedly appears on desktop`);

    const detailsTest = await page.evaluate(() => {
      const el = document.querySelector("details");
      if (!el) return { available: false };
      const summary = el.querySelector("summary");
      const before = el.open;
      summary.click();
      const afterClick = el.open;
      summary.click();
      const afterSecondClick = el.open;
      return { available: true, before, afterClick, afterSecondClick };
    });
    if (detailsTest.available && detailsTest.afterClick === detailsTest.before) failures.push(`${item.name}/${vp.name}: native details did not toggle open`);
    if (detailsTest.available && detailsTest.afterSecondClick !== detailsTest.before) failures.push(`${item.name}/${vp.name}: native details did not toggle back`);

    const tabTest = await page.evaluate(() => {
      const candidates = ["tac-news-1","tac-region-1","tac-assets-4","week-econ-upcoming","week-earnings-upcoming","fed-live-tab-fomc","focus-tab-core"];
      const tested = [];
      for (const id of candidates) {
        const input = document.getElementById(id);
        if (!input || input.type !== "radio") continue;
        const label = document.querySelector('label[for="' + CSS.escape(id) + '"]');
        if (!label) { tested.push({ id, ok: false, reason: "missing label" }); continue; }
        label.click();
        tested.push({ id, ok: input.checked, checked: input.checked });
      }
      return tested;
    });
    for (const t of tabTest) if (!t.ok) failures.push(`${item.name}/${vp.name}: tab interaction failed ${t.id} ${t.reason || ""}`);

    await page.screenshot({ path: path.join(out, `${item.name}-${vp.name}-top.png`), fullPage: false });
    results.push({ template: item.name, viewport: vp, initial, detailsTest, tabTest, browserErrors: errors });
    if (errors.length) failures.push(`${item.name}/${vp.name}: browser errors ${JSON.stringify(errors)}`);
    await page.close();
  }
}
await browser.close();
fs.writeFileSync(path.join(out, "report.json"), JSON.stringify({ results, failures }, null, 2));
console.log(JSON.stringify({ results, failures }, null, 2));
if (failures.length) process.exit(1);
