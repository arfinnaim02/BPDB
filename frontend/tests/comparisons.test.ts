import assert from "node:assert/strict";
import test from "node:test";
import { comparisonFilters, pairedChart, seasonalChart } from "../src/lib/comparison-filters.ts";
import type { ComparisonReport } from "../src/lib/comparison-types.ts";

test("comparison filters preserve repeated years, dates and independent table pages", () => {
  const f = comparisonFilters({ metric: "energy_generated", peak: "day", resolution: "daily",
    year: ["2025", "2024", "2025", "garbage"], start_date: "2024-01-01", month_page: "2", pair_page: "3" });
  assert.deepEqual(f.years, [2024, 2025]);
  assert.deepEqual(f.query.getAll("year"), ["2024", "2025"]);
  assert.equal(f.peak, "day");
  assert.equal(f.monthPage, 2); assert.equal(f.pairPage, 3);
  assert.equal(f.query.has("pair_page"), false);
  assert.equal(f.query.get("start_date"), "2024-01-01");
  assert.equal(comparisonFilters({ peak: "unknown", pair_page: "-1" }).peak, "evening");
});
test("comparison filters reject too many years and invalid date windows", () => {
  assert.ok(comparisonFilters({ year: Array.from({ length: 9 }, (_, i) => String(2000 + i)) }).error);
  assert.ok(comparisonFilters({ start_date: "2026-02-30" }).error);
  assert.ok(comparisonFilters({ start_date: "2026-03-01", end_date: "2026-02-01" }).error);
});
test("seasonal plotting preserves missing months, zero and incomplete coverage", () => {
  const report = { selected_years: [2025], unit: "million_kWh", monthly: [
    { label: "2025-01", value: "0", observed_days: 31, expected_days: 31, complete_period: true },
    { label: "2025-03", value: "1.123456", observed_days: 2, expected_days: 31, complete_period: false },
  ] } as ComparisonReport;
  const chart = seasonalChart(report);
  assert.equal(chart.labels.length, 12);
  assert.deepEqual(chart.series[0].values.slice(0, 3), ["0", null, "1.123456"]);
  assert.equal(chart.series[0].incomplete[2], true);
  assert.equal(chart.series[0].notes[0], "31/31 observed/calendar days");
  assert.equal(chart.unit, "million kWh");
});
test("paired plotting preserves signed difference and absent observations", () => {
  const report = { paired_points: [
    { label: "2025-01", generation_mean: "10", demand_mean: "9", difference_mean: "-1", paired_days: 31, expected_days: 31, complete_period: true },
    { label: "2025-02", generation_mean: null, demand_mean: null, difference_mean: null, paired_days: 0, expected_days: 28, complete_period: false },
  ] } as ComparisonReport;
  const chart = pairedChart(report);
  assert.deepEqual(chart.series[2].values, ["-1", null]);
  assert.equal(chart.series[1].notes[1], "0/28 paired/calendar days");
  assert.equal(chart.series.length, 3);
});
