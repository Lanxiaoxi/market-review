"""
数据清洗/归一/分档 —— 将 provider 原始数据聚合成 schemas 所需结构
"""

import datetime

from app.config import SHANGHAI_TZ
from app.schemas.overview import (
    OverviewOut,
    IndexSnapshotOut,
    MarketBreadthOut,
    LimitUpStockOut,
    DistBucketOut,
    SectorItemOut,
)


async def build_overview() -> OverviewOut:
    """
    聚合 tushare + tencent providers → OverviewOut
    """
    from app.services.tushare_provider import (
        fetch_index_daily,
        fetch_daily_market,
        fetch_limit_list,
        fetch_sector_daily,
    )

    indices_raw = await fetch_index_daily()
    breadth_raw = await fetch_daily_market()
    limit_raw = await fetch_limit_list()

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
    all_sectors = await fetch_sector_daily()
    sorted_desc = sorted(all_sectors, key=lambda s: s["pct"], reverse=True)
    sorted_asc = sorted(all_sectors, key=lambda s: s["pct"])

    sectors_up = [
        SectorItemOut(
            name=s["name"],
            pct=s["pct"],
            leading=s.get("leading", "—"),
            sparkline=s["sparkline"],
        )
        for s in sorted_desc[:5]
    ]
    sectors_down = [
        SectorItemOut(
            name=s["name"],
            pct=s["pct"],
            leading=s.get("leading", "—"),
            sparkline=s["sparkline"],
        )
        for s in sorted_asc[:5]
    ]

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


async def build_sectors() -> list[SectorItemOut]:
    """聚合申万一级行业排名"""
    from app.services.tushare_provider import fetch_sector_daily

    all_sectors = await fetch_sector_daily()
    return [
        SectorItemOut(
            name=s["name"],
            pct=s["pct"],
            leading=s.get("leading", "—"),
            sparkline=s["sparkline"],
        )
        for s in all_sectors
    ]
