import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchWatchlist,
  addWatchlistItem,
  deleteWatchlistItem,
  updateWatchlistItem,
  type WatchlistResponse,
} from "@/api/watchlist";
import { useWatchlistStore } from "@/stores/watchlist";
import { MOCK_WATCHLIST } from "@/mocks";
import type { WatchlistItem } from "@/types/market";

export { MOCK_WATCHLIST };

/** 自选池查询（后端不可用时回退 mock） */
export function useWatchlistQuery() {
  const setItems = useWatchlistStore((s) => s.setItems);
  const setSummary = useWatchlistStore((s) => s.setSummary);

  return useQuery<WatchlistResponse>({
    queryKey: ["watchlist"],
    queryFn: async () => {
      try {
        const data = await fetchWatchlist();
        setItems(data.items);
        setSummary(data.summary);
        return data;
      } catch {
        setItems(MOCK_WATCHLIST.items);
        setSummary(MOCK_WATCHLIST.summary);
        return MOCK_WATCHLIST;
      }
    },
    placeholderData: MOCK_WATCHLIST,
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
