import Link from "next/link";
import { requireSession } from "../../lib/auth";
import { readApi } from "../../lib/backend";
import { ANALYTIC_METRICS, analyticsFilters, exactDisplay } from "../../lib/analytics-filters";
import { calendar, count } from "../../lib/format";
import type { Params } from "../../lib/filters";
import type { AnalyticsReport } from "../../lib/types";
import { Empty, ErrorPanel, Heading, Shell, Stat, Updated } from "../../components/ui";
import { HistoryChart } from "../../components/history-chart";
export const dynamic = "force-dynamic";

export default async function Analytics({ searchParams }: { searchParams: Promise<Params> }) {
  await requireSession();
  const f = analyticsFilters(await searchParams);
  const result = f.error ? null : await readApi<AnalyticsReport>(`/api/v1/analytics/generation-demand?${f.query}`);
  const d = result?.ok ? result.data : null;
  const unit = d?.unit === "million_kWh" ? "million kWh" : "MW";
  const energy = d?.aggregation === "observed_sum";
  const tableSize = 50;
  const tablePages = d ? Math.ceil(d.points.length / tableSize) : 0;
  const tablePoints = d?.points.slice((f.page - 1) * tableSize, f.page * tableSize) ?? [];
  const href = (page: number) => { const q = new URLSearchParams(f.query); q.set("table_page", String(page)); return `/analytics?${q}#period-table`; };
  return <Shell active="/analytics">
    <Heading eyebrow="OBSERVED NATIONAL HISTORY" title="Generation & demand" description="Explore available measurements with coverage-aware summaries. No imputation or forecasts."><Link href="/analytics/comparisons" className="button primary">Trends & comparisons →</Link><Link href="/quality" className="button secondary">Review data quality →</Link></Heading>
    <section className="panel filter-panel"><form key={f.query.toString()} action="/analytics" className="filter-form">
      <div className="field"><label htmlFor="metric">Measurement</label><select id="metric" name="metric" defaultValue={f.metric}>{ANALYTIC_METRICS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
      <div className="field"><label htmlFor="resolution">View</label><select id="resolution" name="resolution" defaultValue={f.resolution}><option value="daily">Daily</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></div>
      <div className="field"><label htmlFor="start_date">From date</label><input type="date" id="start_date" name="start_date" defaultValue={f.start}/></div>
      <div className="field"><label htmlFor="end_date">To date</label><input type="date" id="end_date" name="end_date" defaultValue={f.end}/></div>
      <div className="filter-actions"><button className="button primary">Apply filters</button><Link className="text-button" href="/analytics">Reset</Link></div>
    </form></section>
    {f.error && <div role="alert" className="notice error-notice">{f.error}</div>}
    {result && !result.ok && <ErrorPanel message={result.message}/>}
    {d && <>
      <div className="section-meta"><span className="scope-tag">{d.resolution} · {energy ? "observed energy sums" : "observed daily means"}</span><Updated at={d.generated_at}/></div>
      <div className="stat-grid"><Stat label="DATES WITH A VALUE" value={count(d.statistics.observations)} detail={`${count(d.calendar_days)} calendar days · ${count(d.canonical_dates)} canonical dates`}/><Stat label={energy ? `OBSERVED ENERGY (${unit})` : `MEAN DAILY VALUE (${unit})`} value={exactDisplay(energy ? d.statistics.observed_total : d.statistics.mean)} detail={energy ? "Sum over observed dates only" : "Arithmetic mean of available daily values"} accent/><Stat label={`MINIMUM DAILY VALUE (${unit})`} value={exactDisplay(d.statistics.minimum)} detail="Lowest observed value in the selected window"/><Stat label={`MAXIMUM DAILY VALUE (${unit})`} value={exactDisplay(d.statistics.maximum)} detail="Highest observed value in the selected window"/></div>
      <div className="notice"><strong>Availability varies with the source layout</strong><p>{d.parser_support === "legacy_and_modern" ? "This metric is supported by both existing legacy and modern parsers." : "This metric is supported by the modern parser; older reports may not provide a comparable field."} In this window, values cover {d.metric_calendar_coverage_percent == null ? "—" : `${d.metric_calendar_coverage_percent.toFixed(1)}%`} of calendar days. There are {count(d.missing_canonical_dates)} missing canonical dates and {count(d.unavailable_metric_dates)} canonical dates without a value for this metric.</p></div>
      {!d.start_date ? <Empty title="No overlap with canonical history" text={`Available canonical date bounds: ${calendar(d.earliest_canonical_date)} – ${calendar(d.latest_canonical_date)}. Try another date range.`}/> : <>
        <section className="panel"><div className="panel-heading"><div><h2>{d.label} · observed history</h2><p>{calendar(d.start_date)} – {calendar(d.end_date)} · selected dates are clipped to known canonical-history bounds</p></div></div>
          {d.statistics.observations ? <HistoryChart report={d}/> : <Empty title="No non-null measurements in this window" text="Unavailable values remain blank. Try a different metric or date range."/>}
          <div className="panel-body"><p className="small-note">{energy ? "Period values are sums of observed daily energy; incomplete periods are not estimated full-period totals." : "Period values are arithmetic means of observed daily MW measurements. MW values are never summed across days."} Missing values break the line. Amber points indicate incomplete periods or date-window slices. Use the slider to zoom; the period table retains exact decimal strings.</p></div>
        </section>
        <section className="panel"><div className="panel-heading"><div><h2>Daily-value descriptive statistics</h2><p>Calculated from the available daily observations, independent of the chart resolution.</p></div></div><dl className="detail-list"><div><dt>Mean ({unit})</dt><dd>{exactDisplay(d.statistics.mean)}</dd></div><div><dt>Median ({unit})</dt><dd>{exactDisplay(d.statistics.median)}</dd></div><div><dt>Sample standard deviation ({unit})</dt><dd>{exactDisplay(d.statistics.sample_stddev)}</dd></div><div><dt>Observed zero days</dt><dd>{count(d.statistics.zero_days)}</dd></div><div><dt>First available value</dt><dd>{d.first_value_date ? calendar(d.first_value_date) : "Not available"}</dd></div><div><dt>Last available value</dt><dd>{d.last_value_date ? calendar(d.last_value_date) : "Not available"}</dd></div></dl><div className="panel-body"><p className="small-note">Derived statistics are rounded to six decimal places. Standard deviation describes spread; it is not a forecast interval or an uncertainty estimate for independent observations.</p></div></section>
        <section className="panel" id="period-table"><div className="panel-heading"><div><h2>{d.resolution[0].toUpperCase() + d.resolution.slice(1)} period table</h2><p>Open a period to inspect the corresponding source records. Empty means no observed value; zero remains zero.</p></div><span className="scope-tag">{count(d.points.length)} periods</span></div>
          {!tablePoints.length ? <Empty title="No periods on this page" text="Return to the first table page."/> : <div className="table-scroll"><table><caption className="sr-only">Observed values and completeness of each period</caption><thead><tr><th>Period</th><th className="numeric">{energy ? "Observed sum" : "Observed mean"} ({unit})</th><th className="numeric">Observed / calendar days</th><th className="numeric">Min daily value</th><th className="numeric">Max daily value</th><th>Coverage status</th></tr></thead><tbody>{tablePoints.map(p => <tr key={p.label}><td><Link className="inline-link" href={`/dataset?${new URLSearchParams({ start_date: p.start_date, end_date: p.end_date, column: d.metric })}`}>{p.label} ↗</Link></td><td className="numeric table-strong">{exactDisplay(p.value)}</td><td className="numeric">{p.observed_days} / {p.expected_days}</td><td className="numeric">{exactDisplay(p.minimum)}</td><td className="numeric">{exactDisplay(p.maximum)}</td><td><span className={`badge ${p.complete_period ? "success" : "warning"}`}>{p.observed_days === 0 ? "No observations" : p.complete_period ? "Complete period" : !p.full_period_selected ? "Date-window slice" : "Partial observations"}</span></td></tr>)}</tbody></table></div>}
          {tablePages > 0 && <div className="pagination"><span>Table page {f.page} / {tablePages} · chart includes all periods</span><div>{f.page > 1 && <><Link className="button secondary" href={href(1)}>First</Link><Link className="button secondary" href={href(f.page - 1)}>← Previous</Link></>}{f.page < tablePages && <Link className="button secondary" href={href(f.page + 1)}>Next →</Link>}</div></div>}
        </section>
      </>}
      <div className="notice"><strong>Research interpretation</strong><p>Unverified source gaps remain unknown. This view does not label every gap as an unavailable official report, estimate missing values, mix unlike definitions, or establish causal relationships.</p><p className="mono">Request data fingerprint: {d.data_fingerprint}</p><p>This fingerprint identifies the selected records and values; it is not a saved research snapshot or model result.</p></div>
    </>}
  </Shell>;
}

