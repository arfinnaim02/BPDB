import test from 'node:test';
import assert from 'node:assert/strict';
import * as echarts from 'echarts';
import {edaFilters,box,csvRows,edaPair} from '../src/lib/eda.ts';
import type {EdaReport,EdaStats} from '../src/lib/eda';
import {edaOptions} from '../src/lib/eda-options.ts';
const stats={observations:7,mean:'4',sample_stddev:'2',median:'4',q1:'2',q3:'6',whisker_low:'0',whisker_high:'8'} as EdaStats;
const fixture={variables:[{key:'a',label:'Energy',unit:'million_kWh',statistics:stats,lags:[{lag:1,n:5,r:.8,status:'available'}]},{key:'b',label:'Demand',unit:'MW',statistics:stats,lags:[]}],rows:Array.from({length:9},(_,i)=>({date:`2025-01-${String(i+1).padStart(2,'0')}`,a:i===3?null:String(i),b:i===5?null:String(i*2)})),relationships:[{x:'a',y:'a',n:8,pearson:1,spearman:1,change_n:6,change_pearson:1},{x:'a',y:'b',n:7,pearson:1,spearman:1,change_n:4,change_pearson:1},{x:'b',y:'b',n:8,pearson:1,spearman:1,change_n:6,change_pearson:1}]} as unknown as EdaReport;
test('EDA filters retain repeated variables, bound selections and reject invalid dates',()=>{
 const f=edaFilters({metric:['energy_generated','maximum_temperature'],start_date:'2024-01-01',end_date:'2025-12-31'});assert.equal(f.error,null);assert.deepEqual(f.query.getAll('metric'),['energy_generated','maximum_temperature']);
 for(const p of [{metric:['energy_generated','energy_generated']},{metric:['bad']},{metric:Array(9).fill('energy_generated')},{start_date:'2025-02-30'},{start_date:'2026-01-01',end_date:'2025-01-01'}])assert.ok(edaFilters(p).error);
});
test('boxplots preserve zero and unavailable groups, CSV escapes and blanks retain precision',()=>{
 assert.deepEqual(box([0,1,2,3,4]),[0,1,2,3,4]);assert.equal(box([]),null);const s=csvRows([['date','value'],['2025-01-01','123.123456'],['2025-01-02',null],['2025-01-03',0]]);assert.ok(s.includes('"123.123456"'));assert.ok(s.includes('"2025-01-02",""'));assert.ok(s.includes('"0"'));assert.equal(edaPair(fixture,'b','a')?.n,7);
});
test('all twelve real EDA chart configurations render SVG at desktop and mobile widths',()=>{
 const o=edaOptions(fixture,'a','a','b');for(const width of [360,900])for(const key of ['timeline','scatter','correlation','sample','boxes','histogram','monthly','weekday','lags','difference','availability','heat'] as const){const c=echarts.init(null,undefined,{renderer:'svg',ssr:true,width,height:430});try{c.setOption({animation:false,...o[key]});const svg=c.renderToSVGString();assert.ok(svg.startsWith('<svg'),key);assert.ok(!svg.includes('NaN'),key);}finally{c.dispose();}}
});
test('first differences and standardized comparisons do not cross calendar gaps',()=>{
 const o=edaOptions(fixture,'a','a','b');assert.equal(o.difference.series[0].data[3],'-');assert.equal(o.difference.series[0].data[4],'-');assert.equal(o.timeline.series[0].data[3],'-');assert.equal(o.histogram.series[0].data.reduce((a,b)=>a+b,0),8);
 const changes=edaOptions(fixture,'a','b','a','change_pearson');assert.equal(changes.sample.series[0].data[1][2],4);
});

test('empty and constant variables leave correlations undefined and charts render without NaN',()=>{
 const empty=structuredClone(fixture);empty.rows=fixture.rows.map(d=>({...d,a:null,b:'0'}));empty.variables=fixture.variables.map(v=>({...v,statistics:{...v.statistics,mean:'0',sample_stddev:'0'}}));empty.relationships=fixture.relationships.map(p=>({...p,pearson:null,spearman:null,change_pearson:null,n:p.x==='a'||p.y==='a'?0:9}));
 const o=edaOptions(empty,'a','a','b');assert.equal(o.correlation.series[0].data.length,0);for(const key of ['timeline','scatter','boxes','histogram','monthly','heat'] as const){const c=echarts.init(null,undefined,{renderer:'svg',ssr:true,width:600,height:400});try{c.setOption({animation:false,...o[key]});assert.ok(!c.renderToSVGString().includes('NaN'),key);}finally{c.dispose();}}
});
