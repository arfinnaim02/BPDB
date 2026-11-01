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
