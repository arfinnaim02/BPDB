import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import zlib from 'node:zlib';
import * as echarts from 'echarts';
import {treatmentCharts,treatmentExports,treatmentPolicies} from '../src/lib/treatment.ts';
import type {TreatmentReport} from '../src/lib/treatment.ts';
const r=JSON.parse(zlib.gunzipSync(fs.readFileSync(process.env.BPDB_TREATMENT_ASSET||'../backend/app/data/treatment_study.json.gz')).toString()) as TreatmentReport;
test('treatment chart keeps abstention error unavailable and coverage numeric',()=>{
 const o=treatmentCharts(r.summaries,1) as any;
 assert.equal(o.coverage.series[0].data[0],0);
 assert.equal(o.error.series[0].data[0],null);
 assert.equal(o.error.series[1].data[0],null);
 assert.equal(o.error.series[1].data.length,5);
 assert.equal(r.short_gap_ranking[0].policy,'past_original_3');
 assert.equal(r.short_gap_ranking[0].n,77);
});
test('all real treatment chart configurations render at mobile and desktop widths',()=>{
 for(const length of [1,3,7,14,30])for(const width of [360,900]){
  for(const option of Object.values(treatmentCharts(r.summaries,length))){
   const chart=echarts.init(null,undefined,{renderer:'svg',ssr:true,width,height:420});
   try{chart.setOption(option);const svg=chart.renderToSVGString();assert.ok(svg.startsWith('<svg'));assert.ok(!svg.includes('NaN'));assert.ok(svg.includes('<path')||svg.includes('<rect'));}
   finally{chart.dispose();}
  }
 }
});
test('methods and export kinds are bounded and the endpoint requires authentication',()=>{
 assert.equal(treatmentPolicies.length,5);assert.equal(treatmentExports.length,7);
 assert.ok(treatmentExports.includes('input_candidates'));
 const route=fs.readFileSync('src/app/api/treatment-study/route.ts','utf8');
 assert.ok(route.indexOf('isAuthenticated())')<route.indexOf('backendResponse('));
 assert.ok(route.includes('treatmentExports as readonly string[]'));
 assert.ok(route.includes("'Cache-Control':'no-store'"));
 const page=fs.readFileSync('src/app/quality/treatment/page.tsx','utf8');
 assert.ok(page.includes('await requireSession()'));
 assert.ok(page.includes('provisional'));
 assert.ok(page.includes('not been adopted'));
});
