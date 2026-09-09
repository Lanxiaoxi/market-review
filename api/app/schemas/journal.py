"""订单复盘响应模型 —— camelCase 输出"""

from pydantic import BaseModel, ConfigDict, alias_generators


class CamelModel(BaseModel):
    """camelCase 输出统一；内部字段保持 snake_case"""
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class OrderOut(CamelModel):
    id: int
    symbol: str               # 标的名
    trade_date: str           # 订单日期 YYYY-MM-DD
    pnl: float                # 带符号盈亏（万元，正盈负亏）
    open_logic: str           # 开仓逻辑
    close_logic: str          # 平仓逻辑
    note: str = ""            # 订单笔记
    image_url: str = ""       # 截图访问地址（/uploads/...）


class JournalSummaryOut(CamelModel):
    total: int                # 订单总笔数
    win_count: int            # 盈利笔数
    loss_count: int           # 亏损笔数
    win_rate: float           # 胜率 %（盈利笔 / 总笔）
    total_pnl: float          # 累计盈亏（万元）


class JournalResponse(CamelModel):
    items: list[OrderOut]
    summary: JournalSummaryOut
