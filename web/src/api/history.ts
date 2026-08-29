import apiClient from "./client";
import type { OverviewData } from "@/types/market";

export async function fetchHistory(date: string): Promise<OverviewData> {
  const { data } = await apiClient.get<OverviewData>("/history", {
    params: { date },
  });
  return data;
}