import test from "node:test";
import assert from "node:assert/strict";
import { finalChart, finalExports, evaluationMonth } from "../src/lib/final-evaluation.ts";
import type { ModelPrediction } from "../src/lib/model-comparison.ts";
const row = (date: string, actual: number | null): ModelPrediction => ({ date, actual, latest_donor: null, replaced_inputs: 0,
  latest_report: 1, weekly: 2, ridge: 3, autoregression: 4, random_forest: 5, gradient_boosting: 6 });
test("final chart preserves 2025 zero and missing targets with correct refitted names", () => {
  const chart = finalChart([row("2025-01-01", 0), row("2025-01-02", null)]);
  assert.equal(chart.series.length, 7);
  assert.deepEqual(chart.series[0].values, ["0", null]);
  assert.equal(chart.series[3].name, "Ridge · refitted");
  assert.equal(chart.series[4].name, "OLS · primary");
  assert.match(chart.series[4].notes[1], /Unscored/);
});
test("final month selector rejects malformed and repeated months", () => {
  assert.equal(evaluationMonth("05"), "05");
  for (const value of ["00", "13", "5", ["05", "06"], undefined]) assert.equal(evaluationMonth(value), "01");
});
test("final evidence exports include thesis tables and exclude arbitrary paths", () => {
  assert.deepEqual(finalExports, ["predictions", "metrics", "monthly", "sensitivity", "models", "report", "test_report"]);
});
