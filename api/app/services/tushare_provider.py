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
from app.services.buckets import DIST_LABELS, bucketize, limit_pct, normalize_sparkline
from app.services.provider import BaseProvider, ProviderError

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


# ─── 指数代码映射（主页指数卡顺序：上证→上证50→沪深300→中证500→创业→科创50→中证1000→中证2000）───
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

# 港股指数用腾讯兜底（Tushare 无港股指数）
HK_INDEX_CODES = ["HSI", "HSTECH"]


def _iso_date(yyyymmdd: str) -> str:
    """20260828 → 2026-08-28"""
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def _ymd(d) -> str:
    """date → 20260828（Tushare 接口日期参数格式）"""
    return d.strftime("%Y%m%d")


def _parse_ymd(v) -> datetime.date | None:
    """20260828 / 2026-08-28 → date；无法解析返回 None"""
    s = str(v).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _f(v) -> float | None:
    """转 float：None / 空 / 非法 / NaN 统一返回 None（落库为 NULL）"""
    if v is None or v == "":
        return None
    try:
        val = float(v)
    except (TypeError, ValueError):
        return None
    return None if val != val else val  # NaN 自检


async def fetch_index_daily() -> list[dict]:
    """拉取 10 张指数卡的日线数据 + sparkline（8 只 Tushare + 恒生指数/恒生科技腾讯兜底）"""
    settings = get_settings()
    if not settings.has_tushare:
        raise ProviderError("未配置 TUSHARE_TOKEN，无法获取真实指数数据")

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
                    "sparkline": normalize_sparkline(closes),
                })
            except Exception as e:
                logger.warning("[Tushare] index_daily %s failed: %s", ts_code, e)
        return results

    indices = await asyncio.to_thread(_fetch)

    # 港股指数（恒生指数/恒生科技）用腾讯兜底（真实日 K 生成 sparkline，失败则跳过该指数）
    for hk_code in HK_INDEX_CODES:
        try:
            from app.services.tencent_provider import fetch_hk_snapshot

            hk = await fetch_hk_snapshot(hk_code)
            if hk:
                indices.append(hk)
        except Exception as e:
            logger.warning("[Tencent] %s 兜底失败: %s", hk_code, e)

    return indices


async def fetch_daily_market() -> dict:
    """拉取全市场日线 → 涨跌家数统计（7 档分布）+ 成交额 + 涨跌停数量"""
    settings = get_settings()
    if not settings.has_tushare:
        raise ProviderError("未配置 TUSHARE_TOKEN，无法获取真实涨跌家数")

    def _fetch():
        pro = _ensure_pro()
        trade_date = _latest_trade_date(pro)
        try:
            df = pro.daily(trade_date=trade_date, fields="ts_code,pct_chg,amount")
            if df is None or len(df) == 0:
                raise ProviderError(f"Tushare daily {trade_date} 为空")

            counts = {label: 0 for label in DIST_LABELS}
            limit_up = limit_down = 0
            for ts_code, pct in zip(df["ts_code"], df["pct_chg"]):
                bucket = bucketize(float(pct), str(ts_code))
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
            raise ProviderError(f"Tushare daily 失败: {e}")

    return await asyncio.to_thread(_fetch)


async def fetch_limit_list() -> list[dict]:
    """拉取涨停 TOP5（优先 limit_list_d，权限不足时用 daily 近似）"""
    settings = get_settings()
    if not settings.has_tushare:
        raise ProviderError("未配置 TUSHARE_TOKEN，无法获取真实涨停榜")

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
                raise ProviderError(f"Tushare daily {trade_date} 为空")
            name_map = {}
            try:
                basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name")
                if basic is not None and len(basic) > 0:
                    name_map = dict(zip(basic["ts_code"], basic["name"]))
            except Exception:
                pass
            limit_df = df[
                df.apply(lambda r: r["pct_chg"] >= limit_pct(str(r["ts_code"])), axis=1)
            ].sort_values("pct_chg", ascending=False).head(5)
            return [
                {
                    "name": name_map.get(row["ts_code"], row["ts_code"].split(".")[0]),
                    "pct": round(float(row["pct_chg"]), 2),
                }
                for _, row in limit_df.iterrows()
            ]
        except ProviderError:
            raise
        except Exception as e:
            logger.warning("[Tushare] daily limit fallback failed: %s", e)
            raise ProviderError(f"Tushare daily limit fallback 失败: {e}")

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
        raise ProviderError("未配置 TUSHARE_TOKEN，无法获取真实行业数据")

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
        raise ProviderError(f"Tushare 行业数据准备失败: {e}")

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
                "sparkline": normalize_sparkline(closes[-12:]),
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
        logger.warning("[Tushare] 板块数据为空")
        raise ProviderError("Tushare 行业板块数据为空")
    return sectors


class TushareProvider(BaseProvider):
    """Tushare 数据源（日级主源；无 token 或接口失败时 raise ProviderError，由注册表降级）"""

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

    async def fetch_limit_counts(self, days: int) -> list[dict]:
        """日线涨停/跌停家数（daily 全市场近似分档，升序）—— THS 不可用时的兜底"""

        def _fetch() -> list[dict]:
            pro = _ensure_pro()
            end = _latest_trade_date(pro)
            dates = _recent_trade_dates(pro, end, days)
            result: list[dict] = []
            for d in dates:
                try:
                    df = pro.daily(trade_date=d, fields="ts_code,pct_chg")
                    if df is None or len(df) == 0:
                        continue
                    up = sum(
                        1
                        for c, p in zip(df["ts_code"], df["pct_chg"])
                        if bucketize(float(p), str(c)) == "涨停"
                    )
                    down = sum(
                        1
                        for c, p in zip(df["ts_code"], df["pct_chg"])
                        if bucketize(float(p), str(c)) == "跌停"
                    )
                    result.append({"date": _iso_date(d), "limit_up": up, "limit_down": down})
                except Exception as e:
                    logger.warning("[Tushare] daily %s 涨跌停计数失败: %s", d, e)
            if not result:
                raise ProviderError("Tushare 涨跌停家数序列为空")
            return result

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare 涨跌停家数失败: {e}")

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
            return normalize_sparkline([float(v) for v in df["close"].tolist()])

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare 个股 sparkline {ts_code} 失败: {e}")

    # ─── 回填专用：返回原始行交给 store 落库 ───

    async def fetch_stock_daily_raw(self, trade_date) -> list[dict]:
        """单个交易日全市场个股日线（1 次请求拿全天 ~5400 行）"""
        settings = get_settings()
        if not settings.has_tushare:
            raise ProviderError("未配置 TUSHARE_TOKEN，无法回填个股日线")

        def _fetch() -> list[dict]:
            pro = _ensure_pro()
            df = pro.daily(
                trade_date=_ymd(trade_date), fields="ts_code,close,pct_chg,amount"
            )
            if df is None or len(df) == 0:
                raise ProviderError(f"Tushare daily {trade_date} 为空")
            return [
                {
                    "ts_code": str(c),
                    "close": _f(v),
                    "pct_chg": _f(p),
                    "amount": _f(a),
                }
                for c, v, p, a in zip(
                    df["ts_code"], df["close"], df["pct_chg"], df["amount"]
                )
            ]

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare 个股日线 {trade_date} 失败: {e}")

    async def fetch_index_range(self, start, end) -> list[dict]:
        """指数日线区间（8 只 A 股指数各 1 次请求 + 2 只港股腾讯兜底）"""
        settings = get_settings()
        if not settings.has_tushare:
            raise ProviderError("未配置 TUSHARE_TOKEN，无法回填指数日线")

        def _fetch() -> list[dict]:
            pro = _ensure_pro()
            rows: list[dict] = []
            for ts_code, (code, name) in INDEX_CODES.items():
                try:
                    df = pro.index_daily(ts_code=ts_code, start_date=_ymd(start), end_date=_ymd(end))
                except Exception as e:
                    logger.warning("[Tushare] index_daily %s 区间失败: %s", ts_code, e)
                    continue
                if df is None or len(df) == 0:
                    continue
                for _, r in df.sort_values("trade_date").iterrows():
                    d = _parse_ymd(r["trade_date"])
                    if d is None:
                        continue
                    rows.append(
                        {
                            "ts_code": ts_code,
                            "code": code,
                            "name": name,
                            "trade_date": d,
                            "close": _f(r["close"]) or 0,
                            "change": _f(r["change"]) or 0,
                            "pct_chg": _f(r["pct_chg"]) or 0,
                            "amount": _f(r.get("amount")),
                        }
                    )
            return rows

        rows = await asyncio.to_thread(_fetch)
        from app.services.tencent_provider import fetch_hk_index_range

        rows.extend(await fetch_hk_index_range(start, end))
        if not rows:
            raise ProviderError(f"Tushare 指数日线区间为空（{start} ~ {end}）")
        return rows

    async def fetch_sector_range(self, start, end) -> list[dict]:
        """申万一级行业日线区间（1 次分类 + 每行业 1 次日线）

        历史区间的领涨股无法低成本还原（需逐日全市场成分股比对），故留空为 "—"；
        当日领涨股由实时域 DOMAIN_SECTORS 提供。
        """
        settings = get_settings()
        if not settings.has_tushare:
            raise ProviderError("未配置 TUSHARE_TOKEN，无法回填行业日线")

        def _fetch() -> list[dict]:
            pro = _ensure_pro()
            classify = _get_sw_classify(pro, _ymd(end))
            rows: list[dict] = []
            for index_code, industry_name in classify:
                try:
                    df = pro.sw_daily(ts_code=index_code, start_date=_ymd(start), end_date=_ymd(end))
                except Exception as e:
                    logger.warning("[Tushare] sw_daily %s 区间失败: %s", index_code, e)
                    continue
                if df is None or len(df) == 0:
                    continue
                for _, r in df.sort_values("trade_date").iterrows():
                    d = _parse_ymd(r["trade_date"])
                    if d is None:
                        continue
                    rows.append(
                        {
                            "sector_code": index_code,
                            "name": industry_name,
                            "trade_date": d,
                            "close": _f(r["close"]) or 0,
                            "pct_chg": _f(r["pct_chg"]) or 0,
                            "leading": "—",
                        }
                    )
            return rows

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare 行业日线区间失败: {e}")

    async def fetch_stock_names(self) -> dict[str, str]:
        """全市场代码 → 名称（1 次 stock_basic 请求，供涨停 TOP5 展示）"""
        settings = get_settings()
        if not settings.has_tushare:
            raise ProviderError("未配置 TUSHARE_TOKEN，无法同步股票名称")

        def _fetch() -> dict[str, str]:
            pro = _ensure_pro()
            basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name")
            if basic is None or len(basic) == 0:
                raise ProviderError("Tushare stock_basic 为空")
            return {str(c): str(n) for c, n in zip(basic["ts_code"], basic["name"])}

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare stock_basic 失败: {e}")

    async def fetch_trade_calendar(self, start, end) -> list:
        """交易日历（1 次 trade_cal 请求，覆盖区间内全部开市日）"""
        settings = get_settings()
        if not settings.has_tushare:
            raise ProviderError("未配置 TUSHARE_TOKEN，无法同步交易日历")

        def _fetch() -> list:
            pro = _ensure_pro()
            df = pro.trade_cal(
                exchange="SSE", start_date=_ymd(start), end_date=_ymd(end), is_open="1"
            )
            if df is None or len(df) == 0:
                raise ProviderError("Tushare trade_cal 为空")
            dates = sorted(d for d in (_parse_ymd(v) for v in df["cal_date"]) if d is not None)
            if not dates:
                raise ProviderError("Tushare trade_cal 日期解析结果为空")
            return dates

        try:
            return await asyncio.to_thread(_fetch)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Tushare trade_cal 失败: {e}")
