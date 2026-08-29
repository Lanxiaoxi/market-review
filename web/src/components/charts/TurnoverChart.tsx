import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface TurnoverChartProps {
  times: string[];      // ["09:30", ...]
  amounts: number[];    // 累计成交额（元）
  height?: number;
}

/**
 * 成交额分时：柱 = 区间成交额（亿），线 = 累计成交额（亿，隐藏轴自适应）
 */
export default function TurnoverChart({
  times,
  amounts,
  height = 300,
}: TurnoverChartProps) {
  const option = useMemo(() => {
    const yi = (v: number) => v / 1e8; // 元 → 亿
    // 区间成交额（亿）= 累计值差分
    const bars = amounts.map((v, i) => (i === 0 ? yi(v) : yi(v - amounts[i - 1])));
    const cum = amounts.map(yi);

    // 抽稀：控制在 ~48 个点内
    const N = Math.max(1, Math.floor(times.length / 48));
    const idxs = times
      .map((_, i) => i)
      .filter((i) => i % N === 0 || i === times.length - 1);

    return {
      grid: { top: 16, right: 20, bottom: 40, left: 56 },
      xAxis: {
        type: "category" as const,
        data: idxs.map((i) => times[i]),
        axisLabel: { fontSize: 11, interval: Math.max(0, Math.floor(idxs.length / 5) - 1) },
        axisTick: { show: false },
      },
      yAxis: [
        {
          type: "value" as const,
          name: "亿",
          nameTextStyle: { fontSize: 11, color: TOKENS.muted },
          splitLine: { lineStyle: { color: TOKENS.grid } },
          axisLabel: { fontSize: 11 },
        },
        { type: "value" as const, show: false, splitLine: { show: false } },
      ],
      series: [
        {
          type: "bar" as const,
          name: "区间成交额",
          data: idxs.map((i) => ({
            value: Math.max(0, bars[i]),
            itemStyle: { color: TOKENS.barFill, borderRadius: [2, 2, 0, 0] },
          })),
          barWidth: "55%",
          yAxisIndex: 0,
          silent: true,
        },
        {
          type: "line" as const,
          name: "累计成交额",
          data: idxs.map((i) => cum[i]),
          smooth: false,
          symbol: "none",
          yAxisIndex: 1,
          lineStyle: {
            width: 2,
            color: TOKENS.accent,
            cap: "round" as const,
            join: "round" as const,
          },
        },
      ],
    };
  }, [times, amounts]);

  return <BaseChart option={option} height={height} />;
}
