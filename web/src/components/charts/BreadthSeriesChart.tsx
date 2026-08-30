import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { BreadthSeriesData } from "@/types/market";

interface BreadthSeriesChartProps {
  data: BreadthSeriesData;
  height?: number;
}

/**
 * 日线市场宽度：上涨/平盘/下跌家数堆叠柱（红/灰/绿，与首页市场宽度同语义）。
 * 数据点完整传入，日期标签稀疏展示；tooltip 显示当日三家数。
 */
export default function BreadthSeriesChart({ data, height = 300 }: BreadthSeriesChartProps) {
  const { dates, up, flat, down } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      grid: { top: 28, right: 20, bottom: 20, left: 44 },
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
          name: "上涨家数",
          data: up,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.ink },
          itemStyle: { color: TOKENS.ink },
          z: 5,
        },
      ],
    };
  }, [dates, up, flat, down]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
