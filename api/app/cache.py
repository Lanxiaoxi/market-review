"""内存 TTL 缓存（收盘后 24h / 盘中 60s）"""

import time
from typing import Any, Optional
from collections import OrderedDict


class TTLCache:
    """简单的 TTL 内存缓存"""

    def __init__(self, maxsize: int = 64):
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        expires_at, value = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        # 移到末尾（LRU）
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl_seconds: int):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (time.time() + ttl_seconds, value)
        # 淘汰最旧
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def clear(self):
        self._store.clear()


# 全局限实例
overview_cache = TTLCache()
sectors_cache = TTLCache()
intraday_cache = TTLCache()
stock_sparkline_cache = TTLCache()  # 自选页个股 sparkline（按代码缓存）
charts_cache = TTLCache()           # 图表数据（期现对比等）

# 收盘后 TTL 24h，盘中 60s
DEFAULT_TTL = 60 * 60 * 24
INTRADAY_TTL = 60

_ALL_CACHES = (
    overview_cache,
    sectors_cache,
    intraday_cache,
    stock_sparkline_cache,
    charts_cache,
)


def clear_all() -> None:
    """清空全部内存缓存（L2 回填完成后调用，避免内存层继续吐回填前的旧数据）"""
    for c in _ALL_CACHES:
        c.clear()