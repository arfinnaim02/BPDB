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
