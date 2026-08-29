import apiClient from "./client";
import type { ChartLibItem, IfBasisData, LimitCountsData } from "@/types/market";

export async function fetchCharts(): Promise<ChartLibItem[]> {
  const { data } = await apiClient.get<ChartLibItem[]>("/charts");
  return data;
}

/** 股指期货期现对比（日线，近 days 个交易日；contract: IF/IH/IM） */
export async function fetchFuturesBasis(contract: string, days = 60): Promise<IfBasisData> {
  const { data } = await apiClient.get<IfBasisData>("/charts/futures-basis", {
    params: { contract, days },
    timeout: 30_000,
  });
  return data;
}

/** 日线涨停/跌停家数（近 days 个交易日） */
export async function fetchLimitCounts(days = 60): Promise<LimitCountsData> {
  const { data } = await apiClient.get<LimitCountsData>("/charts/limit-counts", {
    params: { days },
    timeout: 30_000,
  });
  return data;
}

export async function addChart(
  payload: Omit<ChartLibItem, "id"> & { id?: string }
): Promise<ChartLibItem> {
  const { data } = await apiClient.post<ChartLibItem>("/charts", payload);
  return data;
}

export async function updateChart(
  id: string,
  patch: Partial<ChartLibItem>
): Promise<ChartLibItem> {
  const { data } = await apiClient.put<ChartLibItem>(`/charts/${id}`, patch);
  return data;
}

export async function deleteChart(id: string): Promise<void> {
  await apiClient.delete(`/charts/${id}`);
}