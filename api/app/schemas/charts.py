"""图表数据响应模型"""

from pydantic import BaseModel, ConfigDict, alias_generators


class CamelModel(BaseModel):
    """camelCase 输出（与全局 API 风格一致）"""
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class IfBasisOut(BaseModel):
    """股指期货期现对比（日线）：现货收盘 vs 中金所主力合约收盘"""

    contract: str        # IF / IH / IM
    name: str            # 现货指数名称（沪深300 / 上证50 / 中证1000）
    dates: list[str]     # "YYYY-MM-DD"（升序）
    spot: list[float]    # 现货指数收盘
    futures: list[float] # 中金所主力合约收盘
    basis: list[float]   # 基差（点）= 现货 - 期货
    premium: list[float] # 基差率 % = (futures - spot) / spot * 100


class LimitCountsOut(CamelModel):
    """日线涨停/跌停家数序列"""

    dates: list[str]     # "YYYY-MM-DD"（升序）
    limit_up: list[int]  # 每日涨停家数
    limit_down: list[int]  # 每日跌停家数


class BreadthSeriesOut(CamelModel):
    """日线市场宽度序列（上涨/平盘/下跌家数）"""

    dates: list[str]   # "YYYY-MM-DD"（升序）
    up: list[int]      # 每日上涨家数
    flat: list[int]    # 每日平盘家数
    down: list[int]    # 每日下跌家数


class FiftyTwoWeekOut(CamelModel):
    """近 N 日 52 周新高/新低个股家数序列"""

    dates: list[str]    # "YYYY-MM-DD"（升序）
    new_high: list[int] # 每日创 52 周新高个股数
    new_low: list[int]  # 每日创 52 周新低个股数