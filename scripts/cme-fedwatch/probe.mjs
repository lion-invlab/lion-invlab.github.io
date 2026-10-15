import { chromium } from "playwright";
import fs from "node:fs/promises";

const url = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html";
const startedAt = new Date().toISOString();
const events = [];
const errors = [];
const outDir = "artifacts";
await fs.mkdir(outDir, { recursive: true });

let browser;
let page;
let navigationError = null;
const frames = [];
let pageTitle = "";
let pageUrl = "not-opened";

try {
  browser = await chromium.launch({ headless: true, args: ["--disable-http2"] });
  page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(2500);
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

  try {
    await page.goto(url, { waitUntil: "commit", timeout: 12000 });
    await page.waitForTimeout(3000);
  } catch (e) {
    navigationError = String(e);
    errors.push({ stage: "navigation", error: navigationError });
  }

  pageTitle = await Promise.race([page.title().catch(() => ""), new Promise(resolve => setTimeout(() => resolve("[title timeout]"), 1500))]);
  pageUrl = page.url();

  for (const frame of page.frames()) {
    let bodyText = "";
    try {
      bodyText = await Promise.race([
        frame.locator("body").innerText({ timeout: 1500 }),
        new Promise(resolve => setTimeout(() => resolve("[body timeout]"), 1600))
      ]);
      bodyText = String(bodyText).slice(0, 5000);
    } catch (e) {
      bodyText = "[body text unavailable: " + String(e) + "]";
    }
    frames.push({ url: frame.url(), name: frame.name(), bodyText });
  }
} catch (e) {
  errors.push({ stage: "browser-setup-or-probe", error: String(e) });
} finally {
  if (browser) await Promise.race([browser.close().catch(() => {}), new Promise(resolve => setTimeout(resolve, 3000))]);
}

const report = {
  startedAt,
  finishedAt: new Date().toISOString(),
  sourceUrl: url,
  navigationError,
  pageTitle,
  pageUrl,
  frameCount: frames.length,
  frames,
  relevantNetworkEvents: events,
  errors
};
await fs.writeFile(outDir + "/cme-fedwatch-probe.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify({
  sourceUrl: url,
  pageTitle,
  pageUrl,
  frameCount: frames.length,
  frames: frames.map(f => ({ url: f.url, name: f.name, textLength: f.bodyText.length, containsProbability: /probability|probabilities|機率/i.test(f.bodyText) })),
  relevantNetworkEventCount: events.length,
  errorCount: errors.length,
  navigationError
}, null, 2));
