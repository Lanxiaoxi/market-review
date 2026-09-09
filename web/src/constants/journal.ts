/** 订单复盘：开仓 / 平仓逻辑下拉选项（可在此自由增改） */

export const OPEN_LOGIC_OPTIONS = [
  "放量突破",
  "回调低吸",
  "回踩均线",
  "指标金叉",
  "打板接力",
  "题材异动",
  "消息驱动",
  "左侧低吸",
  "随手单",
  "其他",
];

export const CLOSE_LOGIC_OPTIONS = [
  "止盈离场",
  "破位止损",
  "均线走坏",
  "情绪退潮",
  "时间止损",
  "降仓避险",
  "消息利空",
  "纪律执行",
  "随手单",
  "其他",
];

/** 盈亏类型（Segmented 选项） */
export const PNL_TYPE_OPTIONS = [
  { label: "盈利", value: "win" },
  { label: "亏损", value: "loss" },
] as const;

export type PnlType = (typeof PNL_TYPE_OPTIONS)[number]["value"];
