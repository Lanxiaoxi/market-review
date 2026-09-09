/** 订单复盘类型定义 */

export interface TradeOrder {
  id: number;
  /** 标的名 */
  symbol: string;
  /** 订单日期 YYYY-MM-DD */
  tradeDate: string;
  /** 带符号盈亏（万元，正盈负亏） */
  pnl: number;
  /** 开仓逻辑 */
  openLogic: string;
  /** 平仓逻辑 */
  closeLogic: string;
  /** 订单笔记 */
  note: string;
  /** 截图访问地址 */
  imageUrl: string;
}

export interface JournalSummary {
  total: number;
  winCount: number;
  lossCount: number;
  /** 胜率 % */
  winRate: number;
  /** 累计盈亏（万元） */
  totalPnl: number;
}

export interface JournalResponse {
  items: TradeOrder[];
  summary: JournalSummary;
}

/** 新建订单提交载荷（multipart 表单字段，不含文件） */
export interface OrderFormValues {
  symbol: string;
  tradeDate: string;
  /** 正数（万元） */
  amount: string;
  /** win | loss */
  pnlType: "win" | "loss";
  openLogic: string;
  closeLogic: string;
  note: string;
}
