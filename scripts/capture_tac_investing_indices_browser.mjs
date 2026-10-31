#!/usr/bin/env node
/**
 * Browser-based Investing.com HK capture for TAC.
 * Reads rendered page text/DOM with Chromium; no screenshots or OCR.
 * Opens overview first, then extracts the exact requested historical row.
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ITEMS = {
  dow: ["us-30", "DJI", "道瓊"], sp500: ["us-spx-500", "SPX", "標普500"],
  nasdaq_composite: ["nasdaq-composite", "IXIC", "Nasdaq Composite"],
  russell_2000: ["smallcap-2000", "RUT", "Russell 2000"],
  sox: ["phlx-semiconductor", "SOX", "費城半導體"],
  hang_seng: ["hang-sen-40", "HSI", "恒生"],
  shanghai_composite: ["shanghai-composite", "SSEC", "上證"],
  shenzhen_component: ["szse-component", "SZI", "深證成指"],
  nikkei_225: ["japan-ni225", "N225", "日經225"], kospi: ["kospi", "KS11", "KOSPI"],
  twse: ["taiwan-weighted", "TWII", "台灣加權"],
  singapore_sti: ["singapore-straits-time", "STI", "新加坡STI"],
  asx_200: ["aus-200", "AXJO", "澳洲ASX200"], ftse_100: ["uk-100", "FTSE", "FTSE100"],
  dax: ["germany-30", "GDAXI", "DAX"], cac_40: ["france-40", "FCHI", "CAC40"],
  stoxx_europe_600: ["stoxx-600", "STOXX", "STOXX600"],
};
function parseNumber(s) {
  const n = Number(String(s).replace(/,/g, "").replace(/%/g, "").replace(/[−－]/g, "-").replace(/[＋]/g, "+").trim());
  if (!Number.isFinite(n)) throw new Error("invalid numeric cell: " + s);
  return n;
}
function chineseDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${y}年${Number(m)}月${Number(d)}日`;
}
function parseHistoryCells(cells, dateText) {
  if (!cells || cells.length < 6 || !cells[0].includes(dateText)) return null;
  return { close: parseNumber(cells[1]), change: parseNumber(cells[5]) };
}
function selfTest() {
  const p = parseHistoryCells(["2026年10月30日", "51,770.31", "52,383.90", "52,383.90", "51,563.76", "-1.09%"], "2026年10月30日");
  if (!p || p.close !== 51770.31 || p.change !== -1.09) throw new Error("fixture parse failed");
  if (parseHistoryCells(["2026年10月29日", "1", "1", "1", "1", "0%"], "2026年10月30日") !== null) throw new Error("date mismatch accepted");
  console.log("PASS: exact date row parser; PASS: numeric normalization; PASS: date mismatch rejected");
}
async function captureOne(page, key, cfg, tradingDate, observedAt) {
  const [slug, ticker, label] = cfg;
  const base = `https://hk.investing.com/indices/${slug}`;
  const historyUrl = `${base}-historical-data`;
  const overview = await page.goto(base, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (!overview || !overview.ok()) throw new Error(`overview HTTP ${overview?.status()}`);
  await page.locator("h1").first().waitFor({ timeout: 20000 });
  const heading = (await page.locator("h1").first().innerText()).trim();
  if (!heading.toLowerCase().includes(ticker.toLowerCase())) throw new Error(`identity mismatch: ${heading} != ${ticker}`);
  const body = (await page.locator("body").innerText()).split("\n").map(x => x.trim()).filter(Boolean);
  const at = body.findIndex(x => x.includes(heading));
  const overviewContext = body.slice(Math.max(0, at), Math.max(0, at) + 14).join(" | ");

  const hist = await page.goto(historyUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (!hist || !hist.ok()) throw new Error(`history HTTP ${hist?.status()}`);
  const histHeading = (await page.locator("h1").first().innerText()).trim();
  if (!histHeading.toLowerCase().includes(ticker.toLowerCase())) throw new Error(`history identity mismatch: ${histHeading}`);
  const target = chineseDate(tradingDate);
  const rows = await page.locator("table tr").all();
  let found = null;
  for (const row of rows) {
    const cells = (await row.locator("td").allInnerTexts()).map(x => x.trim());
    found = parseHistoryCells(cells, target);
    if (found) break;
  }
  if (!found) throw new Error(`exact row not found: ${target}`);
  return {
    value: found.close, unit: "index_point", change: found.change, change_unit: "percent",
    status: "verified",
    source: { name: "Investing.com 香港站", url: historyUrl, observed_at: observedAt,
      data_date: tradingDate, quote_type: "investing_com_hk_historical_close_pct_change",
      instrument: `${label} (${ticker})` },
    fallback_used: false, fallback_reason: null,
    notes: `先讀取商品綜觀頁確認標的，再讀取歷史數據表指定日期收市價及升跌幅。綜觀頁摘要：${overviewContext.slice(0, 500)}`,
  };
}
async function main() {
  if (process.argv.includes("--self-test")) return selfTest();
  const args = {};
  for (let i = 2; i < process.argv.length; i++) if (process.argv[i].startsWith("--")) args[process.argv[i].slice(2)] = process.argv[++i];
  const tradingDate = args["trading-date"], reportDate = args["report-date"], output = args.output;
  if (!tradingDate || !reportDate || !output) throw new Error("required: --trading-date YYYY-MM-DD --report-date YYYY-MM-DD --output path");
  const observedAt = new Date().toISOString(), records = {}, errors = {};
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ locale: "zh-HK", timezoneId: "Asia/Taipei" });
  const page = await context.newPage();
  try {
    for (const [key, cfg] of Object.entries(ITEMS)) {
      try {
        records[key] = await captureOne(page, key, cfg, tradingDate, observedAt);
        console.log(`VERIFIED ${key}: ${records[key].value} (${records[key].change}%)`);
      } catch (e) {
        errors[key] = String(e);
        records[key] = { value: null, unit: "index_point", change: null, change_unit: "percent",
          status: "pending_verification", source: null, fallback_used: false, fallback_reason: null,
          notes: `瀏覽器擷取失敗，未沿用舊值：${String(e)}` };
        console.log(`PENDING ${key}: ${String(e)}`);
      }
    }
  } finally { await browser.close(); }
  const fragment = { fragment_schema_version: 1, dataset: "tac_global_indices",
    report_date: reportDate, trading_date: tradingDate, fetched_at: observedAt,
    source_priority: "Investing.com Hong Kong rendered overview + exact historical row",
    global_indices: records, errors };
  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(fragment, null, 2) + "\n");
  const verified = Object.values(records).filter(x => x.status === "verified").length;
  console.log(`RESULT ${verified}/17 verified; ${17-verified}/17 pending. Saved ${output}`);
  if (verified !== 17) process.exitCode = 2;
}
main().catch(e => { console.error("FAIL:", e); process.exit(1); });
