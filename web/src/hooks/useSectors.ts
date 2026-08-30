import { useQuery } from "@tanstack/react-query";
import { fetchSectors, fetchSectorHistory } from "@/api/sectors";
import type { SectorHistory } from "@/api/sectors";
import type { SectorItem } from "@/types/market";

/** 行业板块排名（range: 1=当日 / 5=近5日 / 10=近10日 / 20=近20日 动量区间） */
export function useSectors(sort = "pct", range = 1) {
  return useQuery<SectorItem[]>({
    queryKey: ["sectors", sort, range],
    queryFn: () => fetchSectors(sort, range),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}

/** 单个板块历史收盘序列（详情图） */
export function useSectorHistory(code: string | null, days = 60) {
  return useQuery<SectorHistory>({
    queryKey: ["sector-history", code, days],
    queryFn: () => fetchSectorHistory(code!, days),
    enabled: !!code,
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
