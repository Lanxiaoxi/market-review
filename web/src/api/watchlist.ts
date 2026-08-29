import apiClient from "./client";
import type { WatchlistItem, WatchlistSummary } from "@/types/market";

export interface WatchlistResponse {
  items: WatchlistItem[];
  summary: WatchlistSummary;
}

export async function fetchWatchlist(): Promise<WatchlistResponse> {
  const { data } = await apiClient.get<WatchlistResponse>("/watchlist");
  return data;
}

export async function addWatchlistItem(
  payload: Pick<
    WatchlistItem,
    "code" | "name" | "price" | "cost" | "changePct" | "pnl" | "holdingValue" | "positionPct"
  >
): Promise<WatchlistItem> {
  const { data } = await apiClient.post<WatchlistItem>("/watchlist", payload);
  return data;
}

export async function updateWatchlistItem(
  code: string,
  patch: Partial<WatchlistItem>
): Promise<WatchlistItem> {
  const { data } = await apiClient.put<WatchlistItem>(
    `/watchlist/${code}`,
    patch
  );
  return data;
}

export async function deleteWatchlistItem(code: string): Promise<void> {
  await apiClient.delete(`/watchlist/${code}`);
}