import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { FiftyTwoWeekData } from "@/types/market";

interface FiftyTwoWeekChartProps {
  data: FiftyTwoWeekData;
  height?: number;
}

/**
 * 近 N 日 52 周新高/新低个股家数：红柱（新高，--up）与绿柱（新低，--down）并列
 * 数据点完整传入，日期标签抽稀展示；tooltip 显示当日家数
 */
export default function FiftyTwoWeekChart({ data, height = 300 }: FiftyTwoWeekChartProps) {
  const { dates, newHigh, newLow } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      grid: { top: 32, right: 20, bottom: 20, left: 44 },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { fontSize: 11, color: TOKENS.muted },
      },
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
          name: "新高",
          data: newHigh.map((v) => ({
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
          name: "新低",
          data: newLow.map((v) => ({
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
  }, [dates, newHigh, newLow]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
