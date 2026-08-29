import apiClient from "./client";
import type { ChartLibItem } from "@/types/market";

export async function fetchCharts(): Promise<ChartLibItem[]> {
  const { data } = await apiClient.get<ChartLibItem[]>("/charts");
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