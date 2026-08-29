/* 修正检测：取 L 命令最多的 path（即折线本体） */
import * as echarts from "echarts";

const labels242 = Array.from({ length: 242 }, (_, i) => {
  const m = i <= 120 ? 9 * 60 + 30 + i : 13 * 60 + (i - 121);
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
});
const data242 = Array.from({ length: 242 }, (_, i) => Math.sin(i / 40) * 100);

const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 928, height: 216 });
chart.setOption({
  xAxis: { type: "category", data: labels242, boundaryGap: false },
  yAxis: { type: "value" },
  series: [{ type: "line", data: data242, symbol: "none", smooth: false }],
});
const svg = chart.renderToSVGString();
chart.dispose();

const paths = svg.match(/<path[^>]*d="[^"]*"/g) || [];
let best = "", bestCount = 0;
for (const p of paths) {
  const d = p.match(/d="([^"]*)"/)[1];
  const l = (d.match(/L/g) || []).length;
  if (l > bestCount) { bestCount = l; best = d; }
}
console.log("折线 path 点数:", bestCount + 1, "(L 命令数:", bestCount, ")");
const xs = new Set();
for (const m of best.matchAll(/[ML](-?\d+\.?\d*) ?, ?(-?\d+\.?\d*)/g)) xs.add(Math.round(parseFloat(m[1])));
console.log("不同 x 坐标数:", xs.size);
