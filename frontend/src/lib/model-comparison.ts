import type { ComparisonChartData } from "./comparison-types";
import type { Score } from "./experiment";
export const comparisonKeys = ["latest_report", "weekly", "ridge", "autoregression", "random_forest", "gradient_boosting"] as const;
export type ModelKey = typeof comparisonKeys[number];
export const comparisonNames: Record<ModelKey, string> = {
  latest_report: "Latest report · lag 2", weekly: "Same weekday · lag 7", ridge: "Locked Ridge · Release 1",
  autoregression: "Autoregressive OLS", random_forest: "Random Forest", gradient_boosting: "Gradient Boosting",
};
export const comparisonExports = ["predictions", "selection", "models", "report", "test_report"] as const;
export type ModelPrediction = { date: string; actual: number | null; latest_donor: string | null; replaced_inputs: number | null } & Record<ModelKey, number | null>;
export type Configuration = Score & { family: ModelKey; id: string; parameters?: Record<string, number | string | boolean> };
export type ModelComparison = {
  experiment_id: string; snapshot_id: string; reference_experiment_id: string;
  protocol: { timing: string; issue: string; training_scoring: string; selection: string };
  coverage: Record<string, { calendar: number; observed: number; eligible: number; held: number }>;
  training_selected_finalist: ModelKey; training_ranking: Configuration[]; training_cv: Configuration[];
  selected: Record<string, Configuration>;
  folds: { start: string; end: string; common_dates: number; fits: { candidate: string; rows: number; last_label: string; cutoff: string }[] }[];
  validation: { model: ModelKey; calendar_forecasts: number; negative_forecasts: number; own_dates: Score; common_dates: Score }[];
  models: Record<string, { rows: number; last_label: string; cutoff: string; feature_importances: number[] | null; configuration: Configuration }>;
  predictions: ModelPrediction[]; feature_names: string[]; strict_availability_feature_days: number;
  checks: { same_frozen_input: boolean; no_test_labels_in_series: boolean; no_test_predictions: boolean;
    training_scoring_matches_release1: boolean; neon_writes: number; saved_model_max_difference: Record<string, number>;
    ridge_reference_max_difference: number; common_validation_days: number; validation_calendar_days: number };
  reserved_test: { status: string; metrics: null; predictions: null }; limitations: string[];
};
export function modelChart(rows: ModelPrediction[]): ComparisonChartData {
  return { labels: rows.map(r => r.date), unit: "million kWh", series: [
    { name: "Observed validation target", values: rows.map(r => r.actual == null ? null : String(r.actual)),
      notes: rows.map(r => r.actual == null ? "Missing/held target · never filled" : "Original observed target"), incomplete: rows.map(r => r.actual == null) },
    ...comparisonKeys.map(key => ({ name: comparisonNames[key], values: rows.map(r => r[key] == null ? null : String(r[key])),
      notes: rows.map(r => r[key] == null ? "Forecast unavailable" : r.actual == null ? "Unscored forecast · target unavailable" : "Retrospective reporting-delay assumption"),
      incomplete: rows.map(r => r[key] == null || r.actual == null) })),
  ] };
}
export function commonMonthlyErrors(rows: ModelPrediction[]) {
  return Array.from(new Set(rows.map(r => r.date.slice(0, 7)))).sort().map(month => {
    const matched = rows.filter(r => r.date.startsWith(month) && r.actual != null && comparisonKeys.every(k => r[k] != null));
    return { month, n: matched.length, scores: Object.fromEntries(comparisonKeys.map(k => [k, matched.length
      ? matched.reduce((sum, r) => sum + Math.abs(r[k]! - r.actual!), 0) / matched.length : null])) as Record<ModelKey, number | null> };
  });
}
