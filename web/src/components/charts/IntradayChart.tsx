import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface IntradaySeries {
  name: string;
  data: number[];
  color: string; // 必须是真实 hex（ECharts Canvas 不支持 CSS var()）
}

interface IntradayChartProps {
  series: IntradaySeries[];
  timeLabels: string[];
  height?: number;
}

export default function IntradayChart({
  series,
  timeLabels,
  height = 216,
}: IntradayChartProps) {
  const option = useMemo(
    () => ({
      grid: { top: 8, right: 36, bottom: 20, left: 44 },
      xAxis: {
        type: "category" as const,
        data: timeLabels,
        boundaryGap: false,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: "value" as const,
        scale: true,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: {
          fontSize: 11,
          formatter: (v: number) => `${v}%`,
        },
      },
      tooltip: {
        valueFormatter: (v: unknown) => `${v}%`,
      },
      series: series.map((s, i) => ({
        type: "line" as const,
        name: s.name,
        data: s.data,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 2, color: s.color, cap: "round" as const, join: "round" as const },
        itemStyle: { color: s.color },
        // 零线（--grid-strong）：首条系列上画一条 0% 基准线，对齐原型设计
        ...(i === 0
          ? {
              markLine: {
                symbol: "none" as const,
                silent: true,
                label: { show: false },
                lineStyle: { color: TOKENS.gridStrong, width: 1 },
                data: [{ yAxis: 0 }],
              },
            }
          : {}),
      })),
    }),
    [series, timeLabels]
  );

  return <BaseChart option={option} height={height} />;
}
