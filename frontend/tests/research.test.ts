import test from "node:test";
import assert from "node:assert/strict";
import { researchDailyChart, researchExports } from "../src/lib/research.ts";
import type { ResearchDay } from "../src/lib/research.ts";

test("daily chart keeps real zero and gaps and never plots held values as usable", () => {
  const row = (value: string | null, eligible: boolean, held = false): ResearchDay => ({
    date: "2024-01-01", original_value: value, eligible, review_hold: held,
    trailing_7_mean: null, split: "train", source_url: null, source_sha256: null, version_id: null,
  });
  const chart = researchDailyChart([row("0", true), row(null, false), row("20", false, true)]);
  assert.deepEqual(chart.series[0].values, ["0", null, null]);
  assert.deepEqual(chart.series[1].values, [null, null, null]);
  assert.match(chart.series[0].notes[2], /Held/);
  assert.deepEqual(researchExports, ["daily", "monthly", "quarterly", "weekday", "report"]);
});
