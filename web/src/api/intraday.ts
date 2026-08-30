import apiClient from "./client";
import type { IntradayData } from "@/types/market";

export async function fetchIntraday(codes: string[], days = 1): Promise<IntradayData> {
  const { data } = await apiClient.get<IntradayData>("/intraday", {
    params: { codes: codes.join(","), days },
    timeout: 20_000,
  });
  return data;
}
