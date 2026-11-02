import { single, validDate, type Params } from "./filters.ts";
export const ANALYTIC_METRICS = [
  ["day_peak_generation", "Day peak generation"],
  ["evening_peak_generation", "Evening peak generation"],
  ["evening_peak_demand", "Evening peak demand"],
  ["maximum_generation", "Maximum generation"],
  ["energy_generated", "Energy generated"],
  ["day_peak_demand", "Day peak demand"],
  ["minimum_generation", "Minimum generation"],
  ["energy_demand", "Energy demand"],
  ["energy_unserved", "Energy unserved"],
] as const;
export function analyticsFilters(params: Params) {
  const rawMetric = single(params.metric);
  const metric = ANALYTIC_METRICS.find(([key]) => key === rawMetric)?.[0] ?? "day_peak_generation";
  const rawResolution = single(params.resolution);
  const resolution = ["daily", "monthly", "yearly"].includes(rawResolution ?? "") ? rawResolution! : "monthly";
  const start = single(params.start_date) || "";
  const end = single(params.end_date) || "";
  const rawPage = single(params.table_page) || "1";
  const page = /^\d+$/.test(rawPage) && Number(rawPage) >= 1 && Number(rawPage) <= 100000 ? Number(rawPage) : 1;
  const error = (start && !validDate(start)) || (end && !validDate(end))
    ? "Use valid dates in YYYY-MM-DD format." : start && end && start > end
      ? "Start date must be on or before end date." : null;
  const query = new URLSearchParams({ metric, resolution });
  if (start) query.set("start_date", start);
  if (end) query.set("end_date", end);
  return { metric, resolution, start, end, page, error, query };
}
export function exactDisplay(value: string | null): string {
  if (value == null) return "—";
  const [integer, fraction] = value.split(".");
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (fraction ? `.${fraction}` : "");
}
