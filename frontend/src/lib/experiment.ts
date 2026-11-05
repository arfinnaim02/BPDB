import type { ComparisonChartData } from "./comparison-types";
export type Score = { n: number; mae: number | null; rmse: number | null; bias: number | null };
export type Prediction = { date: string; actual: number | null; original_actual: string | null;
  latest_report: number | null; weekly: number | null; ridge: number | null;
  latest_donor: string | null; replaced_inputs: number | null; unknown_availability_inputs: number | null };
export type Experiment = {
  experiment_id: string; snapshot_id: string; selected: { policy: string; alpha: number; mae: number };
  protocol: { start: string; training_end: string; validation_end: string; reserved_test_end: string;
    forecast_issue: string; reporting_scenario: string; features: string[] };
  coverage: Record<string, { calendar: number; observed: number; eligible: number; held: number }>;
  validation: { model: "latest_report" | "weekly" | "ridge"; calendar_forecasts: number;
    own_dates: Score; common_dates: Score }[];
  predictions: Prediction[]; training_cv: { policy: string; alpha: number; mae: number; rmse: number; n: number }[];
  folds: { start: string; end: string; common_dates: number; latest_fit_label: string }[];
  masking: { block_days: number; windows: number; policy: string; masked_days: number; filled_days: number;
    coverage_percent: number; conditional: Score; common: Score }[];
  model: { rows: number; last_label: string; feature_names: string[]; coefficients: number[] };
  strict_availability_feature_days: number; test_report: Record<string, boolean | number>;
  reserved_test: { status: string; metrics: null; predictions: null }; limitations: string[];
  full_history_readiness: { metrics: { metric: string; label: string; non_null_dates: number;
    earliest_value_date: string | null; latest_value_date: string | null }[] } | null;
};
export const modelNames = { latest_report: "Latest report · lag 2", weekly: "Same weekday · lag 7", ridge: "Ridge regression" };
export const policyNames: Record<string, string> = { complete: "Complete original inputs",
  past_original_3: "Previous original · at most 3 days", seasonal_original_7: "Original donor · 7 days earlier" };
export const experimentExports = ["predictions", "selection", "model", "report", "test_report"] as const;
export function experimentChart(rows: Prediction[]): ComparisonChartData {
  return { labels: rows.map(r => r.date), unit: "million kWh", series: [
    { name: "Observed validation target", values: rows.map(r => r.actual == null ? null : String(r.actual)),
      notes: rows.map(r => r.actual == null ? "Missing/held target · never filled" : "Original observed target"),
      incomplete: rows.map(r => r.actual == null) },
    ...(["latest_report", "weekly", "ridge"] as const).map(key => ({ name: modelNames[key],
      values: rows.map(r => r[key] == null ? null : String(r[key])),
      notes: rows.map(r => r[key] == null ? "Forecast unavailable" : r.actual == null ? "Forecast unscored: target unavailable" : "Retrospective reporting-delay scenario"),
      incomplete: rows.map(r => r[key] == null || r.actual == null) })),
  ] };
}
export function monthlyErrors(rows: Prediction[]) {
  return Array.from(new Set(rows.map(r => r.date.slice(0, 7)))).sort().map(month => {
    const matched = rows.filter(r => r.date.startsWith(month) && r.actual != null &&
      r.latest_report != null && r.weekly != null && r.ridge != null);
    const mae = (key: "latest_report" | "weekly" | "ridge") => matched.length
      ? matched.reduce((s, r) => s + Math.abs(r[key]! - r.actual!), 0) / matched.length : null;
    return { month, n: matched.length, latest_report: mae("latest_report"), weekly: mae("weekly"), ridge: mae("ridge") };
  });
}
