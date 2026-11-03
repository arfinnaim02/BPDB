import assert from "node:assert/strict";
import test from "node:test";
import { preparationFilters } from "../src/lib/preparation.ts";

test("preparation requires explicit complete chronological dates", () => {
  assert.equal(preparationFilters({}).entered, false);
  assert.match(preparationFilters({start_date:"2024-01-01"}).error!, /four/);
  const input = {start_date:"2024-01-01",end_date:"2024-12-31",train_end:"2024-06-30",validation_end:"2024-09-30"};
  assert.equal(preparationFilters(input).error,null);
  assert.match(preparationFilters({...input,validation_end:"2024-06-30"}).error!, /training end/);
  assert.match(preparationFilters({...input,start_date:"2024-02-30"}).error!, /valid dates/);
});
test("preparation query allowlists treatment and bounds the window", () => {
  const f = preparationFilters({metric:"secret",policy:"fill_everything",max_gap:"999",download:"true"});
  assert.equal(f.metric,"energy_generated"); assert.equal(f.policy,"observed_only");
  assert.equal(f.maxGap,1); assert.equal(f.query.has("download"),false);
  assert.match(preparationFilters({start_date:"2000-01-01",end_date:"2026-01-01",train_end:"2010-01-01",validation_end:"2020-01-01"}).error!, /3,660/);
});
