import apiClient from "./client";
import type { IntradayData } from "@/types/market";

export async function fetchIntraday(codes: string[]): Promise<IntradayData> {
  const { data } = await apiClient.get<IntradayData>("/intraday", {
    params: { codes: codes.join(",") },
    timeout: 20_000,
  });
  return data;
}
