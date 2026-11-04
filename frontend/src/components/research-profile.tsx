"use client";
import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { ResearchPeriod } from "../lib/research";
echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer]);

export function ResearchProfile({ rows, label }: { rows: ResearchPeriod[]; label: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    let chart: echarts.ECharts | undefined;
    let observer: ResizeObserver | undefined;
    try {
      chart = echarts.init(ref.current, null, { renderer: "svg" });
      chart.setOption({ animation: false,
        legend: { top: 12 }, grid: { top: 80, left: 20, right: 25, bottom: 25, containLabel: true },
        tooltip: { trigger: "axis", renderMode: "richText", formatter: (params: unknown) => {
          const p = Array.isArray(params) ? params[0] : params;
          const i = p && typeof p === "object" && "dataIndex" in p && typeof p.dataIndex === "number" ? p.dataIndex : -1;
          const r = rows[i];
          return r ? `${r.label}\nMean: ${r.mean ?? "Unavailable"} million kWh\nEligible: ${r.eligible_days}/${r.calendar_days} days\nCoverage: ${r.coverage_percent}%\nMissing: ${r.missing_days} · held: ${r.held_days}` : "";
        } },
        xAxis: { type: "category", data: rows.map(r => rows.length === 7 ? r.label.slice(0, 3) : r.label), axisLabel: { fontSize: 10, interval: 0, rotate: rows.length > 7 ? 30 : 0 } },
        yAxis: [{ type: "value", name: "Mean · million kWh", nameTextStyle: { fontSize: 10 } },
          { type: "value", name: "Coverage %", min: 0, max: 100, nameTextStyle: { fontSize: 10 }, splitLine: { show: false } }],
        series: [{ name: "Mean daily energy", type: "bar", barMaxWidth: 44,
          data: rows.map(r => ({ value: r.mean == null ? "-" : Number(r.mean), itemStyle: { color: r.complete ? "#087f76" : "#b98431", borderRadius: [4, 4, 0, 0] } })) },
        { name: "Eligible coverage %", type: "line", yAxisIndex: 1, color: "#476bbc", smooth: false,
          data: rows.map(r => Number(r.coverage_percent)) }],
      });
      observer = new ResizeObserver(() => chart?.resize()); observer.observe(ref.current);
      setError(false);
    } catch { setError(true); }
    return () => { observer?.disconnect(); chart?.dispose(); };
  }, [rows]);
  return <>{error && <p className="notice error-notice">Chart unavailable. Exact statistics and coverage remain in the table.</p>}<div ref={ref} style={{ width: "100%", height: 370 }} role="img" aria-label={`${label}: mean daily energy with a separate coverage percentage axis. Amber bars have incomplete coverage. Exact values follow in the table.`}/></>;
}
