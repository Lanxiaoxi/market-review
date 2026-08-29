import { useQuery } from "@tanstack/react-query";
import { fetchOverview } from "@/api/overview";
import { useMarketStore } from "@/stores/market";

/**
 * 盘中轮询 hook（受 Gate G2 控制：默认仅收盘后数据，可选盘中 60s）
 * 启用时每 60s 轮询 /api/overview，ETag/时间戳去重由后端缓存层处理
 */
export function usePolling(enabled = false) {
  const setSnapshot = useMarketStore((s) => s.setSnapshot);

  return useQuery({
    queryKey: ["overview", "polling"],
    queryFn: async () => {
      const data = await fetchOverview(); // 失败即抛错，保留上次快照
      setSnapshot(data);
      return data;
    },
    refetchInterval: enabled ? 60_000 : false,
    staleTime: enabled ? 55_000 : 1000 * 60 * 5,
    enabled,
  });
}
