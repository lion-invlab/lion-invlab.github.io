#!/usr/bin/env node
/** Offline source-selection contract tests. */
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "tac-fedwatch-test-"));
const script = path.resolve("scripts/select_tac_fedwatch_source.mjs");
const run = (cme, fallback) => {
 const c=path.join(dir,"cme.json"), f=path.join(dir,"fallback.json"), o=path.join(dir,"out.json");
 if(cme===null){try{fs.unlinkSync(c)}catch{}}else fs.writeFileSync(c,JSON.stringify(cme));
 if(fallback===null){try{fs.unlinkSync(f)}catch{}}else fs.writeFileSync(f,JSON.stringify(fallback));
 const r=spawnSync(process.execPath,[script,"--cme",c,"--fallback",f,"--output",o],{encoding:"utf8"});
 return {code:r.status,result:JSON.parse(fs.readFileSync(o,"utf8"))};
};
const fb={status:"captured_for_review",role:"fallback_only_not_CME",source_url:"https://www.investing.com/central-banks/fed-rate-monitor",observed_at:"2026-11-01T00:00:00.000Z",source_updated_at:["Oct 30, 2026 10:45 PM EDT"],validation:{is_fresh:true},meetings:[{meeting_date:"Dec 9, 2026",probabilities:[{target_rate:"3.50-3.75",probability:60},{target_rate:"3.75-4.00",probability:40}]}]};
const goodCme={status:"captured_for_review",page_url:"https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",captured_at:"2026-11-01T00:00:00.000Z",body_text:"FedWatch Target Rate Probability 60%"};
let r=run(goodCme,fb);assert.equal(r.result.selected_source,"CME FedWatch");
r=run({status:"pending_verification"},fb);assert.equal(r.result.selected_source,"Investing.com Fed Rate Monitor");assert.equal(r.result.meetings.length,1);
r=run(null,{...fb,validation:{is_fresh:false}});assert.equal(r.result.status,"pending_verification");
r=run(null,null);assert.equal(r.result.status,"pending_verification");
console.log("PASS: CME primary, live fallback, stale fallback rejection, and both-unavailable cases");
