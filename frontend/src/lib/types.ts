export type Summary = {
  scope: string; canonical_dates: number; earliest_operational_date: string | null;
  latest_operational_date: string | null; missing_dates_between_bounds: number;
  generated_at: string; limitation: string;
};
export type Run = {
  id: string; status: string; trigger: string; started_at: string; finished_at: string | null;
  counters: Record<string, number | null>; pages_scanned: number | null;
  archive_page_failures: number | null; drive_checkpoint_status: string;
};
export type History = { items: Run[]; limit: number; scope: string };
export type Source = { id: string; url: string; sha256: string; category: string };
export type Measurement = {
  metric: string; value: string | null; unit: string; zone: string; period: string;
  fuel: string | null; source_id: string; source_page: number | null; raw_text: string | null;
};
export type Day = {
  operational_date: string; report_version_id: string; parser_version: string;
  available_at: string | null; sources: Source[]; measurements: Measurement[];
};
export type Master = {
  scope: string; total_dates: number; page: number; page_size: number;
  total_pages: number; items: Day[];
};
export type Result<T> = { ok: true; data: T } | { ok: false; message: string };


export type CalendarYear = {
  year: number; calendar_days: number; canonical_dates: number;
  missing_dates: number; coverage_percent: number | null;
};
export type MetricYear = {
  year: number; canonical_dates: number; non_null_dates: number;
  missing_or_null_dates: number; zero_dates: number; coverage_percent: number | null;
};
export type MetricCoverage = {
  metric: string; label: string; unit: string; period: string; fuel: string | null;
  canonical_dates: number; non_null_dates: number; missing_or_null_dates: number;
  zero_dates: number; earliest_value_date: string | null; latest_value_date: string | null;
  coverage_percent: number | null; by_year: MetricYear[];
};
export type QualityReport = {
  scope: string; generated_at: string; canonical_dates: number;
  earliest_operational_date: string | null; latest_operational_date: string | null;
  calendar_days: number; missing_dates: number; calendar_coverage_percent: number | null;
  years: CalendarYear[]; metrics: MetricCoverage[];
  gaps: {
    missing_dates: number; total_ranges: number; page: number; page_size: number; total_pages: number;
    items: { start_date: string; end_date: string; days: number; status: string; source_report_status: string }[];
  };
  limitation: string;
};


export type AuditSource = {
  id: string; url: string; sha256: string; status: string;
  report_date_metadata: string | null; archive_date_hint: string | null;
};
export type AuditIssue = {
  id: string; source_id: string; version_id: string | null;
  code: string; severity: string; resolved: boolean; checks: string[];
};
export type GapAudit = {
  operational_date: string; assessment: string; findings: string[]; source_report_status: string;
  report_ids: string[]; version_count: number;
  versions: { id: string; report_id: string; quality_status: string; is_current: boolean; parser_version: string }[];
  source_count: number; sources: AuditSource[]; archive_hint_count: number;
  archive_hint_candidates: AuditSource[]; issue_count: number; issues: AuditIssue[];
};
export type AuditReport = {
  scope: string; generated_at: string; canonical_dates: number;
  earliest_operational_date: string | null; latest_operational_date: string | null;
  missing_dates: number; gap_page: number; gap_page_size: number; gap_total_pages: number;
  gap_items: GapAudit[]; undated_source_count: number; source_page: number;
  source_page_size: number; source_total_pages: number;
  undated_sources: { source: AuditSource; issue_count: number; issues: AuditIssue[] }[];
  sample_policy: string; sample_candidate_dates: number; sample_review_status: string;
  sample_error: string | null; samples: Day[]; limitation: string;
};

export type AnalyticsPoint = {
  label: string; start_date: string; end_date: string; value: string | null;
  mean: string | null; minimum: string | null; maximum: string | null;
  observed_days: number; canonical_dates: number; expected_days: number;
  coverage_percent: number | null; zero_days: number;
  full_period_selected: boolean; complete_period: boolean;
};
export type AnalyticsReport = {
  scope: string; generated_at: string; metric: string; label: string; unit: string; period: string;
  resolution: "daily" | "monthly" | "yearly"; aggregation: string; parser_support: string;
  earliest_canonical_date: string | null; latest_canonical_date: string | null;
  start_date: string | null; end_date: string | null; calendar_days: number;
  canonical_dates: number; missing_canonical_dates: number; unavailable_metric_dates: number;
  metric_calendar_coverage_percent: number | null; metric_canonical_coverage_percent: number | null;
  first_value_date: string | null; last_value_date: string | null;
  statistics: {
    observations: number; zero_days: number; mean: string | null; median: string | null;
    minimum: string | null; maximum: string | null; sample_stddev: string | null;
    observed_total: string | null;
  };
  points: AnalyticsPoint[]; data_fingerprint: string; limitation: string;
};
