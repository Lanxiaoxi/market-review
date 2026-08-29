import { useQuery } from "@tanstack/react-query";
import { fetchLimitCounts } from "@/api/charts";
import type { LimitCountsData } from "@/types/market";

/** 日线涨停/跌停家数（近 days 个交易日，失败即抛错） */
export function useLimitCounts(days = 60) {
  return useQuery<LimitCountsData>({
    queryKey: ["limit-counts", days],
    queryFn: () => fetchLimitCounts(days),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
