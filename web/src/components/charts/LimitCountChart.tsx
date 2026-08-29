import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { LimitCountsData } from "@/types/market";

interface LimitCountChartProps {
  data: LimitCountsData;
  height?: number;
}

/**
 * 日线涨停/跌停家数：红柱（涨停，--up）与绿柱（跌停，--down）并列
 * 数据点完整传入，日期标签抽稀展示；tooltip 显示当日两家数
 */
export default function LimitCountChart({ data, height = 300 }: LimitCountChartProps) {
  const { dates, limitUp, limitDown } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      grid: { top: 24, right: 20, bottom: 20, left: 44 },
      xAxis: {
        type: "category" as const,
        data: dates,
        axisLabel: {
          fontSize: 11,
          interval: showIdx,
          formatter: (v: string) => v.slice(5), // "MM-DD"
        },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value" as const,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: { fontSize: 11 },
      },
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: "#fff",
        borderColor: TOKENS.gridStrong,
        textStyle: { color: TOKENS.ink },
        valueFormatter: (v: unknown) => `${v} 家`,
      },
      series: [
        {
          type: "bar" as const,
          name: "涨停",
          data: limitUp.map((v) => ({
            value: v,
            itemStyle: { color: TOKENS.up, borderRadius: [2, 2, 0, 0] },
          })),
          barWidth: "38%",
          label: {
            show: true,
            position: "top" as const,
            fontSize: 10,
            color: TOKENS.up,
            formatter: (p: { value: number }) => (p.value > 0 ? String(p.value) : ""),
          },
        },
        {
          type: "bar" as const,
          name: "跌停",
          data: limitDown.map((v) => ({
            value: v,
            itemStyle: { color: TOKENS.down, borderRadius: [2, 2, 0, 0] },
          })),
          barWidth: "38%",
          label: {
            show: true,
            position: "top" as const,
            fontSize: 10,
            color: TOKENS.down,
            formatter: (p: { value: number }) => (p.value > 0 ? String(p.value) : ""),
          },
        },
      ],
    };
  }, [dates, limitUp, limitDown]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
