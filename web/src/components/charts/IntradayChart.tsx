import { useMemo } from "react";
import BaseChart, { TOKENS } from "./BaseChart";

interface IntradaySeries {
  name: string;
  data: number[];
  color: string; // 必须是真实 hex（ECharts Canvas 不支持 CSS var()）
}

interface IntradayChartProps {
  series: IntradaySeries[];
  timeLabels: string[];
  height?: number;
}

export default function IntradayChart({
  series,
  timeLabels,
  height = 216,
}: IntradayChartProps) {
  const option = useMemo(() => {
    // 时间轴刻度抽稀：数据点完整传入（242 点），仅标签按 09:30/10:30/13:00/14:00/15:00 展示；
    // 找不到锚点（如近5日/近20日）时交给 ECharts 自动间隔
    const anchors = new Set(
      ["09:30", "10:30", "13:00", "14:00", "15:00"]
        .map((t) => timeLabels.indexOf(t))
        .filter((i) => i >= 0)
    );
    return {
      grid: { top: 8, right: 36, bottom: 20, left: 44 },
      xAxis: {
        type: "category" as const,
        data: timeLabels,
        boundaryGap: false,
        axisLabel: {
          fontSize: 11,
          interval: anchors.size > 1 ? (idx: number) => anchors.has(idx) : "auto",
        },
      },
      yAxis: {
        type: "value" as const,
        scale: true,
        splitLine: { lineStyle: { color: TOKENS.grid } },
        axisLabel: {
          fontSize: 11,
          formatter: (v: number) => `${Number(v.toFixed(2))}%`,
        },
      },
      tooltip: {
        // 注意：此处覆写会整体替换 baseChartOption 的 tooltip，必须补全 trigger 与样式
        trigger: "axis" as const,
        backgroundColor: "#fff",
        borderColor: TOKENS.gridStrong,
        textStyle: { color: TOKENS.ink },
        valueFormatter: (v: unknown) => `${Number(v).toFixed(2)}%`,
      },
      series: series.map((s, i) => ({
        type: "line" as const,
        // 稳定 id：notMerge=false 合并时按 id 对账，取消勾选后旧系列才会被移除
        id: s.name,
        name: s.name,
        data: s.data,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 2, color: s.color, cap: "round" as const, join: "round" as const },
        itemStyle: { color: s.color },
        // 零线（--grid-strong）：首条系列上画一条 0% 基准线，对齐原型设计
        ...(i === 0
          ? {
              markLine: {
                symbol: "none" as const,
                silent: true,
                label: { show: false },
                lineStyle: { color: TOKENS.gridStrong, width: 1 },
                data: [{ yAxis: 0 }],
              },
            }
          : {}),
      })),
    };
  }, [series, timeLabels]);

  return <BaseChart option={option} height={height} />;
}
