"""
行情数据持久层（L2）表结构

设计原则：按「数据可变性」建模，而不是按请求建模。
- 以 trade_date 为主维度：历史数据一旦落库永不变更，读取零回源
- 明细与聚合双写：stock_daily 保留原始行（可回溯重算任意指标），
  market_daily_agg 存放预聚合结果（查询 O(1)）
- fetch_log 是「不重复获取」的硬闸门：任何回源动作落库后必须登记
"""

from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TradeCalendar(SQLModel, table=True):
    """交易日历（一次同步覆盖未来一年，避免每次取数都调 trade_cal）"""

    __tablename__ = "trade_calendar"

    trade_date: date = Field(primary_key=True)
    is_open: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.now)


class StockDaily(SQLModel, table=True):
    """全市场个股日线明细（数据底座）

    单日全市场约 5400 行，一年约 135 万行（SQLite 约 70MB/年）。
    涨停家数序列、7 档分布、成交额、涨停 TOP5、个股 sparkline 全部可由本表本地聚合。
    """

    __tablename__ = "stock_daily"

    ts_code: str = Field(primary_key=True, max_length=16)
    trade_date: date = Field(primary_key=True)
    close: Optional[float] = Field(default=None)
    pct_chg: Optional[float] = Field(default=None)
    amount: Optional[float] = Field(default=None, description="成交额（千元，Tushare 原始单位）")


class StockName(SQLModel, table=True):
    """个股代码 → 名称映射（涨停 TOP5 等需要展示名称的场景）

    每天同步一次即可，缺失时聚合逻辑回退为显示代码本身。
    """

    __tablename__ = "stock_name"

    ts_code: str = Field(primary_key=True, max_length=16)
    name: str = Field(default="", max_length=64)
    updated_at: datetime = Field(default_factory=datetime.now)


class MarketDailyAgg(SQLModel, table=True):
    """全市场日聚合（由 stock_daily 预计算，查询 O(1)）

    保留本表是为了避免每次请求实时扫描 60 天 × 5400 行。
    """

    __tablename__ = "market_daily_agg"

    trade_date: date = Field(primary_key=True)
    up: int = Field(default=0)
    down: int = Field(default=0)
    flat: int = Field(default=0)
    up_pct: float = Field(default=0)
    down_pct: float = Field(default=0)
    flat_pct: float = Field(default=0)
    turnover_yi: float = Field(default=0, description="成交额（亿元）")
    limit_up: int = Field(default=0)
    limit_down: int = Field(default=0)
    limit_up_top: str = Field(default="[]", max_length=4096, description="JSON: [{name, pct}]")
    dist_json: str = Field(default="[]", max_length=2048, description="JSON: [{label, value}]")
    source: str = Field(default="", max_length=32)
    updated_at: datetime = Field(default_factory=datetime.now)


class IndexDaily(SQLModel, table=True):
    """指数日线（8 只 A 股指数 + 港股指数）"""

    __tablename__ = "index_daily"

    ts_code: str = Field(primary_key=True, max_length=16)
    trade_date: date = Field(primary_key=True)
    code: str = Field(default="", max_length=16, description="展示用短代码，如 000001 / HSI")
    name: str = Field(default="", max_length=32)
    close: float = Field(default=0)
    change: float = Field(default=0)
    pct_chg: float = Field(default=0)
    amount: Optional[float] = Field(default=None)


class SectorDaily(SQLModel, table=True):
    """行业板块日线（同花顺 881xxx / 申万 801xxx）"""

    __tablename__ = "sector_daily"

    sector_code: str = Field(primary_key=True, max_length=16)
    trade_date: date = Field(primary_key=True)
    name: str = Field(default="", max_length=64)
    close: float = Field(default=0)
    pct_chg: float = Field(default=0)
    leading: str = Field(default="—", max_length=64, description="当日领涨股名称")


class FuturesDaily(SQLModel, table=True):
    """中金所股指期货主力连续日线（IF / IH / IM）"""

    __tablename__ = "futures_daily"

    contract: str = Field(primary_key=True, max_length=8)
    trade_date: date = Field(primary_key=True)
    close: float = Field(default=0)


class IntradayBar(SQLModel, table=True):
    """指数当日分时（分钟级，收盘后固化）

    盘中仍走内存短 TTL；收盘后由回填任务固化入库，之后永久读本地。
    """

    __tablename__ = "intraday_bar"

    code: str = Field(primary_key=True, max_length=16, description="腾讯行情代码，如 sh000001")
    trade_date: date = Field(primary_key=True)
    time: str = Field(primary_key=True, max_length=8, description="HH:MM")
    price: float = Field(default=0)
    amount: float = Field(default=0, description="累计成交额（元）")


class BondYield(SQLModel, table=True):
    """中债国债收益率曲线（CCDC 口径，%）

    每个交易日一行，仅存 2/5/10/30 年期四个期限；由每日回填任务拉取一次，零回源。
    """

    __tablename__ = "bond_yield"

    trade_date: date = Field(primary_key=True)
    two_year: Optional[float] = Field(default=None)
    five_year: Optional[float] = Field(default=None)
    ten_year: Optional[float] = Field(default=None)
    thirty_year: Optional[float] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.now)


class FetchLog(SQLModel, table=True):
    """回源去重审计表（domain + ref_key 唯一 → 同一份数据只拉一次）

    ref_key 约定：
    - 日级全域（breadth / indices / sectors / limit_top）→ "YYYY-MM-DD"
    - 期货主力连续 → "IF:YYYY-MM-DD"（按日登记，回填时按缺口区间批量补）
    - 分时固化 → "intraday:YYYY-MM-DD"
    - 日历同步 → "calendar:YYYY"（按年登记）
    """

    __tablename__ = "fetch_log"

    domain: str = Field(primary_key=True, max_length=32)
    ref_key: str = Field(primary_key=True, max_length=64)
    trade_date: Optional[date] = Field(default=None)
    source: str = Field(default="", max_length=32)
    rows_count: int = Field(default=0)
    fetched_at: datetime = Field(default_factory=datetime.now)


class SeriesCache(SQLModel, table=True):
    """通用序列缓存兜底（难以结构化建模的域，如临时聚合结果）"""

    __tablename__ = "series_cache"

    cache_key: str = Field(primary_key=True, max_length=128)
    payload: str = Field(default="", max_length=65536)
    trade_date: Optional[date] = Field(default=None)
    fetched_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None)
