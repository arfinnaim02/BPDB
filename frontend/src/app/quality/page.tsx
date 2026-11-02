import Link from "next/link";
import { requireSession } from "../../lib/auth";
import { readApi } from "../../lib/backend";
import { calendar, count } from "../../lib/format";
import { single, type Params } from "../../lib/filters";
import type { QualityReport } from "../../lib/types";
import { Empty, ErrorPanel, Heading, Shell, Stat, Updated } from "../../components/ui";
export const dynamic = "force-dynamic";

const percent = (value: number | null) => value == null ? "—" : `${value.toFixed(1)}%`;

function Coverage({ value }: { value: number | null }) {
  return <div className="metric-coverage"><div className="mini-track" aria-hidden="true"><span style={{ width: `${value ?? 0}%` }}/></div><span>{percent(value)}</span></div>;
}

export default async function Quality({ searchParams }: { searchParams: Promise<Params> }) {
  await requireSession();
  const params = await searchParams;
  const rawPage = single(params.gap_page) || "1";
  const page = /^\d+$/.test(rawPage) && Number(rawPage) >= 1 && Number(rawPage) <= 100000 ? Number(rawPage) : 1;
  const size = Number(single(params.gap_page_size));
  const pageSize = [20, 50, 100].includes(size) ? size : 20;
  const result = await readApi<QualityReport>(`/api/v1/dataset/quality?gap_page=${page}&gap_page_size=${pageSize}`);
  if (!result.ok) return <Shell active="/quality"><Heading eyebrow="COVERAGE & LIMITATIONS" title="Data quality" description="Full-history canonical coverage and calendar gaps."><Link href="/quality/audit" className="button secondary">Investigate sources →</Link></Heading><ErrorPanel message={result.message}/></Shell>;
  const d = result.data;
  const requestedYear = Number(single(params.metric_year));
  const selectedYear = d.years.some(y => y.year === requestedYear) ? requestedYear : null;
  const metricDenominator = selectedYear == null ? d.canonical_dates : d.years.find(y => y.year === selectedYear)!.canonical_dates;
  const gapHref = (next: number) => {
    const query = new URLSearchParams({ gap_page: String(next), gap_page_size: String(pageSize) });
    if (selectedYear != null) query.set("metric_year", String(selectedYear));
    return `/quality?${query}#calendar-gaps`;
  };

  return <Shell active="/quality">
    <Heading eyebrow="COVERAGE & LIMITATIONS" title="Data quality" description="Full-history coverage of current validated national records, with metric availability by year."><Link href="/quality/audit" className="button primary">Investigate sources →</Link></Heading>
    <div className="section-meta"><span className="scope-tag">All canonical history</span><Updated at={d.generated_at}/></div>
    <div className="stat-grid">
      <Stat label="CANONICAL DATES" value={count(d.canonical_dates)} detail="Current validated national records"/>
      <Stat label="CALENDAR COVERAGE" value={percent(d.calendar_coverage_percent)} detail="Canonical dates / inclusive calendar span" accent/>
      <Stat label="CALENDAR GAPS" value={count(d.missing_dates)} detail="Not a count of missing official PDFs"/>
      <Stat label="CALENDAR SPAN" value={count(d.calendar_days)} detail={`${calendar(d.earliest_operational_date)} – ${calendar(d.latest_operational_date)}`}/>
    </div>

    <section className="panel">
      <div className="panel-heading"><div><h2>Calendar coverage by year</h2><p>First and last years are bounded by the earliest and latest canonical dates. Dates outside those bounds are not assessed.</p></div></div>
      {!d.years.length ? <Empty title="No canonical history yet" text="Calendar and metric coverage will appear once validated records are available."/> : <div className="table-scroll"><table>
        <caption className="sr-only">Calendar coverage of each year within the observed historical bounds</caption>
        <thead><tr><th>Year</th><th className="numeric">Calendar days in scope</th><th className="numeric">Canonical dates</th><th className="numeric">Calendar gaps</th><th>Coverage</th></tr></thead>
        <tbody>{d.years.map(y => <tr key={y.year}><td className="table-strong">{y.year}</td><td className="numeric">{count(y.calendar_days)}</td><td className="numeric">{count(y.canonical_dates)}</td><td className="numeric">{count(y.missing_dates)}</td><td><Coverage value={y.coverage_percent}/></td></tr>)}</tbody>
      </table></div>}
    </section>

    <section className="panel">
      <div className="panel-heading"><div><h2>Metric availability · {selectedYear ?? "all history"}</h2><p>Dates with a non-null value / {count(metricDenominator)} canonical dates in this view. Zero is a value; absent or null observations are unavailable.</p></div>
        <form className="compact-form" action="/quality"><label htmlFor="metric_year">Period</label><select id="metric_year" name="metric_year" defaultValue={selectedYear ?? "all"}><option value="all">All history</option>{d.years.map(y => <option key={y.year} value={y.year}>{y.year}</option>)}</select><input type="hidden" name="gap_page_size" value={pageSize}/><button className="button secondary">Apply</button></form>
      </div>
      {!d.canonical_dates ? <Empty title="No metric coverage to assess" text="No current validated national dates are available."/> : <div className="table-scroll"><table>
        <caption className="sr-only">Full-history or selected-year metric availability, preserving unit, period and fuel dimensions</caption>
        <thead><tr><th>Metric and dimensions</th><th className="numeric">Dates with value</th><th className="numeric">Unavailable</th><th className="numeric">Zero values</th><th>Coverage</th>{selectedYear == null && <><th>First value date</th><th>Last value date</th></>}</tr></thead>
        <tbody>{d.metrics.map(metric => {
          const view = selectedYear == null ? metric : metric.by_year.find(y => y.year === selectedYear)!;
          return <tr key={JSON.stringify([metric.metric, metric.unit, metric.period, metric.fuel])}>
            <td><span className="table-strong">{metric.label}</span><span className="table-sub">{metric.unit} · {metric.period.replaceAll("_", " ")}{metric.fuel ? ` · fuel: ${metric.fuel}` : ""}</span></td>
            <td className="numeric">{count(view.non_null_dates)} / {count(view.canonical_dates)}</td><td className="numeric">{count(view.missing_or_null_dates)}</td><td className="numeric">{count(view.zero_dates)}</td><td><Coverage value={view.coverage_percent}/></td>
            {selectedYear == null && <><td className="nowrap">{metric.earliest_value_date ? calendar(metric.earliest_value_date) : "—"}</td><td className="nowrap">{metric.latest_value_date ? calendar(metric.latest_value_date) : "—"}</td></>}
          </tr>;
        })}</tbody>
      </table></div>}
      <div className="panel-body"><p className="small-note">Metric availability uses canonical dates, not the calendar span. Unsupported fields in older layouts can appear unavailable; this does not prove an extraction failure. Availability alone does not establish accuracy or suitability for forecasting.</p></div>
    </section>

    <section className="panel" id="calendar-gaps">
      <div className="panel-heading"><div><h2>Calendar gaps <span className="count-chip">{count(d.gaps.missing_dates)} dates</span></h2><p>{count(d.gaps.total_ranges)} contiguous ranges, oldest first. This list covers all history; the metric-year selector does not filter gaps.</p></div>
        <form className="compact-form" action="/quality"><label htmlFor="gap_page_size">Show</label><select id="gap_page_size" name="gap_page_size" defaultValue={pageSize}>{[20, 50, 100].map(n => <option key={n} value={n}>{n} ranges</option>)}</select>{selectedYear != null && <input type="hidden" name="metric_year" value={selectedYear}/>}<button className="button secondary">Apply</button></form>
      </div>
      {!d.gaps.items.length ? <Empty title={d.gaps.total_ranges ? "No gap ranges on this page" : "No calendar gaps within observed bounds"} text={d.gaps.total_ranges ? "Use Previous or return to page one." : "Only the span between the first and last canonical dates is assessed. This does not certify complete official-report coverage."}/> : <div className="table-scroll"><table>
        <caption className="sr-only">Contiguous dates with no current validated national record</caption>
        <thead><tr><th>From date</th><th>To date</th><th className="numeric">Missing dates</th><th>Canonical status</th><th>Official source status</th></tr></thead>
        <tbody>{d.gaps.items.map(g => <tr key={g.start_date}><td className="table-strong nowrap">{calendar(g.start_date)}</td><td className="nowrap">{calendar(g.end_date)}</td><td className="numeric">{count(g.days)}</td><td>No canonical record</td><td className="muted">Not assessed</td></tr>)}</tbody>
      </table></div>}
      {d.gaps.total_ranges > 0 && <div className="pagination"><span>{count(d.gaps.total_ranges)} ranges · {count(d.gaps.missing_dates)} missing canonical dates</span><div>{page > 1 && <Link className="button secondary" href={gapHref(page - 1)}>← Previous</Link>}<span>Page {count(page)} / {count(d.gaps.total_pages)}</span>{page < d.gaps.total_pages && <Link className="button secondary" href={gapHref(page + 1)}>Next →</Link>}</div></div>}
    </section>

    <div className="quality-notes">
      <div className="notice"><strong>Gaps need investigation</strong><p>A missing canonical date may reflect an unavailable report, failed extraction, quarantine or an unresolved conflict. This page does not assign a cause without source evidence.</p></div>
      <div className="notice"><strong>Availability is not validation</strong><p>Values are counted across all canonical records. Publication times, outliers, reconciliation, source conflicts and original-PDF verification require separate audits. Missing observations are never changed to zero.</p></div>
    </div>
  </Shell>;
}

