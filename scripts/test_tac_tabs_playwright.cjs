const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const path = require('node:path');

(async () => {
  const server = spawn('python', ['-m', 'http.server', '8765', '--bind', '127.0.0.1'], {
    cwd: process.cwd(), stdio: 'ignore'
  });
  let browser;
  try {
    await new Promise(resolve => setTimeout(resolve, 1200));
    browser = await chromium.launch({ headless: true });
    for (const viewport of [{ width: 390, height: 844 }, { width: 1365, height: 900 }]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto('http://127.0.0.1:8765/index.html', { waitUntil: 'domcontentloaded' });

      const groups = [
        { root: '#news-scan', name: 'tac-news', tabs: 2 },
        { root: '#global-markets', name: 'tac-region', tabs: 3 },
        { root: '#industry-bonds-fx-commodities', name: 'tac-assets', tabs: 5 },
      ];
      for (const group of groups) {
        for (let i = 0; i < group.tabs; i++) {
          await page.locator(`label[for="${group.name}-${i}"]`).click();
          const checked = await page.locator(`#${group.name}-${i}`).isChecked();
          const panel = page.locator(`${group.root} #${group.name}-panel-${i}`);
          const visible = await panel.evaluate(el => getComputedStyle(el).display !== 'none');
          if (!checked || !visible) {
            throw new Error(`Tab interaction failed at ${viewport.width}px: ${group.name}-${i}; checked=${checked}; visible=${visible}`);
          }
          for (let j = 0; j < group.tabs; j++) {
            if (j === i) continue;
            const other = page.locator(`${group.root} #${group.name}-panel-${j}`);
            if (await other.count()) {
              const otherVisible = await other.evaluate(el => getComputedStyle(el).display !== 'none');
              if (otherVisible) throw new Error(`Multiple panels visible: ${group.name}-${i} and ${group.name}-${j} at ${viewport.width}px`);
            }
          }
        }
      }
      if (errors.length) throw new Error(`JavaScript errors at ${viewport.width}px: ${errors.join(' | ')}`);
      console.log(`PASS viewport=${viewport.width}x${viewport.height}: all 10 tab states switch correctly; no page errors`);
      await page.close();
    }
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
})().catch(error => { console.error(error); process.exit(1); });
