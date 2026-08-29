import type { IndexSnapshot } from "@/types/market";
import styles from "./IndexCard.module.css";

interface IndexCardProps {
  data: IndexSnapshot;
}

export default function IndexCard({ data }: IndexCardProps) {
  // 三态：涨红 / 跌绿 / 平盘中性（边框高亮与文字、sparkline 共用同一判定）
  const dir = data.change > 0 ? "up" : data.change < 0 ? "down" : "flat";
  const dirClass = dir === "up" ? styles.up : dir === "down" ? styles.down : styles.flat;
  const cardClass = dir === "up" ? styles.cardUp : dir === "down" ? styles.cardDown : "";
  const sparkColor = dir === "up" ? "var(--up)" : dir === "down" ? "var(--down)" : "var(--series-base)";
  const sign = dir === "up" ? "+" : "";

  return (
    <div className={`${styles.card} ${cardClass}`.trim()}>
      <span className={styles.name}>{data.name}</span>
      <span className={`${styles.value} num`}>{data.value.toLocaleString("zh-CN")}</span>
      <span className={`${styles.change} ${dirClass} num`}>
        {sign}
        {data.change.toFixed(2)}&nbsp;&nbsp;{sign}
        {data.changePct.toFixed(2)}%
      </span>
      <svg className={styles.sparkline} viewBox="0 0 134 28" fill="none">
        <polyline
          points={data.sparkline.map((v, i) => `${2 + i * 11},${v}`).join(" ")}
          stroke={sparkColor}
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}