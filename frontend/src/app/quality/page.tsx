import { requireSession } from "../../lib/auth";
import { readApi } from "../../lib/backend";
import { calendar, count, metricLabel } from "../../lib/format";
import { COLUMNS } from "../../lib/filters";
import type { Master, Summary } from "../../lib/types";
import { Empty, ErrorPanel, Heading, Shell, Stat, Updated } from "../../components/ui";
export const dynamic = "force-dynamic";
export default async function Quality() {
  await requireSession();
  const [summary, sample] = await Promise.all([readApi<Summary>("/api/v1/dataset/summary"), readApi<Master>("/api/v1/dataset/daily?page_size=100")]);
  const d = summary.ok ? summary.data : null;
  const span = d ? d.canonical_dates + d.missing_dates_between_bounds : 0;
  const coverage = d && span ? 100 * d.canonical_dates / span : null;
  const days = sample.ok ? sample.data.items : [];
  return <Shell active="/quality"><Heading eyebrow="COVERAGE & LIMITATIONS" title="Data quality" description="Understand calendar coverage and available measurements before starting analysis."/>
    {!summary.ok && <ErrorPanel message={summary.message}/>}
    {d && <><div className="section-meta"><span className="scope-tag">Canonical records only</span><Updated at={d.generated_at}/></div><div className="stat-grid three"><Stat label="CALENDAR COVERAGE" value={coverage == null ? "—" : `${coverage.toFixed(1)}%`} detail="Canonical dates / inclusive calendar span" accent/><Stat label="CALENDAR GAPS" value={count(d.missing_dates_between_bounds)} detail="Not a count of missing official PDFs"/><Stat label="CALENDAR SPAN" value={count(span)} detail={`${calendar(d.earliest_operational_date)} – ${calendar(d.latest_operational_date)}`}/></div>
    <section className="panel"><div className="panel-heading"><div><h2>Historical date coverage</h2><p>Presence of a current validated national record, not completeness of every metric.</p></div></div><div className="panel-body"><div className="coverage-track" role="img" aria-label={coverage == null ? "No canonical dates" : `${coverage.toFixed(1)} percent calendar coverage`}><span style={{ width: `${coverage ?? 0}%` }}/></div><div className="coverage-legend"><span><i className="legend-dot teal"/> {count(d.canonical_dates)} canonical dates</span><span><i className="legend-dot pale"/> {count(d.missing_dates_between_bounds)} calendar gaps</span></div></div></section></>}
    <section className="panel"><div className="panel-heading"><div><h2>Recent metric availability</h2><p>Non-null observations in the latest {days.length} canonical dates. This is a recent sample, not full-history coverage.</p></div><span className="scope-tag">Up to 100 dates</span></div>{!sample.ok ? <ErrorPanel message={sample.message}/> : !days.length ? <Empty title="No canonical observations yet" text="Metric coverage appears after canonical data is available."/> : <div className="table-scroll"><table><caption className="sr-only">Recent sample metric availability</caption><thead><tr><th>Metric</th><th className="numeric">Dates with value</th><th>Sample coverage</th></tr></thead><tbody>{COLUMNS.map(metric => { const present = days.filter(day => day.measurements.some(m => m.metric === metric && m.value !== null)).length; const pct = 100 * present / days.length; return <tr key={metric}><td className="table-strong">{metricLabel(metric)}</td><td className="numeric">{present} / {days.length}</td><td><div className="metric-coverage"><div className="mini-track"><span style={{ width: `${pct}%` }}/></div><span>{pct.toFixed(0)}%</span></div></td></tr>; })}</tbody></table></div>}</section>
    <div className="quality-notes"><div className="notice"><strong>What these measures tell you</strong><p>A date can be validated for its supported layout while some metrics remain unavailable. Legacy and modern reports expose different fields. Missing values must not be replaced with zero.</p></div><div className="notice"><strong>What still needs an audit</strong><p>Full-history metric coverage, quarantine reasons, source conflicts and publication-time availability require further review. Quarantined sources are excluded from these canonical views.</p></div></div>
  </Shell>;
}
