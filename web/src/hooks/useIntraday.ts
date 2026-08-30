import { useQuery } from "@tanstack/react-query";
import { fetchIntraday } from "@/api/intraday";
import type { IntradayData } from "@/types/market";

/**
 * 指数分时（腾讯兜底 / 本地固化）
 * enabled 控制是否拉取；days 指定最近 N 个交易日（1 = 当日，>1 拼接多日）
 */
export function useIntraday(codes: string[], enabled = true, days = 1) {
  return useQuery<IntradayData>({
    queryKey: ["intraday", codes.join(","), days],
    queryFn: () => fetchIntraday(codes, days),
    enabled: enabled && codes.length > 0,
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
