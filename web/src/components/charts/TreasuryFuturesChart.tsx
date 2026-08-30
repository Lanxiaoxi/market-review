import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { TreasuryFuturesData } from "@/types/market";

interface TreasuryFuturesChartProps {
  data: TreasuryFuturesData;
  height?: number;
}

/** 国债期货主力连续日线（单线） */
export default function TreasuryFuturesChart({ data, height = 300 }: TreasuryFuturesChartProps) {
  const { dates, closes } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      grid: { top: 24, right: 20, bottom: 20, left: 48 },
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
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.accent },
          itemStyle: { color: TOKENS.accent },
        },
      ],
    };
  }, [dates, closes, data.name]);

  if (dates.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
