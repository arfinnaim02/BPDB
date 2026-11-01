import Link from "next/link";
import { requireSession } from "../../lib/auth";
import { readApi } from "../../lib/backend";
import { apiQuery, COLUMNS, filters, pageHref, type Params } from "../../lib/filters";
import { count, metricLabel } from "../../lib/format";
import type { Master } from "../../lib/types";
import { Records } from "../../components/records";
import { ErrorPanel, Heading, Shell } from "../../components/ui";
export const dynamic = "force-dynamic";
export default async function Dataset({ searchParams }: { searchParams: Promise<Params> }) {
  await requireSession();
  const f = filters(await searchParams);
  const result = f.error ? null : await readApi<Master>(`/api/v1/dataset/daily?${apiQuery(f)}`);
  const exportQuery = new URLSearchParams();
  if (f.start) exportQuery.set("start_date", f.start);
  if (f.end) exportQuery.set("end_date", f.end);
  return <Shell active="/dataset"><Heading eyebrow="AUTHORITATIVE RECORDS" title="Master dataset" description="Explore current validated national records, exact measurements and original PDF evidence.">{!f.error && <a className="button primary" href={`/api/export?${exportQuery}`}>Download filtered CSV ↓</a>}</Heading>
    <section className="panel filter-panel"><form action="/dataset" className="filter-form"><div className="field"><label htmlFor="start_date">From date</label><input id="start_date" name="start_date" type="date" defaultValue={f.start}/></div><div className="field"><label htmlFor="end_date">To date</label><input id="end_date" name="end_date" type="date" defaultValue={f.end}/></div><div className="field"><label htmlFor="page_size">Rows per page</label><select name="page_size" id="page_size" defaultValue={f.pageSize}>{[10, 20, 50, 100].map(n => <option key={n}>{n}</option>)}</select></div><div className="filter-actions"><button className="button primary">Apply filters</button><Link className="text-button" href="/dataset">Reset</Link></div><details className="column-picker"><summary>Choose visible metrics ({f.columns.length})</summary><div className="checkbox-grid">{COLUMNS.map(c => <label key={c}><input type="checkbox" name="column" value={c} defaultChecked={f.columns.includes(c)}/>{metricLabel(c)}</label>)}</div></details></form></section>
    {f.error ? <div className="notice error-notice" role="alert">{f.error}</div> : result && !result.ok ? <ErrorPanel message={result.message}/> : result?.ok && <section className="panel"><div className="panel-heading"><div><h2>National daily records <span className="count-chip">{count(result.data.total_dates)}</span></h2><p>Newest operational date first · values shown without rounding</p></div><span className="scope-tag">Current · validated</span></div><Records days={result.data.items} columns={f.columns}/><div className="pagination"><span>{result.data.items.length ? `${count((f.page - 1) * f.pageSize + 1)}–${count((f.page - 1) * f.pageSize + result.data.items.length)} of ${count(result.data.total_dates)} dates` : "No rows on this page"}</span><div>{f.page > 1 && <Link className="button secondary" href={pageHref(f, f.page - 1)}>← Previous</Link>}<span>Page {count(f.page)} / {count(result.data.total_pages)}</span>{f.page < result.data.total_pages && <Link className="button secondary" href={pageHref(f, f.page + 1)}>Next →</Link>}</div></div></section>}
    <div className="notice"><strong>Export and interpretation</strong><p>CSV downloads include all dates matching the date filters, across all pages and metrics, in long format with source lineage. Empty measurements remain empty; a dash in the table means no value is available. Separate page requests can observe subsequent database updates.</p></div>
  </Shell>;
}
