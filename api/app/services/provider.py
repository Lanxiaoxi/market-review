"""
数据源 Provider 注册表与映射表

架构：前端只消费 REST 契约；后端内部按「数据域」从不同数据源取数，
路由与前端无需关心当前用哪个数据源。

本模块职责：
- 能力矩阵 CAPABILITY：每个数据域可用哪些 Provider（按优先级排序）
- 硬编码映射表 DOMAIN_PROVIDER：每个数据域默认用哪个 Provider
  （显式指定主源；主源失败时按能力矩阵自动降级到下一个候选）
- 注册表：懒加载 Provider 实例，提供 get_provider(domain) 与 fetch_domain(domain)

选择策略全部 hardcode 在本文件；.env 只存放各数据源的 token
（TUSHARE_TOKEN / THS_API_KEY），不存放选择策略。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ─── 数据域 ───
DOMAIN_INDICES = "indices"      # 指数卡：8 指数快照 + sparkline
DOMAIN_BREADTH = "breadth"      # 涨跌家数 / 7 档分布 / 成交额
DOMAIN_LIMIT_UP = "limit_up"    # 涨停 TOP5 / 涨停池
DOMAIN_SECTORS = "sectors"      # 板块轮动（行业排名 + 领涨股）
DOMAIN_INTRADAY = "intraday"    # 指数当日分时
DOMAIN_STOCK_SPARKLINE = "stock_sparkline"  # 单只个股近期收盘价 sparkline（自选页）
DOMAIN_INDEX_HISTORY = "index_history"      # 单个指数历史日 K 收盘价序列（期现对比等）
DOMAIN_FUTURES_MAIN = "futures_main"        # 中金所股指期货（IF/IH/IM）主力连续日线
DOMAIN_LIMIT_COUNTS = "limit_counts"        # 日线涨停/跌停家数序列

DOMAINS = (
    DOMAIN_INDICES,
    DOMAIN_BREADTH,
    DOMAIN_LIMIT_UP,
    DOMAIN_SECTORS,
    DOMAIN_INTRADAY,
    DOMAIN_STOCK_SPARKLINE,
    DOMAIN_INDEX_HISTORY,
    DOMAIN_FUTURES_MAIN,
    DOMAIN_LIMIT_COUNTS,
)

# ─── 能力矩阵：每个域可用 Provider（按优先级排列，供 auto/降级使用）───
CAPABILITY: dict[str, list[str]] = {
    DOMAIN_INDICES: ["tushare", "ths"],      # 两者都可；tushare 自带 HSI 腾讯兜底
    DOMAIN_BREADTH: ["tushare", "ths"],      # tushare 一次全市场；ths 需分页
    DOMAIN_LIMIT_UP: ["ths", "tushare"],     # ths 涨停池字段更全；tushare 用 daily 近似
    DOMAIN_SECTORS: ["ths", "tushare"],      # ths 行业指数；tushare sw_daily 需 2000 分
    DOMAIN_INTRADAY: ["tencent"],            # 唯一能力源（ths/tushare 无分钟线）
    DOMAIN_STOCK_SPARKLINE: ["ths", "tushare"],
    DOMAIN_INDEX_HISTORY: ["tushare", "ths"],
    DOMAIN_FUTURES_MAIN: ["tushare"],        # 期货仅 Tushare 有（同花顺/腾讯均无）
    DOMAIN_LIMIT_COUNTS: ["ths", "tushare"], # ths 涨停/跌停池计数权威；tushare 用 daily 近似
}

# ─── 硬编码映射表：每个数据域默认主源（必须属于该域能力矩阵）───
DOMAIN_PROVIDER: dict[str, str] = {
    DOMAIN_INDICES: "tushare",
    DOMAIN_BREADTH: "tushare",
    DOMAIN_LIMIT_UP: "ths",
    DOMAIN_SECTORS: "ths",
    DOMAIN_INTRADAY: "tencent",
    DOMAIN_STOCK_SPARKLINE: "ths",
    DOMAIN_INDEX_HISTORY: "tushare",
    DOMAIN_FUTURES_MAIN: "tushare",
    DOMAIN_LIMIT_COUNTS: "ths",
}

# ─── 数据域 → 协议方法名（域命名与取数语义解耦）───
DOMAIN_METHOD: dict[str, str] = {
    DOMAIN_INDICES: "fetch_indices",
    DOMAIN_BREADTH: "fetch_breadth",
    DOMAIN_LIMIT_UP: "fetch_limit_top",
    DOMAIN_SECTORS: "fetch_sectors",
    DOMAIN_INTRADAY: "fetch_intraday",
    DOMAIN_STOCK_SPARKLINE: "fetch_stock_sparkline",
    DOMAIN_INDEX_HISTORY: "fetch_index_history",
    DOMAIN_FUTURES_MAIN: "fetch_futures_main",
    DOMAIN_LIMIT_COUNTS: "fetch_limit_counts",
}


def normalize_ts_code(code: str) -> str:
    """把自选代码规范为带交易所后缀的标准代码（600519 → 600519.SH）"""
    code = code.strip().upper()
    if "." in code:
        return code
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith(("4", "8", "92")):
        return f"{code}.BJ"
    return f"{code}.SZ"


class ProviderError(Exception):
    """Provider 无法提供该域数据（未配置 token / 接口失败等）"""


class BaseProvider:
    """Provider 基类：各域方法返回统一的归一化结构；不支持或失败时 raise ProviderError"""

    name: str = "base"

    async def fetch_indices(self) -> list[dict]:
        raise ProviderError(f"{self.name} 不支持 indices")

    async def fetch_breadth(self) -> dict:
        raise ProviderError(f"{self.name} 不支持 breadth")

    async def fetch_limit_top(self) -> list[dict]:
        raise ProviderError(f"{self.name} 不支持 limit_up")

    async def fetch_sectors(self) -> list[dict]:
        raise ProviderError(f"{self.name} 不支持 sectors")

    async def fetch_intraday(self, codes: list[str]) -> dict:
        raise ProviderError(f"{self.name} 不支持 intraday")

    async def fetch_stock_sparkline(self, code: str) -> list[float]:
        raise ProviderError(f"{self.name} 不支持 stock_sparkline")

    async def fetch_index_history(self, code: str, days: int) -> list[dict]:
        """单个指数历史日 K 收盘价：返回 [{"date": "YYYY-MM-DD", "close": float}, ...]（升序）"""
        raise ProviderError(f"{self.name} 不支持 index_history")

    async def fetch_futures_main(self, contract: str, days: int) -> list[dict]:
        """中金所股指期货主力连续日线（contract: IF/IH/IM）：返回 [{"date": ..., "close": ...}, ...]（升序）"""
        raise ProviderError(f"{self.name} 不支持 futures_main")

    async def fetch_limit_counts(self, days: int) -> list[dict]:
        """日线涨停/跌停家数：返回 [{"date": "YYYY-MM-DD", "limit_up": int, "limit_down": int}, ...]（升序）"""
        raise ProviderError(f"{self.name} 不支持 limit_counts")


# ─── 注册表 ───
_instances: dict[str, BaseProvider] = {}


def _provider_classes() -> dict[str, type[BaseProvider]]:
    """懒加载 Provider 类（函数内 import 避免与各 provider 模块循环依赖）"""
    from app.services.tushare_provider import TushareProvider
    from app.services.ths_provider import ThsProvider
    from app.services.tencent_provider import TencentProvider

    return {c.name: c for c in (TushareProvider, ThsProvider, TencentProvider)}


def _validate_domain(domain: str):
    if domain not in DOMAINS:
        raise ProviderError(f"未知数据域: {domain}（可用: {', '.join(DOMAINS)}）")


def _resolve_chain(domain: str) -> list[str]:
    """该域实际 Provider 顺序：配置主源 → 能力矩阵中排在它后面的候选（自动降级链）"""
    _validate_domain(domain)
    primary = DOMAIN_PROVIDER[domain]
    caps = CAPABILITY[domain]
    if primary not in caps:
        logger.warning(
            "[provider] %s 配置的主源 %s 不在能力矩阵 %s，回退到 %s",
            domain, primary, caps, caps[0],
        )
        primary = caps[0]
    return caps[caps.index(primary):]


def get_provider(domain: str) -> BaseProvider:
    """返回该域配置的主源 Provider 实例（失败降级由 fetch_domain 处理）"""
    name = _resolve_chain(domain)[0]
    if name not in _instances:
        cls = _provider_classes().get(name)
        if cls is None:
            raise ProviderError(f"未知 Provider: {name}")
        _instances[name] = cls()
    return _instances[name]


async def fetch_domain(domain: str, *args, **kwargs):
    """按该域降级链依次尝试，返回第一个成功的归一化数据；全部失败 raise ProviderError"""
    _validate_domain(domain)
    last_err: Exception | None = None
    for name in _resolve_chain(domain):
        cls = _provider_classes().get(name)
        if cls is None:
            continue
        if name not in _instances:
            _instances[name] = cls()
        try:
            method = getattr(_instances[name], DOMAIN_METHOD[domain])
            result = await method(*args, **kwargs)
            if result is not None:
                return result
        except ProviderError as e:
            last_err = e
            logger.warning("[provider] %s 主源 %s 失败，降级: %s", domain, name, e)
        except Exception as e:  # noqa: BLE001 —— provider 内部错误统一降级
            last_err = e
            logger.warning("[provider] %s 主源 %s 异常，降级: %s", domain, name, e)
    raise ProviderError(f"所有数据源均不可用（{domain}）: {last_err}")
