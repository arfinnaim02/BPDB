import type { ForecastHistory } from "./forecasts";
import type { ComparisonChartData } from "./comparison-types";
export const figures = {models:"Model accuracy comparison",daily:"Observed and predicted daily energy",monthly:"Monthly error comparison",scatter:"Observed versus predicted energy"} as const;
type Score = {model:string; common_dates:{n:number;mae:number|null;rmse:number|null;bias:number|null}};
export type ResearchReport = {
 report_id:string; generated_at:string; scope:string; source_ids:Record<string,string>; code_sha256:Record<string,string>;
 study:{training:string;validation:string;final_test:string;fit_rows:number;last_usable_fit_label:string;test_fit_cutoff:string;issue_scenario:string;input_policy:string;strict_historical_feature_days:number;feature_names:string[]};
 details:{common_diagnostics:{model:string;n:number;median_absolute_error:number;p90_absolute_error:number;p95_absolute_error:number;maximum_absolute_error:number;underprediction_days:number;overprediction_days:number;beats_lag2_days:number}[];monthly_coverage:{month:string;calendar_days:number;observed_days:number;ols_forecasts:number;ols_own_scored:number;common_scored:number}[]};
 effect:{common_dates:number;mae_reduction_percent:number}; current_inventory:{canonical_dates:number;earliest_operational_date:string;latest_operational_date:string};
 validation_scores:Score[];test_scores:Score[];test_predictions:{date:string;actual:number|null;autoregression:number|null}[];
 test_monthly:{month:string;scores:Score[]}[];prospective:ForecastHistory;limitations:string[];
};
export function reportExport(download: string, id: string, figure?: string): string | null {
 if(!/^[a-f0-9]{64}$/.test(id)||!["pdf","json","tables","methods","figure"].includes(download)) return null;
 if(download==="figure" && (!figure || !Object.hasOwn(figures,figure))) return null;
 const q=new URLSearchParams({download,expected_id:id}); if(download==="figure") q.set("figure",figure!);
 return q.toString();
}
export function reportDaily(r:ResearchReport):ComparisonChartData {
 return {labels:r.test_predictions.map(x=>x.date),unit:"million kWh",series:(["actual","autoregression"] as const).map(k=>({name:k==="actual"?"Observed energy":"Primary OLS",values:r.test_predictions.map(x=>x[k]==null?null:String(x[k])),notes:r.test_predictions.map(()=>"Frozen 2025 retrospective scenario; missing values remain gaps"),incomplete:r.test_predictions.map(x=>x[k]==null)}))};
}
export const modelNames:Record<string,string>={latest_report:"Latest report (lag 2)",weekly:"Same weekday (lag 7)",ridge:"Ridge",autoregression:"OLS (primary)",random_forest:"Random Forest",gradient_boosting:"Gradient Boosting"};
