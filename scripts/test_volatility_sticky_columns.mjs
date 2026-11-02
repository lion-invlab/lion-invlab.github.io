import { chromium } from "playwright";
import fs from "node:fs";

const html = fs.readFileSync("volatility.html", "utf8");
const style = html.match(/<style>([\\s\\S]*?)<\\/style>/i)?.[1];
const wrapper = html.match(/<div class="tablewrap" id="constituentTableWrap">([\\s\\S]*?)<\\/div>/i);
const frozenHook = html.match(/\\(function initFrozenColumns\\(\\)\\{[\\s\\S]*?\\}\\)\\(\\);/)?.[0];
if (!style || !wrapper || !frozenHook) {
  throw new Error("Could not extract the real table wrapper, styles, and production frozen-column hook");
}
const table = wrapper[1];
if (!table.includes('class="constituent-table"') || !table.includes("<colgroup>")) {
  throw new Error("Could not extract the real constituent table and its column geometry");
}

const fixtureTable = table.replace('<tbody id="body"></tbody>', `<tbody id="body>${Array.from({length:12},(_,i)=>`<tr><td>${i+1}</td><td class="ticker">T${i}</td>${Array.from({length:10},()=>"<td>12.34%</td>").join("")}</tr>`).join("")}</tbody>`);
const browser = await chromium.launch({ headless: true });
const failures = [];
const widths = [320, 390, 430, 1280];

try {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 844 }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>${style}</style><div class="tablewrap" id="constituentTableWrap">${fixtureTable}</div><script>${frozenHook}<\\/script>`);
    const result = await page.evaluate(() => {
      const wrap = document.getElementById("constituentTableWrap");
      const table = document.querySelector("table.constituent-table");
      wrap.scrollLeft = 450;
      wrap.dispatchEvent(new Event("scroll"));
      const rect = (el) => { const r=el.getBoundingClientRect(); return {left:r.left,width:r.width,transform:getComputedStyle(el).transform}; };
      return {wrap:rect(wrap),rankHead:rect(table.querySelector("th:first-child")),tickerHead:rect(table.querySelector("th:nth-child(2)")),rankCell:rect(table.querySelector("tbody td:first-child")),tickerCell:rect(table.querySelector("tbody td:nth-child(2)")),scrollLeft:wrap.scrollLeft,scrollWidth:wrap.scrollWidth,clientWidth:wrap.clientWidth,hookPresent:getComputedStyle(table.querySelector("tbody td:first-child")).transform!=="none"};
    });
    const close = (a,b) => Math.abs(a-b) <= 1;
    if (!result.hookPresent) failures.push(`${width}px: production scroll hook did not apply a transform`);
    if (width <= 700 && (result.scrollLeft < 400 || result.scrollWidth <= result.clientWidth)) failures.push(`${width}px: horizontal scroll did not engage`);
    if (!close(result.rankHead.left,result.wrap.left) || !close(result.rankCell.left,result.wrap.left)) failures.push(`${width}px: rank column moved while scrolling`);
    if (!close(result.tickerHead.left,result.wrap.left+38) || !close(result.tickerCell.left,result.wrap.left+38)) failures.push(`${width}px: ticker column moved or has incorrect offset`);
    if (!close(result.tickerHead.width,88) || !close(result.tickerCell.width,88)) failures.push(`${width}px: ticker column width is not 88px`);
    console.log(JSON.stringify({width,...result}));
    await page.close();
  }
} finally {
  await browser.close();
}
if (failures.length) { console.error(failures.join("\\n")); process.exit(1); }
console.log("PASS: production hook keeps rank and ticker columns fixed at all tested viewport widths.");
