"use client";
import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { DataZoomComponent, GridComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { AnalyticsReport } from "../lib/types";
echarts.use([LineChart, DataZoomComponent, GridComponent, TooltipComponent, SVGRenderer]);

export function HistoryChart({ report }: { report: AnalyticsReport }) {
  const element = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!element.current) return;
    let chart: echarts.ECharts | undefined;
    let observer: ResizeObserver | undefined;
    try {
      chart = echarts.init(element.current, null, { renderer: "svg" });
      chart.setOption({
        animation: false,
        color: ["#087f76"],
        grid: { left: 22, right: 25, top: 38, bottom: 78, containLabel: true },
        tooltip: { trigger: "axis", renderMode: "richText", formatter: (params: unknown) => {
          const item = Array.isArray(params) ? params[0] : params;
          const index = item && typeof item === "object" && "dataIndex" in item && typeof item.dataIndex === "number" ? item.dataIndex : -1;
          const p = report.points[index];
          if (!p) return "";
          return `${p.label}\n${report.label}: ${p.value ?? "No observation"} ${report.unit}\nObserved days: ${p.observed_days}/${p.expected_days}\n${p.complete_period ? "Complete period" : "Incomplete period or date-window slice"}`;
        } },
        xAxis: { type: "category", boundaryGap: false, data: report.points.map(p => p.label), axisLabel: { color: "#6d8188", fontSize: 10 } },
        yAxis: { type: "value", name: report.unit === "million_kWh" ? "million kWh" : report.unit, nameTextStyle: { color: "#6d8188", fontSize: 10 }, splitLine: { lineStyle: { color: "#eaf0ee" } } },
        dataZoom: [{ type: "inside", filterMode: "none" }, { type: "slider", bottom: 15, height: 20, borderColor: "#dce8e4" }],
        series: [{ name: report.label, type: "line", smooth: false, connectNulls: false,
          showSymbol: report.points.length <= 200, symbolSize: 6,
          data: report.points.map(p => ({ value: p.value == null ? "-" : Number(p.value), itemStyle: { color: p.complete_period ? "#087f76" : "#c58a25" } })),
          lineStyle: { width: 1.8 },
        }],
      });
      observer = new ResizeObserver(() => chart?.resize());
      observer.observe(element.current);
      setError(false);
    } catch { setError(true); }
    return () => { observer?.disconnect(); chart?.dispose(); };
  }, [report]);
  return <>{error && <p className="notice error-notice">The chart could not render. Exact values remain available in the period table below.</p>}<div ref={element} style={{ width: "100%", height: 420 }} role="img" aria-label={`${report.label}, ${report.resolution} observed history. Missing values are gaps. Exact values and coverage are in the period table below.`}/></>;
}
