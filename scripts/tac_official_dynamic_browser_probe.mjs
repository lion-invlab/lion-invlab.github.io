import { chromium } from 'playwright';
import fs from 'node:fs/promises';

const outDir = 'artifacts/tac-official-dynamic-probe';
await fs.mkdir(outDir, { recursive: true });
const result = {
  observed_at: new Date().toISOString(),
  cnn: { status: 'pending' },
  cme: { status: 'pending' }
};
const browser = await chromium.launch({ headless: true });
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

try {
  const cmeUrl = 'https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool';
  await page.goto(cmeUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(12000);
  result.cme.page_title = await page.title();
  result.cme.page_url = page.url();
  const frames = await page.locator('iframe').evaluateAll(nodes => nodes.map(n => ({
    src: n.src || n.getAttribute('src'),
    title: n.title || null,
    id: n.id || null
  })));
  result.cme.iframes = frames;
  const qFrame = frames.find(f => (f.src || '').includes('quikstrike')) || frames[0];
  if (qFrame?.src) {
    const framePage = await context.newPage();
    try {
      await framePage.goto(qFrame.src, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await framePage.waitForTimeout(15000);
      result.cme.tool_url = framePage.url();
      result.cme.tool_title = await framePage.title();
      result.cme.tool_text = (await framePage.locator('body').innerText({ timeout: 15000 })).slice(0, 12000);
      await framePage.screenshot({ path: outDir + '/cme-fedwatch-tool.png', fullPage: true });
      const text = result.cme.tool_text || '';
      result.cme.status = text.length > 300 ? 'tool_rendered_text' : 'tool_loaded_little_or_no_text';
      result.cme.meeting_date_candidates = [...new Set(text.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\s+\\d{1,2},?\\s+20\\d{2}/gi) || [])].slice(0, 20);
      result.cme.probability_mentions = (text.match(/\\b\\d{1,3}\\.\\d+%/g) || []).slice(0, 100);
    } catch (e) {
      result.cme.status = 'iframe_navigation_or_render_failed';
      result.cme.tool_error = String(e);
      try { await framePage.screenshot({ path: outDir + '/cme-fedwatch-error.png', fullPage: true }); } catch {}
    }
  } else {
    result.cme.status = 'no_iframe_found';
  }
  await page.screenshot({ path: outDir + '/cme-official-page.png', fullPage: true });
} catch (e) {
  result.cme.status = 'official_page_navigation_failed';
  result.cme.error = String(e);
  try { await page.screenshot({ path: outDir + '/cme-official-error.png', fullPage: true }); } catch {}
}

await fs.writeFile(outDir + '/probe-result.json', JSON.stringify(result, null, 2));
await browser.close();
console.log(JSON.stringify(result, null, 2));
