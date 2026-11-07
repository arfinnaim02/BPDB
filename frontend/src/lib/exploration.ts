import type { AnalyticsReport } from "./types";
export type MonthlyView={month:string;year:string;number:number;observed:number;expected:number;value:number|null;coverage:number;complete:boolean};
export function exploration(report:AnalyticsReport){
 const days=report.points.map(p=>({date:p.start_date,value:p.value==null?null:Number(p.value)}));
 const byDate=new Map(days.map(d=>[d.date,d.value]));
 const rolling=days.map(d=>{const values:number[]=[];for(let i=0;i<7;i++){const date=new Date(d.date+'T00:00:00Z');date.setUTCDate(date.getUTCDate()-i);const v=byDate.get(date.toISOString().slice(0,10));if(v==null)return null;values.push(v);}return values.reduce((a,b)=>a+b,0)/7;});
 const groups=new Map<string,typeof days>();for(const day of days){const key=day.date.slice(0,7);groups.set(key,[...(groups.get(key)||[]),day]);}
 const energy=report.unit==='million_kWh';
 const months:MonthlyView[]=[...groups].map(([month,rows])=>{const values=rows.flatMap(x=>x.value==null?[]:[x.value]);const [year,m]=month.split('-');const expected=new Date(Date.UTC(Number(year),Number(m),0)).getUTCDate();const complete=rows.length===expected&&values.length===expected;return {month,year,number:Number(m),observed:values.length,expected,value:values.length?values.reduce((a,b)=>a+b,0)/(energy?1:values.length):null,coverage:100*values.length/expected,complete};});
 const values=days.flatMap(x=>x.value==null?[]:[x.value]);const low=values.length?Math.min(...values):0;const high=values.length?Math.max(...values):0;
 const bins=values.length?(low===high?[{label:String(low),count:values.length}]:Array.from({length:10},(_,i)=>{const lower=low+(high-low)*i/10;const upper=low+(high-low)*(i+1)/10;return {label:`${lower.toFixed(1)}–${upper.toFixed(1)}`,count:values.filter(v=>v>=lower&&(i===9?v<=upper:v<upper)).length};})):[];
 const weekdays=Array.from({length:7},(_,i)=>{const rows=days.filter(d=>(new Date(d.date+'T00:00:00Z').getUTCDay()+6)%7===i&&d.value!=null);return {label:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i],count:rows.length,mean:rows.length?rows.reduce((a,d)=>a+d.value!,0)/rows.length:null};});
 return {days,rolling,months,bins,weekdays,years:[...new Set(months.map(m=>m.year))],energy};
}
export function latestWindow(end:string|null,days=365){if(!end)return {};const start=new Date(end+'T00:00:00Z');start.setUTCDate(start.getUTCDate()-days+1);return {start:start.toISOString().slice(0,10),end};}
export function analysisCsv(report:AnalyticsReport){
 const rows=[['Operational date',`${report.label} (${report.unit==='million_kWh'?'million kWh':report.unit})`],...report.points.map(p=>[p.start_date,p.value??''])];
 return '\uFEFF'+rows.map(row=>row.map(x=>'"'+String(x).replaceAll('"','""')+'"').join(',')).join('\r\n');
}
