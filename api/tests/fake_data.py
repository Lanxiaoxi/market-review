"""
测试用确定性数据（替代已删除的 mock_data.py）

仅测试环境使用（conftest 注入到 aggregator.fetch_domain），生产代码无任何 mock。
数值与原 mock 一致，保证既有断言（家数自洽、7 档分布等）继续有效。
"""

from app.services.provider import (
    ProviderError,
    DOMAIN_INDICES,
    DOMAIN_BREADTH,
    DOMAIN_LIMIT_UP,
    DOMAIN_SECTORS,
)

INDICES = [
    {"code": "000001", "name": "上证指数", "value": 3356.21, "change": 18.45, "change_pct": 0.55, "sparkline": [24,22,23,18,20,16,17,12,14,9,11,6]},
    {"code": "000016", "name": "上证50", "value": 2625.10, "change": 12.40, "change_pct": 0.47, "sparkline": [23,21,22,17,19,15,16,11,13,8,10,5]},
    {"code": "000300", "name": "沪深300", "value": 3985.20, "change": 23.10, "change_pct": 0.58, "sparkline": [25,24,22,23,17,19,14,16,10,12,7,5]},
    {"code": "000905", "name": "中证500", "value": 6124.88, "change": 35.66, "change_pct": 0.59, "sparkline": [26,23,25,20,21,15,16,10,12,7,8,3]},
    {"code": "399006", "name": "创业板指", "value": 2245.30, "change": 22.18, "change_pct": 1.00, "sparkline": [25,24,22,23,17,19,14,16,10,12,7,5]},
    {"code": "000688", "name": "科创50", "value": 1012.45, "change": -4.32, "change_pct": -0.42, "sparkline": [6,9,7,12,11,16,15,19,17,22,21,26]},
    {"code": "000852", "name": "中证1000", "value": 6890.42, "change": -28.15, "change_pct": -0.41, "sparkline": [8,6,10,9,14,13,18,16,20,19,24,27]},
    {"code": "932000", "name": "中证2000", "value": 2415.80, "change": -18.90, "change_pct": -0.78, "sparkline": [9,7,11,10,15,14,19,17,22,21,25,28]},
    {"code": "HSI", "name": "恒生指数", "value": 19876.54, "change": 142.30, "change_pct": 0.72, "sparkline": [24,22,23,18,20,16,17,12,14,9,11,6]},
    {"code": "HSTECH", "name": "恒生科技", "value": 4605.15, "change": 33.40, "change_pct": 0.73, "sparkline": [23,21,22,16,18,13,15,9,11,6,8,3]},
]

BREADTH = {
    "up": 3186, "down": 1652, "flat": 208,
    "up_pct": 63.0, "down_pct": 33.0, "flat_pct": 4.0,
    "turnover": "1.26万亿",
    "limit_up_count": 48, "limit_down_count": 6,
    "trade_date": None,
    "dist": [
        {"label": "涨停", "value": 48},
        {"label": "涨2-10%", "value": 380},
        {"label": "涨0-2%", "value": 2758},
        {"label": "平盘", "value": 208},
        {"label": "跌0-2%", "value": 1426},
        {"label": "跌2-10%", "value": 220},
        {"label": "跌停", "value": 6},
    ],
}

LIMIT_UP_TOP = [
    {"name": "寒武纪", "pct": 20.01},
    {"name": "沪电股份", "pct": 10.00},
    {"name": "中科曙光", "pct": 10.00},
    {"name": "工业富联", "pct": 10.00},
    {"name": "紫光股份", "pct": 10.00},
]

SECTORS = [
    {"name": "电子", "pct": 2.86, "leading": "寒武纪", "sparkline": [18,16,17,13,14,10,11,7,9,6,5]},
    {"name": "计算机", "pct": 2.41, "leading": "中科曙光", "sparkline": [19,17,18,14,15,11,12,8,10,7,6]},
    {"name": "汽车", "pct": 1.92, "leading": "比亚迪", "sparkline": [20,18,19,16,17,13,14,11,12,9,8]},
    {"name": "医药生物", "pct": 1.55, "leading": "迈瑞医疗", "sparkline": [17,15,16,12,13,9,10,6,8,5,4]},
    {"name": "通信", "pct": 1.28, "leading": "中兴通讯", "sparkline": [16,14,15,11,12,8,9,5,7,4,3]},
    {"name": "国防军工", "pct": 1.12, "leading": "中航光电", "sparkline": [15,13,14,10,11,7,8,4,6,3,2]},
    {"name": "电力设备", "pct": 0.95, "leading": "宁德时代", "sparkline": [14,12,13,9,10,6,7,3,5,2,1]},
    {"name": "机械设备", "pct": 0.78, "leading": "汇川技术", "sparkline": [13,11,12,8,9,5,6,2,4,1,0]},
    {"name": "传媒", "pct": -0.45, "leading": "分众传媒", "sparkline": [9,11,10,14,13,17,16,20,19,22,23]},
    {"name": "食品饮料", "pct": -0.88, "leading": "贵州茅台", "sparkline": [8,10,9,13,12,16,15,19,18,21,22]},
    {"name": "公用事业", "pct": -1.02, "leading": "长江电力", "sparkline": [7,9,8,12,11,15,14,18,17,20,21]},
    {"name": "银行", "pct": -1.32, "leading": "招商银行", "sparkline": [6,8,7,11,10,14,13,17,16,19,20]},
]


async def fake_fetch_domain(domain: str, *args, **kwargs):
    """替换 aggregator.fetch_domain：按数据域返回确定性数据"""
    if domain == DOMAIN_INDICES:
        return INDICES
    if domain == DOMAIN_BREADTH:
        return BREADTH
    if domain == DOMAIN_LIMIT_UP:
        return LIMIT_UP_TOP
    if domain == DOMAIN_SECTORS:
        return SECTORS
    raise ProviderError(f"测试数据源不支持数据域: {domain}")
