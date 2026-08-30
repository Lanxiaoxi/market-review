import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

/** 分布档位 → 颜色（与首页市场宽度同语义；ECharts Canvas 需要真实 hex，不能用 CSS var()） */
export const DIST_COLOR: Record<string, string> = {
  "涨停": TOKENS.up,
  "涨2-10%": TOKENS.up,
  "涨0-2%": TOKENS.up,
  "平盘": TOKENS.seriesBase,
  "跌0-2%": TOKENS.down,
  "跌2-10%": TOKENS.down,
  "跌停": TOKENS.down,
};

interface BarDistItem {
  label: string;
  value: number;
}

interface BarDistChartProps {
  data: BarDistItem[];
  height?: number;
}

/** 涨跌家数分布（7 档柱状图），颜色按档位语义在组件内映射，页面直接传后端 dist 即可 */
export default function BarDistChart({
  data,
  height = 300,
}: BarDistChartProps) {
  const option = useMemo(
    () => ({
      grid: { top: 16, right: 20, bottom: 40, left: 20 },
      xAxis: {
        type: "category" as const,
        data: data.map((d) => d.label),
        axisLabel: { fontSize: 11, rotate: 0, interval: 0 },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value" as const,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: { fontSize: 11 },
      },
      series: [
        {
          type: "bar" as const,
          data: data.map((d) => ({
            value: d.value,
            itemStyle: {
              color: DIST_COLOR[d.label] ?? TOKENS.seriesBase,
              borderRadius: [2, 2, 0, 0],
            },
          })),
          barWidth: 40,
          label: {
            show: true,
            position: "top" as const,
            fontSize: 12,
            color: TOKENS.mutedStrong,
          },
        },
      ],
    }),
    [data]
  );

  return <BaseChart option={option} height={height} />;
}
