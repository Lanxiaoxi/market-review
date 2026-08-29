"""图表库/钉选配置表"""

from typing import Optional
from sqlmodel import SQLModel, Field


class ChartConfig(SQLModel, table=True):
    """图表库 + 钉选配置"""
    __tablename__ = "chart_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    chart_id: str = Field(index=True, max_length=64)       # 图表唯一 ID
    name: str = Field(max_length=64)                        # 图表名称
    chart_type: str = Field(max_length=32)                  # 图表类型标识
    pinned: bool = Field(default=False)                     # 是否钉选
    config_json: str = Field(default="{}", max_length=4096) # 图表配置 JSON