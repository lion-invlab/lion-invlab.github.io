import { chromium } from 'playwright';
import fs from 'node:fs/promises';

const outDir = 'artifacts/cme-language-page-probe';
await fs.mkdir(outDir, { recursive: true });
const targets = [
  { key: 'zh-t', url: 'https://www.cmegroup.com/cn-t/markets/interest-rates/cme-fedwatch-tool.html' },
  { key: 'en', url: 'https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool' }
];
const browser = await chromium.launch({ headless: true, args: ['--disable-http2'] });
const context = await browser.newContext({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 1, locale: 'zh-TW', timezoneId: 'Asia/Taipei' });
const results = [];
for (const target of targets) {
  const page = await context.newPage();
  const item = { key: target.key, requested_url: target.url, observed_at: new Date().toISOString(), responses: [], console_errors: [], page_status: 'pending', iframe_status: 'not_found' };
  page.on('response', response => { if (/cmegroup|quikstrike/i.test(response.url())) item.responses.push({ status: response.status(), url: response.url() }); });
  page.on('console', message => { if (message.type() === 'error') item.console_errors.push(message.text().slice(0, 500)); });
  page.on('pageerror', error => item.console_errors.push(String(error).slice(0, 500)));
  try {
    const response = await page.goto(target.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    item.main_document_status = response?.status() ?? null;
    await page.waitForTimeout(20000);
    item.final_url = page.url();
    item.title = await page.title();
    item.page_text = (await page.locator('body').innerText({ timeout: 15000 })).slice(0, 10000);
    item.iframes = await page.locator('iframe').evaluateAll(nodes => nodes.map(frame => ({ src: frame.src || frame.getAttribute('src'), title: frame.title || null, width: frame.width || null, height: frame.height || null })));
    item.page_status = response?.ok() ? 'loaded' : 'http_error_or_redirect';
    await page.screenshot({ path: outDir + '/' + target.key + '-full-page.png', fullPage: true, animations: 'disabled' });
    const frames = page.frames().filter(frame => /quikstrike/i.test(frame.url()));
    item.quikstrike_frames = [];
    for (const frame of frames) {
      const frameResult = { url: frame.url(), name: frame.name() };
      try {
        frameResult.title = await frame.title();
        frameResult.text = (await frame.locator('body').innerText({ timeout: 12000 })).slice(0, 16000);
        frameResult.text_length = frameResult.text.length;
        frameResult.percentages = (frameResult.text.match(/\b\d{1,3}(?:\.\d+)?%/g) || []).slice(0, 120);
        frameResult.meeting_dates = [...new Set(frameResult.text.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2}/gi) || [])].slice(0, 30);
        item.iframe_status = frameResult.text_length > 300 ? 'frame_has_content' : 'frame_empty_or_error';
      } catch (error) { frameResult.error = String(error); item.iframe_status = 'frame_read_failed'; }
      item.quikstrike_frames.push(frameResult);
    }
    if (item.iframes.length && item.quikstrike_frames.length === 0) item.iframe_status = 'iframe_element_present_but_no_quikstrike_frame';
    item.probability_table_detected = item.quikstrike_frames.some(frame => (frame.percentages?.length || 0) >= 3 && (frame.text || '').length > 500);
  } catch (error) {
    item.page_status = 'navigation_failed'; item.error = String(error);
    try { await page.screenshot({ path: outDir + '/' + target.key + '-error.png', fullPage: true }); } catch {}
  }
  results.push(item); await page.close();
}
await fs.writeFile(outDir + '/result.json', JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2));
await browser.close();
console.log(JSON.stringify(results.map(item => ({ key: item.key, main_document_status: item.main_document_status, page_status: item.page_status, iframe_status: item.iframe_status, iframe_count: item.iframes?.length || 0, quikstrike_frame_count: item.quikstrike_frames?.length || 0, probability_table_detected: item.probability_table_detected || false, responses: item.responses })), null, 2));