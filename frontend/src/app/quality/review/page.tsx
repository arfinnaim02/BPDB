import Link from "next/link";
import { requireSession } from "../../../lib/auth";
import { readApi } from "../../../lib/backend";
import { calendar, count, metricLabel, safeSourceUrl } from "../../../lib/format";
import { single, validDate, type Params } from "../../../lib/filters";
import { Empty, ErrorPanel, Heading, Shell, Stat, Updated } from "../../../components/ui";

export const dynamic = "force-dynamic";

type Measurement = {
  metric: string; value: string | null; unit: string; period: string;
  source_id: string; source_page: number | null; raw_text: string | null;
  source_url: string | null; source_sha256: string | null; source_linked: boolean;
};
type Review = {
  generated_at: string; rule_version: string; canonical_dates: number; energy_peak_pairs: number;
  flagged_dates: number; flag_counts: Record<string, number>; page: number; page_size: number;
  total_pages: number; data_fingerprint: string; limitation: string;
  items: { operational_date: string; version_id: string; energy_to_peak_ratio: string | null;
    flags: { code: string; kind: string; explanation: string }[]; measurements: Measurement[] }[];
};

export default async function MeasurementReview({ searchParams }: { searchParams: Promise<Params> }) {
  await requireSession();
  const p = await searchParams;
  const rawPage = single(p.page) || "1";
  const page = /^\d+$/.test(rawPage) && Number(rawPage) >= 1 && Number(rawPage) <= 100000 ? Number(rawPage) : 1;
  const rawSize = Number(single(p.page_size));
  const size = [10, 20, 50].includes(rawSize) ? rawSize : 20;
  const start = single(p.start_date) || "";
  const end = single(p.end_date) || "";
  const query = new URLSearchParams({ page: String(page), page_size: String(size) });
  if (start) query.set("start_date", start);
  if (end) query.set("end_date", end);
  const heading = <Heading eyebrow="SOURCE REVIEW BEFORE MODELLING" title="Measurement review" description="Screen existing national energy and generation values, then inspect their original PDFs."><Link href="/quality" className="button secondary">← Data quality</Link></Heading>;
  const error = (start && !validDate(start)) || (end && !validDate(end))
    ? "Use valid dates in YYYY-MM-DD format." : start && end && start > end
      ? "The start date must be on or before the end date." : null;
  if (error) return <Shell active="/quality/review">{heading}<div className="notice error-notice" role="alert"><strong>Check the date filters</strong><p>{error}</p><Link className="inline-link" href="/quality/review">Reset filters</Link></div></Shell>;
  const result = await readApi<Review>(`/api/v1/dataset/measurement-review?${query}`);
  if (!result.ok) return <Shell active="/quality/review">{heading}<ErrorPanel message={result.message}/></Shell>;
  const d = result.data;
  const href = (next: number) => { const q = new URLSearchParams(query); q.set("page", String(next)); return `/quality/review?${q}`; };
  return <Shell active="/quality/review">{heading}
    <div className="section-meta"><span className="scope-tag">Read-only screening · {d.rule_version}</span><Updated at={d.generated_at}/></div>
    <div className="stat-grid three"><Stat label="CANONICAL DATES IN WINDOW" value={count(d.canonical_dates)} detail="Current validated national records"/><Stat label="ENERGY / PEAK PAIRS CHECKED" value={count(d.energy_peak_pairs)} detail="Available, correctly dimensioned energy and positive maximum MW"/><Stat label="DATES REQUIRING REVIEW" value={count(d.flagged_dates)} detail="Flagged by at least one rule; not confirmed errors"/></div>
    <div className="notice"><strong>A review flag is not a correction</strong><p>{d.limitation}</p></div>
    <section className="panel"><form action="/quality/review" className="filter-form"><div className="field"><label htmlFor="start_date">From date</label><input type="date" id="start_date" name="start_date" defaultValue={start}/></div><div className="field"><label htmlFor="end_date">To date</label><input type="date" id="end_date" name="end_date" defaultValue={end}/></div><div className="field"><label htmlFor="page_size">Rows per page</label><select id="page_size" name="page_size" defaultValue={size}>{[10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}</select></div><div className="filter-actions"><button className="button primary">Apply filters</button><Link href="/quality/review" className="inline-link">Reset</Link></div></form></section>
    <section className="panel"><div className="panel-heading"><div><h2>Screening rules</h2><p>Explicit consistency checks and one heuristic; no statistical accuracy claim.</p></div></div><div className="panel-body"><ul style={{ listStyleType: "disc", paddingLeft: 20 }}><li>Energy upper bound: maximum MW × 24 / 1000, in million kWh.</li><li>Energy lower bound, when available: minimum MW × 24 / 1000. Confirm that the source definitions align.</li><li>Energy rounding tolerance: larger of 0.1 million kWh or 0.1% of the applicable bound.</li><li>Heuristic: energy / upper bound below 0.10. This threshold prioritizes review; it is not an established BPDB operating limit.</li><li>Generation exceeding daily maximum by more than 1 MW, non-positive core values, unexpected dimensions and missing version-source links.</li></ul>{Object.entries(d.flag_counts).map(([code, n]) => <p key={code}><strong>{metricLabel(code)}:</strong> {count(n)} dates</p>)}</div></section>
    <section className="panel"><div className="panel-heading"><div><h2>Original-source review queue</h2><p>Oldest operational date first. Expand evidence to compare the extracted text with the actual PDF.</p></div><span className="count-chip">{count(d.flagged_dates)} dates</span></div>
      {!d.items.length ? <Empty title={d.flagged_dates ? "No flagged dates on this page" : "No flags from these screening rules"} text="This does not certify the original PDFs, other metrics, or the accuracy of unflagged values."/> : <div className="table-scroll"><table><caption className="sr-only">Flagged national measurements with original source evidence</caption><thead><tr><th>Operational date</th><th>Review reasons</th><th>Energy / peak ceiling</th><th>Source evidence</th></tr></thead><tbody>{d.items.map(day => <tr key={day.version_id}><td><Link className="inline-link" href={`/dataset?${new URLSearchParams({ start_date: day.operational_date, end_date: day.operational_date })}`}>{calendar(day.operational_date)} ↗</Link></td><td>{day.flags.map(flag => <div className="evidence-item" key={flag.code}><strong>{metricLabel(flag.code)}</strong><p>{flag.kind === "heuristic" ? "Heuristic review" : "Consistency review"}</p><p>{flag.explanation}</p></div>)}</td><td className="mono">{day.energy_to_peak_ratio ?? "Unavailable"}</td><td><details className="source-details"><summary>Compare {day.measurements.length} measurements</summary><div className="source-content"><p className="mono">Version: {day.version_id}</p>{day.measurements.map((m, i) => <div className="evidence-item" key={i}><strong>{metricLabel(m.metric)}: {m.value ?? "null"} {m.unit}</strong><p>{m.period} · PDF page {m.source_page ?? "not recorded"}</p>{m.source_url && safeSourceUrl(m.source_url) ? <a href={safeSourceUrl(m.source_url)} className="inline-link" target="_blank" rel="noreferrer">Open original PDF ↗</a> : <p>Original link unavailable</p>}<p className="mono">SHA-256: {m.source_sha256 ?? "Not recorded"}</p><p className="mono">Source: {m.source_id}</p><p>Version-source link: {m.source_linked ? "Present" : "Missing"}</p>{m.raw_text && <blockquote>{m.raw_text}</blockquote>}</div>)}</div></details></td></tr>)}</tbody></table></div>}
      {d.total_pages > 0 && <div className="pagination"><span>Page {page} / {d.total_pages}</span><div>{page > 1 && <Link className="button secondary" href={href(page - 1)}>← Previous</Link>}{page < d.total_pages && <Link className="button secondary" href={href(page + 1)}>Next →</Link>}</div></div>}
    </section>
    <div className="notice"><strong>How to resolve a flag</strong><p>Confirm the operational date and printed value in the PDF. Record whether it agrees, differs, or is unreadable. A confirmed parser correction must be tested and imported as a new version before changing the canonical pointer. This page does not save review decisions.</p><p className="mono">Request fingerprint: {d.data_fingerprint}</p><p>This identifies the screened data and rules, not a saved research dataset.</p></div>
  </Shell>;
}
