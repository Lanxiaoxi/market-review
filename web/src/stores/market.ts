import { create } from "zustand";
import type { OverviewData } from "@/types/market";

interface MarketState {
  /** 今日行情快照 */
  snapshot: OverviewData | null;
  /** 上次刷新时间戳（毫秒） */
  lastRefresh: number;
  /** 是否正在刷新 */
  refreshing: boolean;

  setSnapshot: (data: OverviewData) => void;
  setRefreshing: (v: boolean) => void;
  /** 节流刷新：距离上次不足 minInterval 则跳过 */
  throttleRefresh: (minIntervalMs: number) => boolean;
}

export const useMarketStore = create<MarketState>((set, get) => ({
  snapshot: null,
  lastRefresh: 0,
  refreshing: false,

  setSnapshot: (data) =>
    set({ snapshot: data, lastRefresh: Date.now(), refreshing: false }),

  setRefreshing: (v) => set({ refreshing: v }),

  throttleRefresh: (minIntervalMs) => {
    const { lastRefresh, refreshing } = get();
    if (refreshing) return false;
    if (Date.now() - lastRefresh < minIntervalMs) return false;
    set({ refreshing: true });
    return true;
  },
}));