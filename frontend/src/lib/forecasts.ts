import type { ComparisonChartData } from "./comparison-types";
export type ForecastOutcome = { observed: string; signed_error: string; absolute_error: string;
  actual_version_id: string; source_id: string; compared_at: string; lineage: { source_url: string; source_sha256: string; captured_at: string } };
export type ForecastRow = { id: string; model_id: string; model_experiment_id: string; target_date: string;
  issued_at: string; status: "forecast" | "withheld"; prediction: string | null; input_fingerprint: string;
  reason: string | null; latest_donor: string | null; substituted_slots: number; unknown_official_time_slots: number;
  outcome: ForecastOutcome | null };
export type ModelCard = { model_id: string; experiment_id: string; family: string; unit: string;
  last_fit_label: string; fit_rows: number; historical_test_mae: number; policy: string; features: string[] };
export type ForecastHistory = { generated_at: string; model: ModelCard; items: ForecastRow[]; limit: number;
  summary: { window_start: string; window_end: string; completed_targets_attempted: number;
    completed_targets_with_forecast: number; scored_dates: number; mae: number | null; rmse: number | null;
    bias: number | null; selection_rule: string }; limitation: string; outcome_scope: string };
export type CapturedInput = { date: string; value: string | null; eligible: boolean; reasons: string[];
  version_id?: string; source_id?: string; source_url?: string; source_sha256?: string;
  requested_date?: string; substituted?: boolean; retrieved_at?: string | null; published_at?: string | null };
export type ForecastDetail = ForecastRow & { limitation: string; payload: { policy: string; model_card: ModelCard;
  captured_at: string; reason: string | null; missing_requested_dates: string[]; features: number[] | null;
  feature_names: string[]; used_inputs: CapturedInput[]; snapshot: CapturedInput[];
  substituted_slots: number; unknown_official_time_slots: number; latest_donor: string | null;
  availability_basis: string; calculation: { intercept: number; terms: { feature: string; input: number;
    mean: number; scale: number; coefficient: number; contribution: number }[] } | null } };
export function forecastLimit(value: unknown): number {
  return typeof value === "string" && [20, 50, 100].includes(Number(value)) ? Number(value) : 20;
}
export function validIssue(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{64}$/.test(value); }
export function nextDhakaDay(instant: string): string {
  const local = new Date(Date.parse(instant)+6*60*60*1000);
  if (Number.isNaN(local.getTime())) return "";
  local.setUTCDate(local.getUTCDate()+1);
  return local.toISOString().slice(0,10);
}
export function withheldReason(reason: string | null): string {
  return reason === "missing_usable_original_inputs" ? "Required original inputs unavailable" : reason === "unsafe_model_output"
    ? "Model output outside the permitted numeric range" : reason || "—";
}
export function forecastChart(rows: ForecastRow[]): ComparisonChartData {
  const first = new Map<string, ForecastRow>();
  [...rows].sort((a,b) => a.issued_at.localeCompare(b.issued_at) || a.id.localeCompare(b.id)).forEach(r => {
    if (r.status === "forecast" && !first.has(r.target_date)) first.set(r.target_date, r);
  });
  const points = [...first.values()].sort((a,b) => a.target_date.localeCompare(b.target_date));
  return { labels: points.map(r => r.target_date), unit: "million kWh", series: [
    { name: "Recorded OLS forecast", values: points.map(r => r.prediction),
      notes: points.map(r => `Actual issue ${r.issued_at}; ${r.substituted_slots} substituted past-input slots`), incomplete: points.map(() => false) },
    { name: "Latest retained observed actual", values: points.map(r => r.outcome?.observed ?? null),
      notes: points.map(r => r.outcome ? `Retained source version ${r.outcome.actual_version_id}` : "Awaiting observed outcome · never filled"),
      incomplete: points.map(r => !r.outcome) },
  ] };
}
