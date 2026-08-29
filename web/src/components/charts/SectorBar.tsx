import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface SectorBarItem {
  name: string;
  pct: number; // 正 = 涨，负 = 跌
}

interface SectorBarChartProps {
  data: SectorBarItem[];
  height?: number;
}

export default function SectorBarChart({
  data,
  height = 200,
}: SectorBarChartProps) {
  const option = useMemo(() => {
    // 按绝对值排序（涨幅高的在上面）
    const sorted = [...data].sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct));
    const names = sorted.map((d) => d.name);
    const values = sorted.map((d) => d.pct);

    return {
      grid: { top: 8, right: 40, bottom: 16, left: 80 },
      xAxis: {
        type: "value" as const,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: { fontSize: 11, formatter: "{value}%" },
      },
      yAxis: {
        type: "category" as const,
        data: names,
        inverse: true,
        axisLabel: { fontSize: 12, color: TOKENS.ink },
        axisTick: { show: false },
        axisLine: { show: false },
      },
      series: [
        {
          type: "bar" as const,
          data: values.map((v) => ({
            value: Math.abs(v),
            itemStyle: {
              color: v >= 0 ? TOKENS.up : TOKENS.down,
              borderRadius: [0, 4, 4, 0],
            },
          })),
          barWidth: 10,
          label: {
            show: true,
            position: "right" as const,
            fontSize: 12,
            fontWeight: 500,
            formatter: (p: { value: number; dataIndex: number }) =>
              `${values[p.dataIndex] >= 0 ? "+" : ""}${values[p.dataIndex].toFixed(2)}%`,
            color: TOKENS.ink,
          },
        },
      ],
    };
  }, [data]);

  return <BaseChart option={option} height={height} />;
}
