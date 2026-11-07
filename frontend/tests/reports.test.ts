import test from "node:test";
import assert from "node:assert/strict";
import {reportExport,reportDaily,figures} from "../src/lib/reports.ts";
import type {ResearchReport} from "../src/lib/reports.ts";
test("report exports allow only bounded kinds and exact snapshot identities",()=>{
 const id="a".repeat(64);for(const kind of ["pdf","json","tables","methods"])assert.ok(reportExport(kind,id));
 for(const figure of Object.keys(figures))assert.ok(reportExport("figure",id,figure));
 for(const [kind,key,figure] of [["html",id,""],["pdf","wrong",""],["figure",id,"../../secret"],["figure",id,"toString"]])assert.equal(reportExport(kind,key,figure),null);
});
test("daily report chart preserves missing values and exact stored values",()=>{
 const r={test_predictions:[{date:"2025-01-01",actual:null,autoregression:123.456789},{date:"2025-01-02",actual:0,autoregression:null}]} as ResearchReport;
 const c=reportDaily(r);assert.deepEqual(c.series[0].values,[null,"0"]);assert.deepEqual(c.series[1].values,["123.456789",null]);assert.deepEqual(c.series[0].incomplete,[true,false]);assert.equal(c.labels.length,2);
});
