import { useQuery } from "@tanstack/react-query";
import { fetchLimitCounts } from "@/api/charts";
import { MOCK_LIMIT_COUNTS } from "@/mocks";
import type { LimitCountsData } from "@/types/market";

/** 日线涨停/跌停家数（近 days 个交易日；后端不可用时回退 mock） */
export function useLimitCounts(days = 60) {
  return useQuery<LimitCountsData>({
    queryKey: ["limit-counts", days],
    queryFn: async () => {
      try {
        return await fetchLimitCounts(days);
      } catch {
        return MOCK_LIMIT_COUNTS;
      }
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
    placeholderData: MOCK_LIMIT_COUNTS,
  });
}
