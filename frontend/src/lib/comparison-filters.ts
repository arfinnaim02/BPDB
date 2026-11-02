import { analyticsFilters } from "./analytics-filters.ts";
import { single, type Params } from "./filters.ts";
import type { ComparisonChartData, ComparisonReport } from "./comparison-types.ts";

export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const boundedPage = (value: string | undefined) => value && /^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 100000 ? Number(value) : 1;
export function comparisonFilters(params: Params) {
  const f = analyticsFilters(params);
  const peak = single(params.peak) === "day" ? "day" : "evening";
  const supplied = params.year;
  const years = [...new Set((Array.isArray(supplied) ? supplied : supplied ? [supplied] : [])
    .filter(y => /^\d{4}$/.test(y) && Number(y) >= 1900 && Number(y) <= 2200).map(Number))].sort((a, b) => a - b);
  const query = new URLSearchParams(f.query);
  query.set("peak", peak);
  years.forEach(year => query.append("year", String(year)));
  return { ...f, peak, years, query, monthPage: boundedPage(single(params.month_page)),
    pairPage: boundedPage(single(params.pair_page)), error: f.error || (years.length > 8 ? "Select at most eight comparison years." : null) };
}
export function pairedChart(d: ComparisonReport): ComparisonChartData {
  return { labels: d.paired_points.map(p => p.label), unit: "MW", series: [
    ["Generation", "generation_mean"], ["Demand", "demand_mean"], ["Demand minus generation", "difference_mean"],
  ].map(([name, field]) => ({ name, values: d.paired_points.map(p => p[field as "generation_mean" | "demand_mean" | "difference_mean"]),
    notes: d.paired_points.map(p => `${p.paired_days}/${p.expected_days} paired/calendar days`),
    incomplete: d.paired_points.map(p => !p.complete_period) })) };
}
export function seasonalChart(d: ComparisonReport): ComparisonChartData {
  const lookup = new Map(d.monthly.map(p => [p.label, p]));
  return { labels: MONTHS, unit: d.unit === "million_kWh" ? "million kWh" : d.unit,
    series: d.selected_years.map(year => {
      const periods = MONTHS.map((_, i) => lookup.get(`${year}-${String(i + 1).padStart(2, "0")}`));
      return { name: String(year), values: periods.map(p => p?.value ?? null),
        notes: periods.map(p => p ? `${p.observed_days}/${p.expected_days} observed/calendar days` : "Outside selected date window"),
        incomplete: periods.map(p => !p?.complete_period) };
    }) };
}
export const CHANGE_STATUS: Record<string, string> = {
  comparable_complete_months: "Both complete calendar months",
  current_month_incomplete: "Current month incomplete or sliced",
  baseline_outside_window: "Baseline outside selected window",
  baseline_month_incomplete: "Baseline month incomplete or sliced",
  zero_baseline: "Baseline is zero; percentage undefined",
  unavailable: "No comparable observations",
};
