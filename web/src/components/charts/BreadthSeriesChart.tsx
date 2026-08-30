import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { BreadthSeriesData } from "@/types/market";

interface BreadthSeriesChartProps {
  data: BreadthSeriesData;
  height?: number;
}

/**
 * 日线市场宽度：上涨/平盘/下跌家数堆叠柱（红/灰/绿，与首页市场宽度同语义）。
 * 折线为「上涨占比」= 上涨家数 ÷（上涨+下跌），右轴 0–100%，50% 为多空平衡。
 */
export default function BreadthSeriesChart({ data, height = 300 }: BreadthSeriesChartProps) {
  const { dates, up, flat, down } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    // 上涨占比（%）：上涨 ÷ (上涨+下跌)，分母为 0 时按 0 处理
    const upRatio = up.map((u, i) => {
      const denom = u + down[i];
      return denom > 0 ? (u / denom) * 100 : 0;
    });

    return {
      grid: { top: 28, right: 44, bottom: 20, left: 44 },
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
      yAxis: [
        {
          type: "value" as const,
          splitLine: { lineStyle: { color: TOKENS.grid } },
          axisLabel: { fontSize: 11 },
        },
        {
          type: "value" as const,
          min: 0,
          max: 100,
          splitLine: { show: false },
          axisLabel: { fontSize: 11, formatter: (v: number) => `${v}%` },
        },
      ],
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: "#fff",
        borderColor: TOKENS.gridStrong,
        textStyle: { color: TOKENS.ink },
      },
      series: [
        {
          type: "bar" as const,
          name: "上涨",
          stack: "breadth",
          data: up,
          itemStyle: { color: TOKENS.up },
          barWidth: "45%",
        },
        {
          type: "bar" as const,
          name: "平盘",
          stack: "breadth",
          data: flat,
          itemStyle: { color: TOKENS.seriesBase },
          barWidth: "45%",
        },
        {
          type: "bar" as const,
          name: "下跌",
          stack: "breadth",
          data: down,
          itemStyle: { color: TOKENS.down },
          barWidth: "45%",
        },
        {
          type: "line" as const,
          name: "上涨占比",
          data: upRatio,
          yAxisIndex: 1,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.ink },
          itemStyle: { color: TOKENS.ink },
          tooltip: {
            valueFormatter: (v: unknown) => `${Number(v).toFixed(1)}%`,
          },
          z: 5,
        },
      ],
    };
  }, [dates, up, flat, down]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
