import type {EChartsCoreOption} from 'echarts/core';
export const treatmentPolicies = ['observed_only','past_original_3','seasonal_original_7','weekday_median_28','past_median_365'] as const;
export const treatmentExports = ['summary','masked_trials','masked_windows','training_calendar','input_candidates','report','methods'] as const;
export type TreatmentPolicy = typeof treatmentPolicies[number];
export const treatmentNames:Record<TreatmentPolicy,string> = {
 observed_only:'Observed only',past_original_3:'Recent original (≤3 days)',seasonal_original_7:'Previous week',
 weekday_median_28:'Weekday median (28 days)',past_median_365:'Past-year median',
};
export type TreatmentScore={n:number;mae:number|null;rmse:number|null;bias:number|null};
export type TreatmentSummary={block_days:number;policy:TreatmentPolicy;windows:number;masked_days:number;filled_days:number;coverage_percent:number;known_time_fillable_days:number;conditional:TreatmentScore;common:TreatmentScore};
export type TreatmentReport={
 study_id:string;protocol:{version:string;start:string;end:string;metric:string;unit:string;seed:number;requested_windows_per_length:number;block_days:number[];snapshot_id:string;source_bundle_sha256:string;policies:Record<TreatmentPolicy,string>;timing:string;masks:string;selection:string;real_gap_candidates:string};
 summaries:TreatmentSummary[];short_gap_ranking:({policy:TreatmentPolicy}&TreatmentScore)[];provisional_candidate:TreatmentPolicy|null;
 checks:{training_days:number;eligible_originals:number;validation_test_rows_used:number;forecast_models_trained:number;database_writes:number;all_donors_strictly_past:boolean;all_masks_eligible_training_originals:boolean};
 register:{date:string;category:string;original_value:string;review_flags:string;version_id:string;source_id:string;source_sha256:string|null;recovery_status:string;action:string}[];
 actual_candidate_summary:Record<TreatmentPolicy,number>;limitations:string[];
};
export function treatmentCharts(rows:TreatmentSummary[], length:number):{coverage:EChartsCoreOption;error:EChartsCoreOption}{
 const own=rows.filter(r=>r.block_days===length);
 const base:EChartsCoreOption={animation:false,tooltip:{trigger:'axis',confine:true},grid:{left:12,right:35,top:55,bottom:42,containLabel:true},
 yAxis:{type:'category',data:own.map(r=>treatmentNames[r.policy]),axisLabel:{width:140,overflow:'truncate',fontSize:11}},aria:{enabled:true}};
 return {coverage:{...base,xAxis:{type:'value',name:'Filled (%)',nameLocation:'middle',nameGap:28,min:0,max:100},series:[{name:'Filled dates (%)',type:'bar',data:own.map(r=>r.coverage_percent),itemStyle:{color:'#087f76'}}]},
 error:{...base,legend:{top:0},xAxis:{type:'value',name:'MAE (million kWh)',nameLocation:'middle',nameGap:28},series:[
 {name:'Own filled dates',type:'bar',data:own.map(r=>r.conditional.mae)},
 {name:'Shared filled dates',type:'bar',data:own.map(r=>r.common.mae)},
 ]}};
}
