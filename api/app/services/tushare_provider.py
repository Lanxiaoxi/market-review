"""
Tushare Pro 数据源（2000 积分）
接口：index_daily / daily / limit_list_d / sw_daily / index_classify / index_member / stock_basic / trade_cal
未配置 TUSHARE_TOKEN 时返回 mock 数据
"""

import asyncio
import datetime
import logging
from typing import Optional

from app.config import get_settings
from app.services.mock_data import MOCK_DATA
from app.services.provider import BaseProvider

logger = logging.getLogger(__name__)


def _get_pro():
    """初始化 Tushare pro_api（惰性，仅首次调用时初始化）"""
    import tushare as ts

    settings = get_settings()
    if not settings.has_tushare:
        return None
    ts.set_token(settings.tushare_token)
    return ts.pro_api()


_pro = None


def _ensure_pro():
    global _pro
    if _pro is None:
        _pro = _get_pro()
    return _pro


def _latest_trade_date(pro) -> Optional[str]:
    """获取最近交易日（Tushare trade_cal 接口）"""
    try:
        df = pro.trade_cal(
            exchange="SSE",
            start_date=(datetime.date.today() - datetime.timedelta(days=15)).strftime("%Y%m%d"),
            end_date=datetime.date.today().strftime("%Y%m%d"),
            is_open="1",
        )
        if df is not None and len(df) > 0:
            # trade_cal 返回顺序不保证（实测为降序），按 cal_date 升序排序后取最后一个
            dates = sorted(str(d) for d in df["cal_date"].tolist())
            return dates[-1]
    except Exception as e:
        logger.warning("[Tushare] trade_cal failed: %s", e)
    # fallback: 用今天或昨天（周一到周五）
    today = datetime.date.today()
    for _ in range(7):
        if today.weekday() < 5:
            return today.strftime("%Y%m%d")
        today -= datetime.timedelta(days=1)
    return today.strftime("%Y%m%d")


def _recent_trade_dates(pro, end_date: str, n: int) -> list[str]:
    """返回 end_date 之前（含）的最近 n 个交易日（升序）"""
    start = (datetime.date.fromisoformat(end_date) - datetime.timedelta(days=31)).strftime("%Y%m%d")
    try:
        df = pro.trade_cal(exchange="SSE", start_date=start, end_date=end_date, is_open="1")
        if df is not None and len(df) > 0:
            dates = sorted(str(d) for d in df["cal_date"].tolist())
            return dates[-n:]
    except Exception as e:
        logger.warning("[Tushare] trade_cal(recent) failed: %s", e)
    return [end_date]


# ─── 指数代码映射 ───
INDEX_CODES = {
    "000001.SH": ("000001", "上证指数"),
    "399001.SZ": ("399001", "深证成指"),
    "399006.SZ": ("399006", "创业板指"),
    "000688.SH": ("000688", "科创50"),
    "000300.SH": ("000300", "沪深300"),
    "000905.SH": ("000905", "中证500"),
    "000852.SH": ("000852", "中证1000"),
}

# 恒生指数用腾讯兜底（Tushare 无 HSI）
HSI_CODE = ("HSI", "恒生指数")


def _normalize_sparkline(values: list[float], target_min=4, target_max=24) -> list[float]:
    """将原始收盘价归一化到 sparkline 的 y 坐标范围"""
    if not values:
        return [14] * 12
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [14] * len(values)
    return [target_max - (v - vmin) / (vmax - vmin) * (target_max - target_min) for v in values]


def _limit_pct(ts_code: str) -> float:
    """按板块返回近似涨停/跌停阈值（主板 10%，创业板/科创板 20%，北交所 30%）"""
    if ts_code.startswith(("300", "301", "688")):
        return 19.8
    if ts_code.startswith(("4", "8", "92")):
        return 29.8
    return 9.8


def _iso_date(yyyymmdd: str) -> str:
    """20260828 → 2026-08-28"""
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


DIST_LABELS = ["涨停", "涨2-10%", "涨0-2%", "平盘", "跌0-2%", "跌2-10%", "跌停"]


def _bucketize(pct: float, ts_code: str) -> str:
    """把涨跌幅归入 7 档分布区间（涨停/跌停按板块阈值近似）"""
    th = _limit_pct(ts_code)
    if pct >= th:
        return "涨停"
    if pct <= -th:
        return "跌停"
    if pct >= 2:
        return "涨2-10%"
    if pct <= -2:
        return "跌2-10%"
    if pct > 0:
        return "涨0-2%"
    if pct < 0:
        return "跌0-2%"
    return "平盘"


async def fetch_index_daily() -> list[dict]:
    """拉取 8 张指数卡的日线数据 + sparkline（7 只 Tushare + 1 只 HSI 腾讯兜底）"""
    settings = get_settings()
    if not settings.has_tushare:
        return MOCK_DATA["indices"]

    def _fetch():
        pro = _ensure_pro()
        results = []
        for ts_code, (code, name) in INDEX_CODES.items():
            try:
                df = pro.index_daily(ts_code=ts_code, limit=12)
                if df is None or len(df) == 0:
                    continue
                df = df.sort_values("trade_date")
                closes = df["close"].tolist()
                latest = df.iloc[-1]
                change = float(latest["change"])
                pct_chg = float(latest["pct_chg"])

                results.append({
                    "code": code,
                    "name": name,
                    "value": round(float(latest["close"]), 2),
                    "change": round(change, 2),
                    "change_pct": round(pct_chg, 2),
                    "sparkline": _normalize_sparkline(closes),
                })
            except Exception as e:
                logger.warning("[Tushare] index_daily %s failed: %s", ts_code, e)
        return results

    indices = await asyncio.to_thread(_fetch)

    # 恒生指数用腾讯兜底（真实日 K 生成 sparkline，失败则回退 mock）
    try:
        from app.services.tencent_provider import fetch_hsi_snapshot

        hsi = await fetch_hsi_snapshot()
        if hsi:
            indices.append(hsi)
    except Exception as e:
        logger.warning("[Tencent] HSI fallback failed: %s", e)

    return indices


async def fetch_daily_market() -> dict:
    """拉取全市场日线 → 涨跌家数统计（7 档分布）+ 成交额 + 涨跌停数量"""
    settings = get_settings()
    if not settings.has_tushare:
        return MOCK_DATA["breadth"]

    def _fetch():
        pro = _ensure_pro()
        trade_date = _latest_trade_date(pro)
        try:
            df = pro.daily(trade_date=trade_date, fields="ts_code,pct_chg,amount")
            if df is None or len(df) == 0:
                return MOCK_DATA["breadth"]

            counts = {label: 0 for label in DIST_LABELS}
            limit_up = limit_down = 0
            for ts_code, pct in zip(df["ts_code"], df["pct_chg"]):
                bucket = _bucketize(float(pct), str(ts_code))
                counts[bucket] += 1
                if bucket == "涨停":
                    limit_up += 1
                elif bucket == "跌停":
                    limit_down += 1

            up = counts["涨停"] + counts["涨2-10%"] + counts["涨0-2%"]
            down = counts["跌停"] + counts["跌2-10%"] + counts["跌0-2%"]
            flat = counts["平盘"]
            total = up + down + flat
            # Tushare daily.amount 单位千元 → 转亿元（千元/1e5 = 亿元）
            total_yi = float(df["amount"].sum()) / 1e5

            return {
                "up": up,
                "down": down,
                "flat": flat,
                "up_pct": round(up / total * 100, 1) if total else 0,
                "down_pct": round(down / total * 100, 1) if total else 0,
                "flat_pct": round(flat / total * 100, 1) if total else 0,
                "turnover": f"{total_yi / 1e4:.2f}万亿" if total_yi > 1e4 else f"{total_yi:.0f}亿",
                "limit_up_count": limit_up,
                "limit_down_count": limit_down,
                "trade_date": trade_date,
                "dist": [{"label": k, "value": v} for k, v in counts.items()],
            }
        except Exception as e:
            logger.warning("[Tushare] daily failed: %s", e)
            return MOCK_DATA["breadth"]

    return await asyncio.to_thread(_fetch)


async def fetch_limit_list() -> list[dict]:
    """拉取涨停 TOP5（优先 limit_list_d，权限不足时用 daily 近似）"""
    settings = get_settings()
    if not settings.has_tushare:
        return MOCK_DATA["limit_up_top"]

    def _fetch():
        pro = _ensure_pro()
        trade_date = _latest_trade_date(pro)
        # 先尝试 limit_list_d（2000 积分接口）
        try:
            df = pro.limit_list_d(trade_date=trade_date, limit_type="U")
            if df is not None and len(df) > 0:
                df = df.sort_values("pct_chg", ascending=False).head(5)
                return [
                    {"name": row["name"], "pct": round(float(row["pct_chg"]), 2)}
                    for _, row in df.iterrows()
                ]
        except Exception as e:
            logger.warning("[Tushare] limit_list_d 无权限，改用 daily 近似: %s", e)

        # 兜底：daily 中接近涨停池（daily 无名称 → 用 stock_basic 映射）
        try:
            df = pro.daily(trade_date=trade_date, fields="ts_code,pct_chg")
            if df is None or len(df) == 0:
                return MOCK_DATA["limit_up_top"]
            name_map = {}
            try:
                basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name")
                if basic is not None and len(basic) > 0:
                    name_map = dict(zip(basic["ts_code"], basic["name"]))
            except Exception:
                pass
            limit_df = df[
                df.apply(lambda r: r["pct_chg"] >= _limit_pct(str(r["ts_code"])), axis=1)
            ].sort_values("pct_chg", ascending=False).head(5)
            return [
                {
                    "name": name_map.get(row["ts_code"], row["ts_code"].split(".")[0]),
                    "pct": round(float(row["pct_chg"]), 2),
                }
                for _, row in limit_df.iterrows()
            ]
        except Exception as e:
            logger.warning("[Tushare] daily limit fallback failed: %s", e)
            return MOCK_DATA["limit_up_top"]

    return await asyncio.to_thread(_fetch)


# ─── 申万一级行业：分类 / 成分 / 日线（带缓存 + 并发） ───

_sw_classify_cache: dict = {"date": "", "rows": []}
_sw_members_cache: dict = {"date": "", "members": {}}


def _get_sw_classify(pro, trade_date: str) -> list[tuple[str, str]]:
    """申万一级行业分类 [(index_code, industry_name)]，按日缓存"""
    if _sw_classify_cache["date"] == trade_date and _sw_classify_cache["rows"]:
        return _sw_classify_cache["rows"]
    df = pro.index_classify(level="L1", src="SW2021")
    if df is None or len(df) == 0:
        raise RuntimeError("index_classify 返回空")
    rows = list(zip(df["index_code"].tolist(), df["industry_name"].tolist()))
    _sw_classify_cache.update(date=trade_date, rows=rows)
    return rows


def _get_sw_members(pro, trade_date: str) -> dict[str, dict[str, str]]:
    """申万一级行业成分股 {index_code: {ts_code: con_name}}，按日缓存

    注意：index_member 返回的列在不同环境/权限下可能没有 con_name，
    此时用 stock_basic 的 ts_code→name 映射兜底，避免 KeyError 导致领涨股恒为空。
    """
    if _sw_members_cache["date"] == trade_date and _sw_members_cache["members"]:
        return _sw_members_cache["members"]
    members: dict[str, dict[str, str]] = {}
    name_map: dict[str, str] = {}
    try:
        classify = _get_sw_classify(pro, trade_date)
        for index_code, _ in classify:
            try:
                df = pro.index_member(index_code=index_code)
                if df is not None and len(df) > 0:
                    codes = df["con_code"].tolist()
                    if "con_name" in df.columns:
                        names = df["con_name"].tolist()
                    else:
                        # 兜底：index_member 无 con_name 列时，用 stock_basic 名称映射
                        if not name_map:
                            try:
                                basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name")
                                if basic is not None and len(basic) > 0:
                                    name_map = dict(zip(basic["ts_code"], basic["name"]))
                            except Exception as e:
                                logger.warning("[Tushare] stock_basic(name_map) failed: %s", e)
                        names = [name_map.get(c, c.split(".")[0]) for c in codes]
                    members[index_code] = dict(zip(codes, names))
            except Exception as e:
                logger.warning("[Tushare] index_member %s 失败（可能无权限）: %s", index_code, e)
        _sw_members_cache.update(date=trade_date, members=members)
    except Exception as e:
        logger.warning("[Tushare] index_member 整体失败: %s", e)
    return members


def _daily_pct_map(pro, trade_date: str) -> dict[str, float]:
    """当日全市场 ts_code → pct_chg"""
    try:
        df = pro.daily(trade_date=trade_date, fields="ts_code,pct_chg")
        if df is None or len(df) == 0:
            return {}
        return dict(zip(df["ts_code"].tolist(), (float(v) for v in df["pct_chg"].tolist())))
    except Exception as e:
        logger.warning("[Tushare] daily(pct_map) failed: %s", e)
        return {}


def _industry_leader(member_map: dict[str, str], pct_map: dict[str, float]) -> str:
    """行业内当日涨幅最大的成分股名（无数据返回 —）"""
    best_code, best_pct = None, float("-inf")
    for code, name in member_map.items():
        pct = pct_map.get(code)
        if pct is not None and pct > best_pct:
            best_code, best_pct = code, pct
    if best_code is None:
        return "—"
    return member_map[best_code]


async def fetch_sector_daily() -> list[dict]:
    """拉取申万一级行业日线 → SectorItem（并发抓取，含领涨股）"""
    settings = get_settings()
    if not settings.has_tushare:
        return MOCK_DATA["all_sectors"]

    def _prepare():
        pro = _ensure_pro()
        trade_date = _latest_trade_date(pro)
        classify = _get_sw_classify(pro, trade_date)
        dates = _recent_trade_dates(pro, trade_date, 12)
        members = _get_sw_members(pro, trade_date)
        pct_map = _daily_pct_map(pro, trade_date)
        return pro, dates, classify, members, pct_map

    try:
        pro, dates, classify, members, pct_map = await asyncio.to_thread(_prepare)
    except Exception as e:
        logger.warning("[Tushare] sector prepare failed: %s", e)
        return MOCK_DATA["all_sectors"]

    sem = asyncio.Semaphore(5)  # 控制 Tushare 并发，避免触发频率限制

    def _fetch_one(ts_code: str, name: str) -> dict | None:
        try:
            daily_df = pro.sw_daily(ts_code=ts_code, start_date=dates[0], end_date=dates[-1])
            if daily_df is None or len(daily_df) == 0:
                return None
            daily_df = daily_df.sort_values("trade_date")
            latest = daily_df.iloc[-1]
            closes = daily_df["close"].tolist()
            return {
                "name": name,
                "pct": round(float(latest["pct_chg"]), 2),
                "leading": _industry_leader(members.get(ts_code, {}), pct_map),
                "sparkline": _normalize_sparkline(closes[-12:]),
            }
        except Exception as e:
            logger.warning("[Tushare] sw_daily %s 失败: %s", ts_code, e)
            return None

    async def worker(ts_code: str, name: str) -> dict | None:
        async with sem:
            return await asyncio.to_thread(_fetch_one, ts_code, name)

    results = await asyncio.gather(*(worker(c, n) for c, n in classify))
    sectors = [r for r in results if r is not None]
    if not sectors:
        logger.warning("[Tushare] 板块数据为空，回退 mock")
        return MOCK_DATA["all_sectors"]
    return sectors


class TushareProvider(BaseProvider):
    """Tushare 数据源（日级主源；内部自带 mock 兜底与腾讯 HSI 补充）"""

    name = "tushare"

    async def fetch_indices(self) -> list[dict]:
        return await fetch_index_daily()

    async def fetch_breadth(self) -> dict:
        return await fetch_daily_market()

    async def fetch_limit_top(self) -> list[dict]:
        return await fetch_limit_list()

    async def fetch_sectors(self) -> list[dict]:
        return await fetch_sector_daily()

    async def fetch_index_history(self, code: str, days: int) -> list[dict]:
        """单个指数历史日 K 收盘价（升序）—— 期现对比等场景用"""
        ts_code = code.upper()

        def _fetch() -> list[dict]:
            pro = _ensure_pro()
            df = pro.index_daily(ts_code=ts_code, limit=days + 5, fields="trade_date,close")
            if df is None or len(df) == 0:
                raise ProviderError(f"Tushare index_daily {ts_code} 为空")
            df = df.sort_values("trade_date")
            rows = df.tail(days)
            return [
                {"date": _iso_date(str(d)), "close": round(float(c), 2)}
                for d, c in zip(rows["trade_date"], rows["close"])
            ]

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare 指数历史 {ts_code} 失败: {e}")

    async def fetch_futures_main(self, contract: str, days: int) -> list[dict]:
        """中金所股指期货主力连续日线（contract: IF/IH/IM，升序）

        主力判断：fut_mapping 给出每个交易日的主力合约映射，
        再按映射合约取 fut_daily 收盘价拼成连续序列。
        """
        contract = contract.upper()

        def _fetch() -> list[dict]:
            pro = _ensure_pro()
            mapping = pro.fut_mapping(ts_code=f"{contract}.CFX")
            if mapping is None or len(mapping) == 0:
                raise ProviderError(f"Tushare fut_mapping {contract}.CFX 为空")
            mapping = mapping.sort_values("trade_date")
            # 只取今天及之前（映射可能包含未来交易日，fut_daily 尚无数据）
            today = datetime.date.today().strftime("%Y%m%d")
            mapping = mapping[mapping["trade_date"].astype(str) <= today].tail(days)

            start = str(mapping["trade_date"].iloc[0])
            end = str(mapping["trade_date"].iloc[-1])
            contracts = mapping["mapping_ts_code"].unique().tolist()

            # 按合约拉取区间日线（主力合约通常 2~4 个）
            close_by_key: dict[tuple[str, str], float] = {}
            for c in contracts:
                df = pro.fut_daily(ts_code=c, start_date=start, end_date=end, fields="trade_date,close")
                if df is None or len(df) == 0:
                    continue
                for _, r in df.iterrows():
                    close_by_key[(str(r["trade_date"]), c)] = float(r["close"])

            series = []
            for _, r in mapping.iterrows():
                date, c = str(r["trade_date"]), r["mapping_ts_code"]
                close = close_by_key.get((date, c))
                if close is None:
                    continue  # 该日主力合约数据缺失则跳过
                series.append({"date": _iso_date(date), "close": round(close, 2)})
            if not series:
                raise ProviderError(f"Tushare {contract} 主力连续为空")
            return series

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare {contract} 主力连续失败: {e}")

    async def fetch_stock_sparkline(self, code: str) -> list[float]:
        """单只个股近 12 个交易日收盘价 → 归一化 sparkline（自选页分时走势）"""
        from app.services.provider import normalize_ts_code

        ts_code = normalize_ts_code(code)

        def _fetch() -> list[float]:
            pro = _ensure_pro()
            df = pro.daily(ts_code=ts_code, limit=12, fields="trade_date,close")
            if df is None or len(df) == 0:
                raise ProviderError(f"Tushare daily {ts_code} 为空")
            df = df.sort_values("trade_date")  # daily 默认降序，先排序
            return _normalize_sparkline([float(v) for v in df["close"].tolist()])

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare 个股 sparkline {ts_code} 失败: {e}")
