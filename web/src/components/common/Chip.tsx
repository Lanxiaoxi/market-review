import styles from "./Chip.module.css";

interface ChipProps {
  text: string;
  dotColor?: string;
  /** 持续状态（如「交易中」）：状态点呼吸动效 */
  live?: boolean;
}

export default function Chip({ text, dotColor, live = false }: ChipProps) {
  return (
    <span className={styles.chip}>
      <span
        className={`${styles.dot} ${live ? styles.live : ""}`}
        style={dotColor ? { background: dotColor } : undefined}
      />
      <span className={styles.text}>{text}</span>
    </span>
  );
}