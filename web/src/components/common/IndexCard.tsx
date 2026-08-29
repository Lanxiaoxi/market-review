import type { IndexSnapshot } from "@/types/market";
import styles from "./IndexCard.module.css";

interface IndexCardProps {
  data: IndexSnapshot;
}

export default function IndexCard({ data }: IndexCardProps) {
  const isUp = data.change >= 0;
  const dirClass = isUp ? styles.up : styles.down;
  const sign = isUp ? "+" : "";
  const pctSign = isUp ? "+" : "";

  return (
    <div className={styles.card}>
      <span className={styles.name}>{data.name}</span>
      <span className={`${styles.value} num`}>{data.value.toLocaleString("zh-CN")}</span>
      <span className={`${styles.change} ${dirClass} num`}>
        {sign}
        {data.change.toFixed(2)}&nbsp;&nbsp;{pctSign}
        {data.changePct.toFixed(2)}%
      </span>
      <svg className={styles.sparkline} viewBox="0 0 134 28" fill="none">
        <polyline
          points={data.sparkline.map((v, i) => `${2 + i * 11},${v}`).join(" ")}
          stroke={isUp ? "var(--up)" : "var(--down)"}
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}