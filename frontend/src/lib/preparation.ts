import { COLUMNS, single, validDate, type Params } from "./filters.ts";

export function preparationFilters(params: Params) {
  const metric = COLUMNS.find(m => m === single(params.metric)) || "energy_generated";
  const start = single(params.start_date) || "";
  const end = single(params.end_date) || "";
  const train = single(params.train_end) || "";
  const validation = single(params.validation_end) || "";
  const policy = single(params.policy) === "past_week_train_only" ? "past_week_train_only" : "observed_only";
  const maxGap = [1, 2, 3].includes(Number(single(params.max_gap))) ? Number(single(params.max_gap)) : 1;
  const entered = [start, end, train, validation].some(Boolean);
  const error = !entered ? null : ![start, end, train, validation].every(validDate)
    ? "Enter all four valid dates in YYYY-MM-DD format."
    : !(start <= train && train < validation && validation < end)
      ? "Use from date ≤ training end < validation end < to date."
      : (Date.parse(end) - Date.parse(start)) / 86400000 >= 3660
        ? "Select at most 3,660 calendar days." : null;
  const query = new URLSearchParams({ metric, start_date: start, end_date: end,
    train_end: train, validation_end: validation, policy, max_gap: String(maxGap) });
  return { metric, start, end, train, validation, policy, maxGap, entered, error, query };
}
export type ResearchRow = {
  operational_date: string; split: string; state: string; original_value: string | null;
  prepared_train_value: string | null; method: string; reason: string; review_flags: string;
  donor_date: string | null;
};
export type ResearchSnapshot = {
  snapshot_id: string; config: Record<string, string | number | null>;
  splits: Record<string, { calendar_days: number; observed_days: number; missing_days: number;
    review_held_days: number; observed_target_candidates: number; estimated_training_days: number;
    prepared_training_days: number }>;
  reasons: Record<string, number>; limitations: string[]; preview_rows: ResearchRow[]; preview_limit: number;
  months: { month: string; calendar_days_selected: number; whole_month_selected: boolean;
    all_days_observed_unheld: boolean; split: string; observed_month_total: string | null }[];
};
