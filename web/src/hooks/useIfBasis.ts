import { useQuery } from "@tanstack/react-query";
import { fetchFuturesBasis } from "@/api/charts";
import { mockIfBasisFor } from "@/mocks";
import type { IfBasisData } from "@/types/market";

/** 股指期货期现对比（日线，近 days 个交易日；contract: IF/IH/IM，后端不可用时回退 mock） */
export function useIfBasis(contract = "IF", days = 60) {
  return useQuery<IfBasisData>({
    queryKey: ["futures-basis", contract, days],
    queryFn: async () => {
      try {
        return await fetchFuturesBasis(contract, days);
      } catch {
        return mockIfBasisFor(contract);
      }
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
    placeholderData: () => mockIfBasisFor(contract),
  });
}
