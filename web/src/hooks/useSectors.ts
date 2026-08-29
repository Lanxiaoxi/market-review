import { useQuery } from "@tanstack/react-query";
import { fetchSectors } from "@/api/sectors";
import { MOCK_SECTORS } from "@/mocks";
import type { SectorItem } from "@/types/market";

export function useSectors(sort = "pct") {
  return useQuery<SectorItem[]>({
    queryKey: ["sectors", sort],
    queryFn: async () => {
      try {
        return await fetchSectors(sort);
      } catch {
        // 后端未就绪 → 返回按涨跌幅排序的 mock
        return [...MOCK_SECTORS].sort(
          (a, b) => (sort === "pct-asc" ? a.pct - b.pct : b.pct - a.pct)
        );
      }
    },
    staleTime: 1000 * 60 * 5,
    retry: 1,
    placeholderData: MOCK_SECTORS,
  });
}
