import { chromium } from "playwright";
import fs from "node:fs";

const html=fs.readFileSync("volatility.html","utf8");
const style=html.match(/<style>([\s\S]*?)<\/style>/i)?.[1];
const wrapper=html.match(/<div class="tablewrap" id="constituentTableWrap">([\s\S]*?)<\/div>/i);
if(!style||!wrapper)throw new Error("Could not extract production wrapper and styles");
const table=wrapper[1];
if(!table.includes('class="constituent-table"')||!table.includes("<colgroup>"))throw new Error("Production table geometry missing");
if(html.includes("initFrozenColumns")||html.includes("--frozen-x"))throw new Error("Legacy scroll-transform implementation remains");
const rows=Array.from({length:40},(_,i)=>'<tr><td>'+(i+1)+'</td><td class="ticker">T'+i+'</td>'+Array.from({length:10},()=>"<td>12.34%</td>").join("")+"</tr>").join("");
const fixture=table.replace('<tbody id="body"></tbody>','<tbody id="body">'+rows+'</tbody>');
const browser=await chromium.launch({headless:true}),failures=[];
try{
 for(const width of [320,390,430,1280]){
  const page=await browser.newPage({viewport:{width,height:844},deviceScaleFactor:1});
  await page.setContent('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+style+'</style><div class="tablewrap" id="constituentTableWrap">'+fixture+'</div>');
  const r=await page.evaluate(()=>{
   const w=document.getElementById("constituentTableWrap"),t=document.querySelector("table.constituent-table");w.scrollLeft=450;w.scrollTop=300;
   const rect=e=>{const b=e.getBoundingClientRect(),s=getComputedStyle(e);return{left:b.left,width:b.width,position:s.position,stickyLeft:s.left}};
   const rh=t.querySelector("th:first-child"),th=t.querySelector("th:nth-child(2)");return{wrap:rect(w),rankHead:rect(rh),tickerHead:rect(th),rankHeadText:rh.textContent.trim(),tickerHeadText:th.textContent.trim(),rankCell:rect(t.querySelector("tbody td:first-child")),tickerCell:rect(t.querySelector("tbody td:nth-child(2)")),scrollLeft:w.scrollLeft,scrollTop:w.scrollTop,scrollHeight:w.scrollHeight,clientHeight:w.clientHeight,scrollWidth:w.scrollWidth,clientWidth:w.clientWidth};
  });
  const near=(a,b)=>Math.abs(a-b)<=1;
  if(width<=700&&(r.scrollLeft<400||r.scrollWidth<=r.clientWidth))failures.push(width+"px: horizontal scroll failed");
  if(!near(r.rankHead.left,r.wrap.left)||!near(r.rankCell.left,r.wrap.left))failures.push(width+"px: rank column moved");
  if(!near(r.tickerHead.left,r.wrap.left+38)||!near(r.tickerCell.left,r.wrap.left+38))failures.push(width+"px: ticker column moved or offset incorrect");
  for(const [n,c] of [["rank",r.rankCell],["ticker",r.tickerCell]])if(c.position!=="sticky")failures.push(width+"px: "+n+" is not sticky");
  if(!near(r.tickerCell.width,88))failures.push(width+"px: ticker width incorrect");
  if(r.rankHeadText!=="#"||r.tickerHeadText!=="代號")failures.push(width+"px: frozen header labels missing");
  if(width<=700&&r.scrollTop<200)failures.push(width+"px: vertical scroll did not engage");
  if(width<=700&&(!near(r.rankHead.left,r.wrap.left)||!near(r.rankHead.left,r.wrap.left+1)))failures.push(width+"px: rank header not aligned to scrollport after vertical scroll");
  if(width<=700&&(!near(r.rankHead.top,r.wrap.top+1)||!near(r.tickerHead.top,r.wrap.top+1)))failures.push(width+"px: frozen header row scrolled vertically out of view");
  if(Number(r.rankHead.position!=="sticky")||Number(r.tickerHead.position!=="sticky"))failures.push(width+"px: frozen header cells lost sticky positioning");
  if(Number(r.rankHead.stickyLeft!=="0px")||Number(r.tickerHead.stickyLeft!=="38px"))failures.push(width+"px: frozen header offsets incorrect");
  console.log(JSON.stringify({width,...r}));await page.close();
 }
}finally{await browser.close()}
if(failures.length){console.error(failures.join("\n"));process.exit(1)}
console.log("PASS: native sticky columns stay fixed at all tested viewport widths.");