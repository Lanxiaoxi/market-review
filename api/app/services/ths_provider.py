"""
同花顺金融数据 API Provider（fuyao.aicubes.cn）

鉴权：.env 的 THS_API_KEY，请求头 X-api-key（同花顺账号在 fuyao.aicubes.cn 签发）。
能力（已实测）：
- indices：指数快照（批量）+ 历史日 K（sparkline）
- breadth：全市场分页快照 → 涨跌家数 7 档分布 + 成交额
- limit_up：涨停股票池（原因/连板/封单）
- sectors：同花顺行业指数 + 成分股（领涨股）
- intraday：无分钟线，不支持（该域能力矩阵只有 tencent）

失败或未配置 token 时 raise ProviderError，由 provider 注册表的降级链处理。
"""

from __future__ import annotations

import asyncio
import datetime
import logging

import httpx

from app.config import SHANGHAI_TZ, get_settings
from app.services.buckets import DIST_LABELS, bucketize, normalize_sparkline
from app.services.provider import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

BASE_URL = "https://fuyao.aicubes.cn"

# 指数代码映射：与 tushare_provider.INDEX_CODES 对齐（港股指数由腾讯兜底）
INDEX_CODES = {
    "000001.SH": ("000001", "上证指数"),
    "000016.SH": ("000016", "上证50"),
    "000300.SH": ("000300", "沪深300"),
    "000905.SH": ("000905", "中证500"),
    "399006.SZ": ("399006", "创业板指"),
    "000688.SH": ("000688", "科创50"),
    "000852.SH": ("000852", "中证1000"),
    "932000.CSI": ("932000", "中证2000"),
}

# 港股指数（腾讯兜底，THS 无）
HK_INDEX_CODES = ["HSI", "HSTECH"]

# 同花顺一级行业指数前缀（行业目录含多级，板块页只展示一级）
THS_INDUSTRY_PREFIX = "881"

# 全市场分页大小（实测 500 可用）
PAGE_SIZE = 500
# 分页间隔（秒）：温和限速，避免触发 4001 频率超限
PAGE_SLEEP = 0.05
# 并发上限（行业 K 线 / 成分股）
MAX_CONCURRENCY = 6

def _iso_date(yyyymmdd: str) -> str:
    """20260828 → 2026-08-28"""
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def _parse_ymd(v) -> datetime.date | None:
    """20260828 / 2026-08-28 → date；无法解析返回 None"""
    s = str(v).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _num(v, scale: float = 1.0) -> float | None:
    """转 float（可带单位换算）；None / 空 / 非法 → None"""
    if v is None or v == "":
        return None
    try:
        val = float(v) * scale
    except (TypeError, ValueError):
        return None
    return None if val != val else val


class ThsProvider(BaseProvider):
    """同花顺数据源（结构化 REST，X-api-key 鉴权）"""

    name = "ths"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.ths_api_key
        if not self._api_key:
            logger.warning("[THS] 未配置 THS_API_KEY，同花顺数据源将降级到其他源")

    # ─── 内部工具 ───

    async def _get(self, path: str, params: dict) -> dict:
        """GET 同花顺 REST 接口，返回 data 容器（code!=0 时 raise）"""
        if not self._api_key:
            raise ProviderError("THS_API_KEY 未配置")
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{BASE_URL}{path}",
                params=params,
                headers={"X-api-key": self._api_key},
            )
            resp.raise_for_status()
            body = resp.json()
        if body.get("code") != 0:
            raise ProviderError(
                f"THS 接口错误 {path}: code={body.get('code')} {body.get('message')}"
            )
        return body.get("data") or {}

    async def _calendar(self) -> list[dict]:
        """近一年交易日序列（升序），每条含 date_ms / date(yyyyMMdd)"""
        data = await self._get("/api/a-share/calendar/trading-days", {})
        days = data.get("item") or []
        if not days:
            raise ProviderError("THS 交易日历为空")
        return days

    async def _paged_market(self) -> list[dict]:
        """全市场行情快照（分页拉全，返回全部 item）"""
        items: list[dict] = []
        offset = 0
        while True:
            data = await self._get(
                "/api/a-share/prices/snapshot",
                {"limit": PAGE_SIZE, "offset": offset},
            )
            page = data.get("item") or []
            total = data.get("total") or 0
            if not page:
                break
            items.extend(page)
            offset += len(page)
            if offset >= total or len(page) < PAGE_SIZE:
                break
            await asyncio.sleep(PAGE_SLEEP)
        return items

    # ─── 各域实现 ───

    async def fetch_indices(self) -> list[dict]:
        """指数卡：批量快照 + 历史日 K sparkline（HSI 走腾讯兜底）"""
        data = await self._get(
            "/api/a-share-index/prices/snapshot",
            {"thscodes": ",".join(INDEX_CODES)},
        )
        snap = {i["thscode"]: i for i in (data.get("item") or [])}
        if not snap:
            raise ProviderError("THS 指数快照为空")

        days = await self._calendar()
        end_ms = days[-1]["date_ms"]
        start_ms = end_ms - 31 * 86_400_000

        async def _hist(ts_code: str) -> list[float]:
            try:
                d = await self._get(
                    "/api/a-share-index/prices/historical",
                    {"thscode": ts_code, "interval": "1d", "start": start_ms, "end": end_ms},
                )
                bars = d.get("item") or []
                return [float(b["close_price"]) for b in bars]
            except ProviderError as e:
                logger.warning("[THS] 指数 %s 历史K线失败: %s", ts_code, e)
                return []

        closes_map = dict(
            zip(INDEX_CODES, await asyncio.gather(*(_hist(c) for c in INDEX_CODES)))
        )

        result = []
        for ts_code, (code, name) in INDEX_CODES.items():
            s = snap.get(ts_code)
            if s is None:
                continue
            result.append({
                "code": code,
                "name": name,
                "value": round(float(s["last_price"]), 2),
                "change": round(float(s["price_change"]), 2),
                "change_pct": round(float(s["price_change_ratio_pct"]), 2),
                "sparkline": normalize_sparkline(closes_map.get(ts_code, [])),
            })

        # 港股指数（恒生指数/恒生科技）：THS 无 → 腾讯兜底
        for hk_code in HK_INDEX_CODES:
            try:
                from app.services.tencent_provider import fetch_hk_snapshot

                hk = await fetch_hk_snapshot(hk_code)
                if hk:
                    result.append(hk)
            except Exception as e:  # noqa: BLE001
                logger.warning("[THS] %s 腾讯兜底失败: %s", hk_code, e)
        return result

    async def fetch_breadth(self) -> dict:
        """涨跌家数 7 档分布 + 成交额（全市场分页统计）"""
        items = await self._paged_market()
        if not items:
            raise ProviderError("THS 全市场快照为空")

        counts = {label: 0 for label in DIST_LABELS}
        total_turnover = 0.0
        for it in items:
            pct = float(it.get("price_change_ratio_pct") or 0)
            ticker = it.get("ticker") or ""
            counts[bucketize(pct, ticker)] += 1
            total_turnover += float(it.get("turnover") or 0)

        up = counts["涨停"] + counts["涨2-10%"] + counts["涨0-2%"]
        down = counts["跌停"] + counts["跌2-10%"] + counts["跌0-2%"]
        flat = counts["平盘"]
        total = up + down + flat

        days = await self._calendar()
        total_yi = total_turnover / 1e8  # 元 → 亿
        return {
            "up": up,
            "down": down,
            "flat": flat,
            "up_pct": round(up / total * 100, 1) if total else 0,
            "down_pct": round(down / total * 100, 1) if total else 0,
            "flat_pct": round(flat / total * 100, 1) if total else 0,
            "turnover": (
                f"{total_yi / 1e4:.2f}万亿" if total_yi > 1e4 else f"{total_yi:.0f}亿"
            ),
            "limit_up_count": counts["涨停"],
            "limit_down_count": counts["跌停"],
            "trade_date": days[-1]["date"],
            "dist": [{"label": k, "value": v} for k, v in counts.items()],
        }

    async def fetch_limit_top(self) -> list[dict]:
        """涨停 TOP5（按封板时间最早排序，字段含原因/连板）"""
        days = await self._calendar()
        data = await self._get(
            "/api/a-share/special-data/limit-up-pool",
            {
                "date_ms": days[-1]["date_ms"],
                "page": 1,
                "size": 5,
                "sort_field": "limit_up_time",
                "sort_dir": "asc",
            },
        )
        items = data.get("item") or []
        if not items:
            raise ProviderError("THS 涨停池为空")
        return [
            {
                "name": it["name"],
                "pct": round(float(it["price_change_ratio_pct"]), 2),
            }
            for it in items
        ]

    async def fetch_stock_sparkline(self, code: str) -> list[float]:
        """单只个股近 30 天日 K 收盘价 → 归一化 sparkline（自选页分时走势）"""
        from app.services.provider import normalize_ts_code

        thscode = normalize_ts_code(code)
        days = await self._calendar()
        end_ms = days[-1]["date_ms"]
        start_ms = end_ms - 31 * 86_400_000
        d = await self._get(
            "/api/a-share/prices/historical",
            {"thscode": thscode, "interval": "1d", "start": start_ms, "end": end_ms},
        )
        bars = d.get("item") or []
        if len(bars) < 2:
            raise ProviderError(f"THS 股票 {thscode} 历史K线为空")
        closes = [float(b["close_price"]) for b in bars]
        return normalize_sparkline(closes)

    async def fetch_index_history(self, code: str, days: int) -> list[dict]:
        """单个指数历史日 K 收盘价（升序）—— 与 tushare 返回结构一致"""
        import datetime

        thscode = code.upper()
        days_data = await self._calendar()
        if not days_data:
            raise ProviderError("THS 交易日历为空")
        end_ms = days_data[-1]["date_ms"]
        start_ms = end_ms - (days + 10) * 86_400_000
        d = await self._get(
            "/api/a-share-index/prices/historical",
            {"thscode": thscode, "interval": "1d", "start": start_ms, "end": end_ms},
        )
        bars = d.get("item") or []
        if len(bars) < 2:
            raise ProviderError(f"THS 指数 {thscode} 历史K线为空")
        # date_ms 是 Asia/Shanghai 00:00 的毫秒戳
        rows = bars[-days:]
        return [
            {
                "date": datetime.datetime.fromtimestamp(
                    b["date_ms"] / 1000, tz=datetime.timezone(datetime.timedelta(hours=8))
                ).strftime("%Y-%m-%d"),
                "close": round(float(b["close_price"]), 2),
            }
            for b in rows
        ]

    async def fetch_limit_counts(self, days: int) -> list[dict]:
        """日线涨停/跌停家数（按日取同花顺涨停池/跌停池的 total 计数，升序）"""
        cal = await self._calendar()
        recent = cal[-days:]

        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async def _counts_for(day: dict) -> dict | None:
            async with sem:
                try:
                    up = await self._get(
                        "/api/a-share/special-data/limit-up-pool",
                        {"date_ms": day["date_ms"], "page": 1, "size": 1},
                    )
                    down = await self._get(
                        "/api/a-share/special-data/limit-down-pool",
                        {"date_ms": day["date_ms"], "page": 1, "size": 1},
                    )
                    up_total = (up.get("pagination") or {}).get("total", 0)
                    down_total = (down.get("pagination") or {}).get("total", 0)
                    return {
                        "date": _iso_date(str(day["date"])),
                        "limit_up": int(up_total),
                        "limit_down": int(down_total),
                    }
                except ProviderError as e:
                    logger.warning("[THS] %s 涨跌停计数失败: %s", day.get("date"), e)
                    return None

        results = [
            r
            for r in await asyncio.gather(*(_counts_for(d) for d in recent))
            if r is not None
        ]
        if not results:
            raise ProviderError("THS 涨跌停家数序列为空")
        return results

    async def fetch_sectors(self) -> list[dict]:
        """行业板块：THS 一级行业指数 K 线（pct + sparkline）+ 领涨股"""
        catalog_data = await self._get(
            "/api/a-share-index/catalog/ths-index-list", {"tag": "industry"}
        )
        catalog = [
            (it["thscode"], it["name"])
            for it in (catalog_data.get("item") or [])
            if it.get("thscode", "").startswith(THS_INDUSTRY_PREFIX)
        ]
        if not catalog:
            raise ProviderError("THS 行业指数目录为空")

        days = await self._calendar()
        end_ms = days[-1]["date_ms"]
        start_ms = end_ms - 31 * 86_400_000
        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async def _fetch_one(ts_code: str, name: str) -> dict | None:
            async with sem:
                try:
                    d = await self._get(
                        "/api/a-share-index/prices/historical",
                        {"thscode": ts_code, "interval": "1d", "start": start_ms, "end": end_ms},
                    )
                    bars = d.get("item") or []
                    if len(bars) < 2:
                        return None
                    closes = [float(b["close_price"]) for b in bars]
                    pct = round((closes[-1] / closes[-2] - 1) * 100, 2)
                    return {
                        "ts_code": ts_code,
                        "name": name,
                        "pct": pct,
                        "leading": "—",
                        "sparkline": normalize_sparkline(closes),
                    }
                except ProviderError as e:
                    logger.warning("[THS] 行业 %s K线失败: %s", ts_code, e)
                    return None

        sectors = [
            r
            for r in await asyncio.gather(*(_fetch_one(c, n) for c, n in catalog))
            if r is not None
        ]
        if not sectors:
            raise ProviderError("THS 行业数据为空")

        # 领涨股：全市场当日涨跌幅映射 + 行业成分股（尽力而为，失败不阻塞）
        try:
            pct_map: dict[str, float] = {}
            for it in await self._paged_market():
                pct_map[it["thscode"]] = float(it.get("price_change_ratio_pct") or 0)

            sem2 = asyncio.Semaphore(MAX_CONCURRENCY)

            async def _members(ts_code: str) -> dict[str, str]:
                async with sem2:
                    try:
                        d = await self._get(
                            "/api/a-share-index/constituents/ths-stock-list",
                            {"thscode": ts_code},
                        )
                        return {
                            it["thscode"]: it["name"] for it in (d.get("item") or [])
                        }
                    except ProviderError:
                        return {}

            members_map = dict(
                zip(
                    [c for c, _ in catalog],
                    await asyncio.gather(*(_members(c) for c, _ in catalog)),
                )
            )
            for s in sectors:
                best_code, best_pct = None, float("-inf")
                for code in members_map.get(s["ts_code"], {}):
                    p = pct_map.get(code)
                    if p is not None and p > best_pct:
                        best_code, best_pct = code, p
                if best_code:
                    s["leading"] = members_map[s["ts_code"]][best_code]
        except Exception as e:  # noqa: BLE001
            logger.warning("[THS] 领涨股计算失败（回退 —）: %s", e)

        for s in sectors:
            s.pop("ts_code", None)
        return sectors

    # ─── 回填专用：返回原始行交给 store 落库 ───

    @staticmethod
    def _ms(d) -> int:
        """date（上海时区 00:00）→ 毫秒戳"""
        return int(
            datetime.datetime(
                d.year, d.month, d.day, tzinfo=datetime.timezone(datetime.timedelta(hours=8))
            ).timestamp()
            * 1000
        )

    async def _index_bars(self, thscode: str, start, end) -> list[tuple]:
        """区间日 K → [(date, close), ...] 升序"""
        d = await self._get(
            "/api/a-share-index/prices/historical",
            {"thscode": thscode, "interval": "1d", "start": self._ms(start), "end": self._ms(end)},
        )
        bars = d.get("item") or []
        pairs = []
        for b in bars:
            try:
                close = float(b["close_price"])
                dte = datetime.datetime.fromtimestamp(
                    b["date_ms"] / 1000, tz=datetime.timezone(datetime.timedelta(hours=8))
                ).date()
            except (KeyError, TypeError, ValueError):
                continue
            pairs.append((dte, close))
        pairs.sort()
        return pairs

    async def fetch_stock_daily_raw(self, trade_date) -> list[dict]:
        """全市场个股日线（THS 只有当日快照，历史区间请走 Tushare）"""
        days = await self._calendar()
        latest = _iso_date(str(days[-1]["date"]))
        if trade_date.isoformat() != latest:
            raise ProviderError(f"THS 仅支持当日快照（{latest}），无法回填 {trade_date}")

        items = await self._paged_market()
        if not items:
            raise ProviderError("THS 全市场快照为空")

        from app.services.provider import normalize_ts_code

        return [
            {
                "ts_code": normalize_ts_code(str(it.get("thscode") or it.get("ticker") or "")),
                "close": _num(it.get("last_price")),
                "pct_chg": _num(it.get("price_change_ratio_pct")),
                "amount": _num(it.get("turnover"), scale=1e-3),  # 元 → 千元
            }
            for it in items
            if it.get("thscode") or it.get("ticker")
        ]

    async def fetch_index_range(self, start, end) -> list[dict]:
        """指数日线区间（每只指数 1 次请求，涨跌幅由收盘价差分推算）"""
        results = await asyncio.gather(
            *(self._index_bars(ts_code, start, end) for ts_code in INDEX_CODES)
        )
        rows: list[dict] = []
        for ts_code, series in zip(INDEX_CODES, results):
            code, name = INDEX_CODES[ts_code]
            prev = None
            for dte, close in series:
                rows.append(
                    {
                        "ts_code": ts_code,
                        "code": code,
                        "name": name,
                        "trade_date": dte,
                        "close": round(close, 2),
                        "change": round(close - prev, 2) if prev is not None else 0,
                        "pct_chg": round((close / prev - 1) * 100, 2) if prev else 0,
                        "amount": None,
                    }
                )
                prev = close

        from app.services.tencent_provider import fetch_hk_index_range

        rows.extend(await fetch_hk_index_range(start, end))
        if not rows:
            raise ProviderError(f"THS 指数日线区间为空（{start} ~ {end}）")
        return rows

    async def fetch_sector_range(self, start, end) -> list[dict]:
        """行业日线区间（目录 1 次 + 每行业 1 次）

        领涨股依赖当日全市场快照 + 成分股，成本过高，
        因此只对区间最后一日补齐，其余日期为 "—"。
        """
        catalog_data = await self._get(
            "/api/a-share-index/catalog/ths-index-list", {"tag": "industry"}
        )
        catalog = [
            (it["thscode"], it["name"])
            for it in (catalog_data.get("item") or [])
            if it.get("thscode", "").startswith(THS_INDUSTRY_PREFIX)
        ]
        if not catalog:
            raise ProviderError("THS 行业指数目录为空")

        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async def _one(ts_code: str, name: str) -> list[dict]:
            async with sem:
                try:
                    series = await self._index_bars(ts_code, start, end)
                except ProviderError as e:
                    logger.warning("[THS] 行业 %s 日线区间失败: %s", ts_code, e)
                    return []
                rows, prev = [], None
                for dte, close in series:
                    rows.append(
                        {
                            "sector_code": ts_code,
                            "name": name,
                            "trade_date": dte,
                            "close": round(close, 2),
                            "pct_chg": round((close / prev - 1) * 100, 2) if prev else 0,
                            "leading": "—",
                        }
                    )
                    prev = close
                return rows

        results = await asyncio.gather(*(_one(c, n) for c, n in catalog))
        rows = [r for rs in results for r in rs]
        if not rows:
            raise ProviderError(f"THS 行业日线区间为空（{start} ~ {end}）")

        await self._patch_latest_leading(rows, end)
        return rows

    async def _patch_latest_leading(self, rows: list[dict], end) -> None:
        """为区间最后一日补齐领涨股（复用实时域的领涨股计算结果，按名称匹配）"""
        if end != datetime.datetime.now(SHANGHAI_TZ).date():
            return
        try:
            sectors = await self.fetch_sectors()
        except Exception as e:  # noqa: BLE001 —— 领涨股是增强字段，失败不影响主数据
            logger.warning("[THS] 领涨股补齐失败（回退 —）: %s", e)
            return
        name_to_leading = {s["name"]: s.get("leading", "—") for s in sectors}
        for r in rows:
            if r["trade_date"] == end:
                r["leading"] = name_to_leading.get(r["name"], "—")

    async def fetch_trade_calendar(self, start, end) -> list:
        """交易日历（THS 一次返回近一年，调用侧再按区间裁剪）"""
        days = await self._calendar()
        out = []
        for d in days:
            dte = _parse_ymd(str(d["date"]))
            if dte is not None and start <= dte <= end:
                out.append(dte)
        return sorted(out)
