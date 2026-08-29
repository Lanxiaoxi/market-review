"""检查 /api/intraday 数据质量：三条线的长度、时间连续性、数值合理性"""
import json
import urllib.request

url = "http://127.0.0.1:8000/api/intraday?codes=sh000001,sh000300,sz399006"
with urllib.request.urlopen(url, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))

for code, series in data["codes"].items():
    times, prices = series["times"], series["prices"]
    amounts = series.get("amounts", [])
    print(f"=== {code} ===")
    print(f"  点数: {len(times)}  时间: {times[0] if times else '-'} ~ {times[-1] if times else '-'}")
    print(f"  prices: {len(prices)}  首={prices[0] if prices else '-'} 末={prices[-1] if prices else '-'}  min={min(prices) if prices else '-'} max={max(prices) if prices else '-'}")
    print(f"  amounts: {len(amounts)}  首={amounts[0] if amounts else '-'} 末={amounts[-1] if amounts else '-'}")
    # 时间连续性检查：应 09:30→11:30、13:00→15:00
    if len(times) > 2:
        gap = sum(
            1 for i in range(1, len(times))
            if times[i] == times[i - 1]  # 重复时间
        )
        print(f"  重复时间戳数: {gap}")
    # 价格突变检查（相邻差超过 1% 的次数）
    if len(prices) > 2:
        jumps = sum(
            1 for i in range(1, len(prices))
            if abs(prices[i] - prices[i - 1]) / prices[i - 1] > 0.01
        )
        print(f"  相邻涨跌>1% 的次数: {jumps}")
