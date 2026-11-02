import assert from "node:assert/strict";
import test from "node:test";
import { missingnessFilters, missingnessHref } from "../src/lib/missingness-filters.ts";

test("missingness filters support all metrics and preserve independent pages", () => {
  const f = missingnessFilters({ metric: "total_production_cost", gap_page: "2", month_page: "3",
    gap_page_size: "50", start_date: "2025-01-01", end_date: "2026-01-01" });
  assert.equal(f.metric, "total_production_cost");
  assert.equal(f.pageSize, 50);
  assert.equal(f.gapPage, 2); assert.equal(f.monthPage, 3);
  const href = missingnessHref(f, 4, f.monthPage, "missing-runs");
  const url = new URL(href, "https://example.test");
  assert.equal(url.searchParams.get("gap_page"), "4");
  assert.equal(url.searchParams.get("month_page"), "3");
  assert.equal(url.searchParams.get("metric"), "total_production_cost");
  assert.equal(url.searchParams.get("start_date"), "2025-01-01");
  assert.equal(url.hash, "#missing-runs");
});
test("missingness filters bound invalid input and validate dates", () => {
  const f = missingnessFilters({ metric: "unknown", gap_page: "0", month_page: "100001", gap_page_size: "100" });
  assert.equal(f.metric, "energy_generated");
  assert.equal(f.gapPage, 1); assert.equal(f.monthPage, 1); assert.equal(f.pageSize, 20);
  assert.ok(missingnessFilters({ start_date: "2026-02-30" }).error);
  assert.ok(missingnessFilters({ start_date: "2026-02-01", end_date: "2026-01-01" }).error);
  assert.equal(missingnessFilters({ start_date: "2024-02-29" }).error, null);
});
