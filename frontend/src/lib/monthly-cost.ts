import report from "../data/monthly-cost-20261108.json" with { type: "json" };
import type { ComparisonChartData } from "./comparison-types";
export const monthlyCost = report;
export const methods = ["latest_total", "daily_mean", "ols", "ridge"] as const;
export const methodNames = { latest_total: "Latest total baseline", daily_mean: "Daily-mean baseline", ols: "OLS", ridge: "Ridge · predefined primary" };
export function billion(value: number | string | null | undefined): string {
  return value == null ? "—" : (Number(value)/1e9).toLocaleString("en-US", {minimumFractionDigits:3,maximumFractionDigits:3});
}
export function monthlyChart(): ComparisonChartData {
  const rows=report.predictions;
  return { labels:rows.map(r=>r.target_month), unit:"billion BDT",series:[{name:"Observed complete-month total", values:rows.map(r=>r.actual_bdt==null?null:String(Number(r.actual_bdt)/1e9)),notes:rows.map(()=>"Original complete monthly target; missing actual stays unscored"),incomplete:rows.map(()=>false)},...methods.map(k=>({name:methodNames[k],values:rows.map(r=>r.forecasts_bdt[k]==null?null:String(Number(r.forecasts_bdt[k])/1e9)),notes:rows.map(()=>"Retrospective scenario; historical publication times are unverified"),incomplete:rows.map(()=>false)}))] };
}
export function predictionsCsv(): string {
 const header=["Target month","Actual total production cost (BDT)",...methods.map(k=>methodNames[k]+" (BDT)"),"Record type"];
 const rows=report.predictions.map(r=>[r.target_month,r.actual_bdt??"",...methods.map(k=>r.forecasts_bdt[k]??""),"Historical scenario"]);
 rows.push([report.future.target_month,"",...methods.map(k=>report.future.forecasts_bdt[k]),"Issued future forecast"]);
 return '\uFEFF'+[header,...rows].map(row=>row.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
}
