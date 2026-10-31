import { chromium } from 'playwright';
import fs from 'node:fs/promises';

const outDir = 'artifacts/tac-official-dynamic-probe';
await fs.mkdir(outDir, { recursive: true });
const result = {
  observed_at: new Date().toISOString(),
  cnn: { status: 'pending' },
};
const browser = await chromium.launch({ headless: true, args: ['--disable-http2'] });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  locale: 'en-US',
  timezoneId: 'America/New_York'
});
const page = await context.newPage();

try {
  const endpoint = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2021-02-01';
  const headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://www.cnn.com',
    'Referer': 'https://www.cnn.com/markets/fear-and-greed'
  };
  const response = await context.request.get(endpoint, { headers, timeout: 30000 });
  const body = await response.text();
  result.cnn.http_status = response.status();
  result.cnn.content_type = response.headers()['content-type'] || null;
  if (response.ok() && (response.headers()['content-type'] || '').includes('json')) {
    try {
      const json = JSON.parse(body);
      const series = json.fear_and_greed_historical?.data || [];
      result.cnn.status = series.length ? 'json_received' : 'json_received_empty_series';
      result.cnn.series_count = series.length;
      result.cnn.latest_record = series.length ? series[series.length - 1] : null;
      result.cnn.top_level_keys = Object.keys(json);
      await fs.writeFile(outDir + '/cnn-response.json', JSON.stringify(json, null, 2));
    } catch (e) {
      result.cnn.status = 'json_parse_failed';
      result.cnn.error = String(e);
    }
  } else {
    result.cnn.status = response.status() === 403 ? 'blocked_403' : 'http_not_ok';
    result.cnn.body_excerpt = body.slice(0, 1200);
  }
  try {
    await page.goto('https://www.cnn.com/markets/fear-and-greed', { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(8000);
    result.cnn.page_title = await page.title();
    result.cnn.page_url = page.url();
    result.cnn.page_text_excerpt = (await page.locator('body').innerText({ timeout: 10000 })).slice(0, 5000);
    await page.screenshot({ path: outDir + '/cnn-page.png', fullPage: true });
    result.cnn.browser_page = 'loaded';
  } catch (e) {
    result.cnn.browser_page = 'navigation_or_render_failed';
    result.cnn.browser_error = String(e);
    try { await page.screenshot({ path: outDir + '/cnn-page-error.png', fullPage: true }); } catch {}
  }
} catch (e) {
  result.cnn.status = 'request_failed';
  result.cnn.error = String(e);
}




await fs.writeFile(outDir + '/probe-result.json', JSON.stringify(result, null, 2));
await browser.close();
console.log(JSON.stringify(result, null, 2));
