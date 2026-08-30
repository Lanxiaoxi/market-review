import { useQuery } from "@tanstack/react-query";
import { fetchTreasuryFutures } from "@/api/charts";
import type { TreasuryFuturesData } from "@/types/market";

/** 国债期货主力连续日线（contract: TS/TF/T/TL，近 days 个交易日） */
export function useTreasuryFutures(contract = "T", days = 60) {
  return useQuery<TreasuryFuturesData>({
    queryKey: ["treasury-futures", contract, days],
    queryFn: () => fetchTreasuryFutures(contract, days),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
