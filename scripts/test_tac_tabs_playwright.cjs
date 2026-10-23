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
const masterSignatures = {};
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

        // Validate that the summary no longer presents the stale 10/21 headline as current.
        const summaryHeadline = (await page.locator('.bluf h1').innerText()).trim();
        if (summaryHeadline !== '同日市場摘要待核實') {
          throw new Error(`${target.label}: stale or unexpected summary headline: ${summaryHeadline}`);
        }
        const summaryWarning = await page.locator('.bluf').innerText();
        if (!summaryWarning.includes('待同步核實') || !summaryWarning.includes('2026/10/22')) {
          throw new Error(`${target.label}: same-session verification warning/date is missing`);
        }
        const datedMarketPanel = await page.locator('#global-markets .tab-panel-meta').first().innerText();
        if (!/20\\d{2}\\/\\d{2}\\/\\d{2}/.test(datedMarketPanel)) {
          throw new Error(`${target.label}: market data source date label is missing`);
        }

        // Shared content should stay aligned between Monday and Tue-Fri masters;
        // Monday's two additional "last week" sections are intentionally excluded.
        const signature = {
          headline: summaryHeadline,
          warning: summaryWarning,
          weeklyCalendar: (await page.locator('#calendar .title').innerText()).trim(),
          weeklyEarnings: (await page.locator('#earnings .title').innerText()).trim(),
          tabLabels: await page.locator('.tac-tabset .tac-tab-nav label').allInnerTexts(),
          sourceDate: datedMarketPanel.trim()
        };
        const viewportSignature = JSON.stringify(signature);
        if (!masterSignatures[target.label]) masterSignatures[target.label] = viewportSignature;
        else if (masterSignatures[target.label] !== viewportSignature) {
          throw new Error(`${target.label}: shared content/date labels differ by viewport size`);
        }

        // Check page-level horizontal overflow. Horizontal navigation and explicitly
        // scrollable calendar tables are intentional and excluded from the document width.
        const overflow = await page.evaluate(() => ({
          viewport: document.documentElement.clientWidth,
          document: document.documentElement.scrollWidth,
          offenders: [...document.querySelectorAll('body *')]
            .filter(el => {
              if (el.closest('.nav, .event-table-wrap')) return false;
              const r = el.getBoundingClientRect();
              const style = getComputedStyle(el);
              return style.position !== 'fixed' && r.width > 0 &&
                (r.right > document.documentElement.clientWidth + 2 || r.left < -2) &&
                style.overflowX !== 'auto' && style.overflowX !== 'scroll';
            })
            .slice(0, 8)
            .map(el => ({tag: el.tagName, id: el.id, className: String(el.className).slice(0, 80),
              left: Math.round(el.getBoundingClientRect().left), right: Math.round(el.getBoundingClientRect().right)}))
        }));
        if (overflow.document > overflow.viewport + 2 || overflow.offenders.length) {
          throw new Error(`${target.label}: horizontal overflow at ${viewport.width}px: ${JSON.stringify(overflow)}`);
        }

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
    const mondaySignature = masterSignatures['Monday master'];
    const weekdaySignature = masterSignatures['Tuesday-Friday master'];
    if (mondaySignature !== weekdaySignature) {
      throw new Error('Monday and Tue-Fri masters have diverged in shared summary, weekly calendar/earnings dates, tab labels, or market source-date labels');
    }
    console.log('PASS shared master sync: summary warnings, weekly calendar/earnings labels, tab labels, and market source-date labels match');
  } finally {
    if (browser) await browser.close();
    server.kill('SIGTERM');
  }
})().catch(error => { console.error(error); process.exit(1); });
