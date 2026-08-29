"""
Mock 数据层 —— 与前端 MOCK_OVERVIEW 完全对齐
无 Tushare Token 时使用，确保 API 可独立运行
"""

MOCK_DATA: dict = {
    "indices": [
        {"code": "000001", "name": "上证指数", "value": 3356.21, "change": 18.45, "change_pct": 0.55, "sparkline": [24,22,23,18,20,16,17,12,14,9,11,6]},
        {"code": "399001", "name": "深证成指", "value": 10842.67, "change": 86.12, "change_pct": 0.80, "sparkline": [26,23,25,20,21,15,16,10,12,7,8,3]},
        {"code": "399006", "name": "创业板指", "value": 2245.30, "change": 22.18, "change_pct": 1.00, "sparkline": [25,24,22,23,17,19,14,16,10,12,7,5]},
        {"code": "000688", "name": "科创50", "value": 1012.45, "change": -4.32, "change_pct": -0.42, "sparkline": [6,9,7,12,11,16,15,19,17,22,21,26]},
        {"code": "000300", "name": "沪深300", "value": 3985.20, "change": 23.10, "change_pct": 0.58, "sparkline": [25,24,22,23,17,19,14,16,10,12,7,5]},
        {"code": "000905", "name": "中证500", "value": 6124.88, "change": 35.66, "change_pct": 0.59, "sparkline": [26,23,25,20,21,15,16,10,12,7,8,3]},
        {"code": "000852", "name": "中证1000", "value": 6890.42, "change": -28.15, "change_pct": -0.41, "sparkline": [8,6,10,9,14,13,18,16,20,19,24,27]},
        {"code": "HSI", "name": "恒生指数", "value": 19876.54, "change": 142.30, "change_pct": 0.72, "sparkline": [24,22,23,18,20,16,17,12,14,9,11,6]},
    ],
    "breadth": {
        "up": 3186, "down": 1652, "flat": 208,
        "up_pct": 63.0, "down_pct": 33.0, "flat_pct": 4.0,
        "turnover": "1.26万亿",
        "limit_up_count": 48, "limit_down_count": 6,
        "trade_date": None,  # mock 模式由 aggregator 填充上海时区当日
        "dist": [
            {"label": "涨停", "value": 48},
            {"label": "涨2-10%", "value": 380},
            {"label": "涨0-2%", "value": 2758},
            {"label": "平盘", "value": 208},
            {"label": "跌0-2%", "value": 1426},
            {"label": "跌2-10%", "value": 220},
            {"label": "跌停", "value": 6},
        ],
    },
    "limit_up_top": [
        {"name": "寒武纪", "pct": 20.01},
        {"name": "沪电股份", "pct": 10.00},
        {"name": "中科曙光", "pct": 10.00},
        {"name": "工业富联", "pct": 10.00},
        {"name": "紫光股份", "pct": 10.00},
    ],
    "sectors_up": [
        {"name": "半导体", "pct": 2.86, "leading": "寒武纪", "sparkline": [18,16,17,13,14,10,11,7,9,6,5]},
        {"name": "消费电子", "pct": 2.41, "leading": "立讯精密", "sparkline": [19,17,18,14,15,11,12,8,9,7,6]},
        {"name": "汽车零部件", "pct": 1.92, "leading": "汇川技术", "sparkline": [20,18,19,16,17,13,14,11,12,9,8]},
        {"name": "医疗服务", "pct": 1.55, "leading": "迈瑞医疗", "sparkline": [17,15,16,12,13,9,10,6,8,5,4]},
        {"name": "通信设备", "pct": 1.28, "leading": "中兴通讯", "sparkline": [16,14,15,11,12,8,9,5,7,4,3]},
    ],
    "sectors_down": [
        {"name": "煤炭", "pct": -1.84, "leading": "中国神华", "sparkline": [7,9,8,12,11,15,14,18,17,20,21]},
        {"name": "银行", "pct": -1.32, "leading": "招商银行", "sparkline": [6,8,7,11,10,14,13,17,16,19,20]},
        {"name": "房地产", "pct": -0.95, "leading": "万科A", "sparkline": [8,10,9,13,12,16,15,19,18,21,22]},
        {"name": "钢铁", "pct": -0.88, "leading": "宝钢股份", "sparkline": [9,11,10,14,13,17,16,20,19,22,23]},
        {"name": "电力", "pct": -0.62, "leading": "长江电力", "sparkline": [10,12,11,15,14,18,17,21,20,23,24]},
    ],
    "intraday_points": [132, 117, 142, 127, 104, 110, 97, 90, 94, 77],
    "all_sectors": [
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
        {"name": "煤炭", "pct": -1.84, "leading": "中国神华", "sparkline": [5,7,6,10,9,13,12,16,15,18,19]},
    ],
}