import { useRef, useEffect, useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { LineChart, BarChart, CustomChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption, EChartsInstance } from "echarts-for-react";

// 按需注册，减小 bundle
echarts.use([
  LineChart,
  BarChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  CanvasRenderer,
]);

// ═══════════════════════════════════════
//  Token → ECharts 映射表（来自 tokens.css）
// ═══════════════════════════════════════

function readTokens(): Record<string, string> {
  if (typeof document === "undefined") return {};
  const style = getComputedStyle(document.documentElement);
  return {
    ink: style.getPropertyValue("--ink").trim() || "#1d1d1f",
    muted: style.getPropertyValue("--muted").trim() || "#7a7a7a",
    mutedStrong: style.getPropertyValue("--muted-strong").trim() || "#333333",
    accent: style.getPropertyValue("--accent").trim() || "#0066cc",
    up: style.getPropertyValue("--up").trim() || "#d04545",
    down: style.getPropertyValue("--down").trim() || "#2f9e6e",
    grid: style.getPropertyValue("--grid").trim() || "#f2f2f4",
    gridStrong: style.getPropertyValue("--grid-strong").trim() || "#e8e8ec",
    seriesPurple: style.getPropertyValue("--series-purple").trim() || "#8e6cc9",
    seriesBase: style.getPropertyValue("--series-base").trim() || "#c7c7cc",
    barFill: style.getPropertyValue("--bar-fill").trim() || "#e8eef7",
    fontSans: style.getPropertyValue("--font-sans").trim() || "sans-serif",
  };
}

/**
 * 设计 token 的真实值快照（模块加载时读取一次）。
 * ECharts 走 Canvas 渲染，不支持 CSS var() 字符串，
 * 所有图表组件必须用这里的 hex 值，禁止写 "var(--x, #fff)"。
 */
export const TOKENS = readTokens();

/** 多系列色序 */
export const SERIES_COLORS = ["#1d1d1f", "#0066cc", "#8e6cc9"];

/** 图表统一基础 option */
export function baseChartOption(
  overrides: Partial<EChartsOption> = {}
): EChartsOption {
  const t = readTokens();
  return {
    textStyle: {
      fontFamily: t.fontSans,
      fontSize: 12,
      color: t.muted,
    },
    grid: {
      top: 20,
      right: 20,
      bottom: 32,
      left: 44,
      containLabel: false,
    },
    xAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { color: t.muted, fontSize: 11 },
    },
    yAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: {
        lineStyle: { color: t.grid, width: 1 },
      },
      axisLabel: { color: t.muted, fontSize: 11 },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#fff",
      borderColor: t.gridStrong,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: t.ink, fontSize: 12 },
      // v2：tooltip 与卡片体系对齐（发丝边 + 12px 圆角）
      extraCssText: "border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.06);",
    },
    color: SERIES_COLORS,
    // v2 动效：入场 900ms ease-in-out，多系列错峰；数据更新 500ms 平滑过渡
    animation: true,
    animationDuration: 900,
    animationEasing: "cubicInOut",
    animationDurationUpdate: 500,
    animationEasingUpdate: "cubicOut",
    ...overrides,
  } as EChartsOption;
}

// ═══════════════════════════════════════
//  BaseChart 组件
// ═══════════════════════════════════════

interface BaseChartProps {
  option: EChartsOption;
  height?: number | string;
  width?: number | string;
  onChartReady?: (instance: EChartsInstance) => void;
  style?: React.CSSProperties;
  className?: string;
}

export default function BaseChart({
  option,
  height = 260,
  width = "100%",
  onChartReady,
  style,
  className,
}: BaseChartProps) {
  const chartRef = useRef<EChartsInstance | null>(null);

  useEffect(() => {
    const handleResize = () => {
      chartRef.current?.resize();
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 合并 base option + 外部 option，并为多系列补充错峰延迟
  const mergedOption = useMemo(() => {
    const merged = {
      ...baseChartOption(),
      ...option,
    } as EChartsOption & { series?: unknown };

    const series = merged.series;
    if (Array.isArray(series)) {
      merged.series = series.map((s, i) => ({
        animationDelay: (idx: number) => idx * 8 + i * 150,
        ...(s as object),
      }));
    }
    return merged;
  }, [option]);

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={mergedOption}
      style={{ width, height, ...style }}
      className={className}
      onChartReady={(instance) => {
        chartRef.current = instance;
        onChartReady?.(instance);
      }}
      notMerge={false}
      lazyUpdate={true}
    />
  );
}