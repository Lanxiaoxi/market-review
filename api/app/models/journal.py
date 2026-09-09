"""订单复盘表"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TradeOrder(SQLModel, table=True):
    """一笔订单复盘：标的 + 日期 + 盈亏 + 开平仓逻辑 + 笔记 + 截图"""
    __tablename__ = "trade_orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, max_length=32)           # 标的名（必填）
    trade_date: str = Field(index=True, max_length=10)       # 订单日期 YYYY-MM-DD（列表排序字段）
    pnl: float = Field(default=0)                            # 带符号盈亏（元，正盈负亏）
    open_logic: str = Field(default="", max_length=32)       # 开仓逻辑
    close_logic: str = Field(default="", max_length=32)      # 平仓逻辑
    note: str = Field(default="", max_length=2000)           # 订单笔记
    image_path: str = Field(default="", max_length=255)      # 相对 UPLOAD_DIR 的路径，如 orders/202609/xxx.png
    created_at: datetime = Field(default_factory=datetime.now)
