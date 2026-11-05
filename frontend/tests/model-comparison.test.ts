import test from "node:test";
import assert from "node:assert/strict";
import { comparisonKeys, comparisonExports, modelChart, commonMonthlyErrors } from "../src/lib/model-comparison.ts";
import type { ModelPrediction } from "../src/lib/model-comparison.ts";
const row = (date: string, actual: number | null): ModelPrediction => ({date, actual, latest_donor: null, replaced_inputs: 0,
  latest_report: 12, weekly: 8, ridge: 10, autoregression: 11, random_forest: 9, gradient_boosting: 13});
test("six-method chart preserves zero targets, gaps and unscored predictions", () => {
  const chart = modelChart([row("2024-01-01", 0), row("2024-01-02", null)]);
  assert.equal(chart.series.length, 7);
  assert.deepEqual(chart.series[0].values, ["0", null]);
  assert.match(chart.series[6].notes[1], /Unscored/);
});
test("monthly model comparison requires all six forecasts on the same observed dates", () => {
  const missing = row("2024-01-03", 10); missing.gradient_boosting = null;
  const result = commonMonthlyErrors([row("2024-01-01", 10), row("2024-01-02", null), missing, row("2024-02-01", null)]);
  assert.equal(result[0].n, 1);
  assert.equal(result[0].scores.autoregression, 1);
  assert.equal(result[0].scores.gradient_boosting, 3);
  assert.equal(result[1].n, 0);
  assert.ok(comparisonKeys.every(k => result[1].scores[k] === null));
});
test("comparison download kinds are bounded and include safe JSON models", () => {
  assert.deepEqual(comparisonExports, ["predictions", "selection", "models", "report", "test_report"]);
});
