"""总览页响应模型 —— 与前端 types/market.ts 对齐（camelCase 输出）"""

from pydantic import BaseModel, ConfigDict, alias_generators


class CamelModel(BaseModel):
    """统一 camelCase 输出，内部保持 snake_case"""
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class IndexSnapshotOut(CamelModel):
    code: str
    name: str
    value: float
    change: float
    change_pct: float
    sparkline: list[float]
    closes: list[float] = []   # 真实收盘价（升序，近 12 个交易日）


class LimitUpStockOut(CamelModel):
    name: str
    pct: float


class DistBucketOut(CamelModel):
    """涨跌家数分布区间（如 涨停 / 涨2-10% / 平盘 / 跌停）"""
    label: str
    value: int


class MarketBreadthOut(CamelModel):
    up: int
    down: int
    flat: int
    up_pct: float
    down_pct: float
    flat_pct: float
    turnover: str
    limit_up_count: int
    limit_down_count: int
    limit_up_top: list[LimitUpStockOut]
    dist: list[DistBucketOut] = []   # 涨跌家数分布（7 档）
    # 较上一交易日成交额变化（亿元 / %），无上一交易日数据时为 None
    turnover_change_yi: float | None = None
    turnover_change_pct: float | None = None


class SectorItemOut(CamelModel):
    """行业板块（总览与板块页共用，单一来源）"""
    name: str
    pct: float
    leading: str
    sparkline: list[float]
    code: str = ""           # 板块代码（详情图用）
    up_days: int = 0         # 连涨天数（截至最新交易日）
    new_high_10d: bool = False  # 10 日新高


class OverviewOut(CamelModel):
    date: str
    weekday: str
    closed: bool
    indices: list[IndexSnapshotOut]
    breadth: MarketBreadthOut
    sectors_up: list[SectorItemOut]
    sectors_down: list[SectorItemOut]
