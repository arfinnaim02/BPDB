import { modelChart, comparisonNames } from "./model-comparison.ts";
import type { ModelComparison, ModelPrediction, ModelKey } from "./model-comparison";
export const finalNames: Record<ModelKey, string> = { ...comparisonNames, ridge: "Ridge · refitted", autoregression: "OLS · primary" };
export const finalExports = ["predictions", "metrics", "monthly", "sensitivity", "models", "report", "test_report"] as const;
export type FinalEvaluation = {
  experiment_id: string; evaluation_key: string; snapshot_id: string; reference_experiment_id: string;
  primary_model: ModelKey; scores: ModelComparison["validation"];
  coverage: ModelComparison["coverage"]; models: Record<string, { rows: number; cutoff: string; last_label: string; configuration_id: string }>;
  monthly: { month: string; calendar_days: number; observed_targets: number; scores: ModelComparison["validation"] }[];
  paired_mae_sensitivity: { block_days: number; common_dates: number; point_difference: number | null;
    lower_2_5: number | null; upper_97_5: number | null; requested_replicates: number; valid_replicates: number }[];
  predictions: (ModelPrediction & { unknown_availability_inputs: number | null })[];
  strict_availability_feature_days: number; feature_names: string[];
  final_test: { year: number; status: string; selection_changed: boolean };
  protocol: { issue: string; reporting_scenario: string; fit_start: string; fit_end: string;
    test_start: string; test_end: string; test_inputs: string; parameter_updates_in_test: boolean };
  checks: { same_frozen_input: boolean; locked_release2_settings: boolean; no_test_labels_in_fit: boolean;
    no_test_parameter_updates: boolean; all_donors_at_or_before_t_minus_2: boolean; neon_writes: number;
    calendar_days: number; common_scored_dates: number; saved_model_max_difference: Record<string, number> };
  limitations: string[];
};
export function finalChart(rows: ModelPrediction[]) {
  const chart = modelChart(rows);
  return { ...chart, series: chart.series.map((s, i) => ({ ...s, name: i === 0 ? "Observed 2025 target"
    : finalNames[(["latest_report", "weekly", "ridge", "autoregression", "random_forest", "gradient_boosting"] as const)[i-1]] })) };
}
export function evaluationMonth(value: unknown): string {
  return typeof value === "string" && /^(0[1-9]|1[0-2])$/.test(value) ? value : "01";
}
