"use client";
import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { ComparisonChartData } from "../lib/comparison-types";
echarts.use([LineChart, DataZoomComponent, GridComponent, LegendComponent, TooltipComponent, SVGRenderer]);

export function ComparisonChart({ data, description }: { data: ComparisonChartData; description: string }) {
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
        color: ["#087f76", "#476bbc", "#b36a27", "#97569a", "#688736", "#bf5574", "#576c78", "#8b6746"],
        legend: { type: "scroll", top: 12, left: 22, right: 22, textStyle: { fontSize: 11 } },
        grid: { left: 22, right: 25, top: 75, bottom: 80, containLabel: true },
        tooltip: { trigger: "axis", renderMode: "richText", formatter: (params: unknown) => {
          const item = Array.isArray(params) ? params[0] : params;
          const index = item && typeof item === "object" && "dataIndex" in item && typeof item.dataIndex === "number" ? item.dataIndex : -1;
          if (index < 0) return "";
          return `${data.labels[index]}\n` + data.series.map(s => `${s.name}: ${s.values[index] ?? "No observation"} ${data.unit}\n${s.notes[index]}${s.incomplete[index] ? " · incomplete/sliced" : " · complete"}`).join("\n");
        } },
        xAxis: { type: "category", boundaryGap: false, data: data.labels, axisLabel: { color: "#6d8188", fontSize: 10 } },
        yAxis: { type: "value", name: data.unit, nameTextStyle: { color: "#6d8188", fontSize: 10 }, splitLine: { lineStyle: { color: "#eaf0ee" } } },
        dataZoom: [{ type: "inside", filterMode: "none" }, { type: "slider", bottom: 15, height: 20, borderColor: "#dce8e4" }],
        series: data.series.map(s => ({ name: s.name, type: "line", smooth: false, connectNulls: false,
          showSymbol: data.labels.length <= 200, symbolSize: 6, lineStyle: { width: 1.8 },
          data: s.values.map((value, i) => ({ value: value == null ? "-" : Number(value),
            symbol: s.incomplete[i] ? "emptyDiamond" : "circle", symbolSize: s.incomplete[i] ? 8 : 5 })),
        })),
      });
      observer = new ResizeObserver(() => chart?.resize());
      observer.observe(element.current);
      setError(false);
    } catch { setError(true); }
    return () => { observer?.disconnect(); chart?.dispose(); };
  }, [data]);
  return <>{error && <p className="notice error-notice">Chart rendering failed. Exact values and coverage remain in the tables below.</p>}<div ref={element} role="img" aria-label={description} style={{ height: 440, width: "100%" }}/></>;
}
