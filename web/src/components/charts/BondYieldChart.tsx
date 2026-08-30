import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { BondYieldData } from "@/types/market";

interface BondYieldChartProps {
  data: BondYieldData;
  height?: number;
}

/** 中债国债收益率曲线（2/5/10/30 年期）四线对比 */
export default function BondYieldChart({ data, height = 300 }: BondYieldChartProps) {
  const { dates, twoYear, fiveYear, tenYear, thirtyYear } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    const line = (name: string, values: (number | null)[], color: string) => ({
      type: "line" as const,
      name,
      data: values,
      smooth: true,
      symbol: "none",
      lineStyle: { width: 2, color },
      itemStyle: { color },
      connectNulls: false,
    });

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
          formatter: (v: string) => v.slice(5),
        },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value" as const,
        scale: true,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: { fontSize: 11, formatter: (v: number) => `${v}%` },
      },
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: "#fff",
        borderColor: TOKENS.gridStrong,
        textStyle: { color: TOKENS.ink },
        valueFormatter: (v: unknown) => (v == null ? "—" : `${v}%`),
      },
      series: [
        line("2年期", twoYear, "#2f8fd6"),
        line("5年期", fiveYear, "#c97b2d"),
        line("10年期", tenYear, TOKENS.ink),
        line("30年期", thirtyYear, "#b048c8"),
      ],
    };
  }, [dates, twoYear, fiveYear, tenYear, thirtyYear]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
