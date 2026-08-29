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
    """沪深300 期现对比（日线）：现货收盘 vs 中金所 IF 主力收盘"""

    dates: list[str]      # "YYYY-MM-DD"（升序）
    spot: list[float]     # 沪深300 现货收盘
    futures: list[float]  # 中金所 IF 主力合约收盘
    premium: list[float]  # 基差率 % = (futures - spot) / spot * 100