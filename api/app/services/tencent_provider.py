"""
腾讯接口兜底（免费）
- 港股指数（恒生指数/恒生科技）实时快照 + 日 K（Tushare 无港股指数）
- 指数分时分钟线：web.ifzq.gtimg.cn/appstock/app/minute/query
- 盘中实时快照：qt.gtimg.cn
"""

import asyncio
import logging
import math
import re

import httpx

from app.services.provider import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

# 港股指数代码映射：逻辑码 → (腾讯实时代码, 腾讯日K代码, 展示名)
HK_INDICES = {
    "HSI": {"qt": "r_hkHSI", "kline": "hkHSI", "name": "恒生指数"},
    "HSTECH": {"qt": "r_hkHSTECH", "kline": "hkHSTECH", "name": "恒生科技"},
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


async def fetch_hk_kline(code: str, days: int = 12) -> list[float] | None:
    """拉取港股指数日 K 收盘价（真实 sparkline 数据源），code: HSI / HSTECH"""
    cfg = HK_INDICES.get(code)
    if cfg is None:
        return None
    url = f"https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param={cfg['kline']},day,,,{days}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            node = data.get("data", {}).get(cfg["kline"], {})
            # day 或 qfqday：每行 [date, open, close, high, low, amount]
            rows = node.get("qfqday") or node.get("day") or []
            closes = _parse_kline_rows(rows)
            if not closes:
                return None
            return closes
    except Exception as e:
        logger.warning("[Tencent] %s kline failed: %s", code, e)
        return None


async def fetch_hk_index_range(start, end) -> list[dict]:
    """港股指数日线区间（Tushare / THS 均无港股指数，由腾讯兜底）

    腾讯日 K 按「根数」取，故按区间天数换算并多取一些以覆盖节假日。
    change / pct_chg 腾讯日 K 不直接提供，置 0（港股卡仅展示点位与涨跌幅，
    涨跌幅由收盘价差分在调用侧计算）。
    """
    bars = max(20, int((end - start).days * 1.6) + 20)
    rows: list[dict] = []
    for code in HK_INDEX_CODES:
        series = await fetch_hk_kline_rows(code, bars)
        prev: float | None = None
        for d, close in series or []:
            if d is None or not (start <= d <= end):
                continue
            rows.append(
                {
                    "ts_code": code,
                    "code": code,
                    "name": HK_INDICES[code]["name"],
                    "trade_date": d,
                    "close": close,
                    "change": round(close - prev, 2) if prev is not None else 0,
                    "pct_chg": round((close / prev - 1) * 100, 2) if prev else 0,
                    "amount": None,
                }
            )
            prev = close
    return rows


async def fetch_hk_kline_rows(code: str, days: int = 12) -> list[tuple] | None:
    """港股指数日 K（带日期），code: HSI / HSTECH

    返回 [(date, close), ...] 升序；回填历史区间时用。date 解析失败时为 None。
    """
    cfg = HK_INDICES.get(code)
    if cfg is None:
        return None
    url = f"https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param={cfg['kline']},day,,,{days}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            node = resp.json().get("data", {}).get(cfg["kline"], {})
            rows = node.get("qfqday") or node.get("day") or []
            pairs = _parse_kline_pairs(rows)
            return pairs or None
    except Exception as e:
        logger.warning("[Tencent] %s kline(rows) failed: %s", code, e)
        return None


async def fetch_hk_snapshot(code: str) -> dict | None:
    """
    拉取港股指数实时快照（腾讯兜底），code: HSI / HSTECH
    返回格式与 tushare index_daily 一致；sparkline 用真实日 K，失败回退 mock
    """
    cfg = HK_INDICES.get(code)
    if cfg is None:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://qt.gtimg.cn/q={cfg['qt']}")
            resp.encoding = "gbk"
            parsed = _parse_qt_response(resp.text, [cfg["qt"]])
            if cfg["qt"] not in parsed:
                return None
            fields = parsed[cfg["qt"]]
            # 腾讯港股字段: [1]=名称 [3]=现价 [4]=昨收 [31]=涨跌额 [32]=涨跌幅%
            if len(fields) < 33:
                return None
            value = float(fields[3])
            change = float(fields[31])
            pct = float(fields[32])

            # sparkline：真实日 K（归一化），失败时为空数组（卡片不渲染迷你线）
            closes = await fetch_hk_kline(code, days=12)
            if closes:
                from app.services.buckets import normalize_sparkline

                sparkline = normalize_sparkline(closes)
            else:
                sparkline = []

            return {
                "code": code,
                "name": cfg["name"],
                "value": round(value, 2),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
                "sparkline": sparkline,
            }
    except Exception as e:
        logger.warning("[Tencent] %s snapshot failed: %s", code, e)
        return None


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
    return [close for _, close in _parse_kline_pairs(rows)]


def _parse_kline_pairs(rows: list[list]) -> list[tuple]:
    """解析腾讯日 K 行 → [(date, close), ...]（回填需要日期，故单独提供）"""
    import datetime as _dt

    pairs = []
    for row in rows:
        try:
            close = float(row[2])
        except (IndexError, TypeError, ValueError):
            continue
        raw = str(row[0]).strip()
        d = None
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                d = _dt.datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        pairs.append((d, close))
    return pairs


async def fetch_intraday(code: str) -> dict | None:
    """
    拉取指数日内分时（当日分钟线）
    code: sh000001 / sz399001 等
    返回 {"times": [...], "prices": [...], "amounts": [累计成交额(元), ...]}，失败返回 None
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
    """腾讯接口（免费兜底：指数分时 + 港股指数）"""

    name = "tencent"

    async def fetch_intraday(self, codes: list[str]) -> dict:
        """多指数当日分时（真实数据，无 mock；全部失败时 raise 交给注册表降级）"""
        results = await asyncio.gather(*(fetch_intraday(c) for c in codes))
        payload = {
            c: r for c, r in zip(codes, results) if r is not None
        }
        if not payload:
            raise ProviderError("腾讯分时接口全部失败")
        return payload
