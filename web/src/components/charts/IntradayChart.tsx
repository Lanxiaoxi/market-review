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
        splitLine: { lineStyle: { color: TOKENS.grid } },
      },
      series: series.map((s) => ({
        type: "line" as const,
        name: s.name,
        data: s.data,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 2, color: s.color, cap: "round" as const, join: "round" as const },
        itemStyle: { color: s.color },
      })),
    }),
    [series, timeLabels]
  );

  return <BaseChart option={option} height={height} />;
}
