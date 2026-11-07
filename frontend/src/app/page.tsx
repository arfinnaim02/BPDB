import Link from 'next/link';
import {requireSession} from '../lib/auth';
import {readApi} from '../lib/backend';
import {calendar,count} from '../lib/format';
import {latestWindow} from '../lib/exploration';
import type {Summary,AnalyticsReport} from '../lib/types';
import type {ForecastHistory} from '../lib/forecasts';
import type {FinalEvaluation} from '../lib/final-evaluation';
import {Shell,Heading,Stat,ErrorPanel,Icon} from '../components/ui';
import {ExplorationCharts} from '../components/studio-charts';
import {ModelEvidenceCharts} from '../components/model-evidence-charts';
export const dynamic='force-dynamic';
export default async function Overview(){
 await requireSession();const summary=await readApi<Summary>('/api/v1/dataset/summary');const d=summary.ok?summary.data:null;const window=latestWindow(d?.latest_operational_date??null);
 const q=new URLSearchParams({metric:'energy_generated',resolution:'daily'});if(window.start)q.set('start_date',window.start);if(window.end)q.set('end_date',window.end);
 const [history,forecast,model]=await Promise.all([d?readApi<AnalyticsReport>(`/api/v1/analytics/generation-demand?${q}`):Promise.resolve(null),readApi<ForecastHistory>('/api/v1/forecasts?limit=20'),readApi<FinalEvaluation>('/api/v1/research/release3')]);
 const energy=history?.ok?history.data:null;const f=forecast.ok?forecast.data:null;const latest=f?.items[0];
 return <Shell active="/"><Heading eyebrow="BANGLADESH · POWER ANALYTICS" title="See the system. Understand the patterns." description="A research workspace for observed electricity data, transparent comparisons and evidence-backed interpretation."><Link className="button primary" href="/explore">Start exploring <Icon name="arrow"/></Link><Link className="button secondary" href="/reports">Research report ↓</Link></Heading>
 {!summary.ok&&<ErrorPanel message={summary.message}/>}
 <section className="workspace-hero"><div><span className="hero-kicker">YOUR ANALYTICAL WORKSPACE</span><h2>From daily observations<br/>to informed questions.</h2><p>Follow the trend, compare periods, examine uncertainty and inspect the original evidence before drawing a conclusion.</p><div className="hero-links"><Link href="/explore">Explore data ↗</Link><Link href="/insights">Planning insights ↗</Link></div></div><div className="hero-status"><span className="status-orbit" aria-hidden="true"><Icon name="bolt"/></span><span>Latest canonical operational date</span><strong>{calendar(d?.latest_operational_date??null)}</strong><small>National measurements · official source evidence</small></div></section>
 {d&&<div className="stat-grid"><Stat label="HISTORICAL DATES" value={count(d.canonical_dates)} detail={`Since ${calendar(d.earliest_operational_date)}`}/><Stat label="RECENT ENERGY COVERAGE" value={energy?.metric_calendar_coverage_percent==null?'—':`${energy.metric_calendar_coverage_percent.toFixed(1)}%`} detail="Available daily values in the latest selected 365-day window" accent/><Stat label="LATEST FORECAST TARGET" value={latest?calendar(latest.target_date):'Not available'} detail={latest?.status==='withheld'?'Prediction withheld; inspect its evidence':'Latest retained issue; may not be tomorrow’s target'}/><Stat label="PROSPECTIVE SCORED DATES" value={f?String(f.summary.scored_dates):'—'} detail="Separate 90-day outcome log; pending actuals stay unavailable"/></div>}
 <div className="section-title"><div><span className="tiny-label">RECENT OBSERVED HISTORY</span><h2>National energy at a glance</h2><p>{window.start} – {window.end} · million kWh · clipped to available canonical history</p></div><Link className="inline-link" href="/explore">Open full analysis studio →</Link></div>
 {history&&!history.ok&&<ErrorPanel message={history.message}/>}{energy&&<ExplorationCharts report={energy} compact/>}
 <div className="section-title"><div><span className="tiny-label">RESEARCH, NOT A GUARANTEE</span><h2>How the models compare</h2><p>Frozen historical errors are distinct from current prospective performance.</p></div><Link href="/analytics/final-evaluation" className="inline-link">Evaluation details →</Link></div>
 {model.ok?<ModelEvidenceCharts report={model.data} compact/>:<ErrorPanel message={model.message}/>}
 {!forecast.ok&&<ErrorPanel message={forecast.message}/>}
 <section className="journey-grid">{[['01','Explore patterns','Zoom daily timelines, compare complete months and inspect distribution and coverage.','/explore'],['02','Compare evidence','Contrast observed generation and demand on the same dates and measurement units.','/analytics/comparisons'],['03','Interpret responsibly','Use evidence and limitations to frame planning questions and follow-up investigations.','/insights']].map(([n,title,text,href])=><Link className="journey-card" href={href} key={n}><span>{n}</span><h2>{title}</h2><p>{text}</p><strong>Open workspace →</strong></Link>)}</section>
 <section className="notice"><strong>Understand the scope</strong><p>Observed national Page 1 measurements and a daily energy-generation forecasting study. Missing values remain gaps. Cost, fuel and zonal prediction modules are not yet supported. The research report explains study definitions and limitations.</p></section>
 </Shell>;
}
