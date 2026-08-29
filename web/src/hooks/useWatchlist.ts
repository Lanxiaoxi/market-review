import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchWatchlist,
  addWatchlistItem,
  deleteWatchlistItem,
  updateWatchlistItem,
  type WatchlistResponse,
} from "@/api/watchlist";
import { useWatchlistStore } from "@/stores/watchlist";
import type { WatchlistItem } from "@/types/market";

/** 自选池查询（失败即抛错，页面显示空态） */
export function useWatchlistQuery() {
  const setItems = useWatchlistStore((s) => s.setItems);
  const setSummary = useWatchlistStore((s) => s.setSummary);

  return useQuery<WatchlistResponse>({
    queryKey: ["watchlist"],
    queryFn: async () => {
      const data = await fetchWatchlist();
      setItems(data.items);
      setSummary(data.summary);
      return data;
    },
  });
}

/** 添加自选 → 落库 + 刷新列表 */
export function useAddWatchlistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: addWatchlistItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}

/** 更新自选 → 落库 + 刷新列表 */
export function useUpdateWatchlistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ code, patch }: { code: string; patch: Partial<WatchlistItem> }) =>
      updateWatchlistItem(code, patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}

/** 删除自选 → 落库 + 刷新列表 */
export function useDeleteWatchlistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteWatchlistItem,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}
