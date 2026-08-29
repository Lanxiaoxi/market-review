import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCharts, updateChart, addChart } from "@/api/charts";
import { useChartLibStore } from "@/stores/chartLib";
import type { ChartLibItem } from "@/types/market";

/** 内置图表清单（自定义图表页可钉选的图表） */
export const BUILTIN_CHARTS: ChartLibItem[] = [
  { id: "bar-dist", name: "涨跌家数分布", type: "barDist", pinned: false },
  { id: "turnover-intraday", name: "成交额分时", type: "turnoverIntraday", pinned: false },
];

/** 图表库查询：后端列表 + 内置清单合并，写入 store */
export function useChartLibQuery() {
  const setCharts = useChartLibStore((s) => s.setCharts);

  return useQuery<ChartLibItem[]>({
    queryKey: ["chart-lib"],
    queryFn: async () => {
      let remote: ChartLibItem[] = [];
      try {
        remote = await fetchCharts();
      } catch {
        remote = [];
      }
      // 合并：内置清单（保证两张图可钉选）+ 后端记录（含钉选状态）
      const merged = BUILTIN_CHARTS.map((c) => {
        const r = remote.find((x) => x.id === c.id);
        return r ? { ...c, pinned: r.pinned } : c;
      });
      setCharts(merged);
      return merged;
    },
  });
}

/**
 * 钉选/取消钉选 → 更新 store + 同步后端
 * 后端已有记录 → PUT 更新 pinned；没有 → POST 创建
 */
export function useToggleChartPin() {
  const queryClient = useQueryClient();
  const togglePin = useChartLibStore((s) => s.togglePin);

  return useMutation({
    mutationFn: async (chart: ChartLibItem) => {
      const nextPinned = !chart.pinned;
      try {
        const remote = await fetchCharts();
        const exists = remote.some((r) => r.id === chart.id);
        if (exists) {
          await updateChart(chart.id, { pinned: nextPinned });
        } else {
          await addChart({ id: chart.id, name: chart.name, type: chart.type, pinned: nextPinned });
        }
      } catch {
        // 后端不可用：仅本地 store 生效（mock 模式）
      }
      return nextPinned;
    },
    onSuccess: (nextPinned, chart) => {
      togglePin(chart.id);
      queryClient.invalidateQueries({ queryKey: ["chart-lib"] });
    },
  });
}