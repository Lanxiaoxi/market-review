"""图表库种子：确保内置图表在库中存在（幂等，仅补缺不覆盖）"""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.chart_config import ChartConfig

# 内置图表清单：新增图表时在此登记，前端自定义图表页据此渲染对应卡片
KNOWN_CHARTS: list[dict] = [
    {"chart_id": "bar-dist", "name": "涨跌家数分布", "chart_type": "barDist"},
    {"chart_id": "turnover-intraday", "name": "成交额分时", "chart_type": "turnoverIntraday"},
    {"chart_id": "if-basis", "name": "沪深300期现对比", "chart_type": "ifBasis"},
]


async def seed_chart_library(session: AsyncSession) -> None:
    """启动时调用：chart_id 不存在才插入（不覆盖用户已钉选状态）"""
    for k in KNOWN_CHARTS:
        dup = await session.execute(
            select(ChartConfig).where(ChartConfig.chart_id == k["chart_id"])
        )
        if dup.scalar_one_or_none() is None:
            session.add(
                ChartConfig(
                    chart_id=k["chart_id"],
                    name=k["name"],
                    chart_type=k["chart_type"],
                    pinned=False,
                )
            )
    await session.commit()
