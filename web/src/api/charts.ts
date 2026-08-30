import apiClient from "./client";
import type {
  IfBasisData,
  LimitCountsData,
  BreadthSeriesData,
  FiftyTwoWeekData,
  BondYieldData,
  TreasuryFuturesData,
} from "@/types/market";

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

/** 近 days 个交易日的 52 周新高/新低个股家数（滚动 250 日窗口） */
export async function fetch52wHighLow(days = 60): Promise<FiftyTwoWeekData> {
  const { data } = await apiClient.get<FiftyTwoWeekData>("/charts/52w-high-low", {
    params: { days },
    timeout: 30_000,
  });
  return data;
}

/** 中债国债收益率曲线（2/5/10/30 年期，近 days 个交易日） */
export async function fetchBondYield(days = 60): Promise<BondYieldData> {
  const { data } = await apiClient.get<BondYieldData>("/charts/bond-yield", {
    params: { days },
    timeout: 20_000,
  });
  return data;
}

/** 国债期货主力连续日线（contract: TS/TF/T/TL） */
export async function fetchTreasuryFutures(
  contract: string,
  days = 60
): Promise<TreasuryFuturesData> {
  const { data } = await apiClient.get<TreasuryFuturesData>("/charts/treasury-futures", {
    params: { contract, days },
    timeout: 30_000,
  });
  return data;
}
