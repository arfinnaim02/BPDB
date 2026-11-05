import test from "node:test";
import assert from "node:assert/strict";
import { forecastChart, forecastLimit, nextDhakaDay, validIssue, withheldReason } from "../src/lib/forecasts.ts";
import type { ForecastRow } from "../src/lib/forecasts.ts";
const row = (id: string, at: string, prediction: string): ForecastRow => ({ id, issued_at: at, prediction,
  target_date: "2026-11-06", status: "forecast", model_id: "m", model_experiment_id: "e",
  input_fingerprint: "input", reason: null, latest_donor: "2026-11-04", substituted_slots: 0,
  unknown_official_time_slots: 9, outcome: null });
test("forecast chart keeps earliest displayed issue and leaves pending actual blank", () => {
  const first = row("a", "2026-11-05T06:01:00Z", "301.123456789");
  const later = row("b", "2026-11-05T08:01:00Z", "299");
  const held = { ...later, id: "c", status: "withheld" as const, prediction: null };
  const chart = forecastChart([later, held, first]);
  assert.deepEqual(chart.labels, ["2026-11-06"]);
  assert.deepEqual(chart.series[0].values, ["301.123456789"]);
  assert.deepEqual(chart.series[1].values, [null]);
});
test("tomorrow uses Bangladesh midnight rather than UTC midnight", () => {
  assert.equal(nextDhakaDay("2026-11-05T17:59:00Z"), "2026-11-06");
  assert.equal(nextDhakaDay("2026-11-05T18:00:00Z"), "2026-11-07");
  assert.equal(nextDhakaDay("invalid"), "");
});
test("forecast selectors reject arbitrary paths and bound history limits", () => {
  assert.equal(forecastLimit("100"), 100);
  assert.equal(forecastLimit("1000"), 20);
  assert.equal(forecastLimit(["20"]), 20);
  assert.ok(validIssue("a".repeat(64)));
  assert.ok(!validIssue("../secret"));
  assert.match(withheldReason("missing_usable_original_inputs"), /unavailable/);
});
