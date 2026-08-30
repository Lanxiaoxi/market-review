"""中债（CCDC）国债收益率数据源 —— 财政部页面背后的官方接口

POST https://yield.chinabond.com.cn/cbweb-czb-web/czb/historyQuery?startDate=&endDate=&gjqx=0&locale=cn_ZH&qxmc=1
返回 heList[]，每个交易日一行，含 threeMonth~thirtyYear 整条曲线（2 位小数，字符串或 null）。
无登录/验证码，普通浏览器 UA 即可；服务端不强制一年上限，但按年分段请求避免大范围高频。

注意：响应中 qxmc（曲线名）字段乱码，数值字段正常，忽略即可。
"""

import asyncio
import logging
from datetime import date, datetime

import httpx

from app.services.provider import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

BASE_URL = "https://yield.chinabond.com.cn/cbweb-czb-web/czb/historyQuery"

# 请求头：普通浏览器 UA（文档实测无需 Referer）
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

# 需要保留的期限字段映射：接口字段 → 落库字段
_TENOR_MAP = {
    "twoYear": "two_year",
    "fiveYear": "five_year",
    "tenYear": "ten_year",
    "thirtyYear": "thirty_year",
}


def _parse_ymd(v) -> date | None:
    """workTime 形如 '2026-08-28'；解析失败返回 None"""
    s = str(v).strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _f(v) -> float | None:
    """'1.69' / 1.69 / None → float；非法返回 None"""
    if v is None or v == "":
        return None
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


class CcdcProvider(BaseProvider):
    """中债国债收益率（CCDC 口径）"""

    name = "ccdc"

    async def fetch_bond_yield(self, start: date, end: date) -> list[dict]:
        """拉取 [start, end] 区间的国债收益率曲线（每个交易日一行）

        返回 [{trade_date: date, two_year, five_year, ten_year, thirty_year}]（升序）。
        调用侧（回填）按年分段、间隔请求，避免短时频繁大范围请求。
        """
        params = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "gjqx": "0",
            "locale": "cn_ZH",
            "qxmc": "1",
        }
        try:
            async with httpx.AsyncClient(timeout=20, headers=_HEADERS) as client:
                resp = await client.post(BASE_URL, params=params)
                resp.raise_for_status()
                body = resp.json()
        except Exception as e:  # noqa: BLE001 —— 网络/解析失败统一降级
            raise ProviderError(f"中债收益率接口失败: {e}")

        rows = []
        for it in body.get("heList") or []:
            d = _parse_ymd(it.get("workTime"))
            if d is None:
                continue
            rows.append(
                {
                    "trade_date": d,
                    **{
                        f: _f(it.get(k))
                        for k, f in _TENOR_MAP.items()
                    },
                }
            )
        if not rows:
            raise ProviderError(f"中债收益率区间为空（{start} ~ {end}）")
        rows.sort(key=lambda r: r["trade_date"])
        return rows
