export const COLUMNS = [
  "day_peak_generation", "evening_peak_generation", "evening_peak_demand", "energy_generated",
  "day_peak_demand", "minimum_generation", "maximum_generation", "energy_unserved", "energy_demand",
  "maximum_temperature", "gas_supplied", "production_cost_per_kwh", "total_production_cost",
] as const;
export type Params = Record<string, string | string[] | undefined>;
export const single = (value: string | string[] | undefined) => typeof value === "string" ? value : undefined;
export function validDate(value: string | undefined): boolean {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === value;
}
export function filters(params: Params) {
  const start = single(params.start_date) || "";
  const end = single(params.end_date) || "";
  const rawPage = single(params.page) || "1";
  const page = /^\d+$/.test(rawPage) && Number(rawPage) >= 1 && Number(rawPage) <= 100000 ? Number(rawPage) : 1;
  const size = single(params.page_size);
  const pageSize = [10, 20, 50, 100].includes(Number(size)) ? Number(size) : 20;
  const supplied = params.column;
  const selected = Array.isArray(supplied) ? supplied : supplied ? [supplied] : [];
  const columns = COLUMNS.filter(c => selected.includes(c));
  const error = (start && !validDate(start)) || (end && !validDate(end))
    ? "Use valid dates in YYYY-MM-DD format." : start && end && start > end
      ? "The start date must be on or before the end date." : null;
  return { start, end, page, pageSize, columns: columns.length ? columns : COLUMNS.slice(0, 4), error };
}
export function apiQuery(f: ReturnType<typeof filters>, page = f.page): URLSearchParams {
  const q = new URLSearchParams({ page: String(page), page_size: String(f.pageSize) });
  if (f.start) q.set("start_date", f.start);
  if (f.end) q.set("end_date", f.end);
  return q;
}
export function pageHref(f: ReturnType<typeof filters>, page: number) {
  const q = apiQuery(f, page);
  f.columns.forEach(c => q.append("column", c));
  return `/dataset?${q}`;
}
