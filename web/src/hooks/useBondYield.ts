import { useQuery } from "@tanstack/react-query";
import { fetchBondYield } from "@/api/charts";
import type { BondYieldData } from "@/types/market";

/** 中债国债收益率曲线（2/5/10/30 年期，近 days 个交易日，失败即抛错） */
export function useBondYield(days = 60) {
  return useQuery<BondYieldData>({
    queryKey: ["bond-yield", days],
    queryFn: () => fetchBondYield(days),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
