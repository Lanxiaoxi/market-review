"""
腾讯接口兜底（免费）
- 恒生指数实时快照 + 日 K（Tushare 无 HSI）
- 指数分时分钟线：web.ifzq.gtimg.cn/appstock/app/minute/query
- 盘中实时快照：qt.gtimg.cn
"""

import asyncio
import logging
import math
import re

import httpx

from app.services.mock_data import MOCK_DATA
from app.services.provider import BaseProvider

logger = logging.getLogger(__name__)

# 腾讯行情代码映射
TENCENT_INDEX_CODES = {
    "HSI": "r_hkHSI",   # 恒生指数
}


def _parse_qt_response(text: str, code_keys: list[str]) -> dict[str, list[str]]:
    """解析腾讯 qt.gtimg.cn 的响应文本"""
    result = {}
    for key in code_keys:
        # 格式: v_r_hkHSI="恒生指数~19876.54~..."
        pattern = rf'v_{key}="([^"]+)"'
        m = re.search(pattern, text)
        if m:
            result[key] = m.group(1).split("~")
    return result


async def fetch_hsi_kline(days: int = 12) -> list[float] | None:
    """拉取恒生指数日 K 收盘价（真实 sparkline 数据源）"""
    url = f"https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=hkHSI,day,,,{days}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            node = data.get("data", {}).get("hkHSI", {})
            # day 或 qfqday：每行 [date, open, close, high, low, amount]
            rows = node.get("qfqday") or node.get("day") or []
            closes = _parse_kline_rows(rows)
            if not closes:
                return None
            return closes
    except Exception as e:
        logger.warning("[Tencent] HSI kline failed: %s", e)
        return None


async def fetch_hsi_snapshot() -> dict | None:
    """
    拉取恒生指数实时快照（腾讯兜底）
    返回格式与 tushare index_daily 一致；sparkline 用真实日 K，失败回退 mock
    """
    tencent_code = "r_hkHSI"
    url = f"https://qt.gtimg.cn/q={tencent_code}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.encoding = "gbk"
            parsed = _parse_qt_response(resp.text, [tencent_code])
            if tencent_code not in parsed:
                return None
            fields = parsed[tencent_code]
            # 腾讯恒指字段: [1]=名称 [3]=现价 [4]=昨收 [31]=涨跌额 [32]=涨跌幅%
            if len(fields) < 33:
                return None
            value = float(fields[3])
            change = float(fields[31])
            pct = float(fields[32])

            # sparkline：真实日 K（归一化），失败时回退 mock
            closes = await fetch_hsi_kline(days=12)
            if closes:
                from app.services.tushare_provider import _normalize_sparkline

                sparkline = _normalize_sparkline(closes)
            else:
                sparkline = MOCK_DATA["indices"][7]["sparkline"]

            return {
                "code": "HSI",
                "name": "恒生指数",
                "value": round(value, 2),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
                "sparkline": sparkline,
            }
    except Exception as e:
        logger.warning("[Tencent] HSI snapshot failed: %s", e)
        return None


def _mock_intraday() -> dict:
    """腾讯接口不可用时的分时兜底：生成一个合理的 U 型分时 + 递增成交额"""
    times, prices, amounts = [], [], []
    cumulative = 0.0
    # 09:30 ~ 11:30（121 分钟）+ 13:00 ~ 15:00（121 分钟）
    for idx in range(242):
        if idx <= 120:
            hh, mm = 9 + (30 + idx) // 60, (30 + idx) % 60
        else:
            k = idx - 121
            hh, mm = 13 + k // 60, k % 60
        times.append(f"{hh:02d}:{mm:02d}")
        # U 型：早盘低开下探、午前回升、午后回落收平
        phase = math.sin((idx / 241) * math.pi * 2 + 0.6)
        prices.append(round(3950 + phase * 22 - (idx / 241) * 6, 2))
        # 成交额：开盘/尾盘放量，午间缩量（U 型累计曲线）
        volume = 8e10 + 6e10 * math.sin((idx / 241) * math.pi) * (1 + 0.6 * math.cos(idx / 241 * math.pi * 4))
        cumulative += volume
        amounts.append(round(cumulative, 2))
    return {"times": times, "prices": prices, "amounts": amounts}


def _parse_minute_rows(rows: list[str]) -> dict | None:
    """解析腾讯分时行（每行 "HHMM price vol amount"）→ {times, prices, amounts}"""
    times, prices, amounts = [], [], []
    for row in rows:
        parts = row.split(" ")
        if len(parts) < 4:
            continue
        hhmm = parts[0]
        times.append(f"{hhmm[:2]}:{hhmm[2:]}")
        prices.append(float(parts[1]))
        amounts.append(float(parts[3]))  # 累计成交额（元）
    if not prices:
        return None
    return {"times": times, "prices": prices, "amounts": amounts}


def _parse_kline_rows(rows: list[list]) -> list[float]:
    """解析腾讯日 K 行（[date, open, close, high, low, amount]）→ 收盘价列表"""
    closes = []
    for row in rows:
        try:
            closes.append(float(row[2]))
        except (IndexError, TypeError, ValueError):
            continue
    return closes


async def fetch_intraday(code: str) -> dict | None:
    """
    拉取指数日内分时（当日分钟线）
    code: sh000001 / sz399001 等
    返回 {"times": [...], "prices": [...], "amounts": [累计成交额(元), ...]}
    Tushare 分钟线需 5000 分 → 腾讯兜底
    """
    url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={code}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            node = data.get("data", {}).get(code, {}).get("data", {}).get("data")
            if not node:
                return None
            return _parse_minute_rows(node)
    except Exception as e:
        logger.warning("[Tencent] minute %s failed: %s", code, e)
        return None


async def fetch_intraday_with_fallback(code: str) -> dict:
    """分时数据 + 腾讯不可用时的 mock 兜底（保证前端恒有数据）"""
    data = await fetch_intraday(code)
    return data if data is not None else _mock_intraday()


async def fetch_realtime_snapshot(codes: list[str]) -> dict[str, float]:
    """
    盘中实时快照（批量实时价）
    codes: ['sh000001', 'sz399001', ...]
    """
    result: dict[str, float] = {}
    try:
        url = f"https://qt.gtimg.cn/q={','.join(codes)}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.encoding = "gbk"
            parsed = _parse_qt_response(resp.text, codes)
            for key, fields in parsed.items():
                try:
                    result[key] = float(fields[3])
                except (IndexError, ValueError):
                    continue
    except Exception as e:
        logger.warning("[Tencent] realtime snapshot failed: %s", e)
    return result


class TencentProvider(BaseProvider):
    """腾讯接口（免费兜底：指数分时 + 恒生指数）"""

    name = "tencent"

    async def fetch_intraday(self, codes: list[str]) -> dict:
        """多指数当日分时（腾讯不可用时逐代码回退 mock，保证前端恒有数据）"""
        results = await asyncio.gather(*(fetch_intraday_with_fallback(c) for c in codes))
        return {c: r for c, r in zip(codes, results)}
