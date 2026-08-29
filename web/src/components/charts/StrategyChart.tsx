import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface StrategyChartProps {
  /** 策略收益曲线数据 */
  strategyData: number[];
  /** 基准（如沪深300）数据 */
  benchmarkData: number[];
  /** 成交量柱数据 */
  volumeData: number[];
  /** X 轴标签（如日期） */
  labels?: string[];
  height?: number;
}

export default function StrategyChart({
  strategyData,
  benchmarkData,
  volumeData,
  labels,
  height = 300,
}: StrategyChartProps) {
  const option = useMemo(
    () => ({
      grid: { top: 16, right: 36, bottom: 16, left: 48 },
      xAxis: {
        type: "category" as const,
        data: labels ?? strategyData.map((_, i) => String(i + 1)),
        axisLabel: { fontSize: 11, rotate: 0 },
        axisTick: { show: false },
      },
      // 双 y 轴：成交量走隐藏轴（自适应），收益/基准走主轴
      yAxis: [
        {
          type: "value" as const,
          splitLine: { lineStyle: { color: TOKENS.grid } },
          axisLabel: { fontSize: 11 },
        },
        {
          type: "value" as const,
          show: false,
          min: 0,
          splitLine: { show: false },
        },
      ],
      series: [
        {
          type: "bar" as const,
          data: volumeData.map((v) => ({
            value: v,
            itemStyle: {
              color: TOKENS.barFill,
              borderRadius: [2, 2, 0, 0],
            },
          })),
          barWidth: "40%",
          yAxisIndex: 1,
          silent: true,
        },
        {
          type: "line" as const,
          name: "策略收益",
          data: strategyData,
          smooth: false,
          symbol: "none",
          yAxisIndex: 0,
          lineStyle: {
            width: 2,
            color: TOKENS.accent,
            cap: "round" as const,
            join: "round" as const,
          },
        },
        {
          type: "line" as const,
          name: "沪深300",
          data: benchmarkData,
          smooth: false,
          symbol: "none",
          yAxisIndex: 0,
          lineStyle: {
            width: 2,
            color: TOKENS.seriesBase,
            cap: "round" as const,
            join: "round" as const,
          },
        },
      ],
    }),
    [strategyData, benchmarkData, volumeData, labels]
  );

  return <BaseChart option={option} height={height} />;
}
