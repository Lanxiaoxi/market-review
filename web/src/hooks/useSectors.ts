import { useQuery } from "@tanstack/react-query";
import { fetchSectors } from "@/api/sectors";
import type { SectorItem } from "@/types/market";

export function useSectors(sort = "pct") {
  return useQuery<SectorItem[]>({
    queryKey: ["sectors", sort],
    queryFn: () => fetchSectors(sort), // 失败即抛错，页面显示「暂无有效数据」
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
