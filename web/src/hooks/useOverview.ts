import { useQuery } from "@tanstack/react-query";
import { fetchOverview } from "@/api/overview";
import { useMarketStore } from "@/stores/market";
import type { OverviewData } from "@/types/market";

export function useOverview() {
  const setSnapshot = useMarketStore((s) => s.setSnapshot);

  return useQuery<OverviewData>({
    queryKey: ["overview"],
    queryFn: async () => {
      const data = await fetchOverview(); // 失败即抛错，页面显示「暂无有效数据」
      setSnapshot(data);
      return data;
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
