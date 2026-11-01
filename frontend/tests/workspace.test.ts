import assert from "node:assert/strict";
import test from "node:test";
import { createSession, validSession, SESSION_SECONDS, sameSecret } from "../src/lib/session.ts";
import { filters, apiQuery, pageHref, validDate } from "../src/lib/filters.ts";
import { safeSourceUrl } from "../src/lib/format.ts";
const secret = "a-unique-session-signing-secret-over-32-characters";
const now = Date.UTC(2026, 10, 1);
test("signed sessions reject tampering, wrong key and expiry", () => {
  const token = createSession(secret, now);
  assert.equal(validSession(token, secret, now), true);
  assert.equal(validSession(token + "x", secret, now), false);
  assert.equal(validSession(token, "different-session-secret-over-32-characters", now), false);
  assert.equal(validSession(token, secret, now + SESSION_SECONDS * 1000), false);
  assert.equal(validSession(token, secret, now - 1000), false);
  assert.equal(validSession(undefined, secret, now), false);
  assert.equal(validSession(token, "short", now), false);
  assert.equal(sameSecret("one", "one"), true);
  assert.equal(sameSecret("one", "two"), false);
});
test("filters reject impossible or reversed dates and bound pagination", () => {
  assert.equal(validDate("2026-02-30"), false);
  assert.equal(validDate("2024-02-29"), true);
  assert.ok(filters({ start_date: "2026-02-30" }).error);
  assert.ok(filters({ start_date: "2026-02-01", end_date: "2026-01-01" }).error);
  const f = filters({ page: "-9", page_size: "999", column: "unsupported" });
  assert.equal(f.page, 1); assert.equal(f.pageSize, 20); assert.equal(f.columns.length, 4);
});
test("pagination preserves filters and selected metrics", () => {
  const f = filters({ start_date: "2026-01-01", end_date: "2026-01-10", column: "energy_generated", page_size: "50" });
  assert.equal(apiQuery(f).get("start_date"), "2026-01-01");
  const url = new URL(pageHref(f, 2), "https://workspace.example");
  assert.equal(url.searchParams.get("page"), "2");
  assert.equal(url.searchParams.get("page_size"), "50");
  assert.deepEqual(url.searchParams.getAll("column"), ["energy_generated"]);
});
test("source links reject executable and credential-bearing URLs", () => {
  assert.equal(safeSourceUrl("javascript:alert(1)"), undefined);
  assert.equal(safeSourceUrl("https://user:password@example.com/a.pdf"), undefined);
  assert.equal(safeSourceUrl("https://misc.bpdb.gov.bd/a.pdf"), "https://misc.bpdb.gov.bd/a.pdf");
});
