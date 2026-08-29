"""自选/持仓表"""

from typing import Optional
from sqlmodel import SQLModel, Field


class WatchlistItem(SQLModel, table=True):
    """自选池个股"""
    __tablename__ = "watchlist"

    id: Optional[int] = Field(default=None, primary_key=True)
    # 唯一约束由 db.py 迁移逻辑创建（CREATE UNIQUE INDEX ux_watchlist_code），
    # 兼容历史库（create_all 不会为已有表补列/索引）。
    code: str = Field(index=True, max_length=16)          # e.g. "600519.SH"
    name: str = Field(max_length=32)                       # e.g. "贵州茅台"
    price: float = Field(default=0)                        # 现价（元）
    cost: float = Field(default=0)                         # 成本价（元，持仓盈亏计算用）
    change_pct: float = Field(default=0)
    pnl: float = Field(default=0)                           # 今日盈亏（万）
    holding_value: float = Field(default=0)                 # 持仓市值（万）
    position_pct: float = Field(default=0)                  # 仓位占比 %
    sort_order: int = Field(default=0)