"""
数据清洗/归一/分档 —— 将 provider 原始数据聚合成 schemas 所需结构

数据源解耦：聚合层不直接依赖任何具体数据源，只通过 provider 注册表
（fetch_domain）按「数据域」取归一化数据，换源/加源不影响本层与路由。

L2 优先：传入 session 时按「数据是否已定格」决定取数路径
- 已定格（收盘后 / 历史日）→ 先读本地库，命中即返回，零回源
- 盘中 → 先取实时源，本地库仅作兜底
session 为 None 时退化为纯 provider 取数（兼容不落库的调用场景）。
"""

import datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import SHANGHAI_TZ
from app.schemas.overview import (
    OverviewOut,
    IndexSnapshotOut,
    MarketBreadthOut,
    LimitUpStockOut,
    DistBucketOut,
    SectorItemOut,
)
from app.services import store
from app.services.provider import (
    ProviderError,
    fetch_domain,
    DOMAIN_INDICES,
    DOMAIN_BREADTH,
    DOMAIN_LIMIT_UP,
    DOMAIN_SECTORS,
)


async def _resolve(session, trade_date, local_reader, domain, *args):
    """按数据定格状态选路：定格走本地，盘中走实时（本地兜底）"""
    if session is None or trade_date is None:
        return await fetch_domain(domain, *args)

    if store.is_settled(trade_date):
        data = await local_reader(session, trade_date)
        if data is not None:
            return data
        return await fetch_domain(domain, *args)

    try:
        return await fetch_domain(domain, *args)
    except ProviderError:
        data = await local_reader(session, trade_date)
        if data is None:
            raise
        return data


def _sector_out(s: dict) -> SectorItemOut:
    return SectorItemOut(
        name=s["name"],
        pct=s["pct"],
        leading=s.get("leading", "—"),
        sparkline=s["sparkline"],
    )


async def build_overview(session: AsyncSession | None = None) -> OverviewOut:
    """按域取数并聚合成 OverviewOut（传入 session 时优先读 L2 持久层）"""
    trade_date = await store.latest_trade_date(session) if session is not None else None

    indices_raw = await _resolve(
        session, trade_date, store.read_indices, DOMAIN_INDICES
    )
    breadth_raw = await _resolve(
        session, trade_date, store.read_breadth, DOMAIN_BREADTH
    )
    limit_raw = await _resolve(
        session, trade_date, store.read_limit_top, DOMAIN_LIMIT_UP
    )

    indices = [
        IndexSnapshotOut(
            code=i["code"],
            name=i["name"],
            value=i["value"],
            change=i["change"],
            change_pct=i["change_pct"],
            sparkline=i["sparkline"],
        )
        for i in indices_raw
    ]

    # 分布桶（7 档）为真实统计来源；涨停/跌停家数取桶值，避免与 TOP5 列表长度混淆
    dist_raw = breadth_raw.get("dist", [])
    dist = [DistBucketOut(label=d["label"], value=d["value"]) for d in dist_raw]
    _bucket_value = lambda label: next((d.value for d in dist if d.label == label), 0)

    breadth = MarketBreadthOut(
        up=breadth_raw["up"],
        down=breadth_raw["down"],
        flat=breadth_raw["flat"],
        up_pct=breadth_raw["up_pct"],
        down_pct=breadth_raw["down_pct"],
        flat_pct=breadth_raw["flat_pct"],
        turnover=breadth_raw["turnover"],
        limit_up_count=_bucket_value("涨停") or breadth_raw.get("limit_up_count", len(limit_raw)),
        limit_down_count=_bucket_value("跌停") or breadth_raw.get("limit_down_count", 0),
        limit_up_top=[LimitUpStockOut(**lt) for lt in limit_raw],
        dist=dist,
    )

    # 行业 TOP5 从真实 sector 数据取
    all_sectors = await _resolve(
        session, trade_date, store.read_sectors, DOMAIN_SECTORS
    )
    sorted_desc = sorted(all_sectors, key=lambda s: s["pct"], reverse=True)
    sorted_asc = sorted(all_sectors, key=lambda s: s["pct"])

    sectors_up = [_sector_out(s) for s in sorted_desc[:5]]
    sectors_down = [_sector_out(s) for s in sorted_asc[:5]]

    # 日期/收盘状态统一用上海时区；数据日期优先取行情交易日（周末/节假日与数据一致）
    now = datetime.datetime.now(SHANGHAI_TZ)
    today = now.date()
    data_date = datetime.date.fromisoformat(breadth_raw.get("trade_date") or today.isoformat())
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    is_closed = data_date < today or now.hour >= 15

    return OverviewOut(
        date=data_date.isoformat(),
        weekday=weekdays[data_date.weekday()],
        closed=is_closed,
        indices=indices,
        breadth=breadth,
        sectors_up=sectors_up,
        sectors_down=sectors_down,
    )


async def build_sectors(session: AsyncSession | None = None) -> list[SectorItemOut]:
    """聚合行业板块排名（传入 session 时优先读 L2 持久层）"""
    trade_date = await store.latest_trade_date(session) if session is not None else None
    all_sectors = await _resolve(
        session, trade_date, store.read_sectors, DOMAIN_SECTORS
    )
    return [_sector_out(s) for s in all_sectors]
