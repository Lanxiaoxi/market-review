import apiClient from "./client";
import type { OverviewData } from "@/types/market";

export async function fetchOverview(): Promise<OverviewData> {
  const { data } = await apiClient.get<OverviewData>("/overview");
  return data;
}

/** 按日期取历史总览（后端：快照优先，否则 L2 本地按日聚合，非交易日吸附到最近交易日） */
export async function fetchOverviewByDate(date: string): Promise<OverviewData> {
  const { data } = await apiClient.get<OverviewData>("/history", { params: { date } });
  return data;
}