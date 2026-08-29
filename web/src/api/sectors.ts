import apiClient from "./client";
import type { SectorItem } from "@/types/market";

export async function fetchSectors(sort = "pct"): Promise<SectorItem[]> {
  const { data } = await apiClient.get<SectorItem[]>("/sectors", {
    params: { sort },
  });
  return data;
}