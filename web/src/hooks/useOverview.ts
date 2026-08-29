import { useQuery } from "@tanstack/react-query";
import { fetchOverview } from "@/api/overview";
import { useMarketStore } from "@/stores/market";
import { MOCK_OVERVIEW } from "@/mocks";
import type { OverviewData } from "@/types/market";

export { MOCK_OVERVIEW };

export function useOverview() {
  const setSnapshot = useMarketStore((s) => s.setSnapshot);

  return useQuery<OverviewData>({
    queryKey: ["overview"],
    queryFn: async () => {
      try {
        const data = await fetchOverview();
        setSnapshot(data);
        return data;
      } catch {
        // 后端未就绪 → 返回 mock 数据
        setSnapshot(MOCK_OVERVIEW);
        return MOCK_OVERVIEW;
      }
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
    placeholderData: MOCK_OVERVIEW,
  });
}
