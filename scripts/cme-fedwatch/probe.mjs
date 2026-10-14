import { chromium } from "playwright";
import fs from "node:fs/promises";

const url = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html";
const startedAt = new Date().toISOString();
const events = [];
const errors = [];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
page.setDefaultTimeout(15000);

page.on("request", req => {
  if (/quikstrike|fedwatch|probab|meeting|api/i.test(req.url())) {
    events.push({ type: "request", method: req.method(), url: req.url(), resourceType: req.resourceType() });
  }
});
page.on("response", res => {
  if (/quikstrike|fedwatch|probab|meeting|api/i.test(res.url())) {
    events.push({ type: "response", status: res.status(), url: res.url(), contentType: res.headers()["content-type"] || "" });
  }
});
page.on("pageerror", e => errors.push(String(e)));
page.on("requestfailed", req => {
  if (/quikstrike|fedwatch|probab|meeting|api/i.test(req.url())) {
    errors.push({ request: req.url(), failure: req.failure()?.errorText || "unknown" });
  }
});

let navigationError = null;
try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(20000);
} catch (e) {
  navigationError = String(e);
}

const frames = [];
for (const frame of page.frames()) {
  let bodyText = "";
  try { bodyText = (await frame.locator("body").innerText({ timeout: 5000 })).slice(0, 12000); }
  catch (e) { bodyText = "[body text unavailable: " + String(e) + "]"; }
  frames.push({
    url: frame.url(),
    name: await frame.name().catch(() => ""),
    title: await frame.title().catch(() => ""),
    bodyText
  });
}

const report = {
  startedAt,
  finishedAt: new Date().toISOString(),
  sourceUrl: url,
  navigationError,
  pageTitle: await page.title().catch(() => ""),
  pageUrl: page.url(),
  frameCount: frames.length,
  frames,
  relevantNetworkEvents: events,
  errors
};

await fs.mkdir("artifacts", { recursive: true });
await page.screenshot({ path: "artifacts/cme-fedwatch-page.png", fullPage: true, timeout: 30000 }).catch(e => errors.push("screenshot: " + String(e)));
report.errors = errors;
await fs.writeFile("artifacts/cme-fedwatch-probe.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify({
  sourceUrl: report.sourceUrl,
  pageTitle: report.pageTitle,
  frameCount: report.frameCount,
  frames: frames.map(f => ({ url: f.url, name: f.name, textLength: f.bodyText.length, containsProbability: /probability|probabilities|機率/i.test(f.bodyText) })),
  relevantNetworkEventCount: events.length,
  errorCount: errors.length,
  navigationError
}, null, 2));

await browser.close();
