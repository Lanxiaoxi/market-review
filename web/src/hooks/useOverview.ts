import { useQuery } from "@tanstack/react-query";
import { fetchOverview, fetchOverviewByDate } from "@/api/overview";
import { useMarketStore } from "@/stores/market";
import type { OverviewData } from "@/types/market";

export function useOverview(date?: string | null) {
  const setSnapshot = useMarketStore((s) => s.setSnapshot);

  return useQuery<OverviewData>({
    queryKey: ["overview", date ?? "latest"],
    queryFn: async () => {
      // date 为空 → 最新总览；指定 date → 历史日期（后端 L2 按日聚合）
      const data = date ? await fetchOverviewByDate(date) : await fetchOverview();
      setSnapshot(data);
      return data;
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
