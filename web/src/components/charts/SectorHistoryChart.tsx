import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { SectorHistory } from "@/api/sectors";

interface SectorHistoryChartProps {
  data: SectorHistory;
  height?: number;
}

/** 单个板块收盘日线（详情图） */
export default function SectorHistoryChart({ data, height = 240 }: SectorHistoryChartProps) {
  const { dates, closes } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      grid: { top: 16, right: 20, bottom: 20, left: 52 },
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
          type: "line" as const,
          name: data.name,
          data: closes,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.accent },
          itemStyle: { color: TOKENS.accent },
          areaStyle: { color: TOKENS.accent, opacity: 0.08 },
        },
      ],
    };
  }, [dates, closes, data.name]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
