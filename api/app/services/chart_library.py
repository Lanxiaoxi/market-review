"""图表库种子：确保内置图表在库中存在（幂等，仅补缺不覆盖）"""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.chart_config import ChartConfig

# 内置图表清单：新增图表时在此登记，前端自定义图表页据此渲染对应卡片
KNOWN_CHARTS: list[dict] = [
    {"chart_id": "bar-dist", "name": "涨跌家数分布", "chart_type": "barDist"},
    {"chart_id": "turnover-intraday", "name": "成交额分时", "chart_type": "turnoverIntraday"},
    {"chart_id": "if-basis", "name": "股指期现对比", "chart_type": "ifBasis"},
    {"chart_id": "limit-count", "name": "涨跌停家数", "chart_type": "limitCount"},
    {"chart_id": "breadth-series", "name": "市场宽度", "chart_type": "breadthSeries"},
]


async def seed_chart_library(session: AsyncSession) -> None:
    """启动时调用：chart_id 不存在才插入；已存在的内置图表同步显示名（不覆盖钉选状态）"""
    for k in KNOWN_CHARTS:
        row = (
            await session.execute(
                select(ChartConfig).where(ChartConfig.chart_id == k["chart_id"])
            )
        ).scalar_one_or_none()
        if row is None:
            session.add(
                ChartConfig(
                    chart_id=k["chart_id"],
                    name=k["name"],
                    chart_type=k["chart_type"],
                    pinned=False,
                )
            )
        elif row.name != k["name"]:
            row.name = k["name"]  # 内置图表改名时同步存量行
    await session.commit()
