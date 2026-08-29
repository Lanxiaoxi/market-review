import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { EChartsOption } from "echarts-for-react";

interface SparklineChartProps {
  data: number[];
  isUp: boolean;
  width?: number | string;
  height?: number;
}

export default function SparklineChart({
  data,
  isUp,
  width = "100%",
  height = 28,
}: SparklineChartProps) {
  const option: EChartsOption = useMemo(
    () => ({
      grid: { top: 0, right: 0, bottom: 0, left: 0 },
      xAxis: { show: false, data: data.map((_, i) => i) },
      yAxis: { show: false, min: Math.min(...data) - 2, max: Math.max(...data) + 2 },
      series: [
        {
          type: "line",
          data,
          smooth: false,
          showSymbol: false,
          lineStyle: {
            width: 1.5,
            color: isUp ? TOKENS.up : TOKENS.down,
            cap: "round",
            join: "round",
          },
        },
      ],
    }),
    [data, isUp]
  );

  // 空数据防御：少于 2 个点无法成线（且 min/max 会算出 Infinity）
  if (!data || data.length < 2) return null;

  return <BaseChart option={option} width={width} height={height} />;
}
