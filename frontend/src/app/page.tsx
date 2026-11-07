import Link from "next/link";
import { requireSession } from "../lib/auth";
import { readApi } from "../lib/backend";
import { calendar, count } from "../lib/format";
import type { Summary } from "../lib/types";
import { ErrorPanel, Heading, Icon, Shell, Stat, Updated } from "../components/ui";
export const dynamic = "force-dynamic";
export default async function Overview() {
  await requireSession();
  const summary = await readApi<Summary>("/api/v1/dataset/summary");
  const data = summary.ok ? summary.data : null;
  return <Shell active="/"><Heading eyebrow="YOUR RESEARCH, IN VIEW" title="Workspace overview" description="Explore national power-sector data, historical trends and forecasting results."><Link className="button primary" href="/dataset">Explore dataset <Icon name="arrow"/></Link></Heading>
    {!summary.ok && <ErrorPanel message={summary.message}/>}
    {data && <><div className="section-meta"><span className="scope-tag">Validated national records</span><Updated at={data.generated_at}/></div><div className="stat-grid"><Stat label="CANONICAL DATES" value={count(data.canonical_dates)} detail="One current validated record per date" accent/><Stat label="LATEST OPERATIONAL DATE" value={calendar(data.latest_operational_date)} detail="Date covered by the latest canonical report"/><Stat label="HISTORY STARTS" value={calendar(data.earliest_operational_date)} detail="Earliest canonical operational date"/><Stat label="CALENDAR GAPS" value={count(data.missing_dates_between_bounds)} detail="Dates without a canonical record between bounds"/></div></>}
    <div className="overview-grid"><section className="panel"><div className="panel-heading"><div><span className="tiny-label">ANALYSIS & COMPARISONS</span><h2>Understand the data</h2></div><Icon name="grid"/></div><div className="panel-body"><p>Explore generation and demand, compare periods and examine the coverage behind each result.</p><p><Link href="/analytics" className="inline-link">Generation & demand →</Link></p><p><Link href="/analytics/comparisons" className="inline-link">Trends & comparisons →</Link></p><p><Link href="/quality" className="inline-link">Data quality & coverage →</Link></p></div></section>
    <section className="research-card"><span className="tiny-label">MODELS & RESULTS</span><h2>Compare models.<br/>Inspect predictions.</h2><p>Review chronological experiments, the retained final evaluation and separately recorded research forecasts.</p><p><Link href="/analytics/final-evaluation" className="light-link">Final evaluation <Icon name="arrow"/></Link></p><p><Link href="/forecasts" className="light-link">Research forecasts <Icon name="arrow"/></Link></p></section></div>
    <section className="panel"><div className="panel-heading"><div><h2>Detailed research report</h2><p>Methods, model comparisons, monthly errors, figures and interpretation.</p></div><Link href="/reports" className="button primary">Open research report →</Link></div><div className="panel-body"><p>Read the expanded results and download the PDF, numerical tables, editable figures and source evidence. Historical test performance and prospective forecast outcomes are reported separately.</p></div></section>
    <div className="notice"><strong>Current research scope</strong><p>Supported Page 1 national metrics. Regional, fuel-wise and recorded zonal load-shedding extraction are still pending. Calendar gaps do not prove that official reports are missing.</p></div>
  </Shell>;
}
