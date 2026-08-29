import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface BarDistItem {
  label: string;
  value: number;
  color: string; // 必须是 TOKENS 中的真实 hex 值（ECharts Canvas 不支持 CSS var()）
}

interface BarDistChartProps {
  data: BarDistItem[];
  height?: number;
}

export default function BarDistChart({
  data,
  height = 300,
}: BarDistChartProps) {
  const option = useMemo(
    () => ({
      grid: { top: 16, right: 20, bottom: 40, left: 20 },
      xAxis: {
        type: "category" as const,
        data: data.map((d) => d.label),
        axisLabel: { fontSize: 11, rotate: 0, interval: 0 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value" as const,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: { fontSize: 11 },
      },
      series: [
        {
          type: "bar" as const,
          data: data.map((d) => ({
            value: d.value,
            itemStyle: {
              color: d.color,
              borderRadius: [2, 2, 0, 0],
            },
          })),
          barWidth: 40,
          label: {
            show: true,
            position: "top" as const,
            fontSize: 12,
            color: TOKENS.mutedStrong,
          },
        },
      ],
    }),
    [data]
  );

  return <BaseChart option={option} height={height} />;
}
