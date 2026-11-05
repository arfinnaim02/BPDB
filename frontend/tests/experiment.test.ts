import test from "node:test";
import assert from "node:assert/strict";
import { experimentChart, monthlyErrors } from "../src/lib/experiment.ts";
import type { Prediction } from "../src/lib/experiment.ts";

const row = (date: string, actual: number | null, ridge: number | null): Prediction => ({
  date, actual, original_actual: actual == null ? null : String(actual), ridge,
  latest_report: 12, weekly: 8, latest_donor: null, replaced_inputs: 0, unknown_availability_inputs: 9,
});
test("forecast chart retains zero and missing targets without replacing actuals", () => {
  const chart = experimentChart([row("2024-01-01", 0, 10), row("2024-01-02", null, 10)]);
  assert.deepEqual(chart.series[0].values, ["0", null]);
  assert.deepEqual(chart.series[3].values, ["10", "10"]);
  assert.match(chart.series[3].notes[1], /unscored/);
});
test("monthly comparison uses only identical common observed dates", () => {
  const result = monthlyErrors([row("2024-01-01", 10, 11), row("2024-01-02", null, 11),
    row("2024-01-03", 10, null), row("2024-02-01", null, 11)]);
  assert.deepEqual(result[0], { month: "2024-01", n: 1, latest_report: 2, weekly: 2, ridge: 1 });
  assert.equal(result[1].n, 0); assert.equal(result[1].ridge, null);
});
