import apiClient from "./client";
import type { OverviewData } from "@/types/market";

export async function fetchOverview(): Promise<OverviewData> {
  const { data } = await apiClient.get<OverviewData>("/overview");
  return data;
}