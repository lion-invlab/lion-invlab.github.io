import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const out = "data/fedwatch-evidence";
await fs.mkdir(out, { recursive: true });
const cmeUrl = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool";
const quikstrikeUrl = "https://cmegroup-tools.quikstrike.net/User/QuikStrikeTools.aspx?company=&companyType=&jobRole=&userId=lwolf&viewitemid=IntegratedFedWatchTool";
const evidence = { captured_at_utc: new Date().toISOString(), attempts: [], errors: [] };
let browser;
try {
  browser = await chromium.launch({ headless: true, args: ["--disable-http2", "--no-sandbox", "--disable-dev-shm-usage"] });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
    locale: "en-US",
    timezoneId: "America/New_York",
    ignoreHTTPSErrors: true,
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
  });
  const targets = [
    { name: "cme-parent", url: cmeUrl },
    { name: "quikstrike-direct", url: quikstrikeUrl, referer: cmeUrl }
  ];
  for (const target of targets) {
    const page = await context.newPage();
    page.setDefaultNavigationTimeout(45000);
    const item = { name: target.name, requested_url: target.url, http_status: null, final_url: null, title: null, body_text: "", frames: [], errors: [] };
    page.on("requestfailed", request => {
      const failure = request.failure();
      if (/cmegroup|quikstrike/i.test(request.url())) item.errors.push("requestfailed " + request.url() + ": " + (failure?.errorText || "unknown"));
    });
    try {
      const response = await page.goto(target.url, { waitUntil: "domcontentloaded", ...(target.referer ? { referer: target.referer } : {}) });
      item.http_status = response?.status() ?? null;
      await page.waitForTimeout(12000);
      item.final_url = page.url();
      item.title = await page.title().catch(() => null);
      item.body_text = (await page.locator("body").innerText({ timeout: 10000 }).catch(e => "BODY_TEXT_ERROR: " + e.message)).slice(0, 25000);
      for (const frame of page.frames()) {
        const f = { url: frame.url(), name: frame.name(), title: null, text: "" };
        try { f.title = await frame.title(); f.text = (await frame.locator("body").innerText({ timeout: 7000 })).slice(0, 25000); }
        catch (e) { f.text = "FRAME_READ_ERROR: " + e.message; }
        item.frames.push(f);
      }
      await page.screenshot({ path: path.join(out, target.name + ".png"), fullPage: true, animations: "disabled" })
        .catch(async e => { item.errors.push("screenshot: " + e.message); });
    } catch (e) {
      item.errors.push("navigation/capture: " + (e?.stack || String(e)));
    }
    evidence.attempts.push(item);
    await page.close().catch(() => {});
  }
} catch (e) {
  evidence.errors.push("browser launch failed: " + (e?.stack || String(e)));
} finally {
  if (browser) await browser.close().catch(() => {});
  await fs.writeFile(path.join(out, "cme-fedwatch-rendered.txt"), JSON.stringify(evidence, null, 2), "utf8");
}
console.log(JSON.stringify({
  output: out,
  attempts: evidence.attempts.map(a => ({ name: a.name, http_status: a.http_status, final_url: a.final_url, title: a.title, body_chars: a.body_text.length, frames: a.frames.map(f => ({ url: f.url, title: f.title, text_chars: f.text.length })), errors: a.errors })),
  errors: evidence.errors
}, null, 2));
