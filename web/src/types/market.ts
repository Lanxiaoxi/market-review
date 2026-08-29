/* ===== 前端类型定义（与后端 pydantic schemas 对齐） ===== */

/** 指数快照 */
export interface IndexSnapshot {
  code: string;
  name: string;
  value: number;
  change: number;
  changePct: number;
  sparkline: number[]; // 12 个归一化点
}

/** 涨跌家数分布区间 */
export interface DistBucket {
  label: string;
  value: number;
}

/** 市场宽度 */
export interface MarketBreadth {
  up: number;
  down: number;
  flat: number;
  upPct: number;
  downPct: number;
  flatPct: number;
  turnover: string; // e.g. "1.26万亿"
  limitUpCount: number;
  limitDownCount: number;
  limitUpTop: LimitUpStock[];
  dist: DistBucket[]; // 7 档分布（后端真实统计）
}

/** 涨停个股 */
export interface LimitUpStock {
  name: string;
  pct: number;
}

/** 行业板块 */
export interface SectorItem {
  name: string;
  pct: number;
  leading: string;
  sparkline: number[];
}

/** 今日总览数据 */
export interface OverviewData {
  date: string;
  weekday: string;
  closed: boolean;
  indices: IndexSnapshot[];
  breadth: MarketBreadth;
  sectorsUp: SectorItem[];
  sectorsDown: SectorItem[];
}

/** 自选持仓 */
export interface WatchlistItem {
  code: string;
  name: string;
  price: number;
  cost: number;        // 成本价（元）
  changePct: number;
  pnl: number;         // 今日盈亏（万）
  holdingValue: number; // 持仓市值（万）
  positionPct: number;  // 仓位占比 %
  sparkline: number[];
}

/** 自选汇总 */
export interface WatchlistSummary {
  totalValue: number;  // 总市值（万）
  todayPnl: number;    // 今日盈亏（万）
  holdingPnl: number;  // 持仓盈亏（万）
  position: number;    // 仓位 %
}

/** 图表库项 */
export interface ChartLibItem {
  id: string;
  name: string;
  type: string;
  pinned: boolean;
}

/** 指数当日分时（腾讯兜底） */
export interface IntradaySeries {
  times: string[];    // ["09:30", "09:31", ...]
  prices: number[];
  amounts: number[];  // 累计成交额（元）
}

export interface IntradayData {
  codes: Record<string, IntradaySeries>; // key = 腾讯代码，如 sh000001
}
