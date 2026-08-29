import { useQuery } from "@tanstack/react-query";
import { fetchFuturesBasis } from "@/api/charts";
import type { IfBasisData } from "@/types/market";

/** 股指期货期现对比（日线，近 days 个交易日；contract: IF/IH/IM，失败即抛错） */
export function useIfBasis(contract = "IF", days = 60) {
  return useQuery<IfBasisData>({
    queryKey: ["futures-basis", contract, days],
    queryFn: () => fetchFuturesBasis(contract, days),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
