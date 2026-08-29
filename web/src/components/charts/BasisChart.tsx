import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { IfBasisData } from "@/types/market";

interface BasisChartProps {
  data: IfBasisData;
  height?: number;
}

/**
 * 沪深300 期现对比（日线）：现货（ink）vs 中金所 IF 主力（accent）
 * 数据点完整传入，日期标签按 ~6 个锚点抽稀；tooltip 附基差率
 */
export default function BasisChart({ data, height = 300 }: BasisChartProps) {
  const { dates, spot, futures, premium } = data;

  const option = useMemo(() => {
    const n = dates.length;
    // 日期标签抽稀：首/尾 + 均匀 ~6 个
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      grid: { top: 16, right: 36, bottom: 20, left: 56 },
      xAxis: {
        type: "category" as const,
        data: dates,
        boundaryGap: false,
        axisLabel: {
          fontSize: 11,
          interval: showIdx,
          formatter: (v: string) => v.slice(5), // "MM-DD"
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
        // 覆写会整体替换 base 的 tooltip，需补全 trigger 与样式
        trigger: "axis" as const,
        backgroundColor: "#fff",
        borderColor: TOKENS.gridStrong,
        textStyle: { color: TOKENS.ink },
        formatter: (params: unknown) => {
          const arr = params as Array<{ marker: string; seriesName: string; value: number; dataIndex: number }>;
          const i = arr[0]?.dataIndex ?? 0;
          const lines = arr
            .map((p) => `${p.marker}${p.seriesName}：${p.value.toFixed(2)}`)
            .join("<br/>");
          const prem = premium[i];
          const premStr = `${prem >= 0 ? "+" : ""}${prem.toFixed(3)}%`;
          return `${dates[i]}<br/>${lines}<br/><span style="color:${TOKENS.muted}">基差率 ${premStr}</span>`;
        },
      },
      series: [
        {
          type: "line" as const,
          name: "沪深300现货",
          data: spot,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.ink, cap: "round" as const, join: "round" as const },
          itemStyle: { color: TOKENS.ink },
        },
        {
          type: "line" as const,
          name: "IF主力合约",
          data: futures,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.accent, cap: "round" as const, join: "round" as const },
          itemStyle: { color: TOKENS.accent },
        },
      ],
    };
  }, [dates, spot, futures, premium]);

  if (dates.length < 2 || spot.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
