const { chromium } = require('playwright');
const { spawn } = require('node:child_process');

const targets = [
  { label: 'Monday master', file: 'index_母版_修正測試_週一.html' },
  { label: 'Tuesday-Friday master', file: 'index_母版_修正測試_週二至週五.html' },
];
const viewports = [
  { width: 390, height: 844, label: 'mobile-sized' },
  { width: 1365, height: 900, label: 'desktop-sized' },
];
const groups = [
  { root: '#news-scan', name: 'tac-news', tabs: 2 },
  { root: '#global-markets', name: 'tac-region', tabs: 3 },
  { root: '#industry-bonds-fx-commodities', name: 'tac-assets', tabs: 5 },
];

(async () => {
  const server = spawn('python', ['-m', 'http.server', '8765', '--bind', '127.0.0.1'], {
    cwd: process.cwd(), stdio: 'ignore'
  });
  let browser;
  try {
    await new Promise(resolve => setTimeout(resolve, 1200));
    browser = await chromium.launch({ headless: true });
    for (const target of targets) {
      for (const viewport of viewports) {
        const page = await browser.newPage({ viewport });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const encodedFile = encodeURIComponent(target.file);
        await page.goto(`http://127.0.0.1:8765/test-masters/${encodedFile}`, {
          waitUntil: 'domcontentloaded', timeout: 30000
        });

        // Dismiss the fund-date modal so it cannot intercept tab clicks.
        const fundNotice = page.locator('#tac-fund-notice');
        await fundNotice.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
        if (await fundNotice.isVisible()) {
          await page.locator('#tfn-close').click();
          await fundNotice.waitFor({ state: 'hidden', timeout: 3000 });
        }

        for (const group of groups) {
          for (let i = 0; i < group.tabs; i++) {
            await page.locator(`label[for="${group.name}-${i}"]`).click();
            const checked = await page.locator(`#${group.name}-${i}`).isChecked();
            const panel = page.locator(`${group.root} #${group.name}-panel-${i}`);
            const visible = await panel.evaluate(el => getComputedStyle(el).display !== 'none');
            if (!checked || !visible) {
              throw new Error(`${target.label}: tab failed at ${viewport.width}px: ${group.name}-${i}; checked=${checked}; visible=${visible}`);
            }
            for (let j = 0; j < group.tabs; j++) {
              if (j === i) continue;
              const other = page.locator(`${group.root} #${group.name}-panel-${j}`);
              if (await other.count()) {
                const otherVisible = await other.evaluate(el => getComputedStyle(el).display !== 'none');
                if (otherVisible) {
                  throw new Error(`${target.label}: multiple panels visible: ${group.name}-${i} and ${group.name}-${j} at ${viewport.width}px`);
                }
              }
            }
          }
        }
        if (errors.length) {
          throw new Error(`${target.label}: JavaScript errors at ${viewport.width}px: ${errors.join(' | ')}`);
        }
        console.log(`PASS ${target.label} | ${viewport.label} ${viewport.width}x${viewport.height}: all 10 tab states switch correctly; no page errors`);
        await page.close();
      }
    }
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
})().catch(error => { console.error(error); process.exit(1); });
