import assert from "node:assert/strict";
import test from "node:test";
import { analyticsFilters, exactDisplay } from "../src/lib/analytics-filters.ts";

test("analytics filters bound query values and keep dates", () => {
  const f = analyticsFilters({ metric: "energy_generated", resolution: "yearly", start_date: "2020-01-01", end_date: "2021-01-01", table_page: "2" });
  assert.equal(f.metric, "energy_generated");
  assert.equal(f.resolution, "yearly");
  assert.equal(f.page, 2);
  assert.equal(f.query.get("start_date"), "2020-01-01");
  assert.equal(f.query.has("table_page"), false);
  const invalid = analyticsFilters({ metric: "unknown", resolution: "hourly", table_page: "-1" });
  assert.equal(invalid.metric, "day_peak_generation");
  assert.equal(invalid.resolution, "monthly");
  assert.equal(invalid.page, 1);
});
test("analytics rejects impossible dates and reversed bounds", () => {
  assert.ok(analyticsFilters({ start_date: "2026-02-30" }).error);
  assert.ok(analyticsFilters({ start_date: "2026-02-01", end_date: "2026-01-01" }).error);
  assert.equal(analyticsFilters({ start_date: "2024-02-29" }).error, null);
});
test("decimal formatting preserves precision and zero without floating conversion", () => {
  assert.equal(exactDisplay("999999999999.123456"), "999,999,999,999.123456");
  assert.equal(exactDisplay("0"), "0");
  assert.equal(exactDisplay(null), "—");
  assert.equal(exactDisplay("-1234.56"), "-1,234.56");
});
