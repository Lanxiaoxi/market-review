import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface BreadthBarProps {
  up: number;
  flat: number;
  down: number;
  height?: number;
}

export default function BreadthBar({
  up,
  flat,
  down,
  height = 24,
}: BreadthBarProps) {
  const option = useMemo(
    () => ({
      grid: { top: 0, right: 0, bottom: 0, left: 0 },
      xAxis: { show: false, max: "dataMax" },
      yAxis: { show: false },
      series: [
        {
          type: "bar" as const,
          stack: "total",
          data: [{ value: up, itemStyle: { color: TOKENS.up } }],
          barWidth: "100%",
          silent: true,
        },
        {
          type: "bar" as const,
          stack: "total",
          data: [{ value: flat, itemStyle: { color: TOKENS.seriesBase } }],
          barWidth: "100%",
          silent: true,
        },
        {
          type: "bar" as const,
          stack: "total",
          data: [{ value: down, itemStyle: { color: TOKENS.down } }],
          barWidth: "100%",
          silent: true,
        },
      ],
    }),
    [up, flat, down]
  );

  return <BaseChart option={option} width="100%" height={height} />;
}
