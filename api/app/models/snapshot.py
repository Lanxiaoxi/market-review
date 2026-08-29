"""每日收盘快照表"""

from typing import Optional
from datetime import date, datetime
from sqlmodel import SQLModel, Field


class DailySnapshot(SQLModel, table=True):
    """每日收盘快照（行情全量）"""
    __tablename__ = "daily_snapshot"

    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_date: date = Field(index=True, unique=True)    # 快照日期
    data_json: str = Field(max_length=65536)                # 全量 JSON（OverviewData）
    created_at: datetime = Field(default_factory=datetime.now)