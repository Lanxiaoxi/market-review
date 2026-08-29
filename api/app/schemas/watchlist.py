"""自选响应模型 —— camelCase 输出"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, alias_generators, Field, field_validator


class CamelModel(BaseModel):
    """camelCase 出入参统一；内部字段保持 snake_case"""
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


CODE_PATTERN = r"^[0-9]{6}(\.[A-Za-z]{2})?$"


class WatchlistItemOut(CamelModel):
    code: str
    name: str
    price: float
    cost: float = 0          # 成本价（元）
    change_pct: float
    pnl: float               # 今日盈亏（万）
    holding_value: float = 0  # 持仓市值（万）
    position_pct: float = 0   # 仓位占比 %
    sparkline: list[float] = []


class WatchlistSummaryOut(CamelModel):
    total_value: float       # 总市值（万）
    today_pnl: float         # 今日盈亏（万）
    holding_pnl: float       # 持仓盈亏（万）
    position: float          # 仓位 %


class WatchlistResponse(CamelModel):
    items: list[WatchlistItemOut]
    summary: WatchlistSummaryOut


class WatchlistCreateIn(CamelModel):
    code: str = Field(pattern=CODE_PATTERN, description="6 位数字，可选 .SH/.SZ/.BJ 后缀")
    name: str
    price: float = 0
    cost: float = 0
    change_pct: float = 0
    pnl: float = 0
    holding_value: float = 0
    position_pct: float = 0

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("名称不能为空")
        return v


class WatchlistUpdateIn(CamelModel):
    name: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    change_pct: Optional[float] = None
    pnl: Optional[float] = None
    holding_value: Optional[float] = None
    position_pct: Optional[float] = None
