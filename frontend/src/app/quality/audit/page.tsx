import Link from "next/link";
import { requireSession } from "../../../lib/auth";
import { readApi } from "../../../lib/backend";
import { calendar, count, metricLabel, safeSourceUrl } from "../../../lib/format";
import { type Params } from "../../../lib/filters";
import type { AuditIssue, AuditReport, AuditSource } from "../../../lib/types";
import { Empty, ErrorPanel, Heading, Shell, Stat, Updated } from "../../../components/ui";
import { auditFilters, auditHref } from "../../../lib/audit-filters";
export const dynamic = "force-dynamic";

const labels: Record<string, string> = {
  registered_evidence: "Registered evidence found",
  archive_hints_only: "Archive hints only",
  no_date_linked_evidence: "No date-linked evidence in Neon",
  national_report_row_registered: "National report row registered",
  version_partial: "Partial report version present",
  version_quarantined: "Quarantined report version present",
  version_conflict: "Conflicting report version present",
  version_validated: "Validated version present, not canonical",
  source_quarantined: "Date-linked source is quarantined",
  source_review_required: "Date-linked source needs review",
  source_failed: "Date-linked source marked failed",
  date_linked_source_metadata: "Source report-date metadata or version link found",
  unresolved_extraction_issues: "Unresolved extraction issues recorded",
};


function Source({ source }: { source: AuditSource }) {
  const url = safeSourceUrl(source.url);
  return <div className="source-item">{url ? <a href={url} className="inline-link" target="_blank" rel="noreferrer">Open registered PDF ↗</a> : <span>Source URL unavailable</span>}<p>Status: {source.status.replaceAll("_", " ")}</p><p>Report-date metadata: {source.report_date_metadata ? calendar(source.report_date_metadata) : "Not recorded"}</p><p>Archive hint: {source.archive_date_hint ? calendar(source.archive_date_hint) : "Not recorded"}</p><p className="mono">SHA-256: {source.sha256}</p><p className="mono">Source: {source.id}</p></div>;
}
function Issues({ issues, total }: { issues: AuditIssue[]; total: number }) {
  return <><p className="small-note">{count(total)} recorded issues; showing {issues.length}.</p>{issues.map(issue => <div className="evidence-item" key={issue.id}><strong>{metricLabel(issue.code)}</strong><p>{issue.severity} · {issue.resolved ? "Resolved flag recorded" : "Unresolved"}</p>{issue.checks.length > 0 && <p>Checks: {issue.checks.map(metricLabel).join(", ")}</p>}<p className="mono">Source: {issue.source_id}{issue.version_id ? ` · Version: ${issue.version_id}` : ""}</p></div>)}</>;
}

export default async function Audit({ searchParams }: { searchParams: Promise<Params> }) {
  await requireSession();
  const f = auditFilters(await searchParams);
  const page = f.gapPage, sourcePage = f.sourcePage, pageSize = f.pageSize;
  const result = f.error ? {ok:false as const,message:f.error} : await readApi<AuditReport>(`/api/v1/dataset/audit?${f.query}`);
  const heading = <Heading eyebrow="REGISTERED EVIDENCE & PDF REVIEW" title="Source audit" description="Investigate missing canonical dates using registered evidence, then verify original PDFs."><Link href="/quality/review" className="button secondary">Review measurements →</Link><Link href="/quality" className="button secondary">← Data quality</Link></Heading>;
  if (!result.ok) return <Shell active="/quality">{heading}<ErrorPanel message={result.message}/></Shell>;
  const d = result.data;
  const href = (gap: number, source: number, section: string) => auditHref(f,gap,source,section);
  return <Shell active="/quality">{heading}
    <section className="panel"><form key={f.dates.toString()} className="filter-form" action="/quality/audit">
      <div className="field"><label htmlFor="start_date">Gap window from</label><input type="date" id="start_date" name="start_date" defaultValue={f.start}/></div>
      <div className="field"><label htmlFor="end_date">Gap window to</label><input type="date" id="end_date" name="end_date" defaultValue={f.end}/></div>
      <input type="hidden" name="gap_page_size" value={pageSize}/>
      <div className="filter-actions"><button className="button primary">Apply dates</button><Link href="/quality/audit" className="text-button">Reset</Link></div>
    </form><div className="panel-body"><p>Dates filter the missing-canonical-date worklist. The undated-source queue and PDF verification plan below remain full-history views.</p><a href={`/api/recovery-worklist?${f.dates}`} className="button secondary">Download complete recovery worklist ↓</a><p className="small-note">Includes every gap date in the selected window, across all pages; maximum 3,660 calendar days. Source detail lists remain capped with explicit counts and truncation flags. No PDFs are downloaded or records repaired by this export.</p><p><a className="inline-link" href="https://github.com/arfinnaim02/BPDB/actions/workflows/recovery-investigation.yml" target="_blank" rel="noreferrer">Open online gap investigation →</a></p><p className="small-note">Run the online GitHub investigation to retrieve bounded source candidates and preserve evidence in Drive. Original-PDF review is still required before any import or promotion.</p></div></section>
    <div className="section-meta"><span className="scope-tag">Read-only evidence review</span><Updated at={d.generated_at}/></div>
    <div className="stat-grid"><Stat label="MISSING CANONICAL DATES" value={count(d.missing_dates)} detail={`${calendar(d.selected_start_date)} – ${calendar(d.selected_end_date)} · selected window`}/><Stat label="DATE-LINKED EVIDENCE" value={count(d.gap_items.filter(g => g.assessment === "registered_evidence").length)} detail={`Among ${d.gap_items.length} dates on this page only`}/><Stat label="ARCHIVE HINTS ONLY" value={count(d.gap_items.filter(g => g.assessment === "archive_hints_only").length)} detail="Among displayed dates; operational date unconfirmed"/><Stat label="UNDATED HELD SOURCES" value={count(d.undated_source_count)} detail="Registered Page 1 sources without national date links"/></div>
    <div className="notice"><strong>Evidence is not an established cause</strong><p>No date-linked record in Neon does not prove a missing official PDF. Historical local quarantines and failed downloads may not have been registered. Archive hints must not be treated as operational dates.</p></div>

    <section className="panel" id="gap-audit"><div className="panel-heading"><div><h2>Missing-date evidence</h2><p>Individual gap dates, oldest first. No records are promoted, repaired or filled by this view.</p></div><form className="compact-form" action="/quality/audit"><label htmlFor="gap_page_size">Show</label><select name="gap_page_size" id="gap_page_size" defaultValue={pageSize}>{[10, 20, 50].map(n => <option key={n} value={n}>{n} dates</option>)}</select><input type="hidden" name="source_page" value={sourcePage}/><input type="hidden" name="start_date" value={f.start}/><input type="hidden" name="end_date" value={f.end}/><button className="button secondary">Apply</button></form></div>
      {!d.gap_items.length ? <Empty title={d.missing_dates ? "No gap dates on this page" : "No calendar gaps within observed bounds"} text="Dates are clipped to known canonical-history bounds; a filtered gap-only window is retained."/> : <div className="table-scroll"><table><caption className="sr-only">Registered evidence for missing canonical dates</caption><thead><tr><th>Operational date</th><th>Evidence assessment</th><th>Registered details</th><th>Official report status</th></tr></thead><tbody>{d.gap_items.map(g => <tr key={g.operational_date}><td className="table-strong nowrap">{calendar(g.operational_date)}</td><td><span className="table-strong">{labels[g.assessment] || metricLabel(g.assessment)}</span>{g.findings.map(f => <p key={f} className="small-note">{labels[f] || metricLabel(f)}</p>)}</td><td><details className="source-details"><summary>{g.version_count} versions · {g.source_count} sources · {g.archive_hint_count} hints</summary><div className="source-content">
        <h4>Report versions</h4><p className="small-note">Showing {g.versions.length} of {g.version_count}.</p>{g.versions.map(v => <div className="evidence-item" key={v.id}><strong>{v.quality_status} · {v.is_current ? "current pointer" : "not current"}</strong><p className="mono">Version: {v.id}</p><p className="mono">Stored parser/version key: {v.parser_version}</p></div>)}
        <h4>Date-linked source metadata</h4><p className="small-note">Showing {g.sources.length} of {g.source_count}. Report-date metadata or a national report-version link is present; verify the date inside the PDF.</p>{g.sources.map(s => <Source key={s.id} source={s}/>)}
        <h4>Archive-hint candidates</h4><p className="small-note">Showing {g.archive_hint_candidates.length} of {g.archive_hint_count}. These are possible matches only; a PDF may concern another operational date.</p>{g.archive_hint_candidates.map(s => <Source key={s.id} source={s}/>)}
        <h4>Extraction issues</h4><Issues issues={g.issues} total={g.issue_count}/>
      </div></details></td><td className="muted">Not assessed</td></tr>)}</tbody></table></div>}
      {d.gap_total_pages > 0 && <div className="pagination"><span>{count(d.missing_dates)} missing dates · page {page} / {d.gap_total_pages}</span><div>{page > 1 && <><Link href={href(1, sourcePage, "gap-audit")} className="button secondary">First</Link><Link href={href(page - 1, sourcePage, "gap-audit")} className="button secondary">← Previous</Link></>}{page < d.gap_total_pages && <Link href={href(page + 1, sourcePage, "gap-audit")} className="button secondary">Next →</Link>}</div></div>}
    </section>

    <section className="panel" id="undated"><div className="panel-heading"><div><h2>Held sources without operational-date links</h2><p>Quarantined, review-required or failed Page 1 sources with no report-date metadata or national version link. Archive hints do not resolve their operational dates.</p></div><span className="count-chip">{count(d.undated_source_count)}</span></div>
      {!d.undated_sources.length ? <Empty title="No undated held sources on this page" text="This is a registered-Neon queue, not proof that historical local extraction issues have all been resolved."/> : <div className="table-scroll"><table><caption className="sr-only">Undated registered sources held for review</caption><thead><tr><th>Source and date metadata</th><th>Recorded extraction issues</th></tr></thead><tbody>{d.undated_sources.map(item => <tr key={item.source.id}><td><Source source={item.source}/></td><td><Issues issues={item.issues} total={item.issue_count}/></td></tr>)}</tbody></table></div>}
      {d.source_total_pages > 0 && <div className="pagination"><span>Page {sourcePage} / {d.source_total_pages} · 10 sources per page</span><div>{sourcePage > 1 && <Link href={href(page, sourcePage - 1, "undated")} className="button secondary">← Previous</Link>}{sourcePage < d.source_total_pages && <Link href={href(page, sourcePage + 1, "undated")} className="button secondary">Next →</Link>}</div></div>}
    </section>

    <section className="panel" id="pdf-plan"><div className="panel-heading"><div><h2>Original-PDF verification plan</h2><p>{d.sample_policy}</p></div><span className="scope-tag">Verification not recorded here</span></div>
      <div className="panel-body"><ol style={{ listStyleType: "decimal", paddingLeft: 20 }}><li>Open each original PDF and confirm its operational date and legacy/modern layout.</li><li>Compare the displayed numbers, units and page references with the PDF; check any energy-unit conversion.</li><li>Record agreement, discrepancy or unreadable evidence with the PDF checksum and version ID. This page does not save or certify a completed review.</li></ol><p className="small-note">Showing {d.samples.length} of {d.sample_candidate_dates} candidate dates. These targeted checks are not a random estimate of extraction accuracy.</p></div>
      {d.sample_error ? <div className="notice error-notice"><strong>Sample evidence needs investigation</strong><p>{d.sample_error}</p></div> : !d.samples.length ? <Empty title="No canonical sample dates available" text="A verification plan appears when canonical records are available."/> : <div className="table-scroll"><table><caption className="sr-only">Pending original-PDF verification plan with canonical measurements</caption><thead><tr><th>Operational date</th><th>PDF links</th><th>Measurements and evidence</th></tr></thead><tbody>{d.samples.map(day => <tr key={day.report_version_id}><td className="table-strong nowrap">{calendar(day.operational_date)}</td><td>{day.sources.map(s => <div className="source-item" key={s.id}>{safeSourceUrl(s.url) ? <a className="inline-link" href={safeSourceUrl(s.url)} target="_blank" rel="noreferrer">Open original PDF ↗</a> : <span>Source URL unavailable</span>}<p>Linked to this canonical version</p><p className="mono">SHA-256: {s.sha256}</p><p className="mono">Source: {s.id}</p></div>)}</td><td><details className="source-details"><summary>Compare {day.measurements.length} measurements</summary><div className="source-content"><p className="mono">Version: {day.report_version_id}</p>{day.measurements.map((m, i) => <div className="evidence-item" key={i}><strong>{metricLabel(m.metric)}: {m.value ?? "null"} {m.unit}</strong><p>{m.period} · {m.fuel ?? "no fuel dimension"} · page {m.source_page ?? "unknown"}</p><p className="mono">Source: {m.source_id}</p>{m.raw_text && <blockquote>{m.raw_text}</blockquote>}</div>)}</div></details></td></tr>)}</tbody></table></div>}
    </section>
  </Shell>;
}

