import test from 'node:test';
import assert from 'node:assert/strict';
import * as echarts from 'echarts';
import {studioOptions} from '../src/lib/studio-options.ts';
import type {AnalyticsReport} from '../src/lib/types';
const fixture={label:'Energy generated',unit:'million_kWh',points:Array.from({length:35},(_,i)=>{const d=new Date('2024-02-01T00:00:00Z');d.setUTCDate(d.getUTCDate()+i);return {start_date:d.toISOString().slice(0,10),value:i===2?null:String(100+i)}})} as AnalyticsReport;
test('all six actual studio configurations render as SVG at desktop and mobile widths',()=>{
 for(const width of [360,900])for(const [name,option] of Object.entries(studioOptions(fixture))){
  const chart=echarts.init(null,undefined,{renderer:'svg',ssr:true,width,height:330});
  try{chart.setOption({animation:false,...option});const svg=chart.renderToSVGString();assert.ok(svg.startsWith('<svg'),name);assert.ok(svg.includes('<path')||svg.includes('<rect'),name);assert.ok(!svg.includes('NaN'),name);}finally{chart.dispose();}
 }
});
test('timeline options retain missing gaps and monthly profile excludes incomplete months',()=>{
 const o=studioOptions(fixture);assert.equal(o.trend.series[0].connectNulls,false);assert.equal(o.trend.series[0].data[2],'-');assert.ok(o.profile.series[0].data.every(v=>v==='-'));assert.equal(o.histogram.series[0].data.reduce((a,b)=>a+b,0),34);
});
