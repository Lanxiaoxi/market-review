import apiClient from "./client";
import type { ChartLibItem, IfBasisData } from "@/types/market";

export async function fetchCharts(): Promise<ChartLibItem[]> {
  const { data } = await apiClient.get<ChartLibItem[]>("/charts");
  return data;
}

/** 沪深300 期现对比（日线，近 days 个交易日） */
export async function fetchIfBasis(days = 60): Promise<IfBasisData> {
  const { data } = await apiClient.get<IfBasisData>("/charts/if-basis", {
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