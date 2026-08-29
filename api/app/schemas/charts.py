"""图表库响应模型"""

from typing import Optional
from pydantic import BaseModel


class ChartLibItemOut(BaseModel):
    id: str
    name: str
    type: str
    pinned: bool


class ChartCreateIn(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    pinned: bool = False


class ChartUpdateIn(BaseModel):
    name: Optional[str] = None
    pinned: Optional[bool] = None


class IfBasisOut(BaseModel):
    """股指期货期现对比（日线）：现货收盘 vs 中金所主力合约收盘"""

    contract: str        # IF / IH / IM
    name: str            # 现货指数名称（沪深300 / 上证50 / 中证1000）
    dates: list[str]     # "YYYY-MM-DD"（升序）
    spot: list[float]    # 现货指数收盘
    futures: list[float] # 中金所主力合约收盘
    premium: list[float] # 基差率 % = (futures - spot) / spot * 100