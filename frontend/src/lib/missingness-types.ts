export type MissingSummary = {
  metric: string; label: string; unit: string; period: string; fuel: string | null;
  parser_support: string; observed_days: number; zero_days: number; unavailable_days: number;
  calendar_coverage_percent: number | null; missing_canonical_days: number; absent_field_days: number;
  explicit_null_days: number; first_value_date: string | null; last_value_date: string | null;
  before_first_value_days: number | null; after_last_value_days: number | null; internal_missing_days: number | null;
  missing_runs: number; longest_missing_run: number; longest_internal_missing_run: number | null;
  longest_observed_streak: number; latest_observed_streak: number; months_in_window: number;
  whole_months_selected: number; complete_months: number; incomplete_whole_months: number;
  sliced_months: number; zero_observation_months: number; longest_complete_month_streak: number;
};
export type MissingReport = {
  generated_at: string; rule_version: string; scope: string;
  earliest_canonical_date: string | null; latest_canonical_date: string | null;
  start_date: string | null; end_date: string | null; calendar_days: number;
  canonical_dates: number; missing_canonical_days: number; metrics: MissingSummary[];
  selected: MissingSummary; run_bins: { label: string; runs: number; days: number }[];
  gap_page: number; gap_page_size: number; gap_total_pages: number;
  gaps: { start_date: string; end_date: string; days: number; missing_canonical_days: number;
    absent_field_days: number; explicit_null_days: number; position: string; source_cause: string }[];
  month_page: number; month_page_size: number; month_total_pages: number;
  months: { label: string; start_date: string; end_date: string; calendar_days: number;
    canonical_dates: number; observed_days: number; zero_days: number; missing_canonical_days: number;
    absent_field_days: number; explicit_null_days: number; whole_calendar_month_selected: boolean;
    all_calendar_days_observed: boolean; status: string }[];
  next_steps: string[]; data_fingerprint: string; limitation: string;
};
