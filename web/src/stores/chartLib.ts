import { create } from "zustand";
import type { ChartLibItem } from "@/types/market";

interface ChartLibState {
  charts: ChartLibItem[];
  pinnedIds: string[];

  setCharts: (charts: ChartLibItem[]) => void;
  pin: (id: string) => void;
  unpin: (id: string) => void;
  togglePin: (id: string) => void;
  addChart: (chart: ChartLibItem) => void;
  removeChart: (id: string) => void;
}

export const useChartLibStore = create<ChartLibState>((set) => ({
  charts: [],
  pinnedIds: [],

  setCharts: (charts) =>
    set({
      charts,
      pinnedIds: charts.filter((c) => c.pinned).map((c) => c.id),
    }),

  pin: (id) =>
    set((s) => ({
      pinnedIds: s.pinnedIds.includes(id) ? s.pinnedIds : [...s.pinnedIds, id],
      charts: s.charts.map((c) => (c.id === id ? { ...c, pinned: true } : c)),
    })),

  unpin: (id) =>
    set((s) => ({
      pinnedIds: s.pinnedIds.filter((pid) => pid !== id),
      charts: s.charts.map((c) => (c.id === id ? { ...c, pinned: false } : c)),
    })),

  togglePin: (id) =>
    set((s) => {
      const isPinned = s.pinnedIds.includes(id);
      return {
        pinnedIds: isPinned
          ? s.pinnedIds.filter((pid) => pid !== id)
          : [...s.pinnedIds, id],
        charts: s.charts.map((c) =>
          c.id === id ? { ...c, pinned: !c.pinned } : c
        ),
      };
    }),

  addChart: (chart) =>
    set((s) => {
      const charts = [...s.charts, chart];
      const pinnedIds = chart.pinned
        ? [...s.pinnedIds, chart.id]
        : s.pinnedIds;
      return { charts, pinnedIds };
    }),

  removeChart: (id) =>
    set((s) => ({
      charts: s.charts.filter((c) => c.id !== id),
      pinnedIds: s.pinnedIds.filter((pid) => pid !== id),
    })),
}));