'use client';
import {useState} from 'react';
import {COLUMNS} from '../lib/filters';
import {metricLabel} from '../lib/format';
import {canPreviewWeeklyTreatment} from '../lib/dataset-strategy';
export function PreparationDatasetControls({metric,policy}:{metric:string;policy:string}){
 const [selected,setSelected]=useState(metric);
 const [treatment,setTreatment]=useState(canPreviewWeeklyTreatment(metric)?policy:'observed_only');
 const allowed=canPreviewWeeklyTreatment(selected);
 return <><div className="field"><label htmlFor="metric">Measurement</label><select id="metric" name="metric" value={selected} onChange={e=>{setSelected(e.target.value);if(!canPreviewWeeklyTreatment(e.target.value))setTreatment('observed_only');}}>{COLUMNS.map(m=><option key={m} value={m}>{metricLabel(m)}</option>)}</select></div>
 <div className="field"><label htmlFor="policy">Training treatment</label><select id="policy" name="policy" value={treatment} onChange={e=>setTreatment(e.target.value)}><option value="observed_only">Observed only · baseline</option><option value="past_week_train_only" disabled={!allowed}>Previous week · experimental core only</option></select>{!allowed&&<p className="small-note">Modern-layout-only fields stay observed-only. A reporting-period gap is not a value to manufacture.</p>}</div></>;
}
