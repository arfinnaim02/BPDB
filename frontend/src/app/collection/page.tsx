import { requireSession } from "../../lib/auth";
import { readApi } from "../../lib/backend";
import type { History } from "../../lib/types";
import { count } from "../../lib/format";
import { ErrorPanel, Heading, Shell, Stat } from "../../components/ui";
import { RunTable } from "../../components/run-table";
export const dynamic = "force-dynamic";
export default async function Collection({ searchParams }: { searchParams: Promise<{ limit?: string }> }) {
  await requireSession();
  const params = await searchParams;
  const limit = [20, 50, 100].includes(Number(params.limit)) ? Number(params.limit) : 20;
  const result = await readApi<History>(`/api/v1/collection/runs?limit=${limit}`);
  const runs = result.ok ? result.data.items : [];
  return <Shell active="/collection"><Heading eyebrow="PIPELINE OPERATIONS" title="Collection history" description="Follow daily worker outcomes, newly downloaded PDFs and canonical promotions."><a className="button secondary" href="https://github.com/arfinnaim02/BPDB/actions/workflows/daily-collection.yml" target="_blank" rel="noreferrer">GitHub workflow ↗</a></Heading>
    {!result.ok ? <ErrorPanel message={result.message}/> : <><div className="stat-grid three"><Stat label="RUNS IN THIS VIEW" value={count(runs.length)} detail={`Most recent ${limit} requested`}/><Stat label="SUCCEEDED" value={count(runs.filter(r => r.status === "succeeded").length)} detail="Worker outcomes in this view" accent/><Stat label="NEED ATTENTION" value={count(runs.filter(r => ["partial", "failed"].includes(r.status)).length)} detail="Partial or failed runs in this view"/></div>
    <section className="panel"><div className="panel-heading"><div><h2>Worker run log</h2><p>Bangladesh time · newest first · daily worker runs only</p></div><form className="compact-form"><label htmlFor="limit">Show</label><select name="limit" id="limit" defaultValue={limit}>{[20, 50, 100].map(n => <option key={n} value={n}>{n} runs</option>)}</select><button className="button secondary">Apply</button></form></div><RunTable runs={runs} detailed/></section></>}
    <div className="notice"><strong>Read the two outcomes together</strong><p>This table reports the worker outcome. Google Drive checkpoint results are recorded separately in GitHub Actions. A run with no promotions can be healthy when reports have already been processed.</p></div>
    <section className="panel"><div className="panel-heading"><div><h2>Schedule and controls</h2><p>Daily target: 12:00 Bangladesh time. GitHub may start scheduled jobs later.</p></div></div><div className="panel-body"><p>To run collection manually, open the workflow and choose <strong>Run workflow</strong>. Collection credentials and write operations remain in the worker environment.</p><p className="small-note">This website provides read-only monitoring. Historical backfill and correction review are not exposed as browser write controls.</p></div></section>
  </Shell>;
}
