export type ResearchVariable = {
 metric:string;label:string;unit:string;period:string;fuel:string|null;
 parser_support:'legacy_and_modern'|'modern_layout_only';long_history_candidate:boolean;
 earliest_observed_date:string|null;latest_observed_date:string|null;
 full_history_observed_days:number;full_history_calendar_days:number;full_history_calendar_coverage_percent:number|null;
 modern_observed_days:number;modern_calendar_days:number;modern_missing_calendar_days:number;modern_calendar_coverage_percent:number|null;
 experimental_weekly_preparation_allowed:boolean;model_eligibility:string;
};
export type ResearchProfile = {
 id:string;label:string;purpose:string;start_date:string|null;end_date:string|null;boundary_status:string;
 metrics:string[];joint_complete_eligible_dates:null;eligibility_status:string;
};
export type ResearchProfilesReport = {
 rule_version:string;goal:string;generated_at:string;scope:string;profiles:ResearchProfile[];
 variables:ResearchVariable[];research_questions:{question:string;profile:string|null;status:string}[];
 rules:string[];limitations:string[];coverage_assessment_id:string;identity_scope:string;database_writes:number;models_fit:number;
};
const core = new Set(['day_peak_generation','evening_peak_generation','evening_peak_demand','maximum_generation','energy_generated']);
export function canPreviewWeeklyTreatment(metric:string):boolean{return core.has(metric);}
export function displayCoverage(value:number|null):string{return value===null?'Unavailable':value.toFixed(2)+'%';}
