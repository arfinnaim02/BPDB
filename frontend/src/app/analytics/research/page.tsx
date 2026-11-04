import Link from "next/link";
import { requireSession } from "../../../lib/auth";
import { readApi } from "../../../lib/backend";
import { calendar } from "../../../lib/format";
import { exactDisplay } from "../../../lib/analytics-filters";
import { researchDailyChart, researchExports } from "../../../lib/research";
import type { ResearchPeriod, ResearchReport } from "../../../lib/research";
import { ErrorPanel, Heading, Shell, Stat } from "../../../components/ui";
import { ComparisonChart } from "../../../components/comparison-chart";
import { ResearchProfile } from "../../../components/research-profile";

import "./research.css";

export const dynamic = "force-dynamic";
const number = (value: string | null | undefined) => exactDisplay(value ?? null);

function PeriodTable({ rows, weekday = false, changes = false }: { rows: ResearchPeriod[]; weekday?: boolean; changes?: boolean }) {
  return <div className="table-scroll"><table>
    <caption className="sr-only">Frozen observed energy statistics and calendar coverage</caption>
    <thead><tr><th>Period</th><th>Eligible / calendar days</th><th>Missing / held</th><th>Mean</th><th>Median</th><th>Min – max</th><th>Sample SD</th>{!weekday && <th>Complete-period total</th>}{changes && <th>MoM total change</th>}</tr></thead>
    <tbody>{rows.map(r => <tr key={r.label}>
      <th scope="row">{r.label}</th><td>{r.eligible_days}/{r.calendar_days}<p className="small-note">{number(r.coverage_percent)}% · {r.complete ? "Complete" : "Incomplete"}</p></td>
      <td>{r.missing_days} / {r.held_days}</td><td className="numeric">{number(r.mean)}</td><td className="numeric">{number(r.median)}</td><td className="numeric">{number(r.minimum)} – {number(r.maximum)}</td><td className="numeric">{number(r.sample_sd)}</td>
      {!weekday && <td className="numeric">{number(r.complete_total)}{r.complete_total == null && <p className="small-note">Incomplete period</p>}</td>}
      {changes && <td className="numeric">{r.mom_total_percent == null ? "—" : `${number(r.mom_total_percent)}%`}<p className="small-note">{r.change_status === "two_complete_months" ? "Two complete months" : r.change_status === "no_previous_month" ? "No previous month" : r.change_status === "zero_previous_total" ? "Previous total is zero" : "Incomplete months"}</p></td>}
    </tr>)}</tbody>
  </table></div>;
}

export default async function Research({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireSession();
  const params = await searchParams;
  const selected = typeof params.month === "string" && /^(0[1-9]|1[0-2])$/.test(params.month) ? params.month : "01";
  const result = await readApi<ResearchReport>("/api/v1/analytics/frozen-2024");
  const d = result.ok ? result.data : null;
  return <Shell active="/analytics/research">
    <Heading eyebrow="REPRODUCIBLE RESEARCH · OBSERVED VALUES" title="Frozen research analysis" description="Explore the verified 2024 energy-generation baseline with coverage beside every comparison.">
      <div className="research-actions"><Link className="button secondary" href="/analytics/comparisons">Live-data comparisons →</Link>
      <details><summary className="button primary" style={{ cursor: "pointer" }}>Download analysis ↓</summary><div className="research-downloads">{researchExports.map(kind => <a className="button secondary" key={kind} href={`/api/research-analysis?table=${kind}`}>{kind === "report" ? "Full report JSON" : `${kind[0].toUpperCase()}${kind.slice(1)} CSV`}</a>)}</div></details></div>
    </Heading>
    {!result.ok && <ErrorPanel message={result.message}/>}
    {d && <>
      <div className="section-meta"><span className="scope-tag">Frozen · {calendar(d.config.start_date)} – {calendar(d.config.end_date)} · million kWh</span><span className="small-note">Snapshot {d.snapshot_id.slice(0, 12)} · no estimates</span></div>
      <div className="stat-grid"><Stat label="ORIGINAL OBSERVATIONS" value={String(d.observed_days)} detail={`${d.calendar_days} calendar days; exact source-derived daily values`}/><Stat label="MISSING DAYS" value={String(d.missing_days)} detail="Remain blank in tables and gaps in the daily chart"/><Stat label="UNHELD OBSERVATIONS" value={String(d.eligible_days)} detail={`${d.held_days} held by implemented review checks; not final model eligibility`}/><Stat label="MEAN DAILY ENERGY" value={number(d.statistics.mean)} detail="million kWh · observed unheld days only" accent/></div>
      <section className="notice"><strong>A fixed research baseline</strong><p>This page uses the archived snapshot, so later master-dataset updates do not silently change these results. Statistics exclude missing and review-held days. Incomplete periods have no complete-period total. Decimal statistics are rounded to six places; source values retain their stored precision.</p><p>These are descriptive comparisons. One year cannot establish recurring annual seasonality, and weekday differences are not causal effects. No forecasts or imputed values are displayed.</p></section>

      <section className="panel" id="daily-trend"><div className="panel-heading"><div><h2>Daily energy and complete seven-day trend</h2><p>Original eligible values and trailing means · million kWh</p></div></div>
        <ComparisonChart data={researchDailyChart(d.daily)} description="Frozen 2024 daily energy and trailing seven-day mean. Missing and held observations break the lines; seven-day means require seven consecutive eligible calendar days. Exact values follow in the daily table."/>
        <div className="panel-body"><p className="small-note">Use the slider to zoom and the legend to toggle lines. A trailing mean appears only when all seven calendar days are observed and unheld. It never fills a gap or uses a future day.</p></div>
      </section>

      <section className="panel" id="monthly-pattern"><div className="panel-heading"><div><h2>Monthly pattern and coverage</h2><p>Mean daily energy on the left axis; eligible calendar coverage on the right</p></div></div>
        <ResearchProfile rows={d.monthly} label="Monthly energy profile"/>
        <div className="panel-body"><p className="small-note">Amber bars describe an incomplete set of days. Compare them with their coverage before interpreting a rise or fall. Monthly totals and changes are shown only for complete months; month lengths differ.</p></div>
        <PeriodTable rows={d.monthly} changes/>
      </section>

      <section className="panel"><div className="panel-heading"><div><h2>Quarterly comparison</h2><p>Daily distribution summaries in million kWh; no annualized or coverage-scaled totals</p></div></div><PeriodTable rows={d.quarterly}/></section>

      <section className="panel" id="weekday-pattern"><div className="panel-heading"><div><h2>Weekday comparison</h2><p>Observed daily generation grouped Monday through Sunday</p></div></div>
        <ResearchProfile rows={d.weekday} label="Weekday energy comparison"/>
        <div className="panel-body"><p className="small-note">Each weekday can contain a different mixture of months and missing dates. These means describe that observed mixture; they do not isolate a weekday effect. No weekday energy totals are inferred.</p></div>
        <PeriodTable rows={d.weekday} weekday/>
      </section>

      <section className="panel"><div className="panel-heading"><div><h2>Chronological research split audit</h2><p>Coverage of the frozen training, validation and test periods</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>Split</th><th>Calendar days</th><th>Observed</th><th>Missing</th><th>Review held</th></tr></thead><tbody>{["train", "validation", "test"].map(split => <tr key={split}><th scope="row">{split === "train" ? "Training · Jan–Jun" : split === "validation" ? "Validation · Jul–Sep" : "Test · Oct–Dec"}</th><td>{d.splits[split].calendar_days}</td><td>{d.splits[split].observed_days}</td><td>{d.splits[split].missing_days}</td><td>{d.splits[split].review_held_days}</td></tr>)}</tbody></table></div>
        <div className="panel-body"><p><strong>Test coverage: {d.splits.test.observed_days}/{d.splits.test.calendar_days} days.</strong> A score on observed targets would not describe the full quarter. This audit is not a model evaluation; future methods must be selected with training/validation data and a documented evaluation protocol.</p></div>
      </section>

      <section className="panel" id="daily-table"><div className="panel-heading"><div><h2>Exact daily values and PDF evidence</h2><p>Original values remain visible, including any review-held value</p></div><form action="/analytics/research"><label className="small-note" htmlFor="month">Month </label><select id="month" name="month" defaultValue={selected} style={{ padding: 10 }}>{d.monthly.map(m => <option value={m.label.slice(5)} key={m.label}>{m.label}</option>)}</select><button className="button secondary" style={{ marginLeft: 10 }}>Show</button></form></div>
        <div className="table-scroll"><table><thead><tr><th>Operational date</th><th>Original energy</th><th>Complete 7-day mean</th><th>Observation state</th><th>Original PDF</th></tr></thead><tbody>{d.daily.filter(r => r.date.startsWith(`2024-${selected}`)).map(r => <tr key={r.date}><th scope="row">{calendar(r.date)}</th><td className="numeric">{number(r.original_value)}</td><td className="numeric">{number(r.trailing_7_mean)}</td><td>{r.review_hold ? "Review held" : r.eligible ? "Observed · unheld" : "Missing"}</td><td>{r.source_url ? <a className="inline-link" href={r.source_url} target="_blank" rel="noopener noreferrer">Official PDF ↗</a> : "—"}</td></tr>)}</tbody></table></div>
        <div className="panel-body"><p className="small-note">The frozen report records each PDF checksum. An official URL may later serve revised bytes; use the archived research bundle and retained PDF checksum when reproducing this study.</p></div>
      </section>

      <section className="notice"><details><summary>Reproducibility and interpretation notes</summary><p className="mono" style={{ overflowWrap: "anywhere" }}>Snapshot: {d.snapshot_id}<br/>Analysis: {d.analysis_id}</p><p>Verified repaired dates: {d.repaired_dates.join(", ")}.</p><ul>{d.limitations.map(l => <li key={l}>{l}</li>)}</ul><p><a className="inline-link" href="/api/research-analysis?table=report">Download the full analysis with identity and lineage →</a></p></details></section>
    </>}
  </Shell>;
}
