import apiClient from "./client";
import type { IfBasisData, LimitCountsData, BreadthSeriesData } from "@/types/market";

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

/** 日线市场宽度序列（上涨/平盘/下跌家数，近 days 个交易日） */
export async function fetchBreadthSeries(days = 60): Promise<BreadthSeriesData> {
  const { data } = await apiClient.get<BreadthSeriesData>("/charts/breadth-series", {
    params: { days },
    timeout: 30_000,
  });
  return data;
}
