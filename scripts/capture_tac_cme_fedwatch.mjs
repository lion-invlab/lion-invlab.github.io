#!/usr/bin/env node
/**
 * Capture the public CME FedWatch page and its embedded QuikStrike iframe.
 * This is an audit probe only; it does not assign probabilities unless the
 * visible CME widget content is successfully captured and parsed.
 */
import fs from "node:fs";
import { chromium } from "playwright";

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : null;
}
const output = arg("--output") || "/tmp/tac-cme-fedwatch-iframe.html";
const textOutput = arg("--text-output") || "/tmp/tac-cme-fedwatch-iframe.txt";
const jsonOutput = arg("--json-output") || "/tmp/tac-cme-fedwatch-capture.json";
const pageUrl = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html";
const capturedAt = new Date().toISOString();
const responses = [];
const consoleErrors = [];
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    locale: "en-US",
    timezoneId: "Asia/Taipei",
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
  });
  page.on("response", response => {
    const url = response.url();
    if (/cmegroup-tools|quikstrike|fedwatch|probab/i.test(url)) {
      responses.push({ url, status: response.status(), content_type: response.headers()["content-type"] || null });
    }
  });
  page.on("console", message => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  let pageStatus = null;
  let pageError = null;
  let frameUrl = null;
  let frameTitle = null;
  let frameHtml = "";
  let bodyText = "";
  let status = "pending_verification";
  try {
    const response = await page.goto(pageUrl, { waitUntil: "domcontentloaded", timeout: 90000 });
    pageStatus = response?.status() ?? null;
    if (!response || !response.ok()) throw new Error(`CME page HTTP ${pageStatus ?? "no response"}`);
    await page.waitForTimeout(18000);
    const frames = page.frames();
    const candidates = frames.filter(frame => /cmegroup-tools\.quikstrike\.net/i.test(frame.url()));
    const frame = candidates.find(candidate => /IntegratedFedWatchTool/i.test(candidate.url())) || candidates[0] || null;
    if (!frame) throw new Error("CME FedWatch QuikStrike iframe was not found");
    frameUrl = frame.url();
    await frame.waitForSelector("body", { timeout: 30000 });
    await page.waitForTimeout(5000);
    frameTitle = await frame.title();
    bodyText = await frame.locator("body").innerText({ timeout: 20000 });
    frameHtml = await frame.content();
    if (/Access to QuikStrike has been denied|problem loading this content|ErrorPage/i.test(bodyText + " " + frameUrl)) {
      throw new Error("QuikStrike iframe returned an access/referrer error");
    }
    if (/(FedWatch|Target Rate|Probability|Meeting Date)/i.test(bodyText) && /%/.test(bodyText)) {
      status = "captured_for_review";
    } else {
      throw new Error("iframe loaded but no recognizable probability table was found");
    }
  } catch (error) {
    pageError = error.message;
    if (!frameHtml) {
      try { frameHtml = await page.content(); } catch {}
    }
  }

  fs.writeFileSync(output, frameHtml || "<!-- CME FedWatch iframe HTML unavailable -->", "utf8");
  fs.writeFileSync(textOutput, bodyText || pageError || "CME FedWatch iframe text unavailable", "utf8");
  const result = {
    report_date: "2026-11-02",
    trading_date: "2026-10-30",
    page_url: pageUrl,
    page_status: pageStatus,
    iframe_url: frameUrl,
    iframe_title: frameTitle,
    status,
    captured_at: capturedAt,
    body_text: bodyText,
    network_responses: responses,
    console_errors: consoleErrors.slice(0, 30),
    error: pageError,
    html_output: output,
    text_output: textOutput
  };
  fs.writeFileSync(jsonOutput, JSON.stringify(result, null, 2) + "\n", "utf8");
  console.log(JSON.stringify({
    status,
    page_status: pageStatus,
    iframe_url: frameUrl,
    iframe_title: frameTitle,
    response_count: responses.length,
    body_text_preview: bodyText.slice(0, 1600),
    error: pageError,
    outputs: [output, textOutput, jsonOutput]
  }, null, 2));
} finally {
  await browser.close();
}
