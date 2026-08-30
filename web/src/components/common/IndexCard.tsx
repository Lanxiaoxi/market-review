import type { IndexSnapshot } from "@/types/market";
import { useCountUp } from "@/hooks/useCountUp";
import styles from "./IndexCard.module.css";

const VIEW_W = 132;
const VIEW_H = 30;
const PAD_X = 4;

interface IndexCardProps {
  data: IndexSnapshot;
  /** 入场错峰序号（配合 .mr-enter 使用） */
  index?: number;
}

/** sparkline 归一化值（后端 4–24）→ SVG 折线 + 同色面积填充 */
function buildSparkPath(points: number[]) {
  if (!points.length) return { line: "", area: "", endX: PAD_X, endY: VIEW_H / 2 };
  const n = points.length;
  const step = n > 1 ? (VIEW_W - PAD_X * 2) / (n - 1) : 0;
  const coords = points.map((v, i) => `${PAD_X + i * step},${v}`);
  const first = `${PAD_X},${VIEW_H}`;
  const last = `${PAD_X + (n - 1) * step},${VIEW_H}`;
  return {
    line: coords.join(" "),
    area: `M${first} L${coords.join(" L")} L${last} Z`,
    endX: PAD_X + (n - 1) * step,
    endY: points[n - 1],
  };
}

export default function IndexCard({ data, index = 0 }: IndexCardProps) {
  const dir = data.change > 0 ? "up" : data.change < 0 ? "down" : "flat";
  const dirClass = dir === "up" ? styles.up : dir === "down" ? styles.down : styles.flat;
  const barClass =
    dir === "up" ? styles.barUp : dir === "down" ? styles.barDown : styles.barFlat;
  const color =
    dir === "up" ? "var(--up)" : dir === "down" ? "var(--down)" : "var(--series-base)";
  const sign = dir === "up" ? "+" : "";

  const animatedValue = useCountUp(data.value);
  const { line, area, endX, endY } = buildSparkPath(data.sparkline);

  return (
    <div
      className={`${styles.card} mr-enter`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <span className={`${styles.bar} ${barClass}`} />
      <div className={styles.body}>
        <span className={styles.name}>{data.name}</span>
        <span className={`${styles.value} num`}>
          {animatedValue.toLocaleString("zh-CN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </span>
        <span className={`${styles.change} ${dirClass} num`}>
          {sign}
          {data.change.toFixed(2)}&nbsp;&nbsp;{sign}
          {data.changePct.toFixed(2)}%
        </span>
        {line && (
          <svg
            className={styles.sparkline}
            viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
            fill="none"
            aria-hidden="true"
          >
            {/* 数据面积：可视化语义，非装饰性渐变 */}
            <path d={area} fill={color} fillOpacity="0.1" />
            <polyline
              points={line}
              stroke={color}
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx={endX} cy={endY} r="2.2" fill={color} />
          </svg>
        )}
      </div>
    </div>
  );
}
