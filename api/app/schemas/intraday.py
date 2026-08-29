"""盘中分时数据响应模型"""

from pydantic import BaseModel


class IntradaySeriesOut(BaseModel):
    times: list[str]        # ["09:30", "09:31", ...]
    prices: list[float]     # 分钟收盘价
    amounts: list[float]    # 累计成交额（元）


class IntradayOut(BaseModel):
    codes: dict[str, IntradaySeriesOut]   # key = 腾讯代码，如 sh000001
