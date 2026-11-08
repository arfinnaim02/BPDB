import test from "node:test";
import assert from "node:assert/strict";
import { billion, monthlyCost, monthlyChart, predictionsCsv } from "../src/lib/monthly-cost.ts";
test("frozen issue preserves future actual as unknown and pre-outcome issuance",()=>{
 assert.equal(monthlyCost.future.target_month,"2026-12");
 assert.equal(monthlyCost.future.actual_bdt,null);
 assert.ok(monthlyCost.future.issued_at < "2026-12-01");
 assert.equal(monthlyCost.future.fit_rows,8);
 assert.equal(monthlyCost.future.forecasts_bdt.ridge,65062154697.578064);
});
test("chart preserves incomplete actuals and absent learned historical predictions",()=>{
 const c=monthlyChart();assert.equal(c.labels.length,22);
 assert.equal(c.series[0].values.filter(x=>x!==null).length,10);
 assert.ok(c.series[3].values.every(x=>x===null));
 assert.ok(c.series[4].values.every(x=>x===null));
 assert.equal(monthlyCost.shared_scored_months,0);
});
test("CSV separates actuals from predictions and retains unrounded numeric BDT",()=>{
 const c=predictionsCsv();assert.ok(c.startsWith('\uFEFF"Target month"'));
 assert.match(c,/"2026-12","","86248509438","86248509438","66581275459.35771","65062154697.578064","Issued future forecast"/);
 assert.equal(c.trim().split('\r\n').length,24);
 assert.equal(billion(null),"—");assert.equal(billion(65062154697.578064),"65.062");
});
