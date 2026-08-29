"""
涨跌幅分档 + sparkline 归一化

原 tushare_provider / ths_provider 各维护一份实现（语义相同但代码重复），
L2 持久层聚合也要用同一套分档规则，故抽为共享模块——避免「本地算的和 API 拉的不一致」。
"""

DIST_LABELS = ["涨停", "涨2-10%", "涨0-2%", "平盘", "跌0-2%", "跌2-10%", "跌停"]


def limit_pct(code: str) -> float:
    """按板块返回近似涨停/跌停阈值（主板 10%、创业/科创 20%、北交所 30%）

    略低于理论值（9.8 / 19.8 / 29.8）以容忍价格精度误差。
    """
    code = str(code)
    if code.startswith(("300", "301", "688")):
        return 19.8
    if code.startswith(("4", "8", "92")):
        return 29.8
    return 9.8


def bucketize(pct: float, code: str) -> str:
    """把涨跌幅归入 7 档分布区间"""
    th = limit_pct(code)
    if pct >= th:
        return "涨停"
    if pct <= -th:
        return "跌停"
    if pct >= 2:
        return "涨2-10%"
    if pct <= -2:
        return "跌2-10%"
    if pct > 0:
        return "涨0-2%"
    if pct < 0:
        return "跌0-2%"
    return "平盘"


def normalize_sparkline(values: list[float], target_min=4, target_max=24) -> list[float]:
    """将原始收盘价归一化到 sparkline 的 y 坐标范围"""
    if not values:
        return [14] * 12
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [14] * len(values)
    return [target_max - (v - vmin) / (vmax - vmin) * (target_max - target_min) for v in values]
