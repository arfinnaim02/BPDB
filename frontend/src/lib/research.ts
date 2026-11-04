import type { ComparisonChartData } from "./comparison-types";

export type ResearchPeriod = {
  label: string; calendar_days: number; observed_days: number; eligible_days: number;
  held_days: number; missing_days: number; coverage_percent: string; complete: boolean;
  mean: string | null; median: string | null; minimum: string | null;
  maximum: string | null; sample_sd: string | null; complete_total: string | null;
  mom_total_percent?: string | null; change_status?: string;
};
export type ResearchDay = {
  date: string; original_value: string | null; eligible: boolean; review_hold: boolean;
  trailing_7_mean: string | null; split: string; source_url: string | null;
  source_sha256: string | null; version_id: string | null;
};
export type ResearchReport = {
  snapshot_id: string; analysis_id: string; scope: string; unit: string;
  config: { start_date: string; end_date: string; train_end: string; validation_end: string };
  calendar_days: number; observed_days: number; eligible_days: number;
  held_days: number; missing_days: number;
  statistics: { mean: string | null; median: string | null; minimum: string | null;
    maximum: string | null; sample_sd: string | null };
  splits: Record<string, { calendar_days: number; observed_days: number;
    missing_days: number; review_held_days: number; observed_target_candidates: number }>;
  daily: ResearchDay[]; monthly: ResearchPeriod[]; quarterly: ResearchPeriod[];
  weekday: ResearchPeriod[]; repaired_dates: string[]; limitations: string[];
};
export const researchExports = ["daily", "monthly", "quarterly", "weekday", "report"] as const;
export function researchDailyChart(rows: ResearchDay[]): ComparisonChartData {
  return { labels: rows.map(r => r.date), unit: "million kWh", series: [
    { name: "Original eligible daily energy", values: rows.map(r => r.eligible ? r.original_value : null),
      notes: rows.map(r => r.review_hold ? "Held for review" : r.original_value == null ? "Missing calendar day" : "Original source value"),
      incomplete: rows.map(r => !r.eligible) },
    { name: "Complete trailing 7-day mean", values: rows.map(r => r.trailing_7_mean),
      notes: rows.map(r => r.trailing_7_mean == null ? "Seven consecutive eligible days unavailable" : "All seven calendar days observed and unheld"),
      incomplete: rows.map(r => r.trailing_7_mean == null) },
  ] };
}
