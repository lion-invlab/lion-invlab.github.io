import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const out = "data/fedwatch-evidence";
await fs.mkdir(out, { recursive: true });
const evidence = {
  captured_at_utc: new Date().toISOString(),
  target: "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
  title: null,
  final_url: null,
  main_text: "",
  frames: [],
  errors: []
};
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
    locale: "en-US",
    timezoneId: "America/New_York",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
  });
  const page = await context.newPage();
  page.setDefaultNavigationTimeout(60000);
  page.on("requestfailed", request => {
    const failure = request.failure();
    if (/cmegroup|quikstrike/i.test(request.url())) evidence.errors.push("requestfailed " + request.url() + ": " + (failure?.errorText || "unknown"));
  });
  const response = await page.goto(evidence.target, { waitUntil: "domcontentloaded" });
  evidence.http_status = response?.status() ?? null;
  await page.waitForTimeout(15000);
  evidence.title = await page.title().catch(() => null);
  evidence.final_url = page.url();
  evidence.main_text = (await page.locator("body").innerText({ timeout: 10000 }).catch(e => "BODY_TEXT_ERROR: " + e.message)).slice(0, 20000);
  for (const frame of page.frames()) {
    const item = { url: frame.url(), name: frame.name(), title: null, text: "" };
    try {
      item.title = await frame.title();
      item.text = (await frame.locator("body").innerText({ timeout: 8000 })).slice(0, 30000);
    } catch (e) {
      item.text = "FRAME_READ_ERROR: " + e.message;
    }
    evidence.frames.push(item);
  }
  await page.screenshot({ path: path.join(out, "cme-fedwatch.png"), fullPage: true, animations: "disabled" }).catch(async e => {
    evidence.errors.push("screenshot: " + e.message);
    await page.screenshot({ path: path.join(out, "cme-fedwatch.png"), fullPage: false }).catch(e2 => evidence.errors.push("viewport screenshot: " + e2.message));
  });
  await context.close();
} catch (e) {
  evidence.errors.push("browser capture failed: " + (e?.stack || String(e)));
} finally {
  if (browser) await browser.close().catch(() => {});
  await fs.writeFile(path.join(out, "cme-fedwatch-rendered.txt"), JSON.stringify(evidence, null, 2), "utf8");
}
console.log(JSON.stringify({
  output: out,
  http_status: evidence.http_status ?? null,
  title: evidence.title,
  final_url: evidence.final_url,
  frames: evidence.frames.map(f => ({ url: f.url, title: f.title, text_chars: f.text.length })),
  errors: evidence.errors
}, null, 2));
