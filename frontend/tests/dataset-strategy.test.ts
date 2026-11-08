import test from 'node:test';
import assert from 'node:assert/strict';
import {canPreviewWeeklyTreatment,displayCoverage} from '../src/lib/dataset-strategy.ts';
test('preparation treats only the five supported core variables as experimental weekly candidates',()=>{
 for(const m of ['energy_generated','day_peak_generation','evening_peak_generation','evening_peak_demand','maximum_generation'])assert.equal(canPreviewWeeklyTreatment(m),true);
 for(const m of ['day_peak_demand','minimum_generation','energy_demand','energy_unserved','maximum_temperature','gas_supplied','production_cost_per_kwh','total_production_cost','unknown'])assert.equal(canPreviewWeeklyTreatment(m),false);
});
test('unavailable coverage never becomes a numerical zero',()=>{
 assert.equal(displayCoverage(null),'Unavailable');
 assert.equal(displayCoverage(0),'0.00%');
 assert.equal(displayCoverage(33.33),'33.33%');
});
