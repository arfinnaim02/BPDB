import Link from "next/link";
import { requireSession } from "../lib/auth";
import { readApi } from "../lib/backend";
import { calendar, count, timestamp } from "../lib/format";
import type { History, Summary } from "../lib/types";
import { Badge, ErrorPanel, Heading, Icon, Shell, Stat, Updated } from "../components/ui";
import { RunTable } from "../components/run-table";
export const dynamic = "force-dynamic";
export default async function Overview() {
  await requireSession();
  const [summary, history] = await Promise.all([
    readApi<Summary>("/api/v1/dataset/summary"), readApi<History>("/api/v1/collection/runs?limit=5"),
  ]);
  const data = summary.ok ? summary.data : null;
  const latest = history.ok ? history.data.items[0] : undefined;
  return <Shell active="/"><Heading eyebrow="YOUR DATA, IN VIEW" title="Workspace overview" description="A clear view of your national dataset and its daily collection pipeline."><Link className="button primary" href="/dataset">Explore dataset <Icon name="arrow"/></Link></Heading>
    {!summary.ok && <ErrorPanel message={summary.message}/>}
    {data && <><div className="section-meta"><span className="scope-tag">Validated national records</span><Updated at={data.generated_at}/></div><div className="stat-grid"><Stat label="CANONICAL DATES" value={count(data.canonical_dates)} detail="One current validated record per date" accent/><Stat label="LATEST OPERATIONAL DATE" value={calendar(data.latest_operational_date)} detail="Date covered by the latest canonical report"/><Stat label="HISTORY STARTS" value={calendar(data.earliest_operational_date)} detail="Earliest canonical operational date"/><Stat label="CALENDAR GAPS" value={count(data.missing_dates_between_bounds)} detail="Dates without a canonical record between bounds"/></div></>}
    <div className="overview-grid"><section className="panel pipeline-panel"><div className="panel-heading"><div><span className="tiny-label">DAILY OPERATION</span><h2>Collection pipeline</h2></div><Icon name="collection"/></div>{!history.ok ? <ErrorPanel message={history.message}/> : <><div className="pipeline-status">{latest ? <Badge status={latest.status}/> : <span className="muted">No recorded run</span>}<span className="muted">Latest worker outcome</span></div><dl className="detail-list"><div><dt>Latest run</dt><dd>{latest ? timestamp(latest.started_at) + " BD" : "Not recorded"}</dd></div><div><dt>Schedule target</dt><dd>12:00 · Asia/Dhaka</dd></div><div><dt>Execution</dt><dd>GitHub Actions · Python worker</dd></div><div><dt>Drive checkpoint</dt><dd>Verify in GitHub Actions</dd></div></dl><p className="small-note">Scheduled starts can be delayed. Worker success and Drive persistence are separate outcomes.</p><a href="https://github.com/arfinnaim02/BPDB/actions/workflows/daily-collection.yml" target="_blank" rel="noreferrer" className="inline-link">Open workflow runs ↗</a></>}</section>
    <section className="research-card"><span className="tiny-label">RESEARCH FOUNDATION</span><h2>Traceable data.<br/>Trustworthy next steps.</h2><p>Every displayed measurement comes from a current validated Neon record, with its original PDF reference and extraction evidence.</p><div className="research-tags"><span>Source lineage</span><span>Exact units</span><span>Version history</span></div><Link href="/quality" className="light-link">Review data coverage <Icon name="arrow"/></Link></section></div>
    <section className="panel"><div className="panel-heading"><div><h2>Recent collections</h2><p>The latest daily worker runs recorded in Neon.</p></div><Link href="/collection" className="inline-link">View all runs →</Link></div>{history.ok ? <RunTable runs={history.data.items}/> : <ErrorPanel message={history.message}/>}</section>
    <div className="notice"><strong>Current research scope</strong><p>Supported Page 1 national metrics. Regional, fuel-wise and recorded zonal load-shedding extraction are still pending. Calendar gaps do not prove that official reports are missing.</p></div>
  </Shell>;
}
