"""图表库响应模型"""

from typing import Optional
from pydantic import BaseModel


class ChartLibItemOut(BaseModel):
    id: str
    name: str
    type: str
    pinned: bool


class ChartCreateIn(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    pinned: bool = False


class ChartUpdateIn(BaseModel):
    name: Optional[str] = None
    pinned: Optional[bool] = None