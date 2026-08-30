import { useQuery } from "@tanstack/react-query";
import { fetch52wHighLow } from "@/api/charts";
import type { FiftyTwoWeekData } from "@/types/market";

/** 近 days 个交易日的 52 周新高/新低个股家数（失败即抛错） */
export function use52wHighLow(days = 60) {
  return useQuery<FiftyTwoWeekData>({
    queryKey: ["52w-high-low", days],
    queryFn: () => fetch52wHighLow(days),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
