import { useQuery } from "@tanstack/react-query";
import { fetchIntraday } from "@/api/intraday";
import type { IntradayData } from "@/types/market";

/**
 * 指数当日分时（腾讯兜底 + 后端 mock 回退，恒有数据）
 * enabled 控制是否拉取（如仅在「今日」分段激活时请求）
 */
export function useIntraday(codes: string[], enabled = true) {
  return useQuery<IntradayData>({
    queryKey: ["intraday", codes.join(",")],
    queryFn: () => fetchIntraday(codes),
    enabled: enabled && codes.length > 0,
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
