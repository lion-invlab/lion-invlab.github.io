import { chromium } from "playwright";
import fs from "node:fs";

const html = fs.readFileSync("volatility.html", "utf8");
const style = html.match(/<style>([\s\S]*?)<\/style>/i)?.[1];
if (!style) throw new Error("Could not extract dashboard stylesheet");

const browser = await chromium.launch({ headless: true });
const failures = [];
const widths = [320, 390, 430, 1280];

try {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 844 }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>${style}</style>
      <div class="tablewrap" id="wrap"><table><thead><tr><th>#</th><th>代號</th><th>公司</th><th>產業</th><th>價格</th><th>90D</th><th>60D</th><th>30D</th><th>20D</th><th>90D報酬</th><th>最大回撤</th><th>20D/90D</th></tr></thead>
      <tbody>${Array.from({length:12}, (_,i)=>`<tr><td>${i+1}</td><td class="ticker">T${i}</td>${Array.from({length:10},()=>"<td>12.34%</td>").join("")}</tr>`).join("")}</tbody></table></div>`);
    const result = await page.evaluate(() => {
      const wrap = document.querySelector("#wrap");
      wrap.scrollLeft = 450;
      const rect = (el) => { const r=el.getBoundingClientRect(); return {left:r.left,width:r.width,position:getComputedStyle(el).position}; };
      return {wrap:rect(wrap),rankHead:rect(document.querySelector("th:first-child")),tickerHead:rect(document.querySelector("th:nth-child(2)")),rankCell:rect(document.querySelector("tbody td:first-child")),tickerCell:rect(document.querySelector("tbody td:nth-child(2)")),scrollLeft:wrap.scrollLeft,scrollWidth:wrap.scrollWidth,clientWidth:wrap.clientWidth};
    });
    const close = (a,b) => Math.abs(a-b) <= 1;
    if (result.scrollLeft < 400 || result.scrollWidth <= result.clientWidth) failures.push(`${width}px: horizontal scroll did not engage`);
    if (!close(result.rankHead.left,result.wrap.left) || !close(result.rankCell.left,result.wrap.left)) failures.push(`${width}px: rank column moved while scrolling`);
    if (!close(result.tickerHead.left,result.wrap.left+38) || !close(result.tickerCell.left,result.wrap.left+38)) failures.push(`${width}px: ticker column moved or has incorrect offset`);
    if (!close(result.tickerHead.width,88) || !close(result.tickerCell.width,88)) failures.push(`${width}px: ticker column width is not 88px`);
    console.log(JSON.stringify({width,...result}));
    await page.close();
  }
} finally {
  await browser.close();
}
if (failures.length) { console.error(failures.join("\n")); process.exit(1); }
console.log("PASS: rank and ticker columns remain fixed at all tested viewport widths.");
