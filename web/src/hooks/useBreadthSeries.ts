import { useQuery } from "@tanstack/react-query";
import { fetchBreadthSeries } from "@/api/charts";
import type { BreadthSeriesData } from "@/types/market";

/** 日线市场宽度序列（上涨/平盘/下跌家数，近 days 个交易日，失败即抛错） */
export function useBreadthSeries(days = 60) {
  return useQuery<BreadthSeriesData>({
    queryKey: ["breadth-series", days],
    queryFn: () => fetchBreadthSeries(days),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
