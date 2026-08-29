import { create } from "zustand";
import type { WatchlistItem, WatchlistSummary } from "@/types/market";

interface WatchlistState {
  items: WatchlistItem[];
  summary: WatchlistSummary | null;

  setItems: (items: WatchlistItem[]) => void;
  setSummary: (s: WatchlistSummary) => void;
  addItem: (item: WatchlistItem) => void;
  removeItem: (code: string) => void;
  updateItem: (code: string, patch: Partial<WatchlistItem>) => void;
}

export const useWatchlistStore = create<WatchlistState>((set) => ({
  items: [],
  summary: null,

  setItems: (items) => set({ items }),
  setSummary: (summary) => set({ summary }),

  addItem: (item) =>
    set((s) => ({ items: [...s.items, item] })),

  removeItem: (code) =>
    set((s) => ({ items: s.items.filter((i) => i.code !== code) })),

  updateItem: (code, patch) =>
    set((s) => ({
      items: s.items.map((i) => (i.code === code ? { ...i, ...patch } : i)),
    })),
}));