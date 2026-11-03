import assert from 'node:assert/strict';
import test from 'node:test';
import { auditFilters,auditHref } from '../src/lib/audit-filters.ts';
test('source audit keeps date filters and independent pagination',()=>{
 const f=auditFilters({start_date:'2024-01-01',end_date:'2024-12-31',gap_page:'2',source_page:'3',gap_page_size:'50'});
 assert.equal(f.error,null);assert.equal(f.dates.has('gap_page'),false);
 const u=new URL(auditHref(f,3,4,'gap-audit'),'https://example.org');
 assert.equal(u.searchParams.get('start_date'),'2024-01-01');
 assert.equal(u.searchParams.get('gap_page'),'3');assert.equal(u.searchParams.get('source_page'),'4');
});
test('source audit rejects bad dates and bounds paging',()=>{
 assert.match(auditFilters({start_date:'2024-02-30'}).error!,/valid dates/);
 assert.match(auditFilters({start_date:'2024-12-31',end_date:'2024-01-01'}).error!,/before/);
 const f=auditFilters({gap_page:'-1',source_page:'999999',gap_page_size:'999'});
 assert.equal(f.gapPage,1);assert.equal(f.sourcePage,1);assert.equal(f.pageSize,20);
});
