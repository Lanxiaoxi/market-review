import { useQuery } from "@tanstack/react-query";
import { fetchIfBasis } from "@/api/charts";
import { MOCK_IF_BASIS } from "@/mocks";
import type { IfBasisData } from "@/types/market";

/** 沪深300 期现对比（日线，近 days 个交易日；后端不可用时回退 mock） */
export function useIfBasis(days = 60) {
  return useQuery<IfBasisData>({
    queryKey: ["if-basis", days],
    queryFn: async () => {
      try {
        return await fetchIfBasis(days);
      } catch {
        return MOCK_IF_BASIS;
      }
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
    placeholderData: MOCK_IF_BASIS,
  });
}
