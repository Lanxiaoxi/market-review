/**
 * 前端离线 mock 数据（单一来源）
 * 后端 API 不可用时各 hook 回退到这里的常量。
 * 注意：与 api/app/services/mock_data.py 保持数值一致；日期动态生成。
 */
import type { OverviewData, SectorItem, IfBasisData, LimitCountsData } from "@/types/market";
import type { WatchlistResponse } from "@/api/watchlist";

function todayStr(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

export const MOCK_OVERVIEW: OverviewData = {
  date: todayStr(),
  weekday: WEEKDAYS[new Date().getDay()],
  closed: true,
  indices: [
    { code: "000001", name: "上证指数", value: 3356.21, change: 18.45, changePct: 0.55, sparkline: [24,22,23,18,20,16,17,12,14,9,11,6] },
    { code: "399001", name: "深证成指", value: 10842.67, change: 86.12, changePct: 0.80, sparkline: [26,23,25,20,21,15,16,10,12,7,8,3] },
    { code: "399006", name: "创业板指", value: 2245.30, change: 22.18, changePct: 1.00, sparkline: [25,24,22,23,17,19,14,16,10,12,7,5] },
    { code: "000688", name: "科创50", value: 1012.45, change: -4.32, changePct: -0.42, sparkline: [6,9,7,12,11,16,15,19,17,22,21,26] },
    { code: "000300", name: "沪深300", value: 3985.20, change: 23.10, changePct: 0.58, sparkline: [25,24,22,23,17,19,14,16,10,12,7,5] },
    { code: "000905", name: "中证500", value: 6124.88, change: 35.66, changePct: 0.59, sparkline: [26,23,25,20,21,15,16,10,12,7,8,3] },
    { code: "000852", name: "中证1000", value: 6890.42, change: -28.15, changePct: -0.41, sparkline: [8,6,10,9,14,13,18,16,20,19,24,27] },
    { code: "HSI", name: "恒生指数", value: 19876.54, change: 142.30, changePct: 0.72, sparkline: [24,22,23,18,20,16,17,12,14,9,11,6] },
  ],
  breadth: {
    up: 3186, down: 1652, flat: 208,
    upPct: 63, downPct: 33, flatPct: 4,
    turnover: "1.26万亿",
    limitUpCount: 48,
    limitDownCount: 6,
    limitUpTop: [
      { name: "寒武纪", pct: 20.01 },
      { name: "沪电股份", pct: 10.00 },
      { name: "中科曙光", pct: 10.00 },
      { name: "工业富联", pct: 10.00 },
      { name: "紫光股份", pct: 10.00 },
    ],
    dist: [
      { label: "涨停", value: 48 },
      { label: "涨2-10%", value: 380 },
      { label: "涨0-2%", value: 2758 },
      { label: "平盘", value: 208 },
      { label: "跌0-2%", value: 1426 },
      { label: "跌2-10%", value: 220 },
      { label: "跌停", value: 6 },
    ],
  },
  sectorsUp: [
    { name: "半导体", pct: 2.86, leading: "寒武纪", sparkline: [18,16,17,13,14,10,11,7,9,6,5] },
    { name: "消费电子", pct: 2.41, leading: "立讯精密", sparkline: [19,17,18,14,15,11,12,8,9,7,6] },
    { name: "汽车零部件", pct: 1.92, leading: "汇川技术", sparkline: [20,18,19,16,17,13,14,11,12,9,8] },
    { name: "医疗服务", pct: 1.55, leading: "迈瑞医疗", sparkline: [17,15,16,12,13,9,10,6,8,5,4] },
    { name: "通信设备", pct: 1.28, leading: "中兴通讯", sparkline: [16,14,15,11,12,8,9,5,7,4,3] },
  ],
  sectorsDown: [
    { name: "煤炭", pct: -1.84, leading: "中国神华", sparkline: [7,9,8,12,11,15,14,18,17,20,21] },
    { name: "银行", pct: -1.32, leading: "招商银行", sparkline: [6,8,7,11,10,14,13,17,16,19,20] },
    { name: "房地产", pct: -0.95, leading: "万科A", sparkline: [8,10,9,13,12,16,15,19,18,21,22] },
    { name: "钢铁", pct: -0.88, leading: "宝钢股份", sparkline: [9,11,10,14,13,17,16,20,19,22,23] },
    { name: "电力", pct: -0.62, leading: "长江电力", sparkline: [10,12,11,15,14,18,17,21,20,23,24] },
  ],
};

export const MOCK_SECTORS: SectorItem[] = [
  { name: "电子", pct: 2.86, leading: "寒武纪", sparkline: [18,16,17,13,14,10,11,7,9,6,5] },
  { name: "计算机", pct: 2.41, leading: "中科曙光", sparkline: [19,17,18,14,15,11,12,8,10,7,6] },
  { name: "汽车", pct: 1.92, leading: "比亚迪", sparkline: [20,18,19,16,17,13,14,11,12,9,8] },
  { name: "医药生物", pct: 1.55, leading: "迈瑞医疗", sparkline: [17,15,16,12,13,9,10,6,8,5,4] },
  { name: "通信", pct: 1.28, leading: "中兴通讯", sparkline: [16,14,15,11,12,8,9,5,7,4,3] },
  { name: "国防军工", pct: 1.12, leading: "中航光电", sparkline: [15,13,14,10,11,7,8,4,6,3,2] },
  { name: "电力设备", pct: 0.95, leading: "宁德时代", sparkline: [14,12,13,9,10,6,7,3,5,2,1] },
  { name: "机械设备", pct: 0.78, leading: "汇川技术", sparkline: [13,11,12,8,9,5,6,2,4,1,0] },
  { name: "传媒", pct: -0.45, leading: "分众传媒", sparkline: [9,11,10,14,13,17,16,20,19,22,23] },
  { name: "食品饮料", pct: -0.88, leading: "贵州茅台", sparkline: [8,10,9,13,12,16,15,19,18,21,22] },
  { name: "公用事业", pct: -1.02, leading: "长江电力", sparkline: [7,9,8,12,11,15,14,18,17,20,21] },
  { name: "银行", pct: -1.32, leading: "招商银行", sparkline: [6,8,7,11,10,14,13,17,16,19,20] },
  { name: "煤炭", pct: -1.84, leading: "中国神华", sparkline: [5,7,6,10,9,13,12,16,15,18,19] },
];

export const MOCK_WATCHLIST: WatchlistResponse = {
  items: [
    { code: "688256.SH", name: "寒武纪", price: 588.00, cost: 480.00, changePct: 20.01, pnl: 4.9, holdingValue: 58.8, positionPct: 30, sparkline: [18,15,17,12,14,8,10,6,8,4,3] },
    { code: "002594.SZ", name: "比亚迪", price: 245.60, cost: 235.00, changePct: 1.92, pnl: 0.5, holdingValue: 24.56, positionPct: 18, sparkline: [19,17,18,14,15,11,12,9,10,7,6] },
    { code: "600036.SH", name: "招商银行", price: 38.20, cost: 40.00, changePct: -1.32, pnl: -2.5, holdingValue: 11.46, positionPct: 12, sparkline: [6,8,7,11,10,14,13,17,16,19,20] },
    { code: "600519.SH", name: "贵州茅台", price: 1520.00, cost: 1480.00, changePct: 0.45, pnl: 0.1, holdingValue: 15.20, positionPct: 12, sparkline: [20,18,19,16,17,13,14,11,12,9,8] },
    { code: "300750.SZ", name: "宁德时代", price: 210.30, cost: 200.00, changePct: 0.80, pnl: 0.2, holdingValue: 18.58, positionPct: 10, sparkline: [19,17,18,14,15,12,13,9,11,8,7] },
  ],
  summary: { totalValue: 128.6, todayPnl: 2.4, holdingPnl: 12.6, position: 82 },
};

/** 股指期现对比 mock（合成：现货在基准价附近，期货主力小幅升水） */
function genIfBasisMock(n = 40, base = 4600, contract = "IF", name = "沪深300"): IfBasisData {
  const dates: string[] = [];
  const spot: number[] = [];
  const futures: number[] = [];
  const d = new Date();
  let count = 0;
  while (count < n) {
    d.setDate(d.getDate() - 1);
    const wd = d.getDay();
    if (wd === 0 || wd === 6) continue; // 跳过周末
    count++;
    dates.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`);
    const v = base + Math.sin(count / 6) * base * 0.013 + (count % 5) * base * 0.001;
    spot.push(Math.round(v * 100) / 100);
    futures.push(Math.round(v * 1.0028 * 100) / 100);
  }
  return {
    contract,
    name,
    dates,
    spot,
    futures,
    premium: futures.map((f, i) => Math.round(((f - spot[i]) / spot[i]) * 1000) / 1000),
  };
}

/** 各合约 mock 基准价（与真实点位量级对齐） */
const MOCK_CONTRACT_BASE: Record<string, { base: number; name: string }> = {
  IF: { base: 4600, name: "沪深300" },
  IH: { base: 2900, name: "上证50" },
  IM: { base: 7700, name: "中证1000" },
};

export const MOCK_IF_BASIS: IfBasisData = genIfBasisMock(40, MOCK_CONTRACT_BASE.IF.base, "IF", MOCK_CONTRACT_BASE.IF.name);

/** 按合约取 mock（hook 在切换合约且后端不可用时使用） */
export function mockIfBasisFor(contract: string): IfBasisData {
  const cfg = MOCK_CONTRACT_BASE[contract] ?? MOCK_CONTRACT_BASE.IF;
  return genIfBasisMock(40, cfg.base, contract, cfg.name);
}

/** 日线涨跌停家数 mock（合成：涨停 30~90 波动，跌停 2~40） */
function genLimitCountsMock(n = 40): LimitCountsData {
  const dates: string[] = [];
  const limitUp: number[] = [];
  const limitDown: number[] = [];
  const d = new Date();
  let count = 0;
  while (count < n) {
    d.setDate(d.getDate() - 1);
    const wd = d.getDay();
    if (wd === 0 || wd === 6) continue; // 跳过周末
    count++;
    dates.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`);
    limitUp.push(Math.round(55 + Math.sin(count / 5) * 22 + (count % 3) * 6));
    limitDown.push(Math.round(14 + Math.cos(count / 7) * 10 + (count % 4) * 3));
  }
  return { dates, limitUp, limitDown };
}

export const MOCK_LIMIT_COUNTS: LimitCountsData = genLimitCountsMock();
