import apiClient from "./client";
import type { SectorItem } from "@/types/market";

export interface SectorHistory {
  code: string;
  name: string;
  dates: string[];
  closes: number[];
}

export async function fetchSectors(sort = "pct", range = 1): Promise<SectorItem[]> {
  const { data } = await apiClient.get<SectorItem[]>("/sectors", {
    params: { sort, range },
  });
  return data;
}

export async function fetchSectorHistory(code: string, days = 60): Promise<SectorHistory> {
  const { data } = await apiClient.get<SectorHistory>(`/sectors/${code}/history`, {
    params: { days },
  });
  return data;
}
