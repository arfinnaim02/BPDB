"use client";
import {StudioPlot} from './studio-charts';
import {comparisonKeys,comparisonNames} from '../lib/model-comparison';
import type {FinalEvaluation} from '../lib/final-evaluation';
export function ModelEvidenceCharts({report,compact=false}:{report:FinalEvaluation;compact?:boolean}){
 const names=comparisonKeys.map(k=>k==='ridge'?'Ridge':k==='autoregression'?'OLS · primary':comparisonNames[k]);
 const scores=comparisonKeys.map(k=>report.scores.find(s=>s.model===k)!.common_dates);
 const grid={left:20,right:25,top:45,bottom:25,containLabel:true};
 const error={tooltip:{trigger:'axis',renderMode:'richText'},legend:{top:5},grid,xAxis:{type:'value',name:'million kWh',nameLocation:'middle',nameGap:25},yAxis:{type:'category',inverse:true,data:names},series:[{name:'MAE',type:'bar',data:scores.map(x=>x.mae),barMaxWidth:14},{name:'RMSE',type:'bar',data:scores.map(x=>x.rmse),barMaxWidth:14}]};
 const bias={tooltip:{trigger:'axis',renderMode:'richText'},grid,xAxis:{type:'value',name:'million kWh',nameLocation:'middle',nameGap:25},yAxis:{type:'category',inverse:true,data:names},series:[{name:'Mean signed error',type:'bar',data:scores.map(x=>({value:x.bias,itemStyle:{color:x.bias!=null&&x.bias<0?'#487ac4':'#087f76'}})),barMaxWidth:20,markLine:{silent:true,symbol:'none',data:[{xAxis:0}]}}]};
 return <div className={compact?'':'studio-grid'}><StudioPlot title="Forecast error comparison" description={`Frozen 2025 evaluation · ${report.checks.common_scored_dates} identical observed dates. Lower MAE and RMSE are better.`} option={error}/>{!compact&&<StudioPlot title="Prediction bias by model" description="Prediction minus observation. Negative values mean average underprediction; near-zero bias does not mean small errors." option={bias}/>}</div>;
}
