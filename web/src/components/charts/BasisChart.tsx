import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";
import type { IfBasisData } from "@/types/market";

interface BasisChartProps {
  data: IfBasisData;
  height?: number;
}

/**
 * 股指期货期现对比（日线）—— 双 grid 叠加：
 * 上图：现货（ink）vs 主力合约（accent）两条折线
 * 下图：基差柱状（现货 - 期货，点），红正绿负 + 0 零线
 * X 轴共享对齐，tooltip 同时展示两家数与基差/基差率
 */
export default function BasisChart({ data, height = 320 }: BasisChartProps) {
  const { dates, spot, futures, basis, premium } = data;

  const option = useMemo(() => {
    const n = dates.length;
    const step = Math.max(1, Math.ceil(n / 6));
    const showIdx = (i: number) => i === 0 || i === n - 1 || i % step === 0;

    return {
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { fontSize: 11, color: TOKENS.muted },
      },
      grid: [
        { top: 36, right: 48, bottom: 120, left: 56 },
        { top: "auto", right: 48, bottom: 28, left: 56, height: 82 },
      ],
      xAxis: [
        {
          type: "category" as const,
          gridIndex: 0,
          data: dates,
          boundaryGap: false,
          axisLabel: { show: false },
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { show: false },
        },
        {
          type: "category" as const,
          gridIndex: 1,
          data: dates,
          boundaryGap: true,
          axisLabel: { fontSize: 11, interval: showIdx, formatter: (v: string) => v.slice(5) },
          axisTick: { show: false },
          axisLine: { show: false },
          splitLine: { show: false },
        },
      ],
      yAxis: [
        {
          type: "value" as const,
          gridIndex: 0,
          scale: true,
          name: "现货",
          nameTextStyle: { fontSize: 11, color: TOKENS.muted },
          splitLine: { lineStyle: { color: TOKENS.grid } },
          axisLabel: { fontSize: 11 },
        },
        {
          type: "value" as const,
          gridIndex: 0,
          scale: true,
          name: "主力",
          nameTextStyle: { fontSize: 11, color: TOKENS.muted },
          splitLine: { show: false },
          axisLabel: { fontSize: 11 },
        },
        {
          type: "value" as const,
          gridIndex: 1,
          splitLine: { lineStyle: { color: TOKENS.grid } },
          axisLabel: { fontSize: 11, formatter: (v: number) => `${v}` },
        },
      ],
      tooltip: {
        trigger: "axis" as const,
        backgroundColor: "#fff",
        borderColor: TOKENS.gridStrong,
        textStyle: { color: TOKENS.ink },
        formatter: (params: unknown) => {
          const arr = params as Array<{ seriesName: string; value: number; dataIndex: number }>;
          const i = arr[0]?.dataIndex ?? 0;
          const line = (name: string, v: number, color: string) =>
            `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${color};margin-right:6px"></span>${name}：${v.toFixed(2)}`;
          const rows = [
            line("现货指数", spot[i], TOKENS.ink),
            line("主力合约", futures[i], TOKENS.accent),
            line("基差（点）", basis[i], basis[i] >= 0 ? TOKENS.up : TOKENS.down),
          ].join("<br/>");
          const prem = premium[i];
          return `${dates[i]}<br/>${rows}<br/><span style="color:${TOKENS.muted}">基差率 ${prem >= 0 ? "+" : ""}${prem.toFixed(3)}%</span>`;
        },
      },
      series: [
        {
          type: "line" as const,
          name: "现货指数",
          data: spot,
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.ink, cap: "round" as const, join: "round" as const },
          itemStyle: { color: TOKENS.ink },
        },
        {
          type: "line" as const,
          name: "主力合约",
          data: futures,
          xAxisIndex: 0,
          yAxisIndex: 1,
          smooth: false,
          symbol: "none",
          lineStyle: { width: 2, color: TOKENS.accent, cap: "round" as const, join: "round" as const },
          itemStyle: { color: TOKENS.accent },
        },
        {
          type: "bar" as const,
          name: "基差（点）",
          data: basis.map((v) => ({
            value: v,
            itemStyle: { color: v >= 0 ? TOKENS.up : TOKENS.down, borderRadius: [2, 2, 0, 0] },
          })),
          xAxisIndex: 1,
          yAxisIndex: 2,
          barWidth: "55%",
          // 0 零线（--grid-strong）
          markLine: {
            symbol: "none" as const,
            silent: true,
            label: { show: false },
            lineStyle: { color: TOKENS.gridStrong, width: 1 },
            data: [{ yAxis: 0 }],
          },
        },
      ],
    };
  }, [dates, spot, futures, basis, premium]);

  if (dates.length < 2 || spot.length < 2) return null;

  return <BaseChart option={option} height={height} />;
}
