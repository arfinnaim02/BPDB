export type ComparisonPeriod = {
  label: string; start_date: string; end_date: string; value: string | null;
  mean: string | null; minimum: string | null; maximum: string | null;
  observed_days: number; canonical_dates: number; expected_days: number;
  zero_days: number; coverage_percent: number | null; full_period_selected: boolean;
  complete_period: boolean;
};
export type MonthComparison = ComparisonPeriod & {
  mom_percent: string | null; mom_status: string; yoy_percent: string | null; yoy_status: string;
};
export type PairedPeriod = {
  label: string; start_date: string; end_date: string; paired_days: number;
  expected_days: number; coverage_percent: number | null; complete_period: boolean;
  generation_mean: string | null; demand_mean: string | null; difference_mean: string | null;
};
export type ComparisonReport = {
  generated_at: string; scope: string; metric: string; label: string; unit: string;
  aggregation: string; parser_support: string; start_date: string | null; end_date: string | null;
  canonical_dates: number; calendar_days: number; metric_observed_days: number;
  available_years: number[]; selected_years: number[]; monthly: MonthComparison[];
  annual: ComparisonPeriod[]; peak: "day" | "evening"; resolution: string;
  paired_days: number; paired_coverage_percent: number | null; paired_difference_mean: string | null;
  demand_above_generation_days: number; generation_above_demand_days: number; equal_days: number;
  paired_points: PairedPeriod[]; generation_energy_review_dates: number; review_rule_version: string;
  data_fingerprint: string; limitation: string;
};
export type ComparisonChartData = {
  labels: string[]; unit: string;
  series: { name: string; values: (string | null)[]; notes: string[]; incomplete: boolean[] }[];
};
