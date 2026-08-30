import { TOKENS } from "@/components/charts/BaseChart";

/**
 * 分时对比可选指数（7 只 A 股，均有腾讯分钟线；中证2000/港股无分钟线不提供）。
 * 首页分时对比与侧边栏偏好设置共用这一份单一来源。
 */
export const INDEX_SERIES = [
  { name: "上证指数", code: "000001", tencent: "sh000001", color: TOKENS.ink },
  { name: "上证50", code: "000016", tencent: "sh000016", color: TOKENS.accent },
  { name: "沪深300", code: "000300", tencent: "sh000300", color: TOKENS.seriesPurple },
  { name: "中证500", code: "000905", tencent: "sh000905", color: "#c97b2d" },
  { name: "创业板指", code: "399006", tencent: "sz399006", color: "#1f9d8a" },
  { name: "科创50", code: "000688", tencent: "sh000688", color: "#b048c8" },
  { name: "中证1000", code: "000852", tencent: "sh000852", color: "#2f8fd6" },
];

/** 默认显示的指数（上证 + 创业板） */
export const DEFAULT_SELECTED = ["000001", "399006"];
