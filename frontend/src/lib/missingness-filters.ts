import { COLUMNS, single, validDate, type Params } from "./filters.ts";

const pageNumber = (raw: string | undefined) => raw && /^\d+$/.test(raw) && Number(raw) >= 1 && Number(raw) <= 100000 ? Number(raw) : 1;
export function missingnessFilters(params: Params) {
  const raw = single(params.metric);
  const metric = COLUMNS.find(c => c === raw) || "energy_generated";
  const start = single(params.start_date) || "";
  const end = single(params.end_date) || "";
  const size = Number(single(params.gap_page_size));
  const pageSize = [10, 20, 50].includes(size) ? size : 20;
  const error = (start && !validDate(start)) || (end && !validDate(end))
    ? "Use valid dates in YYYY-MM-DD format." : start && end && start > end
      ? "Start date must be on or before end date." : null;
  const query = new URLSearchParams({ metric, gap_page_size: String(pageSize) });
  if (start) query.set("start_date", start);
  if (end) query.set("end_date", end);
  return { metric, start, end, pageSize, error, query,
    gapPage: pageNumber(single(params.gap_page)), monthPage: pageNumber(single(params.month_page)) };
}
export function missingnessHref(f: ReturnType<typeof missingnessFilters>, gap: number, month: number, section: string) {
  const query = new URLSearchParams(f.query);
  query.set("gap_page", String(gap)); query.set("month_page", String(month));
  return `/quality/missing?${query}#${section}`;
}
export const RUN_POSITION: Record<string, string> = {
  leading: "Before first observed value", trailing: "After last observed value",
  internal: "Inside observed value window", no_observed_window: "No observed value window",
};
export const MONTH_STATUS: Record<string, string> = {
  all_days_observed: "All calendar days observed", incomplete_month: "Incomplete full month",
  window_slice: "Date-window slice", no_observations: "No observations",
};
export const MISSING_ACTIONS: Record<string, string> = {
  verify_metric_definition_and_original_source_coverage: "Verify the metric definition, source coverage and parser support before selecting an analysis window.",
  investigate_manifest_quarantine_conflict_and_download_evidence: "Investigate collection manifests, quarantines, conflicts and failed downloads for dates without canonical records.",
  compare_original_pdf_fields_with_parser_support_and_extraction: "Compare the original PDFs with parser support and stored extraction for absent or null fields; recover only source-supported values.",
  review_boundary_unavailability_before_choosing_analysis_window: "Review leading/trailing unavailability before choosing the analysis window. Do not extend modern fields backwards by default.",
  compare_justified_training_only_treatments_after_source_review: "After source review, compare justified missing-data treatments within chronological training folds. Do not use future observations to prepare past predictions.",
  preserve_zeroes_and_evaluate_only_genuinely_observed_test_targets: "Preserve observed zeroes and keep estimated values separate. Evaluate forecasts against genuinely observed test targets.",
};
