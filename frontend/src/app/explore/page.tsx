import Link from 'next/link';
import {requireSession} from '../../lib/auth';
import {readApi} from '../../lib/backend';
import {edaFilters} from '../../lib/eda';
import type {EdaReport} from '../../lib/eda';
import type {Params} from '../../lib/filters';
import {Shell,Heading,Stat,ErrorPanel,Empty,Updated} from '../../components/ui';
import {EdaWorkspace,VariableSelection} from '../../components/eda-workspace';
export const dynamic='force-dynamic';
export default async function Explore({searchParams}:{searchParams:Promise<Params>}){
 await requireSession();const f=edaFilters(await searchParams);const result=f.error?null:await readApi<EdaReport>(`/api/v1/analytics/exploratory?${f.query}`);const d=result?.ok?result.data:null;
 return <Shell active="/explore"><Heading eyebrow="MULTIVARIABLE EXPLORATORY ANALYSIS" title="Ask deeper questions of your data." description="Select variables together. Examine their distributions, relationships, temporal patterns and missingness in one aligned analysis."><Link href="/explore/single" className="button secondary">Single-variable studio →</Link></Heading><section className="panel"><VariableSelection key={f.query.toString()} selected={f.metrics} start={f.start} end={f.end}/></section>
 {f.error&&<div className="notice error-notice" role="alert">{f.error}</div>}{result&&!result.ok&&<ErrorPanel message={result.message}/>}
 {d&&<><div className="section-meta"><span className="scope-tag">{d.start_date??'No overlap'} – {d.end_date??'No overlap'} · current canonical observations</span><Updated at={d.generated_at}/></div><div className="stat-grid"><Stat label="SELECTED VARIABLES" value={String(d.variables.length)} detail="Each has its own units and observation coverage"/><Stat label="CALENDAR DAYS" value={d.calendar_days.toLocaleString()} detail="Dense calendar; no missing-date compression"/><Stat label="ALL-VARIABLE COMPLETE DATES" value={d.complete_case_days.toLocaleString()} detail="Relationships separately use their pairwise available dates" accent/><Stat label="UNIQUE VARIABLE PAIRS" value={String(d.variables.length*(d.variables.length-1)/2)} detail="Pearson, Spearman and first-difference comparisons"/></div>{d.calendar_days?<EdaWorkspace key={d.analysis_id} report={d}/>:<Empty title="No overlap with current history" text="Choose another date window. No synthetic observations are substituted."/>}</>}
 </Shell>;
}
